"""
Scalpel targeting: iterative per-class rate lock to wet-lab Allen means.

Biological / model time only (dt_ms). Does not touch free FSOT scalar parameters —
only phenotype timing knobs: refractory_steps, fi_stim, fire_threshold, adapt_step.

Order of operations (project policy):
  1) Close large errors first (e.g. Pyr ~24%)
  2) Then tight errors (e.g. PV ~8%)
  3) Performance tweaks only after bio gates pass
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch

from .class_ephys import ClassEphysTarget, apply_class_targets_to_genotype_phenotype
from .neuron_batch import FSOTNeuronBatch


@dataclass
class ScalpelClassState:
    cell_type: str
    target_Hz: float
    refractory_steps: int
    fi_stim: float
    fire_threshold: float
    adapt_step: float
    adapt_gain: float
    measured_Hz: float = float("nan")
    rel_err: float = float("nan")
    iters: int = 0


@dataclass
class ScalpelReport:
    classes: Dict[str, ScalpelClassState] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    tol: float = 0.05
    ok: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "tol": self.tol,
            "classes": {k: asdict(v) for k, v in self.classes.items()},
            "history": self.history,
        }


def _mean_rate_by_label(
    rates: Sequence[float],
    labels: Sequence[str],
) -> Dict[str, float]:
    buckets: Dict[str, List[float]] = {}
    for r, lab in zip(rates, labels):
        buckets.setdefault(lab, []).append(float(r))
    return {k: sum(v) / len(v) for k, v in buckets.items() if v}


def _apply_class_knobs(
    net: FSOTNeuronBatch,
    labels: List[str],
    knobs: Dict[str, ScalpelClassState],
    base_d_eff: torch.Tensor,
    base_vrest: torch.Tensor,
    base_adec: torch.Tensor,
) -> None:
    n = len(labels)
    refs, thr, fi, ad_step, again = [], [], [], [], []
    for i, lab in enumerate(labels):
        k = knobs[lab]
        refs.append(int(k.refractory_steps))
        thr.append(k.fire_threshold)
        fi.append(k.fi_stim)
        ad_step.append(k.adapt_step)
        again.append(k.adapt_gain)
    net.apply_bio_params(
        d_eff=base_d_eff,
        fire_threshold=torch.tensor(thr, device=net.device, dtype=net.dtype),
        vrest_mV=base_vrest,
        adapt_gain=torch.tensor(again, device=net.device, dtype=net.dtype),
        adapt_decay=base_adec,
        refractory_steps=torch.tensor(refs, device=net.device, dtype=torch.int32),
        fi_stim=torch.tensor(fi, device=net.device, dtype=net.dtype),
        adapt_step=torch.tensor(ad_step, device=net.device, dtype=net.dtype),
        mode_name="scalpel_rate",
    )


def _measure(
    net: FSOTNeuronBatch,
    labels: List[str],
    steps: int,
    *,
    fi_onset_ms: int = 100,
) -> Dict[str, float]:
    """
    Mean class rate during *sustained FI only* (skip fi_step rest head).

    neuron_batch fi_step: zeros for first 100 ms, then constant fi_stim.
    Using full-trace spike_count/T understates rate by ~onset/T — scalpel
    must match wet-lab FI rates in the drive epoch.
    """
    net.reset()
    hist = net.run(steps, stimulus_pattern="fi_step", record=True)
    fired = hist["fired"]  # [T, B]
    T = int(fired.shape[0])
    onset = min(max(0, fi_onset_ms), T - 1)
    window = fired[onset:]
    dur_s = max(1e-9, (T - onset) * float(net.cfg.dt_ms) / 1000.0)
    # per-unit rate in drive window
    spikes = window.float().sum(dim=0)  # [B]
    rates = (spikes / dur_s).detach().cpu().tolist()
    return _mean_rate_by_label(rates, labels)


def init_knobs_from_targets(
    labels: List[str],
    phenotypes: List[Dict[str, float]],
    targets: Dict[str, ClassEphysTarget],
    mode: str = "bio_match",
) -> Dict[str, ScalpelClassState]:
    """Seed knobs from analytical class map (one state per class present)."""
    knobs: Dict[str, ScalpelClassState] = {}
    for lab, ph0 in zip(labels, phenotypes):
        if lab in knobs:
            continue
        ph = apply_class_targets_to_genotype_phenotype(lab, ph0, targets, mode=mode)
        tgt = targets[lab].mean_rate_Hz if lab in targets else ph.get("class_rate_target_Hz", 15.0)
        knobs[lab] = ScalpelClassState(
            cell_type=lab,
            target_Hz=float(tgt),
            refractory_steps=int(round(ph["refractory_steps"])),
            fi_stim=float(ph["fi_stim"]),
            fire_threshold=float(ph["fire_threshold"]),
            adapt_step=float(ph["adapt_step"]),
            adapt_gain=float(ph["adapt_gain"]),
        )
    return knobs


def scalpel_calibrate(
    net: FSOTNeuronBatch,
    labels: List[str],
    phenotypes: List[Dict[str, float]],
    targets: Dict[str, ClassEphysTarget],
    *,
    focus_order: Optional[List[str]] = None,
    tol: float = 0.05,
    max_iters: int = 24,
    steps: int = 1400,
    mode: str = "bio_match",
    require_classes: Optional[List[str]] = None,
) -> ScalpelReport:
    """
    Iteratively adjust per-class timing knobs until |rate - target|/target ≤ tol.

    focus_order: calibrate classes in this order (e.g. ['Pyr', 'PV'] — large error first).
    When focusing class C, only C's knobs move; others held at last good values.
    """
    n = len(labels)
    assert n == net.cfg.n_units

    # Freeze non-timing phenotype tensors from current genotypes
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

    knobs = init_knobs_from_targets(labels, phenotypes, targets, mode=mode)
    order = focus_order or sorted(knobs.keys(), key=lambda c: -abs(
        # largest relative error first after a probe measure
        0.0
    ))

    report = ScalpelReport(tol=tol)

    # Initial measure
    _apply_class_knobs(net, labels, knobs, base_d_eff, base_vrest, base_adec)
    measured = _measure(net, labels, steps)
    for lab, st in knobs.items():
        m = measured.get(lab, float("nan"))
        st.measured_Hz = m
        if st.target_Hz > 1 and m == m:
            st.rel_err = abs(m - st.target_Hz) / st.target_Hz

    # Sort focus by current error descending if default
    if focus_order is None:
        order = sorted(
            knobs.keys(),
            key=lambda c: -(knobs[c].rel_err if knobs[c].rel_err == knobs[c].rel_err else 0.0),
        )

    report.history.append(
        {
            "iter": 0,
            "phase": "init",
            "measured": dict(measured),
            "rel_err": {k: knobs[k].rel_err for k in knobs},
        }
    )

    for focus in order:
        st = knobs[focus]
        if st.target_Hz <= 1:
            continue
        for it in range(1, max_iters + 1):
            st.iters = it
            m = st.measured_Hz
            tgt = st.target_Hz
            if m != m or m <= 0:
                # dead class: boost FI heavily, shorten R
                st.fi_stim = min(1.5, st.fi_stim * 1.2 + 0.05)
                st.refractory_steps = max(3, int(st.refractory_steps * 0.85))
                st.fire_threshold = max(0.82, st.fire_threshold - 0.02)
            else:
                err = (m - tgt) / tgt
                if abs(err) <= tol:
                    break
                # Scalpel: rate ≈ 1000 / R_eff when FI is suprathreshold
                # Adjust R toward 1000/tgt, with measured feedback
                ideal_R = max(3.0, 1000.0 / tgt - 0.5)
                if m < tgt:
                    # too slow: set R from target (rate≈1000/R), boost drive
                    ratio = max(0.15, m / tgt)
                    st.refractory_steps = max(3, int(round(ideal_R * (0.65 + 0.35 * ratio))))
                    # If still missing spikes (m << 1000/R), cut R harder
                    r_max = 1000.0 / max(1, st.refractory_steps)
                    if m < 0.85 * min(tgt, r_max):
                        st.refractory_steps = max(3, int(round(st.refractory_steps * 0.90)))
                    st.fi_stim = min(1.8, st.fi_stim * (1.0 + min(0.35, (tgt - m) / tgt)))
                    st.fire_threshold = max(0.80, st.fire_threshold - 0.02)
                    st.adapt_step = 0.0 if (tgt - m) / tgt > 0.08 else st.adapt_step
                    st.adapt_gain = min(st.adapt_gain, 0.015) if m < 0.8 * tgt else st.adapt_gain
                else:
                    # too fast: lengthen R toward ideal * (m/tgt)
                    ratio = m / tgt
                    st.refractory_steps = min(
                        200, int(round(ideal_R * ratio * 0.55 + st.refractory_steps * 0.45))
                    )
                    st.fi_stim = max(0.28, st.fi_stim * (1.0 - min(0.12, (m - tgt) / tgt)))

            _apply_class_knobs(net, labels, knobs, base_d_eff, base_vrest, base_adec)
            measured = _measure(net, labels, steps)
            for lab, ks in knobs.items():
                mm = measured.get(lab, float("nan"))
                ks.measured_Hz = mm
                if ks.target_Hz > 1 and mm == mm:
                    ks.rel_err = abs(mm - ks.target_Hz) / ks.target_Hz
            report.history.append(
                {
                    "iter": it,
                    "phase": f"focus:{focus}",
                    "focus": focus,
                    "knobs": {
                        focus: {
                            "R": st.refractory_steps,
                            "fi": st.fi_stim,
                            "thr": st.fire_threshold,
                        }
                    },
                    "measured": dict(measured),
                    "rel_err": {k: knobs[k].rel_err for k in knobs},
                }
            )
            if st.rel_err == st.rel_err and st.rel_err <= tol:
                break

    # Final global polish pass (all classes, fewer iters)
    for it in range(1, max(8, max_iters // 2) + 1):
        dirty = False
        for lab, st in knobs.items():
            if st.target_Hz <= 1 or st.rel_err != st.rel_err:
                continue
            if st.rel_err <= tol:
                continue
            dirty = True
            m, tgt = st.measured_Hz, st.target_Hz
            ideal_R = max(3.0, 1000.0 / tgt - 0.5)
            if m < tgt:
                st.refractory_steps = max(3, int(round(0.35 * st.refractory_steps + 0.65 * ideal_R)))
                st.fi_stim = min(1.8, st.fi_stim * 1.1)
                st.fire_threshold = max(0.80, st.fire_threshold - 0.01)
            else:
                st.refractory_steps = min(
                    200, int(round(0.35 * st.refractory_steps + 0.65 * ideal_R * (m / tgt)))
                )
                st.fi_stim = max(0.28, st.fi_stim * 0.95)
        if not dirty:
            break
        _apply_class_knobs(net, labels, knobs, base_d_eff, base_vrest, base_adec)
        measured = _measure(net, labels, steps)
        for lab, ks in knobs.items():
            mm = measured.get(lab, float("nan"))
            ks.measured_Hz = mm
            if ks.target_Hz > 1 and mm == mm:
                ks.rel_err = abs(mm - ks.target_Hz) / ks.target_Hz
        report.history.append(
            {
                "iter": it,
                "phase": "global_polish",
                "measured": dict(measured),
                "rel_err": {k: knobs[k].rel_err for k in knobs},
            }
        )

    report.classes = knobs
    # Success: required classes (default = focus_order or all in targets ∩ knobs)
    need = require_classes or focus_order or [c for c in knobs if c in targets]
    ok = True
    for lab in need:
        if lab not in knobs or lab not in targets:
            ok = False
            continue
        st = knobs[lab]
        if st.rel_err != st.rel_err or st.rel_err > tol:
            ok = False
    report.ok = ok
    return report
