"""
Refine cycle: score → select highest-below-threshold → test → fix → retest → log.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..paths import DATA, ARTIFACTS
from .layers import score_all_layers, select_refine_target, LayerScore
from .fixes import FIX_DISPATCH, refine_ei_microcircuit


CYCLE_DIR = DATA / "refine_cycles"
LEDGER = CYCLE_DIR / "cycles.jsonl"


@dataclass
class RefineCycleReport:
    ok: bool
    threshold: float
    target_layer: Optional[str]
    target_title: Optional[str]
    before_score: Optional[float]
    after_score: Optional[float]
    all_layers_before: List[Dict[str, Any]] = field(default_factory=list)
    all_layers_after: List[Dict[str, Any]] = field(default_factory=list)
    fix_result: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    ts_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_refine_cycle(
    *,
    threshold: float = 70.0,
    layer_id: Optional[str] = None,
    apply_fix: bool = True,
    domain: str = "all",
) -> RefineCycleReport:
    """
    One iteration of the climb discipline the user asked for:
    test → log → fix → retest.

    domain: 'all' | 'bio' | 'capability' — bio prioritizes wet-lab/sensory/learning.
    """
    notes: List[str] = []
    ts = datetime.now(timezone.utc).isoformat()
    before_layers = score_all_layers(threshold=threshold, domain=domain)
    notes.append(
        f"scored {len(before_layers)} layers; threshold={threshold}; domain={domain}"
    )

    if layer_id:
        target = next((L for L in before_layers if L.layer_id == layer_id), None)
        if target is None:
            notes.append(f"unknown layer_id={layer_id}; falling back to auto-select")
            target = select_refine_target(
                before_layers, threshold=threshold, domain=domain
            )
    else:
        target = select_refine_target(
            before_layers, threshold=threshold, domain=domain
        )

    if target is None:
        notes.append("all layers at or above threshold — nothing to refine")
        rep = RefineCycleReport(
            ok=True,
            threshold=threshold,
            target_layer=None,
            target_title=None,
            before_score=None,
            after_score=None,
            all_layers_before=[L.to_dict() for L in before_layers],
            notes=notes,
            ts_utc=ts,
        )
        _log(rep)
        return rep

    if layer_id and target.layer_id == layer_id:
        notes.append(
            f"TARGET (forced): {target.layer_id} score={target.score:.1f} "
            f"(threshold={threshold})"
        )
    else:
        notes.append(
            f"TARGET (highest below threshold): {target.layer_id} "
            f"score={target.score:.1f} < {threshold}"
        )
    fix_result: Dict[str, Any] = {}
    after_score = target.score

    if apply_fix:
        fn = FIX_DISPATCH.get(target.layer_id)
        if fn is None:
            notes.append(f"no automated fix for {target.layer_id} yet — logged only")
            fix_result = {"skipped": True, "layer_id": target.layer_id}
        else:
            notes.append(f"applying fix: {fn.__name__}")
            fix_result = fn()
            after_score = float(fix_result.get("after_score", target.score))
            notes.append(
                f"fix result: before={fix_result.get('before_score')} "
                f"after={fix_result.get('after_score')} "
                f"improved={fix_result.get('improved')}"
            )

    after_layers = score_all_layers(threshold=threshold, domain=domain)
    # refresh target after score
    t2 = next((L for L in after_layers if L.layer_id == target.layer_id), target)
    after_score = t2.score

    rep = RefineCycleReport(
        ok=True,
        threshold=threshold,
        target_layer=target.layer_id,
        target_title=target.title,
        before_score=target.score,
        after_score=after_score,
        all_layers_before=[L.to_dict() for L in before_layers],
        all_layers_after=[L.to_dict() for L in after_layers],
        fix_result=fix_result,
        notes=notes,
        ts_utc=ts,
    )
    _log(rep)
    return rep


def _log(rep: RefineCycleReport) -> None:
    CYCLE_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rep.to_dict(), default=str) + "\n")
    (ARTIFACTS / "refine_cycle_last.json").write_text(
        json.dumps(rep.to_dict(), indent=2, default=str), encoding="utf-8"
    )
    # human markdown
    md = CYCLE_DIR / "LATEST.md"
    lines = [
        "# Refine cycle (latest)",
        "",
        f"Time: `{rep.ts_utc}`",
        f"Threshold: **{rep.threshold}**",
        f"Target: **{rep.target_title or 'none'}** (`{rep.target_layer}`)",
        f"Score: **{rep.before_score}** → **{rep.after_score}**",
        "",
        "## Notes",
        "",
    ]
    for n in rep.notes:
        lines.append(f"- {n}")
    lines += ["", "## Layers below threshold (after)", ""]
    for L in rep.all_layers_after:
        if L.get("below_threshold"):
            lines.append(f"- `{L['layer_id']}`: {L['score']:.1f}% — {L['title']}")
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")
