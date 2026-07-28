"""
Capability frontier ledger — claims we do **not** yet make, tracked over time.

Three permanent tracking targets (user-specified):

  1. open_world_pixel_identity  — "that is Jake" from pixels alone
  2. self_directed_curriculum   — full autonomous curriculum design
  3. free_monologue             — LLM-style free monologue / generative language

Status vocabulary:
  unclaimed   — not asserted; baseline
  probing     — experimental metric exists, not green
  partial     — measurable progress, still not claimable
  claimed     — only when gates pass (requires explicit human + automated green)

Append-only JSONL under data/capability_frontier/. Local only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .paths import ROOT, DATA
from .thesis_ledger import _git_sha

FRONTIER_DIR = DATA / "capability_frontier"
LEDGER_PATH = FRONTIER_DIR / "frontier_runs.jsonl"
LATEST_PATH = FRONTIER_DIR / "latest.json"
STATUS_MD = FRONTIER_DIR / "STATUS.md"
DOCS_MD = ROOT / "docs" / "CAPABILITY_FRONTIER.md"

# Canonical claim IDs — do not rename lightly (history keys)
CLAIM_OPEN_WORLD = "open_world_pixel_identity"
CLAIM_CURRICULUM = "self_directed_curriculum"
CLAIM_MONOLOGUE = "free_monologue"

CLAIM_DEFS: Dict[str, Dict[str, Any]] = {
    CLAIM_OPEN_WORLD: {
        "title": "Open-world pixel identity",
        "short": "Recognize a specific entity (e.g. Jake) from pixels alone",
        "not_claim": (
            "We do not claim the system can identify Jake (or any character) from "
            "pixels alone without path/title/subtitle/lexicon tutors."
        ),
        "what_counts_as_progress": [
            "Recurring visual clusters co-occur with caption names across episodes",
            "Held-out clip (no path hints, no subtitles) retrieves correct name above chance",
            "Confusion matrix over ≥3 characters with top-1 > chance by clear margin",
        ],
        "claim_gate": (
            "Held-out silent clips of ≥3 characters: top-1 name accuracy ≥ 0.70 "
            "with no path/title/subtitle/lexicon injection at test time; multi-seed."
        ),
        "metrics_keys": [
            "pixel_id_top1",
            "pixel_id_chance",
            "n_characters",
            "n_heldout_clips",
            "tutor_ablated",
        ],
    },
    CLAIM_CURRICULUM: {
        "title": "Self-directed curriculum design",
        "short": "Choose its own learning sequence without human ordering",
        "not_claim": (
            "We do not claim full self-directed curriculum design. Autonomous learn "
            "currently chews what it finds under fixed discovery heuristics, not a "
            "self-authored multi-step curriculum."
        ),
        "what_counts_as_progress": [
            "System proposes next media/doc targets from memory gaps",
            "Revisits weak symbols preferentially",
            "Curriculum plan logged before execution and improves a held metric",
        ],
        "claim_gate": (
            "Without human file lists: agent writes a multi-step plan, executes it, "
            "and improves a pre-registered metric (e.g. recall@k or pixel_id_top1) "
            "vs fixed-order baseline on the same budget."
        ),
        "metrics_keys": [
            "curriculum_steps_planned",
            "curriculum_self_authored",
            "gap_driven_fraction",
            "metric_delta_vs_fixed_order",
        ],
    },
    CLAIM_MONOLOGUE: {
        "title": "LLM-style free monologue",
        "short": "Open-ended generative language like a large language model",
        "not_claim": (
            "We do not claim LLM-style free monologue. Output is compositional "
            "regurgitation from lexicon + stream stats + stored episodes "
            "(compact trinary/machine codes re-expanded to English)."
        ),
        "what_counts_as_progress": [
            "Longer multi-sentence recall grounded in stored episodes",
            "Novel but source-faithful paraphrases of chewed material",
            "Chat-like multi-turn grounded in organism memory (not external LLM)",
        ],
        "claim_gate": (
            "Multi-turn dialogue (≥5 turns) answering open questions about chewed "
            "media/docs using only organism memory + FSOT pathways; human rating "
            "groundedness ≥ 0.8 and zero external LLM dependency."
        ),
        "metrics_keys": [
            "monologue_mode",
            "max_coherent_sentences",
            "groundedness_score",
            "external_llm_used",
            "n_turns",
        ],
    },
}


def baseline_statuses() -> Dict[str, Dict[str, Any]]:
    """Current honest status for each claim."""
    return {
        CLAIM_OPEN_WORLD: {
            "status": "unclaimed",
            "status_note": "AV clusters + tutors exist; pixel-only identity not measured/green",
            "metrics": {
                "pixel_id_top1": None,
                "pixel_id_chance": None,
                "n_characters": 0,
                "n_heldout_clips": 0,
                "tutor_ablated": None,
            },
        },
        CLAIM_CURRICULUM: {
            "status": "probing",
            "status_note": (
                "run_autonomous_learn.py chews discovered docs/media with fixed heuristics; "
                "not self-authored curriculum"
            ),
            "metrics": {
                "curriculum_steps_planned": 0,
                "curriculum_self_authored": False,
                "gap_driven_fraction": 0.0,
                "metric_delta_vs_fixed_order": None,
            },
        },
        CLAIM_MONOLOGUE: {
            "status": "partial",
            "status_note": (
                "plain_english / recall_plain_english are compositional expansions, "
                "not free generative monologue"
            ),
            "metrics": {
                "monologue_mode": "compositional_regurgitation",
                "max_coherent_sentences": None,
                "groundedness_score": None,
                "external_llm_used": False,
                "n_turns": 0,
            },
        },
    }


def log_frontier(
    *,
    experiment: str = "capability_frontier_snapshot",
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    related_metrics: Optional[Dict[str, Any]] = None,
    notes: str = "",
    write_docs: bool = True,
) -> Dict[str, Any]:
    """
    Append one frontier snapshot. overrides merge into baseline per claim_id.
    """
    FRONTIER_DIR.mkdir(parents=True, exist_ok=True)
    claims = baseline_statuses()
    if overrides:
        for cid, blob in overrides.items():
            if cid not in claims:
                continue
            if "status" in blob:
                claims[cid]["status"] = blob["status"]
            if "status_note" in blob:
                claims[cid]["status_note"] = blob["status_note"]
            if "metrics" in blob and isinstance(blob["metrics"], dict):
                claims[cid]["metrics"].update(blob["metrics"])

    row: Dict[str, Any] = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": experiment,
        "git_sha": _git_sha(),
        "authority_pin_prefix": "D1D38A",
        "claims": claims,
        "related_metrics": related_metrics or {},
        "notes": notes,
        "doc_ref": "docs/CAPABILITY_FRONTIER.md",
    }
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
    LATEST_PATH.write_text(json.dumps(row, indent=2, default=str) + "\n", encoding="utf-8")
    _write_status_md(row)
    if write_docs:
        write_capability_frontier_doc(row)
    return row


def read_latest() -> Optional[Dict[str, Any]]:
    if not LATEST_PATH.is_file():
        return None
    return json.loads(LATEST_PATH.read_text(encoding="utf-8"))


def read_history(limit: int = 50) -> List[Dict[str, Any]]:
    if not LEDGER_PATH.is_file():
        return []
    rows = []
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def _write_status_md(row: Dict[str, Any]) -> None:
    lines = [
        "# Capability frontier — live status",
        "",
        f"Updated: `{row.get('ts_utc')}`  ",
        f"Git: `{row.get('git_sha')}`  ",
        f"Experiment: `{row.get('experiment')}`",
        "",
        "| Claim | Status | Note |",
        "|-------|--------|------|",
    ]
    claims = row.get("claims") or {}
    for cid, meta in CLAIM_DEFS.items():
        c = claims.get(cid) or {}
        st = c.get("status", "unclaimed")
        note = (c.get("status_note") or "").replace("|", "/")
        lines.append(f"| **{meta['title']}** (`{cid}`) | `{st}` | {note} |")
    lines += [
        "",
        "See [`docs/CAPABILITY_FRONTIER.md`](../../docs/CAPABILITY_FRONTIER.md) for gates.",
        "",
        "```json",
        json.dumps(row.get("related_metrics") or {}, indent=2),
        "```",
        "",
    ]
    STATUS_MD.write_text("\n".join(lines), encoding="utf-8")


def write_capability_frontier_doc(latest: Optional[Dict[str, Any]] = None) -> Path:
    """Human-facing doctrine + current snapshot."""
    latest = latest or read_latest() or log_frontier(experiment="frontier_doc_bootstrap", write_docs=False)
    claims = latest.get("claims") or baseline_statuses()
    lines = [
        "# Capability frontier — what we do **not** claim (yet)",
        "",
        "These are **tracked gaps**, not failures. We log them on every major climb",
        "so progress is honest and comparable.",
        "",
        f"**Live status file:** [`data/capability_frontier/STATUS.md`](../data/capability_frontier/STATUS.md)  ",
        f"**Append-only ledger:** `data/capability_frontier/frontier_runs.jsonl`  ",
        f"**Last snapshot:** `{latest.get('ts_utc')}` · git `{latest.get('git_sha')}`",
        "",
        "## Status vocabulary",
        "",
        "| Status | Meaning |",
        "|--------|---------|",
        "| `unclaimed` | Not asserted; no green gate |",
        "| `probing` | Experiment exists; not claimable |",
        "| `partial` | Real capability, wrong shape for the full claim |",
        "| `claimed` | Gate passed (explicit) |",
        "",
        "---",
        "",
    ]
    for cid, meta in CLAIM_DEFS.items():
        c = claims.get(cid) or {}
        lines += [
            f"## {meta['title']}",
            "",
            f"**ID:** `{cid}`  ",
            f"**One-liner:** {meta['short']}  ",
            f"**Current status:** `{c.get('status', 'unclaimed')}`  ",
            f"**Note:** {c.get('status_note', '')}",
            "",
            "### We do **not** claim",
            "",
            meta["not_claim"],
            "",
            "### What counts as progress",
            "",
        ]
        for p in meta["what_counts_as_progress"]:
            lines.append(f"- {p}")
        lines += [
            "",
            "### Claim gate (when we may flip to `claimed`)",
            "",
            meta["claim_gate"],
            "",
            "### Metrics keys",
            "",
            ", ".join(f"`{k}`" for k in meta["metrics_keys"]),
            "",
            "### Latest metrics",
            "",
            "```json",
            json.dumps(c.get("metrics") or {}, indent=2),
            "```",
            "",
            "---",
            "",
        ]
    lines += [
        "## Related (claimed or green elsewhere)",
        "",
        "These are **not** the three gaps above; they *are* things we already track:",
        "",
        "- Standalone pin D1D38A · Allen class rates · AV co-stream bind · subtitle dialogue",
        "- Document reading (page text → trinary) · compositional plain-English recall",
        "- Autonomous chew of discovered files (fixed heuristics, not full curriculum design)",
        "",
        "## How to log",
        "",
        "```powershell",
        "python run_capability_frontier.py              # snapshot + print",
        "python run_capability_frontier.py --history 10",
        "```",
        "",
        "Call from runners:",
        "",
        "```python",
        "from fsot_nuron.capability_frontier import log_frontier",
        "log_frontier(experiment='autonomous_learn', related_metrics={...}, notes='...')",
        "```",
        "",
    ]
    DOCS_MD.parent.mkdir(parents=True, exist_ok=True)
    DOCS_MD.write_text("\n".join(lines), encoding="utf-8")
    return DOCS_MD


def snapshot_from_autonomous(report: Any) -> Dict[str, Any]:
    """Build related_metrics + notes from AutonomousLearnReport-like object."""
    d = report.to_dict() if hasattr(report, "to_dict") else dict(report)
    related = {
        "n_documents": d.get("n_documents"),
        "n_media_episodes": d.get("n_media_episodes"),
        "n_memory_saved": d.get("n_memory_saved"),
        "brain_spikes": d.get("brain_spikes"),
        "mean_S": d.get("mean_S"),
        "pattern_census_top": dict(list((d.get("pattern_census") or {}).items())[:12]),
        "pin_mode": d.get("pin_mode"),
    }
    notes = (
        "Autonomous session logged. open_world still unclaimed; "
        "curriculum probing (fixed discovery); monologue remains compositional."
    )
    return log_frontier(
        experiment="autonomous_learn",
        related_metrics=related,
        notes=notes,
        overrides={
            CLAIM_CURRICULUM: {
                "status": "probing",
                "status_note": (
                    f"autonomous_learn ran docs={d.get('n_documents')} "
                    f"media={d.get('n_media_episodes')} under fixed heuristics"
                ),
                "metrics": {
                    "curriculum_steps_planned": int(d.get("n_documents") or 0)
                    + int(d.get("n_media_episodes") or 0),
                    "curriculum_self_authored": False,
                    "gap_driven_fraction": 0.0,
                },
            },
            CLAIM_MONOLOGUE: {
                "status": "partial",
                "metrics": {
                    "monologue_mode": "compositional_regurgitation",
                    "external_llm_used": False,
                    "n_turns": 0,
                },
            },
        },
    )
