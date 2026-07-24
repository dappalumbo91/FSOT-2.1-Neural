"""
Local Obsidian "second brain" export of the FSOT genetic neural network.

100% offline / local:
  - Writes Markdown notes + wikilinks to a folder on disk
  - No HTTP servers, no cloud sync, no web APIs, no remote plugins
  - Open the folder as a vault in the Obsidian *desktop* app (local graph)
  - Or browse the .md files in any editor — structure is plain text

Vault layout (second-brain style):
  00_Home.md                 — entry / MOC
  01_Maps/                   — maps of content
  02_Neurons/N###.md         — one note per unit (genotype + links)
  03_Genes/                  — channel gene notes
  04_Synapses/               — optional strong-edge notes
  05_Dynamics/               — run metrics (if provided)
  06_Atlas/                  — spin/charge cluster hubs
  .obsidian/app.json         — minimal local app prefs (no community plugins)
"""

from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch

from .genetic_genotype import NeuronGenotype, CHANNEL_GENE_ORFS, CHANNEL_ROLES
from .genetic_network import GeneticNetworkConfig, GeneticNeuralNetwork
from .paths import ARTIFACTS, ROOT


@dataclass
class ObsidianExportConfig:
    """Local export knobs — all filesystem-side."""

    n_units: int = 48
    # Graph readability: only wikilink strongest edges (dense W is unreadable)
    top_k_out: int = 6  # strongest outgoing synapses per neuron
    top_k_in: int = 4  # strongest incoming listed on note
    min_abs_w: float = 0.05  # drop near-zero after normalize
    write_synapse_notes: bool = False  # True → one note per kept edge (heavy)
    max_synapse_notes: int = 200
    connectivity: str = "genetic_sparse"
    sparse_keep: float = 0.12
    seed: int = 42
    run_dynamics: bool = True
    dynamics_steps: int = 400
    device: str = "cpu"
    # Vault root: default under project artifacts (fully local)
    vault_name: str = "FSOT_Neural_Second_Brain"


def default_vault_root(name: str = "FSOT_Neural_Second_Brain") -> Path:
    return ARTIFACTS / "obsidian_vaults" / name


def _safe_tag(s: str) -> str:
    return (
        str(s)
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace(".", "_")
    )


def _neuron_title(unit_id: int) -> str:
    return f"N{unit_id:03d}"


def _gene_title(name: str) -> str:
    return f"Gene_{name}"


def _cluster_title(kind: str, bucket: str) -> str:
    return f"Cluster_{kind}_{bucket}"


def _spin_bucket(spin: float) -> str:
    if spin > 0.15:
        return "purine_high"
    if spin < -0.15:
        return "pyrimidine_high"
    return "balanced"


def _charge_bucket(q: float) -> str:
    if q > 0.5:
        return "cationic"
    if q < -0.5:
        return "anionic"
    return "neutral"


def _dominant_channel(ph: Dict[str, float]) -> str:
    ranking = {
        "SCN": ph.get("scn_expression", 0.0),
        "KCN": ph.get("kcn_expression", 0.0),
        "CACNA": ph.get("cacna_expression", 0.0),
        "LEAK": ph.get("leak_expression", 0.0),
    }
    return max(ranking, key=ranking.get)


def _yaml_frontmatter(fields: Dict[str, Any]) -> str:
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    lines.append(f'{k}: "{v}"')
                else:
                    lines.append(f"{k}: {v:.6g}")
            else:
                lines.append(f"{k}: {v}")
        elif isinstance(v, list):
            lines.append(f"{k}: [{', '.join(json.dumps(x) for x in v)}]")
        else:
            # quote strings safely
            s = str(v).replace('"', '\\"')
            lines.append(f'{k}: "{s}"')
    lines.append("---")
    return "\n".join(lines)


def _wikilink(title: str, alias: Optional[str] = None) -> str:
    if alias:
        return f"[[{title}|{alias}]]"
    return f"[[{title}]]"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _select_edges(
    W: torch.Tensor,
    top_k_out: int,
    min_abs_w: float,
) -> List[Tuple[int, int, float]]:
    """
    Keep strongest |W| outgoing edges per pre-synaptic unit.
    Returns list of (post, pre, w) matching W[post, pre].
    """
    n = W.shape[0]
    edges: List[Tuple[int, int, float]] = []
    Wc = W.detach().cpu()
    for pre in range(n):
        col = Wc[:, pre]
        abs_col = col.abs()
        # mask self
        abs_col = abs_col.clone()
        abs_col[pre] = 0.0
        k = min(top_k_out, n - 1)
        if k <= 0:
            continue
        vals, idx = torch.topk(abs_col, k=k)
        for v, post in zip(vals.tolist(), idx.tolist()):
            if v < min_abs_w:
                continue
            w = float(col[int(post)].item())
            edges.append((int(post), int(pre), w))
    return edges


def build_obsidian_vault(
    vault_root: Optional[Path] = None,
    cfg: Optional[ObsidianExportConfig] = None,
    gnet: Optional[GeneticNeuralNetwork] = None,
    dynamics: Optional[Dict[str, Any]] = None,
    clean: bool = True,
) -> Dict[str, Any]:
    """
    Materialize a local Obsidian vault from the genetic network.

    Returns paths + edge stats. Never opens a network socket.
    """
    cfg = cfg or ObsidianExportConfig()
    vault_root = Path(vault_root) if vault_root else default_vault_root(cfg.vault_name)
    vault_root = vault_root.resolve()

    if clean and vault_root.exists():
        # Only wipe if it looks like our vault (safety)
        marker = vault_root / ".fsot_vault_marker"
        if marker.is_file() or not any(vault_root.iterdir()):
            shutil.rmtree(vault_root)
        else:
            # Don't destroy unknown folders
            raise FileExistsError(
                f"Vault path exists and is not an FSOT vault marker: {vault_root}. "
                "Pass clean=False or choose another path."
            )

    vault_root.mkdir(parents=True, exist_ok=True)

    # --- network (local compute only) ---
    if gnet is None:
        gcfg = GeneticNetworkConfig(
            n_units=cfg.n_units,
            connectivity=cfg.connectivity,
            sparse_keep=cfg.sparse_keep,
            seed=cfg.seed,
            diversity=True,
        )
        gnet = GeneticNeuralNetwork(gcfg, device=cfg.device)

    genotypes = gnet.genotypes
    n = len(genotypes)
    W = gnet.W
    edges = _select_edges(W, cfg.top_k_out, cfg.min_abs_w)

    # adjacency helpers
    out_map: Dict[int, List[Tuple[int, float]]] = {i: [] for i in range(n)}
    in_map: Dict[int, List[Tuple[int, float]]] = {i: [] for i in range(n)}
    for post, pre, w in edges:
        out_map[pre].append((post, w))
        in_map[post].append((pre, w))
    for i in range(n):
        out_map[i].sort(key=lambda x: abs(x[1]), reverse=True)
        in_map[i].sort(key=lambda x: abs(x[1]), reverse=True)

    # optional dynamics (local torch)
    dyn = dynamics
    rates: List[float] = [0.0] * n
    if dyn is None and cfg.run_dynamics:
        hist = gnet.run(cfg.dynamics_steps, external_pattern="fi_step", record=True)
        rates = hist["firing_rate_Hz"].detach().cpu().tolist()
        dyn = gnet.dynamics_report(hist)
        dyn["structure"] = gnet.structure_report()
    elif dyn is None:
        dyn = {"structure": gnet.structure_report()}

    generated = datetime.now(timezone.utc).isoformat()

    # ---------- marker + minimal .obsidian (local only) ----------
    _write(
        vault_root / ".fsot_vault_marker",
        "FSOT-2.1-Neural local Obsidian vault\n"
        "offline=true\n"
        "no_server=true\n"
        f"generated_at={generated}\n",
    )
    # Minimal app config — no community plugins, no account features
    _write(
        vault_root / ".obsidian" / "app.json",
        json.dumps(
            {
                "promptDelete": True,
                "alwaysUpdateLinks": True,
                "newFileLocation": "folder",
                "newFileFolderPath": "02_Neurons",
                "attachmentFolderPath": "99_Attachments",
                "showLineNumber": False,
                "strictLineBreaks": False,
            },
            indent=2,
        )
        + "\n",
    )
    _write(
        vault_root / ".obsidian" / "appearance.json",
        json.dumps({"baseFontSize": 16}, indent=2) + "\n",
    )
    _write(
        vault_root / ".obsidian" / "core-plugins.json",
        json.dumps(
            {
                "file-explorer": True,
                "global-search": True,
                "switcher": True,
                "graph": True,
                "backlink": True,
                "outgoing-link": True,
                "tag-pane": True,
                "page-preview": True,
                "note-composer": True,
                "command-palette": True,
                "markdown-importer": False,
                "word-count": True,
                "open-with-default-app": True,
                "file-recovery": True,
                "sync": False,
                "publish": False,
            },
            indent=2,
        )
        + "\n",
    )
    # Graph view defaults — color by tag locally
    _write(
        vault_root / ".obsidian" / "graph.json",
        json.dumps(
            {
                "collapse-filter": False,
                "search": "",
                "showTags": True,
                "showAttachments": False,
                "hideUnresolved": True,
                "showOrphans": True,
                "collapse-color-groups": False,
                "colorGroups": [
                    {"query": "tag:#neuron", "color": {"a": 1, "rgb": 5474784}},
                    {"query": "tag:#gene", "color": {"a": 1, "rgb": 11393254}},
                    {"query": "tag:#cluster", "color": {"a": 1, "rgb": 15277667}},
                    {"query": "tag:#synapse", "color": {"a": 1, "rgb": 16750899}},
                    {"query": "tag:#moc", "color": {"a": 1, "rgb": 5814783}},
                ],
                "collapse-display": False,
                "showArrow": True,
                "textFadeMultiplier": 0,
                "nodeSizeMultiplier": 1.1,
                "lineSizeMultiplier": 1,
                "collapse-forces": False,
                "centerStrength": 0.4,
                "repelStrength": 12,
                "linkStrength": 0.8,
                "linkDistance": 180,
                "scale": 1,
            },
            indent=2,
        )
        + "\n",
    )
    _write(
        vault_root / ".obsidian" / "workspace.json",
        json.dumps({"main": {"id": "fsot-local", "type": "split", "children": []}}, indent=2)
        + "\n",
    )

    # ---------- Gene notes ----------
    gene_dir = vault_root / "03_Genes"
    for gname, orf in CHANNEL_GENE_ORFS.items():
        # mean expression across population
        exprs = [
            float(g.genes[gname].expression)
            for g in genotypes
            if gname in g.genes
        ]
        mean_e = sum(exprs) / max(1, len(exprs))
        # neurons where this gene dominates
        dominant = [
            _neuron_title(g.unit_id)
            for g in genotypes
            if _dominant_channel(g.phenotype) == gname
        ]
        body = [
            _yaml_frontmatter(
                {
                    "type": "gene",
                    "gene": gname,
                    "role": CHANNEL_ROLES.get(gname, gname),
                    "orf": orf,
                    "mean_expression": mean_e,
                    "n_dominant": len(dominant),
                    "tags": ["gene", "fsot", "ion-channel", _safe_tag(gname)],
                }
            ),
            "",
            f"# {_gene_title(gname)}",
            "",
            f"**Role:** {CHANNEL_ROLES.get(gname, gname)}",
            f"**Canonical ORF:** `{orf}`",
            f"**Mean expression (pop):** {mean_e:.4f}",
            "",
            "## Phenotype levers",
            "",
        ]
        levers = {
            "SCN": "Lowers fire threshold · raises FI drive (Na-like)",
            "KCN": "Lengthens refractory (K-like repolarization)",
            "CACNA": "Strengthens adaptation / AHP (Ca-like)",
            "LEAK": "Sets resting S / Vrest proxy",
        }
        body.append(levers.get(gname, "Channel expression modulator"))
        body += ["", "## Neurons where this gene dominates", ""]
        if dominant:
            body.append(", ".join(_wikilink(t) for t in dominant[:64]))
        else:
            body.append("_none in this population sample_")
        body += [
            "",
            "## Map",
            "",
            f"Parent: {_wikilink('Map_Genes')}",
            f"Home: {_wikilink('00_Home')}",
            "",
        ]
        _write(gene_dir / f"{_gene_title(gname)}.md", "\n".join(body))

    # ---------- Cluster hub notes ----------
    cluster_dir = vault_root / "06_Atlas"
    spin_groups: Dict[str, List[str]] = {
        "purine_high": [],
        "pyrimidine_high": [],
        "balanced": [],
    }
    charge_groups: Dict[str, List[str]] = {
        "cationic": [],
        "anionic": [],
        "neutral": [],
    }
    channel_groups: Dict[str, List[str]] = {k: [] for k in CHANNEL_GENE_ORFS}

    for g in genotypes:
        title = _neuron_title(g.unit_id)
        spin_groups[_spin_bucket(g.composite_spin)].append(title)
        charge_groups[_charge_bucket(g.composite_charge)].append(title)
        channel_groups[_dominant_channel(g.phenotype)].append(title)

    for kind, groups in (
        ("spin", spin_groups),
        ("charge", charge_groups),
        ("channel", channel_groups),
    ):
        for bucket, members in groups.items():
            title = _cluster_title(kind, bucket)
            body = [
                _yaml_frontmatter(
                    {
                        "type": "cluster",
                        "cluster_kind": kind,
                        "bucket": bucket,
                        "n_members": len(members),
                        "tags": ["cluster", "fsot", _safe_tag(kind), _safe_tag(bucket)],
                    }
                ),
                "",
                f"# {title}",
                "",
                f"Genetic atlas hub — **{kind}** / **{bucket}**",
                f"Members: **{len(members)}**",
                "",
                "## Members",
                "",
            ]
            if members:
                body.append(", ".join(_wikilink(m) for m in members))
            else:
                body.append("_empty_")
            body += ["", f"← {_wikilink('Map_Atlas')} · {_wikilink('00_Home')}", ""]
            _write(cluster_dir / f"{title}.md", "\n".join(body))

    # ---------- Neuron notes ----------
    neuron_dir = vault_root / "02_Neurons"
    for g in genotypes:
        uid = g.unit_id
        title = _neuron_title(uid)
        ph = g.phenotype
        dom = _dominant_channel(ph)
        rate = float(rates[uid]) if uid < len(rates) else 0.0
        outs = out_map[uid][: cfg.top_k_out]
        ins = in_map[uid][: cfg.top_k_in]

        tags = [
            "neuron",
            "fsot",
            f"dom-{_safe_tag(dom)}",
            f"spin-{_spin_bucket(g.composite_spin)}",
            f"charge-{_charge_bucket(g.composite_charge)}",
        ]
        fm = {
            "type": "neuron",
            "unit_id": uid,
            "title": title,
            "composite_spin": g.composite_spin,
            "composite_charge": g.composite_charge,
            "dominant_channel": dom,
            "d_eff": ph.get("d_eff"),
            "fire_threshold": ph.get("fire_threshold"),
            "refractory_steps": ph.get("refractory_steps"),
            "adapt_step": ph.get("adapt_step"),
            "scn": ph.get("scn_expression"),
            "kcn": ph.get("kcn_expression"),
            "cacna": ph.get("cacna_expression"),
            "leak": ph.get("leak_expression"),
            "rate_hz": rate,
            "n_out": len(outs),
            "n_in": len(ins),
            "tags": tags,
        }

        lines = [
            _yaml_frontmatter(fm),
            "",
            f"# {title}",
            "",
            f"> FSOT genetic unit `{uid}` · dominant [[{_gene_title(dom)}]]",
            "",
            "## Genotype",
            "",
            f"- Composite spin: **{g.composite_spin:+.4f}** → {_wikilink(_cluster_title('spin', _spin_bucket(g.composite_spin)))}",
            f"- Composite charge: **{g.composite_charge:+.4f}** → {_wikilink(_cluster_title('charge', _charge_bucket(g.composite_charge)))}",
            f"- Channel cluster: {_wikilink(_cluster_title('channel', dom))}",
            "",
            "### Ion-channel gene programs",
            "",
            "| Gene | Expression | Spin | AA |",
            "|------|------------|------|-----|",
        ]
        for gname, prog in g.genes.items():
            aa = "".join(r.aa for r in prog.residues)
            lines.append(
                f"| {_wikilink(_gene_title(gname), gname)} | {prog.expression:.3f} | "
                f"{prog.spin:+.3f} | `{aa}` |"
            )

        lines += [
            "",
            "### Phenotype (FSOT parameters)",
            "",
            f"- d_eff: `{ph.get('d_eff'):.3f}`",
            f"- fire threshold: `{ph.get('fire_threshold'):.3f}`",
            f"- refractory (ms floor): `{ph.get('refractory_steps'):.1f}`",
            f"- adapt_step: `{ph.get('adapt_step'):.3f}`",
            f"- fi_stim: `{ph.get('fi_stim'):.3f}`",
            f"- vrest proxy: `{ph.get('vrest_mV'):.1f}` mV",
            "",
            f"**FI rate (last local run):** {rate:.3f} Hz",
            "",
            "## Outgoing synapses (strongest)",
            "",
            "_W[post, pre] — current into target when this unit spikes._",
            "",
        ]
        if outs:
            for post, w in outs:
                sign = "exc" if w > 0 else "inh"
                lines.append(
                    f"- {_wikilink(_neuron_title(post))} · w=`{w:+.4f}` · `{sign}`"
                )
        else:
            lines.append("_no edges above threshold_")

        lines += ["", "## Incoming synapses (strongest)", ""]
        if ins:
            for pre, w in ins:
                sign = "exc" if w > 0 else "inh"
                lines.append(
                    f"- from {_wikilink(_neuron_title(pre))} · w=`{w:+.4f}` · `{sign}`"
                )
        else:
            lines.append("_no edges above threshold_")

        lines += [
            "",
            "## Navigation",
            "",
            f"- {_wikilink('Map_Neurons')}",
            f"- {_wikilink('Map_Connectivity')}",
            f"- {_wikilink('00_Home')}",
            "",
        ]
        _write(neuron_dir / f"{title}.md", "\n".join(lines))

    # ---------- Optional synapse notes ----------
    syn_count = 0
    if cfg.write_synapse_notes:
        syn_dir = vault_root / "04_Synapses"
        # strongest overall edges
        ranked = sorted(edges, key=lambda e: abs(e[2]), reverse=True)[: cfg.max_synapse_notes]
        for post, pre, w in ranked:
            stitle = f"Syn_{_neuron_title(pre)}_to_{_neuron_title(post)}"
            sign = "excitatory" if w > 0 else "inhibitory"
            body = [
                _yaml_frontmatter(
                    {
                        "type": "synapse",
                        "pre": pre,
                        "post": post,
                        "weight": w,
                        "sign": sign,
                        "tags": ["synapse", "fsot", sign],
                    }
                ),
                "",
                f"# {stitle}",
                "",
                f"**Pre:** {_wikilink(_neuron_title(pre))} → **Post:** {_wikilink(_neuron_title(post))}",
                f"**Weight:** `{w:+.6f}` ({sign})",
                "",
                "Derived from FSOT trinary pair interaction + geometric φ falloff + charge term.",
                "",
            ]
            _write(syn_dir / f"{stitle}.md", "\n".join(body))
            syn_count += 1

    # ---------- Dynamics note ----------
    dyn_dir = vault_root / "05_Dynamics"
    structure = dyn.get("structure") or gnet.structure_report()
    dyn_lines = [
        _yaml_frontmatter(
            {
                "type": "dynamics",
                "n_units": n,
                "tags": ["dynamics", "fsot", "report"],
            }
        ),
        "",
        "# Dynamics_Report",
        "",
        f"Generated (UTC): `{generated}`",
        "",
        "Local FI simulation only — no remote data fetch in this export path.",
        "",
        "## Structure",
        "",
        "```json",
        json.dumps(structure, indent=2, default=str),
        "```",
        "",
        "## Dynamics summary",
        "",
        "```json",
        json.dumps({k: v for k, v in dyn.items() if k != "structure"}, indent=2, default=str)[
            :8000
        ],
        "```",
        "",
        f"Home: {_wikilink('00_Home')}",
        "",
    ]
    _write(dyn_dir / "Dynamics_Report.md", "\n".join(dyn_lines))

    # ---------- Maps of Content ----------
    moc_dir = vault_root / "01_Maps"

    # Map_Neurons
    neuron_links = ", ".join(_wikilink(_neuron_title(g.unit_id)) for g in genotypes)
    _write(
        moc_dir / "Map_Neurons.md",
        "\n".join(
            [
                _yaml_frontmatter({"type": "moc", "tags": ["moc", "neurons"]}),
                "",
                "# Map_Neurons",
                "",
                f"All **{n}** genetic units in this vault.",
                "",
                neuron_links,
                "",
                f"← {_wikilink('00_Home')}",
                "",
            ]
        ),
    )

    _write(
        moc_dir / "Map_Genes.md",
        "\n".join(
            [
                _yaml_frontmatter({"type": "moc", "tags": ["moc", "genes"]}),
                "",
                "# Map_Genes",
                "",
                "Ion-channel gene programs (genotype spine):",
                "",
                *[f"- {_wikilink(_gene_title(g))}" for g in CHANNEL_GENE_ORFS],
                "",
                f"← {_wikilink('00_Home')}",
                "",
            ]
        ),
    )

    _write(
        moc_dir / "Map_Atlas.md",
        "\n".join(
            [
                _yaml_frontmatter({"type": "moc", "tags": ["moc", "atlas"]}),
                "",
                "# Map_Atlas",
                "",
                "## Spin clusters",
                "",
                *[f"- {_wikilink(_cluster_title('spin', b))}" for b in spin_groups],
                "",
                "## Charge clusters",
                "",
                *[f"- {_wikilink(_cluster_title('charge', b))}" for b in charge_groups],
                "",
                "## Dominant channel clusters",
                "",
                *[f"- {_wikilink(_cluster_title('channel', b))}" for b in channel_groups],
                "",
                f"← {_wikilink('00_Home')}",
                "",
            ]
        ),
    )

    # Connectivity map — text adjacency for second-brain overview
    conn_lines = [
        _yaml_frontmatter({"type": "moc", "tags": ["moc", "connectivity"]}),
        "",
        "# Map_Connectivity",
        "",
        "Strongest genetic synapses exported as wikilinks on each neuron note.",
        f"- Units: **{n}**",
        f"- Edges kept: **{len(edges)}** (top_k_out={cfg.top_k_out}, min_abs_w={cfg.min_abs_w})",
        f"- Connectivity mode: `{cfg.connectivity}`",
        "",
        "## How to see the graph (local)",
        "",
        "1. Open this folder as a vault in **Obsidian desktop** (Open folder as vault).",
        "2. Open **Graph view** (local core plugin — no internet).",
        "3. Filter tags: `#neuron` / `#gene` / `#cluster`.",
        "4. Click any node → follow outgoing links = synaptic pattern.",
        "",
        "## Hub neurons (highest out-degree in export)",
        "",
    ]
    degree = sorted(
        ((i, len(out_map[i])) for i in range(n)), key=lambda x: x[1], reverse=True
    )
    for i, deg in degree[:12]:
        conn_lines.append(f"- {_wikilink(_neuron_title(i))} · out_edges={deg}")
    conn_lines += ["", f"← {_wikilink('00_Home')}", ""]
    _write(moc_dir / "Map_Connectivity.md", "\n".join(conn_lines))

    # ---------- Home ----------
    home = [
        _yaml_frontmatter(
            {
                "type": "home",
                "tags": ["moc", "home", "fsot"],
                "generated_at": generated,
                "offline": True,
                "n_units": n,
                "n_edges_export": len(edges),
            }
        ),
        "",
        "# 00_Home — FSOT Neural Second Brain",
        "",
        "**Local-only vault.** No server, no web, no cloud required.",
        "",
        "This is a second-brain view of the **FSOT genetic-codon neural network**:",
        "each neuron is a note; wikilinks are genetic synapses; genes and atlas hubs",
        "organize the connective tissue.",
        "",
        "## Open the graph (desktop Obsidian)",
        "",
        "1. Obsidian → **Open folder as vault**",
        f"2. Select: `{vault_root}`",
        "3. Left ribbon → **Graph view**",
        "4. Color groups already set for `#neuron` / `#gene` / `#cluster`",
        "",
        "Sync / Publish core plugins are disabled in this vault config.",
        "",
        "## Maps of content",
        "",
        f"- {_wikilink('Map_Neurons')} — all units",
        f"- {_wikilink('Map_Genes')} — SCN · KCN · CACNA · LEAK",
        f"- {_wikilink('Map_Atlas')} — spin / charge / channel clusters",
        f"- {_wikilink('Map_Connectivity')} — edge policy + hubs",
        f"- {_wikilink('Dynamics_Report')} — local FI metrics",
        "",
        "## Mission spine",
        "",
        "```text",
        "64-codon trinary → ion-channel gene ORFs → phenotype",
        "  → FSOT W_ij (trinary pair + φ geometry + charge)",
        "  → Markdown notes + wikilinks = visible connective pattern",
        "```",
        "",
        "## Stats",
        "",
        f"| | |",
        f"|--|--|",
        f"| Neurons | {n} |",
        f"| Exported edges | {len(edges)} |",
        f"| Gene notes | {len(CHANNEL_GENE_ORFS)} |",
        f"| Synapse notes | {syn_count} |",
        f"| Generated (UTC) | {generated} |",
        f"| Project root | `{ROOT}` |",
        "",
        "## Re-generate (local shell)",
        "",
        "```powershell",
        f'cd "{ROOT}"',
        '$env:PYTHONPATH = "."',
        "python run_obsidian_brain.py",
        "```",
        "",
    ]
    _write(vault_root / "00_Home.md", "\n".join(home))

    # README for non-Obsidian users
    _write(
        vault_root / "README_LOCAL.md",
        "\n".join(
            [
                "# FSOT Neural Second Brain — local vault",
                "",
                "This folder is plain Markdown on disk.",
                "",
                "- **No web server**",
                "- **No cloud account**",
                "- **No outbound network** from the exporter",
                "",
                "Open with:",
                "",
                "1. [Obsidian](https://obsidian.md) desktop → Open folder as vault (graph view), or",
                "2. Any local editor / file browser (wikilinks still readable as `[[Note]]`).",
                "",
                f"Entry note: `00_Home.md`",
                "",
            ]
        ),
    )

    # Machine-readable manifest (local JSON)
    manifest = {
        "offline": True,
        "no_server": True,
        "vault_root": str(vault_root),
        "generated_at": generated,
        "n_units": n,
        "n_edges_export": len(edges),
        "n_synapse_notes": syn_count,
        "config": {
            "top_k_out": cfg.top_k_out,
            "min_abs_w": cfg.min_abs_w,
            "connectivity": cfg.connectivity,
            "sparse_keep": cfg.sparse_keep,
            "seed": cfg.seed,
            "run_dynamics": cfg.run_dynamics,
        },
        "structure": structure,
    }
    _write(vault_root / "vault_manifest.json", json.dumps(manifest, indent=2) + "\n")
    # also copy to artifacts root for quick path discovery
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    _write(
        ARTIFACTS / "obsidian_vault_last.json",
        json.dumps(
            {
                "vault_root": str(vault_root),
                "generated_at": generated,
                "n_units": n,
                "n_edges_export": len(edges),
                "offline": True,
            },
            indent=2,
        )
        + "\n",
    )

    return manifest


def export_from_suite(
    vault_root: Optional[Path] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Convenience: build network + vault with ObsidianExportConfig fields as kwargs."""
    fields = {f.name for f in ObsidianExportConfig.__dataclass_fields__.values()}  # type: ignore
    cfg_kwargs = {k: v for k, v in kwargs.items() if k in fields}
    other = {k: v for k, v in kwargs.items() if k not in fields}
    cfg = ObsidianExportConfig(**cfg_kwargs)
    clean = other.pop("clean", True)
    return build_obsidian_vault(vault_root=vault_root, cfg=cfg, clean=clean)
