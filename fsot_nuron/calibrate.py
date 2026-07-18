"""
FSOT-grade analytical + light polish calibration.

ISI:    set ref_steps from Allen avg_isi (integer ms lock)
Adapt:  set adapt_step from closed-form so
          A ≈ ((n-1)·δ)/(2·R+(n-1)·δ) matches Allen adaptation index
Polish: 1–2 short FI probes to snap residual population bias

Precision ledger: median / mean / max relative error (SMILES Lab style).
"""

from __future__ import annotations

from typing import Any, Dict, List

import torch

from .bio_metrics import population_profiles
from .modes import OperatingMode
from .neuron_batch import FSOTNeuronBatch


def _per_unit_metrics(net: FSOTNeuronBatch, steps: int) -> List[Dict[str, float]]:
    net.reset()
    hist = net.run(steps, stimulus_pattern="fi_step", record=True)
    profiles = population_profiles(hist["fired"], hist["S"])
    return [
        {
            "isi": p.mean_isi_ms,
            "adapt": p.adaptation_index,
            "rate": p.firing_rate_Hz,
            "spikes": float(p.spike_count),
        }
        for p in profiles
    ]


def _err_stats(errors: List[float]) -> Dict[str, float]:
    good = sorted(e for e in errors if e == e)
    if not good:
        return {"median": float("nan"), "mean": float("nan"), "max": float("nan"), "n": 0.0}
    n = len(good)
    return {
        "median": good[n // 2],
        "mean": sum(good) / n,
        "max": good[-1],
        "n": float(n),
    }


def _adapt_step_from_target(R: float, ad: float, n_isi: float = 10.0) -> float:
    """
    Solve A = ((n-1)·δ) / (2·R + (n-1)·δ) for δ.
    A = adaptation index, R = base ISI ms, n_isi = intervals in train.
    """
    A = max(0.0, min(0.5, float(ad)))
    R = max(8.0, float(R))
    n1 = max(2.0, n_isi - 1.0)
    # A*(2R + n1*d) = n1*d  =>  2 A R = n1 d (1-A)  => d = 2 A R / (n1 (1-A))
    if A < 1e-6:
        return 0.0
    d = (2.0 * A * R) / (n1 * (1.0 - A) + 1e-9)
    return float(max(0.0, min(8.0, d)))


def analytical_lock(
    net: FSOTNeuronBatch,
    params: List[Dict[str, float]],
    *,
    mode: str = "bio_match",
) -> Dict[str, Any]:
    """Direct per-unit lock from Allen targets (no free scalar params)."""
    op = OperatingMode.parse(mode)
    isi_scale = 1.0 if op is OperatingMode.BIO_MATCH else 1.0 / 3.0
    refs = []
    steps = []
    for p in params:
        isi = p.get("avg_isi_ms_target", 70.0)
        if isi != isi or isi < 5:
            isi = 70.0
        isi = float(isi) * isi_scale
        ad = p.get("adaptation_target", 0.05)
        if ad != ad:
            ad = 0.05
        # Mean ISI ≈ R + 0.5*(n-1)*δ mid-train; set R so mean ≈ isi target
        # Approximate: use R = isi * (1 - 0.5*A) as base floor
        A = max(0.0, min(0.4, float(ad)))
        R = isi * (1.0 - 0.45 * A)
        R = max(6.0, min(180.0, R))
        d = _adapt_step_from_target(R, A, n_isi=10.0)
        refs.append(int(round(R)))
        steps.append(d)

    net.ref_steps = torch.tensor(refs, device=net.device, dtype=torch.int32)
    net.adapt_step = torch.tensor(steps, device=net.device, dtype=net.dtype)
    return {
        "mean_ref": sum(refs) / len(refs),
        "mean_adapt_step": sum(steps) / len(steps),
        "isi_scale": isi_scale,
    }


def calibrate_batch(
    net: FSOTNeuronBatch,
    params: List[Dict[str, float]],
    *,
    mode: str = "bio_match",
    steps: int = 1000,
    max_iters: int = 4,
    isi_tol: float = 0.005,
    adapt_tol: float = 0.02,
    grade: str = "fsot",
) -> Dict[str, Any]:
    if not params:
        return {"ok": False, "reason": "no params", "iters": []}

    if grade == "fsot":
        isi_tol = min(isi_tol, 0.005)
        adapt_tol = min(adapt_tol, 0.02)
        steps = max(steps, 1000)
        max_iters = max(max_iters, 4)

    op = OperatingMode.parse(mode)
    isi_scale = 1.0 if op is OperatingMode.BIO_MATCH else 1.0 / 3.0
    targets_isi = []
    targets_ad = []
    for p in params:
        isi = p.get("avg_isi_ms_target", 70.0)
        if isi != isi or isi < 5:
            isi = 70.0
        ad = p.get("adaptation_target", 0.05)
        if ad != ad:
            ad = 0.05
        targets_isi.append(float(isi) * isi_scale)
        targets_ad.append(float(ad))

    lock = analytical_lock(net, params, mode=mode)
    history: List[Dict[str, Any]] = []

    for it in range(max_iters):
        rows = _per_unit_metrics(net, steps=steps)
        isi_errs, ad_errs = [], []
        B = min(net.cfg.n_units, len(rows), len(targets_isi))
        for b in range(B):
            isi_sim, ad_sim = rows[b]["isi"], rows[b]["adapt"]
            ti, ta = targets_isi[b], targets_ad[b]
            if isi_sim == isi_sim and isi_sim > 1:
                isi_errs.append(abs(isi_sim - ti) / ti)
            if ad_sim == ad_sim and abs(ta) > 1e-6:
                ad_errs.append(abs(ad_sim - ta) / abs(ta))
            elif ad_sim == ad_sim:
                ad_errs.append(abs(ad_sim - ta))

        isi_stats = _err_stats(isi_errs)
        ad_stats = _err_stats(ad_errs)
        history.append(
            {
                "iter": it,
                "isi_error": isi_stats,
                "adapt_error": ad_stats,
                "pop_mean_isi": sum(r["isi"] for r in rows if r["isi"] == r["isi"])
                / max(1, sum(1 for r in rows if r["isi"] == r["isi"])),
                "pop_mean_adapt": sum(r["adapt"] for r in rows if r["adapt"] == r["adapt"])
                / max(1, sum(1 for r in rows if r["adapt"] == r["adapt"])),
            }
        )

        if (
            isi_stats["median"] == isi_stats["median"]
            and isi_stats["median"] <= isi_tol
            and ad_stats["median"] == ad_stats["median"]
            and ad_stats["median"] <= adapt_tol
        ):
            break

        # Per-unit residual polish
        new_ref = net.ref_steps.float().clone()
        new_step = net.adapt_step.clone()
        for b in range(B):
            isi_sim, ad_sim = rows[b]["isi"], rows[b]["adapt"]
            ti, ta = targets_isi[b], targets_ad[b]
            if isi_sim == isi_sim and isi_sim > 1:
                fac = ti / isi_sim
                fac = 1.0 + 0.9 * (fac - 1.0)
                fac = max(0.85, min(1.18, fac))
                new_ref[b] = max(4.0, min(200.0, float(new_ref[b].item()) * fac))
            if ad_sim == ad_sim:
                if abs(ad_sim) < 1e-5 and abs(ta) > 0.005:
                    sfac = 1.8
                else:
                    sfac = abs(ta) / max(abs(ad_sim), 1e-4)
                sfac = 1.0 + 0.85 * (sfac - 1.0)
                sfac = max(0.4, min(2.5, sfac))
                new_step[b] = max(0.0, min(8.0, float(new_step[b].item()) * sfac))
        net.ref_steps = new_ref.round().to(torch.int32)
        net.adapt_step = new_step

    # Population mean snap — FSOT-grade lock on sample means (Allen cross-ref)
    pop_tgt_isi = sum(targets_isi) / len(targets_isi)
    pop_tgt_ad = sum(targets_ad) / len(targets_ad)
    rows = _per_unit_metrics(net, steps=steps)
    pop_isi = sum(r["isi"] for r in rows if r["isi"] == r["isi"]) / max(
        1, sum(1 for r in rows if r["isi"] == r["isi"])
    )
    pop_ad = sum(r["adapt"] for r in rows if r["adapt"] == r["adapt"]) / max(
        1, sum(1 for r in rows if r["adapt"] == r["adapt"])
    )
    if pop_isi == pop_isi and pop_isi > 1:
        fac = pop_tgt_isi / pop_isi
        fac = max(0.92, min(1.08, fac))
        net.ref_steps = (net.ref_steps.float() * fac).round().clamp(4, 200).to(torch.int32)
    if pop_ad == pop_ad and abs(pop_ad) > 1e-6 and abs(pop_tgt_ad) > 1e-6:
        sfac = abs(pop_tgt_ad) / abs(pop_ad)
        sfac = max(0.7, min(1.5, sfac))
        net.adapt_step = (net.adapt_step * sfac).clamp(0.0, 8.0)

    # Final measure after snap
    rows = _per_unit_metrics(net, steps=steps)
    isi_errs, ad_errs = [], []
    for b in range(min(len(rows), len(targets_isi))):
        isi_sim, ad_sim = rows[b]["isi"], rows[b]["adapt"]
        ti, ta = targets_isi[b], targets_ad[b]
        if isi_sim == isi_sim and isi_sim > 1:
            isi_errs.append(abs(isi_sim - ti) / ti)
        if ad_sim == ad_sim and abs(ta) > 1e-6:
            ad_errs.append(abs(ad_sim - ta) / abs(ta))
    isi_stats = _err_stats(isi_errs)
    ad_stats = _err_stats(ad_errs)
    pop_isi = sum(r["isi"] for r in rows if r["isi"] == r["isi"]) / max(
        1, sum(1 for r in rows if r["isi"] == r["isi"])
    )
    pop_ad = sum(r["adapt"] for r in rows if r["adapt"] == r["adapt"]) / max(
        1, sum(1 for r in rows if r["adapt"] == r["adapt"])
    )
    pop_isi_err = abs(pop_isi - pop_tgt_isi) / pop_tgt_isi if pop_isi == pop_isi else float("nan")
    pop_ad_err = abs(pop_ad - pop_tgt_ad) / abs(pop_tgt_ad) if pop_ad == pop_ad and abs(pop_tgt_ad) > 1e-9 else float("nan")
    final = {
        "iter": "snap",
        "isi_error": isi_stats,
        "adapt_error": ad_stats,
        "pop_mean_isi": pop_isi,
        "pop_mean_adapt": pop_ad,
        "pop_isi_rel_err": pop_isi_err,
        "pop_adapt_rel_err": pop_ad_err,
    }
    history.append(final)

    # Convergence: population means (Allen sample cross-ref) + median per-unit
    pop_ok = (
        pop_isi_err == pop_isi_err
        and pop_isi_err <= max(isi_tol * 2, 0.01)
        and pop_ad_err == pop_ad_err
        and pop_ad_err <= max(adapt_tol * 2.5, 0.05)
    )
    med_ok = (
        isi_stats.get("median", 9) <= max(isi_tol * 4, 0.03)
        and ad_stats.get("median", 9) <= max(adapt_tol * 5, 0.15)
    )
    return {
        "ok": True,
        "converged": bool(pop_ok),
        "converged_median": bool(med_ok),
        "grade": grade,
        "isi_tol": isi_tol,
        "adapt_tol": adapt_tol,
        "analytical_lock": lock,
        "iters": history,
        "final": final,
        "precision_ledger": {
            "isi_median_error_pct": 100.0 * isi_stats.get("median", float("nan")),
            "isi_mean_error_pct": 100.0 * isi_stats.get("mean", float("nan")),
            "isi_max_error_pct": 100.0 * isi_stats.get("max", float("nan")),
            "adapt_median_error_pct": 100.0 * ad_stats.get("median", float("nan")),
            "adapt_mean_error_pct": 100.0 * ad_stats.get("mean", float("nan")),
            "adapt_max_error_pct": 100.0 * ad_stats.get("max", float("nan")),
            "pop_isi_error_pct": 100.0 * pop_isi_err if pop_isi_err == pop_isi_err else float("nan"),
            "pop_adapt_error_pct": 100.0 * pop_ad_err if pop_ad_err == pop_ad_err else float("nan"),
            "reference": "SMILES Lab style; pop means are primary Allen cross-ref",
            "smiles_lab_median_error_pct_bar": 0.058,
            "note": (
                "1 ms grid limits per-unit ISI to ~1–2% on ~70 ms targets; "
                "population mean and analytical adapt_step are the FSOT-grade locks."
            ),
        },
    }
