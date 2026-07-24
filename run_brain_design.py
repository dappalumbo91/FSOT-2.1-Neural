#!/usr/bin/env python3
"""
FSOT multi-region brain design runner (primary path toward a full brain).

Builds:
  cell-typed genetic neurons (Pyr/PV/SST/VIP)
  → local cortical microcircuit motifs + long-range projections
  → thalamo-cortical style drive
  → structure/dynamics reports
  → optional local Obsidian vault (no server/web)

Usage:
  cd "I:\\fsot nuron"
  $env:PYTHONPATH = "I:\\fsot nuron"
  python run_brain_design.py
  python run_brain_design.py --scale 1.5 --steps 1000 --obsidian
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _export_brain_obsidian(brain, vault_name: str = "FSOT_Brain_Design") -> Path:
    """Local vault with region + cell-type tags (files only)."""
    from fsot_nuron.obsidian_brain import (
        ObsidianExportConfig,
        _yaml_frontmatter,
        _wikilink,
        _write,
        _neuron_title,
        _gene_title,
        _dominant_channel,
        _spin_bucket,
        _charge_bucket,
        _cluster_title,
        default_vault_root,
    )
    from fsot_nuron.genetic_genotype import CHANNEL_GENE_ORFS
    import shutil

    vault = default_vault_root(vault_name)
    if vault.exists():
        marker = vault / ".fsot_vault_marker"
        if marker.is_file():
            shutil.rmtree(vault)
        elif any(vault.iterdir()):
            raise FileExistsError(f"not an FSOT vault: {vault}")
    vault.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat()
    _write(
        vault / ".fsot_vault_marker",
        f"FSOT brain design vault\noffline=true\nno_server=true\ngenerated_at={generated}\n",
    )

    # Minimal graph config
    _write(
        vault / ".obsidian" / "core-plugins.json",
        json.dumps(
            {
                "graph": True,
                "file-explorer": True,
                "backlink": True,
                "outgoing-link": True,
                "tag-pane": True,
                "sync": False,
                "publish": False,
            },
            indent=2,
        )
        + "\n",
    )
    _write(
        vault / ".obsidian" / "graph.json",
        json.dumps(
            {
                "showTags": True,
                "hideUnresolved": True,
                "showArrow": True,
                "colorGroups": [
                    {"query": "tag:#region-sens", "color": {"a": 1, "rgb": 5474784}},
                    {"query": "tag:#region-assoc", "color": {"a": 1, "rgb": 11393254}},
                    {"query": "tag:#region-hipp", "color": {"a": 1, "rgb": 15277667}},
                    {"query": "tag:#region-thal", "color": {"a": 1, "rgb": 16750899}},
                    {"query": "tag:#cell-Pyr", "color": {"a": 1, "rgb": 5814783}},
                    {"query": "tag:#cell-PV", "color": {"a": 1, "rgb": 13382451}},
                ],
            },
            indent=2,
        )
        + "\n",
    )

    edges = brain.connectivity_edges(top_k_out=5, min_abs_w=0.02)
    out_map = {i: [] for i in range(brain.n_units)}
    in_map = {i: [] for i in range(brain.n_units)}
    for post, pre, w in edges:
        out_map[pre].append((post, w))
        in_map[post].append((pre, w))

    # Region notes
    reg_dir = vault / "10_Regions"
    for rid, ids in brain.region_index.items():
        types = {}
        for i in ids:
            ct = brain.units[i].cell_type
            types[ct] = types.get(ct, 0) + 1
        links = ", ".join(_wikilink(_neuron_title(i)) for i in ids)
        body = [
            _yaml_frontmatter(
                {
                    "type": "region",
                    "region_id": rid,
                    "n_units": len(ids),
                    "tags": ["region", f"region-{rid}", "fsot", "brain"],
                }
            ),
            "",
            f"# Region_{rid}",
            "",
            f"Units: **{len(ids)}**",
            f"Cell-type mix: `{types}`",
            "",
            "## Members",
            "",
            links,
            "",
            f"← {_wikilink('00_Home')}",
            "",
        ]
        _write(reg_dir / f"Region_{rid}.md", "\n".join(body))

    # Neuron notes
    n_dir = vault / "02_Neurons"
    for u, g in zip(brain.units, brain.genotypes):
        title = _neuron_title(u.global_id)
        ph = g.phenotype
        outs = sorted(out_map[u.global_id], key=lambda x: abs(x[1]), reverse=True)[:5]
        ins = sorted(in_map[u.global_id], key=lambda x: abs(x[1]), reverse=True)[:4]
        tags = [
            "neuron",
            "fsot",
            "brain",
            f"region-{u.region_id}",
            f"cell-{u.cell_type}",
            u.transmitter,
        ]
        lines = [
            _yaml_frontmatter(
                {
                    "type": "neuron",
                    "unit_id": u.global_id,
                    "region": u.region_id,
                    "cell_type": u.cell_type,
                    "transmitter": u.transmitter,
                    "synapse_sign": u.synapse_sign,
                    "d_eff": ph.get("d_eff"),
                    "tags": tags,
                }
            ),
            "",
            f"# {title}",
            "",
            f"**Region:** {_wikilink(f'Region_{u.region_id}')} · "
            f"**Cell type:** `{u.cell_type}` · **Tx:** `{u.transmitter}` "
            f"({'exc' if u.synapse_sign > 0 else 'inh'})",
            "",
            "## Genes",
            "",
        ]
        for gname, prog in g.genes.items():
            lines.append(f"- {gname}: expr={prog.expression:.3f}")
        lines += ["", "## Outgoing", ""]
        for post, w in outs:
            lines.append(f"- {_wikilink(_neuron_title(post))} w=`{w:+.4f}`")
        if not outs:
            lines.append("_none above threshold_")
        lines += ["", "## Incoming", ""]
        for pre, w in ins:
            lines.append(f"- {_wikilink(_neuron_title(pre))} w=`{w:+.4f}`")
        lines += ["", f"← {_wikilink('00_Home')}", ""]
        _write(n_dir / f"{title}.md", "\n".join(lines))

    # Home
    st = brain.structure_report()
    home = [
        _yaml_frontmatter(
            {
                "type": "home",
                "offline": True,
                "n_units": brain.n_units,
                "tags": ["home", "brain", "fsot"],
            }
        ),
        "",
        "# 00_Home — FSOT Brain Design (local)",
        "",
        "**Offline vault.** No server, no web.",
        "",
        "Multi-region brain built from genetic cell-typed neurons.",
        "",
        "## Regions",
        "",
        *[f"- {_wikilink(f'Region_{rid}')} ({info['n']} units)" for rid, info in st["regions"].items()],
        "",
        "## Projections",
        "",
        *[
            f"- `{p['src']}` → `{p['dst']}` ({p['kind']})"
            for p in st["projections"]
        ],
        "",
        f"E/I count ratio: **{st['population']['ei_count_ratio']:.2f}**  ",
        f"E/I synaptic mass ratio: **{st['ei_mass_ratio']:.3f}**  ",
        f"Synapses: **{st['n_synapses']}**",
        "",
        "Open **Graph view** in Obsidian desktop (local).",
        "",
    ]
    _write(vault / "00_Home.md", "\n".join(home))
    _write(
        vault / "vault_manifest.json",
        json.dumps(
            {"offline": True, "vault": str(vault), "structure": st, "generated_at": generated},
            indent=2,
            default=str,
        )
        + "\n",
    )
    return vault


def main() -> int:
    ap = argparse.ArgumentParser(description="FSOT multi-region brain design")
    ap.add_argument(
        "--profile",
        type=str,
        default="ai_efficient",
        choices=["ai_efficient", "wetware_ref"],
        help="ai_efficient=computer-native fewer units; wetware_ref=bio comparison scale",
    )
    ap.add_argument("--scale", type=float, default=1.0, help="Extra scale on profile base sizes")
    ap.add_argument("--steps", type=int, default=800)
    ap.add_argument("--device", type=str, default="cpu")
    ap.add_argument("--obsidian", action="store_true", help="Write local Obsidian vault")
    ap.add_argument("--vault-name", type=str, default="FSOT_Brain_Design")
    args = ap.parse_args()

    from fsot_nuron.archive_pin import pin_archive
    from fsot_nuron.brain_architecture import run_brain_design_suite
    from fsot_nuron.paths import ARTIFACTS
    from fsot_nuron.thesis_ledger import record_run

    print("=== FSOT Brain Design — multi-region genetic architecture ===")
    print("path: codon → cell types → microcircuit → regions → projections")
    print("doctrine: mechanism fidelity + computer-native efficiency (not 86B units)")
    print(f"profile: {args.profile}")
    print("offline dynamics: local torch only")

    pin = pin_archive(write_snapshot=False)
    print(f"archive pin seed_ok: {pin.seed_match_ok}")

    suite = run_brain_design_suite(
        steps=args.steps, device=args.device, scale=args.scale, profile=args.profile
    )
    brain = suite["brain"]
    st = suite["structure"]
    dyn = suite["dynamics"]
    gates = suite["gates"]

    print(f"\n--- Profile: {suite.get('profile')} ---")
    print(f"  intent:    {suite.get('profile_intent')}")
    print(f"  isi_scale: {suite.get('isi_scale')}")
    print(f"  n_units:   {suite['n_units']}  (functional equivalence ≠ human census)")

    print("\n--- Regions ---")
    for rid, info in st["regions"].items():
        print(f"  {rid:8} n={info['n']:3}  types={info['cell_types']}")

    print("\n--- Population ---")
    pop = st["population"]
    print(f"  E/I counts: {pop['n_excitatory']}/{pop['n_inhibitory']}  ratio={pop['ei_count_ratio']:.2f}")
    print(f"  type mix:   {pop['counts']}")
    print(f"  synapses:   {st['n_synapses']}  density={st['synapse_density']:.3f}")
    print(f"  E/I mass:   {st['ei_mass_ratio']:.3f}")

    print("\n--- Dynamics (thalamic drive) ---")
    print(f"  mean rate:  {dyn['mean_rate_Hz']:.3f} Hz")
    print(f"  by region:  { {k: round(v, 2) for k, v in dyn['rate_by_region'].items()} }")
    print(f"  by type:    { {k: round(v, 2) for k, v in dyn['rate_by_cell_type'].items()} }")

    print("\n--- Gates ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mission": suite["mission"],
        "profile": suite.get("profile"),
        "profile_intent": suite.get("profile_intent"),
        "isi_scale": suite.get("isi_scale"),
        "formulas_ref": suite.get("formulas_ref"),
        "thesis_ref": suite.get("thesis_ref"),
        "efficiency_ref": suite.get("efficiency_ref"),
        "pin_seed_ok": pin.seed_match_ok,
        "structure": st,
        "dynamics": dyn,
        "gates": gates,
        "n_units": suite["n_units"],
    }
    record_run(
        "brain_design",
        profile=str(suite.get("profile") or args.profile),
        gates=gates,
        metrics={
            "n_units": suite["n_units"],
            "ei_count_ratio": pop["ei_count_ratio"],
            "ei_mass_ratio": st["ei_mass_ratio"],
            "mean_rate_Hz": dyn["mean_rate_Hz"],
            "n_synapses": st["n_synapses"],
            "isi_scale": suite.get("isi_scale"),
        },
        notes="multi-region FSOT brain; efficiency doctrine active",
    )
    # drop non-serializable
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    art = ARTIFACTS / "brain_design_report.json"
    art.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    res_dir = ROOT / "data" / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    (res_dir / "brain_design_report.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )

    md = [
        "# FSOT Brain Design — report",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        "## Mission",
        "",
        suite["mission"],
        "",
        f"**Profile:** `{suite.get('profile')}` — {suite.get('profile_intent')}",
        f"**Units:** {suite['n_units']} (not a human neuron-count target)",
        f"**Formulas:** {suite.get('formulas_ref')} · **Thesis:** {suite.get('thesis_ref')}",
        "",
        "## Regions",
        "",
    ]
    for rid, info in st["regions"].items():
        md.append(f"- **{rid}**: {info['n']} units · {info['cell_types']}")
    md += [
        "",
        f"- E/I count ratio: **{pop['ei_count_ratio']:.2f}**",
        f"- E/I synaptic mass: **{st['ei_mass_ratio']:.3f}**",
        f"- Mean rate (thal drive): **{dyn['mean_rate_Hz']:.2f} Hz**",
        "",
        "## Gates",
        "",
        *[f"- {k}: **{v}**" for k, v in gates.items()],
        "",
        "## Path forward",
        "",
        "See `BRAIN_PATH.md`.",
        "",
    ]
    (res_dir / "BRAIN_DESIGN.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {art}")
    print(f"Wrote {res_dir / 'BRAIN_DESIGN.md'}")

    if args.obsidian:
        try:
            vpath = _export_brain_obsidian(brain, vault_name=args.vault_name)
            print(f"Obsidian vault (local): {vpath}")
        except FileExistsError as e:
            print(f"Obsidian skip: {e}")
            return 2

    # Remove live object before judging
    ok = all(gates.values()) and bool(pin.seed_match_ok)
    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
