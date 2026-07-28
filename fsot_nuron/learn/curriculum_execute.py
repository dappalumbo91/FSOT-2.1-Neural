"""
Execute a gap-driven curriculum as a sequence of short-horizon learning units.

Each step:
  1. Plan prefers weak symbols
  2. One short-horizon encode (docs + media) is the *unit of learning*
  3. Metrics (recall, pixel-id, caption-bind) are logged before/after the sequence

This is the multi-step snowball: short-horizon is the atom; curriculum is the chain.
Does not claim full self-directed open-world agency until execute-without-human-lists
improves a pre-registered metric vs fixed order on a held budget.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..paths import ARTIFACTS, DATA
from ..seeds import SEEDS
from .curriculum import plan_curriculum, CurriculumPlan, census_from_episodes
from .short_horizon import run_short_horizon_learn, ShortHorizonReport
from ..knowledge.episode_memory import default_memory_dir


@dataclass
class CurriculumStepResult:
    step: int
    target_symbol: str
    short_horizon_ok: bool
    recall_top1: float
    pixel_id_top1: float
    caption_bind_top1: float
    learning_probe_top1: float
    elapsed_min: float
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CurriculumExecuteReport:
    ok: bool
    n_steps: int
    plan_path: str
    before_recall: float
    after_recall: float
    before_pixel: float
    after_pixel: float
    before_caption: float
    after_caption: float
    metric_delta_recall: float
    metric_delta_pixel: float
    metric_delta_vs_fixed_order: float
    step_results: List[CurriculumStepResult] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _snapshot_metrics(
    *,
    max_docs: int,
    max_videos: int,
    media_frames: int,
    seed: int,
    mem_root: Path,
    light: bool = True,
) -> ShortHorizonReport:
    """One short-horizon unit (optionally lighter for mid-curriculum steps)."""
    return run_short_horizon_learn(
        max_docs=max_docs,
        max_videos=max_videos,
        media_frames=media_frames,
        seed=seed,
        memory_root=mem_root,
        run_pixel_id=True,
        run_learning_probe=not light,  # full SME probe on bookend steps
        run_caption_bind=True,
    )


def execute_curriculum(
    *,
    max_steps: int = 3,
    docs_per_step: int = 2,
    videos_per_step: int = 2,
    frames_per_step: int = 8,
    seed: int = 7,
    memory_root: Optional[Path] = None,
) -> CurriculumExecuteReport:
    """
    Plan gap curriculum → run short-horizon once per step → measure deltas.
    """
    notes: List[str] = []
    started = datetime.now(timezone.utc)
    mem_root = memory_root or (ARTIFACTS / "episode_memory_curriculum")
    mem_root.mkdir(parents=True, exist_ok=True)

    # Seed census from any existing short-horizon memory if present
    seed_census = census_from_episodes(root=ARTIFACTS / "episode_memory_short", limit=40)
    if not seed_census:
        seed_census = census_from_episodes(root=mem_root, limit=40)
    plan = plan_curriculum(seed_census or None, max_steps=max_steps, write=True, root=mem_root)
    notes.append(f"plan steps={len(plan.steps)} path={plan.plan_path}")
    notes.append(f"gap_order={plan.gap_order[:8]}")

    # Baseline unit (full probe)
    base = _snapshot_metrics(
        max_docs=docs_per_step,
        max_videos=videos_per_step,
        media_frames=frames_per_step,
        seed=seed,
        mem_root=mem_root,
        light=False,
    )
    notes.append(
        f"baseline recall={base.recall_top1:.3f} pixel={base.pixel_id_top1:.3f} "
        f"caption={base.caption_bind_top1:.3f} ok={base.ok}"
    )

    step_results: List[CurriculumStepResult] = []
    for i, step in enumerate(plan.steps[:max_steps]):
        # Each step is a short-horizon unit; seed shifts for diversity
        sh = _snapshot_metrics(
            max_docs=docs_per_step,
            max_videos=videos_per_step + (1 if step.suggested_kind == "media" else 0),
            media_frames=frames_per_step,
            seed=seed + 11 * (i + 1),
            mem_root=mem_root,
            light=True,
        )
        step_results.append(
            CurriculumStepResult(
                step=step.step,
                target_symbol=step.target_symbol,
                short_horizon_ok=sh.ok,
                recall_top1=sh.recall_top1,
                pixel_id_top1=sh.pixel_id_top1,
                caption_bind_top1=sh.caption_bind_top1,
                learning_probe_top1=sh.learning_probe_top1,
                elapsed_min=sh.encode_minutes_est,
                notes=[f"kind={step.suggested_kind}", step.reason] + sh.notes[:4],
            )
        )
        notes.append(
            f"step {step.step} target={step.target_symbol} "
            f"recall={sh.recall_top1:.3f} pixel={sh.pixel_id_top1:.3f}"
        )

    # Final unit (full probe)
    final = _snapshot_metrics(
        max_docs=docs_per_step + 1,
        max_videos=videos_per_step + 1,
        media_frames=frames_per_step + 2,
        seed=seed + 99,
        mem_root=mem_root,
        light=False,
    )
    notes.append(
        f"final recall={final.recall_top1:.3f} pixel={final.pixel_id_top1:.3f} "
        f"caption={final.caption_bind_top1:.3f} ok={final.ok}"
    )

    d_rec = float(final.recall_top1 - base.recall_top1)
    d_pix = float(final.pixel_id_top1 - base.pixel_id_top1)
    d_cap = float(final.caption_bind_top1 - base.caption_bind_top1)
    # Composite climb score vs synthetic fixed-order delta from plan
    ok = final.ok and (
        d_rec >= -0.05  # hold or improve recall
        and (final.pixel_id_top1 >= 0.5 or final.caption_bind_pairs >= 0)
    )

    finished = datetime.now(timezone.utc)
    rep = CurriculumExecuteReport(
        ok=ok,
        n_steps=len(step_results),
        plan_path=plan.plan_path,
        before_recall=base.recall_top1,
        after_recall=final.recall_top1,
        before_pixel=base.pixel_id_top1,
        after_pixel=final.pixel_id_top1,
        before_caption=base.caption_bind_top1,
        after_caption=final.caption_bind_top1,
        metric_delta_recall=d_rec,
        metric_delta_pixel=d_pix,
        metric_delta_vs_fixed_order=float(plan.metric_delta_vs_fixed_order),
        step_results=step_results,
        notes=notes
        + [
            f"Δcaption_top1={d_cap:.3f}",
            f"plan synthetic Δ_vs_fixed={plan.metric_delta_vs_fixed_order:.4f}",
            "Unit of learning = short_horizon; chain = curriculum steps.",
        ],
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
    )

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out_j = ARTIFACTS / "curriculum_execute_last.json"
    out_j.write_text(json.dumps(rep.to_dict(), indent=2, default=str), encoding="utf-8")
    md = DATA / "results" / "CURRICULUM_EXECUTE.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Curriculum execute (short-horizon units)",
        "",
        f"Time: `{rep.started_at}` → `{rep.finished_at}`",
        f"OK: **{rep.ok}**  steps=**{rep.n_steps}**",
        "",
        f"- recall **{rep.before_recall:.3f}** → **{rep.after_recall:.3f}** (Δ={rep.metric_delta_recall:+.3f})",
        f"- pixel_id **{rep.before_pixel:.3f}** → **{rep.after_pixel:.3f}** (Δ={rep.metric_delta_pixel:+.3f})",
        f"- caption→name **{rep.before_caption:.3f}** → **{rep.after_caption:.3f}**",
        f"- plan Δ_vs_fixed (synthetic)={rep.metric_delta_vs_fixed_order:.4f}",
        "",
        "## Steps",
        "",
    ]
    for s in step_results:
        lines.append(
            f"- step {s.step} `{s.target_symbol}`: recall={s.recall_top1:.3f} "
            f"pixel={s.pixel_id_top1:.3f} caption={s.caption_bind_top1:.3f} "
            f"ok={s.short_horizon_ok}"
        )
    lines += ["", "## Notes", ""]
    for n in notes:
        lines.append(f"- {n}")
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")
    return rep
