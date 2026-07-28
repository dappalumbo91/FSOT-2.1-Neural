"""
FSOT-native precision climb for Allen class rates.

Doctrine:
  - Do NOT fit free parameters on S = K(T1+T2+T3) or seeds.
  - Only phenotype timing knobs (already scalpel domain): R, fi_stim, thr, adapt.
  - Step sizes from full spine: φ, e, π, **POOF**, **SUCTION**, consciousness gate.
  - Near 1% band: FI-only (POOF/SUCTION dual); avoid coarse ±R overshoot.
  - Rollback if error worsens (immune / proofreading).

Target: push rel_err ≤ 1% on Pyr/PV/SST/VIP when 2% already holds.
"""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Sequence

import torch

from .seeds import SEEDS
from .scalpel_rate import (
    ScalpelReport,
    ScalpelClassState,
    scalpel_calibrate,
    _apply_class_knobs,
    _measure,
    init_knobs_from_targets,
)
from .class_ephys import ClassEphysTarget
from .neuron_batch import FSOTNeuronBatch


def _seed_step_R_ms(err: float) -> float:
    """
    Continuous refractory delta in **milliseconds** (not integer steps).
    Uses POOF for fine scale near 1% band — this is the timing fix.
    too fast (err>0) → +R_ms; too slow → −R_ms.
    """
    if abs(err) < 1e-9:
        return 0.0
    s = SEEDS
    # Fine: fraction of a ms from POOF/φ; coarser if far
    if abs(err) <= 0.02:
        mag = s.poof * s.phi * min(2.0, abs(err) / 0.01)  # ~0.15–0.5 ms
    else:
        mag = min(2.0, s.phi * abs(err) / 0.02)
    return mag if err > 0 else -mag


def _seed_fi_factor(err: float) -> float:
    """
    FI tweak using POOF/SUCTION dual (archive term3 valves) + consciousness gate.
    too fast (err>0) → reduce FI; too slow → increase.
    """
    s = SEEDS
    # Dual amplitude: POOF (dispersal valve) + SUCTION (inflow dual)
    dual = 0.5 * (abs(s.poof) + abs(s.suction))
    gate = s.phi / (1.0 + s.phi)  # consciousness gate φ/(1+φ)
    amp = dual * gate * min(1.0, abs(err) / 0.015) * (1.0 / (s.e * s.pi))
    amp = min(0.08, max(0.002, amp))  # cap so we don't blow the 2% floor
    return 1.0 - math.copysign(amp, err)


def precision_micro_climb(
    net: FSOTNeuronBatch,
    labels: List[str],
    phenotypes: List[Dict[str, float]],
    targets: Dict[str, ClassEphysTarget],
    *,
    tol: float = 0.01,
    max_rounds: int = 40,
    steps: int = 1400,
    seed_order: Optional[List[str]] = None,
) -> ScalpelReport:
    """
    1) Run standard scalpel to 2% (or current).
    2) Micro-adjust seed-scaled knobs until ≤ tol or budget.
    """
    # First lock at 2% floor
    base = scalpel_calibrate(
        net,
        labels,
        phenotypes,
        targets,
        focus_order=seed_order or ["Pyr", "PV", "SST", "VIP"],
        tol=max(tol, 0.02),
        max_iters=28,
        steps=steps,
        require_classes=seed_order or ["Pyr", "PV", "SST", "VIP"],
    )

    n = len(labels)
    base_d_eff = torch.tensor(
        [float(phenotypes[i]["d_eff"]) for i in range(n)],
        device=net.device,
        dtype=net.dtype,
    )
    base_vrest = torch.tensor(
        [float(phenotypes[i].get("vrest_mV", -70.0)) for i in range(n)],
        device=net.device,
        dtype=net.dtype,
    )
    base_adec = torch.tensor(
        [float(phenotypes[i].get("adapt_decay", 0.988)) for i in range(n)],
        device=net.device,
        dtype=net.dtype,
    )

    knobs = base.classes
    order = [c for c in (seed_order or ["Pyr", "PV", "SST", "VIP"]) if c in knobs]
    report = ScalpelReport(tol=tol, classes=knobs, history=list(base.history))
    report.history.append({"phase": "precision_climb_start", "tol": tol})

    for rnd in range(1, max_rounds + 1):
        # which classes still outside tol?
        offenders = []
        for lab in order:
            st = knobs[lab]
            if st.target_Hz > 1 and st.rel_err == st.rel_err and st.rel_err > tol:
                offenders.append(lab)
        if not offenders:
            break

        # largest error first
        offenders.sort(key=lambda c: -knobs[c].rel_err)
        focus = offenders[0]
        st = knobs[focus]
        m, tgt = st.measured_Hz, st.target_Hz
        if m != m or tgt <= 0:
            continue
        err = (m - tgt) / tgt
        err_abs_before = abs(err)

        # Snapshot for rollback if error worsens (immune / proofreading)
        cur_R = (
            float(st.refractory_ms)
            if st.refractory_ms == st.refractory_ms
            else float(st.refractory_steps)
        )
        snap = (
            cur_R,
            st.fi_stim,
            st.fire_threshold,
            st.adapt_step,
            st.adapt_gain,
        )

        dR = _seed_step_R_ms(err)
        cur_R = max(3.0, min(200.0, cur_R + dR))
        st.refractory_ms = cur_R
        st.refractory_steps = max(1, int(round(cur_R)))
        # POOF/SUCTION + consciousness-gate FI micro-step
        st.fi_stim = float(max(0.25, min(1.85, st.fi_stim * _seed_fi_factor(err))))
        if abs(err) > 0.015:
            thr_nudge = SEEDS.c_factor * 0.01 * (1.0 if err > 0 else -1.0)
            st.fire_threshold = float(max(0.80, min(1.15, st.fire_threshold + thr_nudge)))
        st.iters = st.iters + 1

        _apply_class_knobs(net, labels, knobs, base_d_eff, base_vrest, base_adec)
        measured = _measure(net, labels, steps)
        for lab, ks in knobs.items():
            mm = measured.get(lab, float("nan"))
            ks.measured_Hz = mm
            if ks.target_Hz > 1 and mm == mm:
                ks.rel_err = abs(mm - ks.target_Hz) / ks.target_Hz

        # Rollback if this class got worse
        new_err = knobs[focus].rel_err
        rolled = False
        if new_err == new_err and new_err > err_abs_before + 1e-6:
            (
                cur_R,
                st.fi_stim,
                st.fire_threshold,
                st.adapt_step,
                st.adapt_gain,
            ) = snap
            st.refractory_ms = cur_R
            st.refractory_steps = max(1, int(round(cur_R)))
            _apply_class_knobs(net, labels, knobs, base_d_eff, base_vrest, base_adec)
            measured = _measure(net, labels, steps)
            for lab, ks in knobs.items():
                mm = measured.get(lab, float("nan"))
                ks.measured_Hz = mm
                if ks.target_Hz > 1 and mm == mm:
                    ks.rel_err = abs(mm - ks.target_Hz) / ks.target_Hz
            rolled = True

        report.history.append(
            {
                "phase": "precision_micro",
                "round": rnd,
                "focus": focus,
                "err_before": err,
                "dR_ms": dR,
                "R_ms": st.refractory_ms,
                "rolled_back": rolled,
                "measured": dict(measured),
                "rel_err": {k: knobs[k].rel_err for k in knobs},
            }
        )

    report.ok = all(
        knobs[c].rel_err == knobs[c].rel_err and knobs[c].rel_err <= tol
        for c in order
        if knobs[c].target_Hz > 1
    )
    report.tol = tol
    report.classes = knobs
    return report


def climb_summary(report: ScalpelReport) -> Dict[str, Any]:
    return {
        "ok": report.ok,
        "tol": report.tol,
        "classes": {
            k: {
                "target_Hz": v.target_Hz,
                "measured_Hz": v.measured_Hz,
                "rel_err": v.rel_err,
                "within_tol": v.rel_err == v.rel_err and v.rel_err <= report.tol,
                "R": v.refractory_steps,
                "fi": v.fi_stim,
            }
            for k, v in report.classes.items()
        },
        "n_history": len(report.history),
        "method": "seed-scaled R/FI/thr micro-steps; FSOT seeds fixed",
        "free_parameters_on_S": 0,
    }
