"""
Apply Allen scalpel class-rate knobs onto an FSOTBrainDesign population.

Keeps multi-region architecture; only timing/FI phenotype moves.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import torch

from .brain_architecture import FSOTBrainDesign, BrainDesignConfig, run_brain_design_suite
from .class_ephys import build_class_targets
from .scalpel_rate import scalpel_calibrate, ScalpelReport


def scalpel_lock_brain(
    brain: FSOTBrainDesign,
    *,
    tol: float = 0.02,
    max_iters: int = 36,
    steps: int = 1600,
    focus: Optional[List[str]] = None,
) -> Tuple[ScalpelReport, List[str]]:
    """
    Run scalpel on the brain's underlying FSOTNeuronBatch using unit cell_type labels.
    Returns report + labels.
    """
    labels = [u.cell_type for u in brain.units]
    phenotypes = [dict(g.phenotype) for g in brain.genotypes]
    targets = build_class_targets(min_cells=15, mouse_only=True)
    focus = focus or ["Pyr", "PV", "SST", "VIP"]
    focus = [c for c in focus if c in set(labels) and c in targets]

    report = scalpel_calibrate(
        brain.net,
        labels,
        phenotypes,
        targets,
        focus_order=focus,
        tol=tol,
        max_iters=max_iters,
        steps=steps,
        require_classes=focus,
    )
    return report, labels


def build_scalpel_brain(
    profile: str = "ai_efficient",
    device: str = "cpu",
    tol: float = 0.02,
) -> Tuple[FSOTBrainDesign, ScalpelReport, Dict[str, Any]]:
    """
    Construct multi-region brain then scalpel-lock class rates to Allen.
    """
    suite = run_brain_design_suite(
        steps=200,  # short; full dynamics after lock
        device=device,
        scale=1.0,
        profile=profile,
        sensory=False,
    )
    brain: FSOTBrainDesign = suite["brain"]
    report, labels = scalpel_lock_brain(brain, tol=tol)
    meta = {
        "profile": profile,
        "scalpel_ok": report.ok,
        "tol": tol,
        "class_rel_err": {k: v.rel_err for k, v in report.classes.items()},
        "class_measured_Hz": {k: v.measured_Hz for k, v in report.classes.items()},
        "labels_count": {c: labels.count(c) for c in set(labels)},
    }
    return brain, report, meta
