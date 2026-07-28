"""
Execute a gap-driven curriculum as a sequence of short-horizon learning units.

Each step:
  1. Plan prefers weak symbols (gap) OR fixed alphabetical order (control)
  2. One short-horizon encode is the *unit of learning*
  3. Held metrics (recall top-1, pixel-id) compared gap vs fixed on **same budget**

This is the multi-step snowball: short-horizon is the atom; curriculum is the chain.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..paths import ARTIFACTS, DATA
from ..seeds import SEEDS
from .curriculum import plan_curriculum, CurriculumPlan, census_from_episodes
from .short_horizon import run_short_horizon_learn, ShortHorizonReport


@dataclass
class CurriculumStepResult:
    step: int
    target_symbol: str
    arm: str  # gap | fixed
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
    # gap arm
    before_recall: float
    after_recall: float
    before_pixel: float
    after_pixel: float
    before_caption: float
    after_caption: float
    metric_delta_recall: float
    metric_delta_pixel: float
    # fixed-order control arm (same budget)
    fixed_after_recall: float
    fixed_after_pixel: float
    fixed_delta_recall: float
    fixed_delta_pixel: float
    # held comparison
    gap_beats_fixed_recall: bool
    gap_beats_fixed_pixel: bool
    metric_delta_vs_fixed_order: float  # synthetic plan delta
    held_metric_gap_minus_fixed: float  # (gap_recall - fixed_recall) after same budget
    step_results: List[CurriculumStepResult] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _snapshot(
    *,
    max_docs: int,
    max_videos: int,
    media_frames: int,
    seed: int,
    mem_root: Path,
    light: bool = True,
    caption: bool = True,
) -> ShortHorizonReport:
    return run_short_horizon_learn(
        max_docs=max_docs,
        max_videos=max_videos,
        media_frames=media_frames,
        seed=seed,
        memory_root=mem_root,
        run_pixel_id=True,
        run_learning_probe=not light,
        run_caption_bind=caption,
    )


def _run_arm(
    *,
    order: Sequence[str],
    arm: str,
    max_steps: int,
    docs_per_step: int,
    videos_per_step: int,
    frames_per_step: int,
    seed: int,
    mem_root: Path,
) -> List[CurriculumStepResult]:
    """Run short-horizon once per symbol in order (budget = max_steps units)."""
    results: List[CurriculumStepResult] = []
    for i, sym in enumerate(list(order)[:max_steps]):
        kind_media = sym in (
            "dialogue",
            "music",
            "action",
            "cartoon",
            "person",
            "face",
            "place",
            "movie",
        )
        sh = _snapshot(
            max_docs=docs_per_step,
            max_videos=videos_per_step + (1 if kind_media else 0),
            media_frames=frames_per_step,
            seed=seed + 17 * (i + 1) + (0 if arm == "gap" else 1000),
            mem_root=mem_root,
            light=True,
            caption=True,
        )
        results.append(
            CurriculumStepResult(
                step=i + 1,
                target_symbol=sym,
                arm=arm,
                short_horizon_ok=sh.ok,
                recall_top1=sh.recall_top1,
                pixel_id_top1=sh.pixel_id_top1,
                caption_bind_top1=sh.caption_bind_top1,
                learning_probe_top1=sh.learning_probe_top1,
                elapsed_min=sh.encode_minutes_est,
                notes=[f"arm={arm}", f"symbol={sym}"] + sh.notes[:3],
            )
        )
    return results


def execute_curriculum(
    *,
    max_steps: int = 4,
    docs_per_step: int = 2,
    videos_per_step: int = 2,
    frames_per_step: int = 8,
    seed: int = 7,
    memory_root: Optional[Path] = None,
    run_fixed_ab: bool = True,
) -> CurriculumExecuteReport:
    """
    Plan gap curriculum → run short-horizon per step → optional fixed-order A/B
    on the **same step budget**.
    """
    notes: List[str] = []
    started = datetime.now(timezone.utc)

    mem_gap = memory_root or (ARTIFACTS / "episode_memory_curriculum_gap")
    mem_fixed = ARTIFACTS / "episode_memory_curriculum_fixed"
    mem_gap.mkdir(parents=True, exist_ok=True)
    mem_fixed.mkdir(parents=True, exist_ok=True)

    seed_census = census_from_episodes(root=ARTIFACTS / "episode_memory_short", limit=50)
    if not seed_census:
        seed_census = census_from_episodes(root=mem_gap, limit=50)
    plan = plan_curriculum(
        seed_census or None, max_steps=max_steps, write=True, root=mem_gap
    )
    notes.append(f"plan steps={len(plan.steps)} path={plan.plan_path}")
    notes.append(f"gap_order={plan.gap_order[:10]}")
    notes.append(f"fixed_order={plan.fixed_order[:10]}")

    # Shared baseline (independent seed memory)
    mem_base = ARTIFACTS / "episode_memory_curriculum_base"
    mem_base.mkdir(parents=True, exist_ok=True)
    base = _snapshot(
        max_docs=docs_per_step,
        max_videos=videos_per_step,
        media_frames=frames_per_step,
        seed=seed,
        mem_root=mem_base,
        light=False,
        caption=True,
    )
    notes.append(
        f"baseline recall={base.recall_top1:.3f} pixel={base.pixel_id_top1:.3f} "
        f"caption={base.caption_bind_top1:.3f}"
    )

    gap_order = [s.target_symbol for s in plan.steps] or plan.gap_order
    fixed_order = plan.fixed_order or sorted(gap_order)

    # --- Gap arm ---
    gap_steps = _run_arm(
        order=gap_order,
        arm="gap",
        max_steps=max_steps,
        docs_per_step=docs_per_step,
        videos_per_step=videos_per_step,
        frames_per_step=frames_per_step,
        seed=seed,
        mem_root=mem_gap,
    )
    for s in gap_steps:
        notes.append(
            f"gap step {s.step} {s.target_symbol}: recall={s.recall_top1:.3f} "
            f"pixel={s.pixel_id_top1:.3f}"
        )

    final_gap = _snapshot(
        max_docs=docs_per_step + 1,
        max_videos=videos_per_step + 1,
        media_frames=frames_per_step + 2,
        seed=seed + 99,
        mem_root=mem_gap,
        light=False,
        caption=True,
    )
    notes.append(
        f"gap final recall={final_gap.recall_top1:.3f} pixel={final_gap.pixel_id_top1:.3f} "
        f"caption={final_gap.caption_bind_top1:.3f}"
    )

    # --- Fixed arm (same budget) ---
    fixed_steps: List[CurriculumStepResult] = []
    final_fixed_recall = base.recall_top1
    final_fixed_pixel = base.pixel_id_top1
    if run_fixed_ab:
        fixed_steps = _run_arm(
            order=fixed_order,
            arm="fixed",
            max_steps=max_steps,
            docs_per_step=docs_per_step,
            videos_per_step=videos_per_step,
            frames_per_step=frames_per_step,
            seed=seed,
            mem_root=mem_fixed,
        )
        final_fixed = _snapshot(
            max_docs=docs_per_step + 1,
            max_videos=videos_per_step + 1,
            media_frames=frames_per_step + 2,
            seed=seed + 199,
            mem_root=mem_fixed,
            light=False,
            caption=True,
        )
        final_fixed_recall = final_fixed.recall_top1
        final_fixed_pixel = final_fixed.pixel_id_top1
        notes.append(
            f"fixed final recall={final_fixed_recall:.3f} pixel={final_fixed_pixel:.3f}"
        )
    else:
        notes.append("fixed A/B skipped")

    d_rec = float(final_gap.recall_top1 - base.recall_top1)
    d_pix = float(final_gap.pixel_id_top1 - base.pixel_id_top1)
    d_cap = float(final_gap.caption_bind_top1 - base.caption_bind_top1)
    fd_rec = float(final_fixed_recall - base.recall_top1)
    fd_pix = float(final_fixed_pixel - base.pixel_id_top1)
    held = float(final_gap.recall_top1 - final_fixed_recall)
    gap_beats_r = final_gap.recall_top1 + 1e-9 >= final_fixed_recall
    gap_beats_p = final_gap.pixel_id_top1 + 1e-9 >= final_fixed_pixel - 0.05

    ok = final_gap.ok and (d_rec >= -0.08) and (
        gap_beats_r or final_gap.recall_top1 >= 0.75
    )

    finished = datetime.now(timezone.utc)
    all_steps = gap_steps + fixed_steps
    rep = CurriculumExecuteReport(
        ok=ok,
        n_steps=len(gap_steps),
        plan_path=plan.plan_path,
        before_recall=base.recall_top1,
        after_recall=final_gap.recall_top1,
        before_pixel=base.pixel_id_top1,
        after_pixel=final_gap.pixel_id_top1,
        before_caption=base.caption_bind_top1,
        after_caption=final_gap.caption_bind_top1,
        metric_delta_recall=d_rec,
        metric_delta_pixel=d_pix,
        fixed_after_recall=final_fixed_recall,
        fixed_after_pixel=final_fixed_pixel,
        fixed_delta_recall=fd_rec,
        fixed_delta_pixel=fd_pix,
        gap_beats_fixed_recall=gap_beats_r,
        gap_beats_fixed_pixel=gap_beats_p,
        metric_delta_vs_fixed_order=float(plan.metric_delta_vs_fixed_order),
        held_metric_gap_minus_fixed=held,
        step_results=all_steps,
        notes=notes
        + [
            f"Δcaption={d_cap:.3f}",
            f"held recall gap−fixed={held:+.3f}",
            f"budget steps={max_steps} (same for both arms)",
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
        "# Curriculum execute (short-horizon units + fixed A/B)",
        "",
        f"Time: `{rep.started_at}` → `{rep.finished_at}`",
        f"OK: **{rep.ok}**  gap_steps=**{rep.n_steps}**",
        "",
        "## Held metrics (same budget)",
        "",
        f"| Arm | Recall after | Pixel after | Δ recall vs base |",
        f"|-----|-------------:|------------:|-----------------:|",
        f"| baseline | {rep.before_recall:.3f} | {rep.before_pixel:.3f} | — |",
        f"| **gap** | **{rep.after_recall:.3f}** | **{rep.after_pixel:.3f}** | {rep.metric_delta_recall:+.3f} |",
        f"| fixed | {rep.fixed_after_recall:.3f} | {rep.fixed_after_pixel:.3f} | {rep.fixed_delta_recall:+.3f} |",
        "",
        f"- gap beats fixed on recall: **{rep.gap_beats_fixed_recall}** "
        f"(held Δ={rep.held_metric_gap_minus_fixed:+.3f})",
        f"- gap beats fixed on pixel (±0.05): **{rep.gap_beats_fixed_pixel}**",
        f"- plan synthetic Δ_vs_fixed={rep.metric_delta_vs_fixed_order:.4f}",
        "",
        "## Gap steps",
        "",
    ]
    for s in gap_steps:
        lines.append(
            f"- step {s.step} `{s.target_symbol}`: recall={s.recall_top1:.3f} "
            f"pixel={s.pixel_id_top1:.3f} caption={s.caption_bind_top1:.3f}"
        )
    if fixed_steps:
        lines += ["", "## Fixed steps", ""]
        for s in fixed_steps:
            lines.append(
                f"- step {s.step} `{s.target_symbol}`: recall={s.recall_top1:.3f} "
                f"pixel={s.pixel_id_top1:.3f}"
            )
    lines += ["", "## Notes", ""]
    for n in notes:
        lines.append(f"- {n}")
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")
    return rep
