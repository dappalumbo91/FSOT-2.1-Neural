"""
Biological equivalent metrics for FSOT neurons.

Maps fluid-state dynamics onto quantities neuroscientists measure
(firing rate, adaptation, rheobase proxy, Vm, ISI stats) so we can
cross-check against Allen / animal / human cortical data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch


@dataclass
class BioProfile:
    """Per-unit or population bio-equivalent report."""

    firing_rate_Hz: float
    adaptation_index: float
    mean_isi_ms: float
    isi_cv: float
    rheobase_stim: float
    mean_S: float
    mean_Vm_proxy_mV: float
    spike_count: int
    emergent_fraction: float


def isi_stats(fired: torch.Tensor, dt_ms: float = 1.0) -> Tuple[float, float]:
    """
    fired: [T] bool for one unit.
    Returns mean_isi_ms, CV_isi.
    """
    idx = torch.nonzero(fired, as_tuple=False).flatten()
    if idx.numel() < 2:
        return float("nan"), float("nan")
    isi = (idx[1:] - idx[:-1]).float() * dt_ms
    mean = float(isi.mean().item())
    std = float(isi.std(unbiased=False).item()) if isi.numel() > 1 else 0.0
    cv = std / mean if mean > 0 else float("nan")
    return mean, cv


def adaptation_index(fired: torch.Tensor) -> float:
    """
    Allen-like adaptation: (ISI_late - ISI_early) / (ISI_late + ISI_early).

    Uses mean of the first third vs last third of ISIs when the train is long
    enough (more stable than single first/last ISI). Falls back to early/late
    spike-count asymmetry if the unit barely fires.
    """
    idx = torch.nonzero(fired, as_tuple=False).flatten()
    if idx.numel() >= 4:
        isi = (idx[1:] - idx[:-1]).float()
        n = int(isi.numel())
        if n >= 6:
            k = max(1, n // 3)
            early = isi[:k].mean()
            late = isi[-k:].mean()
        elif n >= 3:
            early = isi[:2].mean()
            late = isi[-2:].mean()
        else:
            early = isi[0]
            late = isi[-1]
        return float(((late - early) / (late + early + 1e-6)).item())
    T = fired.shape[0]
    mid = max(1, T // 2)
    early_n = float(fired[:mid].sum().item())
    late_n = float(fired[mid:].sum().item())
    return (early_n - late_n) / (early_n + late_n + 1e-6)


def profile_from_history(
    fired: torch.Tensor,
    S: torch.Tensor,
    vrest_mV: float = -70.0,
    resting_S: float = 0.46,
    s_scale: float = 80.0,
    dt_ms: float = 1.0,
    rheobase_stim: float = float("nan"),
) -> BioProfile:
    """
    fired, S: [T] for a single unit.
    """
    spikes = int(fired.sum().item())
    T = fired.shape[0]
    rate = spikes / (T * dt_ms / 1000.0)
    mean_isi, cv = isi_stats(fired, dt_ms)
    adapt = adaptation_index(fired)
    mean_S = float(S.mean().item())
    vm = vrest_mV + (mean_S - resting_S) * s_scale
    # ternary proxy from S
    emergent = float((S > 0.4).float().mean().item())
    return BioProfile(
        firing_rate_Hz=rate,
        adaptation_index=adapt,
        mean_isi_ms=mean_isi,
        isi_cv=cv,
        rheobase_stim=rheobase_stim,
        mean_S=mean_S,
        mean_Vm_proxy_mV=vm,
        spike_count=spikes,
        emergent_fraction=emergent,
    )


@torch.no_grad()
def estimate_rheobase(
    neuron_factory,
    stim_grid: Optional[Sequence[float]] = None,
    steps: int = 200,
    min_spikes: int = 1,
) -> float:
    """
    Small current-step search: lowest constant stimulus that elicits spikes.
    neuron_factory() -> FSOTNeuronBatch with n_units=1 preferred.
    """
    if stim_grid is None:
        stim_grid = [i * 0.05 for i in range(0, 21)]  # 0..1.0
    for stim in stim_grid:
        net = neuron_factory()
        net.reset()
        hist = net.run(steps, stimulus_pattern="constant" if stim > 0 else "rest", record=True)
        # Override: constant pattern uses 0.6; do manual loop for exact stim
        net.reset()
        for _ in range(steps):
            net.step(float(stim))
        if int(net.spike_count.sum().item()) >= min_spikes:
            return float(stim)
    return float("nan")


def population_profiles(
    fired: torch.Tensor,
    S: torch.Tensor,
    **kwargs,
) -> List[BioProfile]:
    """fired, S: [T, B]."""
    B = fired.shape[1]
    return [profile_from_history(fired[:, b], S[:, b], **kwargs) for b in range(B)]


def summarize_profiles(profiles: List[BioProfile]) -> Dict[str, float]:
    def mean_ok(vals: List[float]) -> float:
        good = [v for v in vals if v == v]  # not NaN
        return sum(good) / len(good) if good else float("nan")

    return {
        "mean_firing_rate_Hz": mean_ok([p.firing_rate_Hz for p in profiles]),
        "mean_adaptation_index": mean_ok([p.adaptation_index for p in profiles]),
        "mean_isi_ms": mean_ok([p.mean_isi_ms for p in profiles]),
        "mean_isi_cv": mean_ok([p.isi_cv for p in profiles]),
        "mean_Vm_proxy_mV": mean_ok([p.mean_Vm_proxy_mV for p in profiles]),
        "mean_emergent_fraction": mean_ok([p.emergent_fraction for p in profiles]),
        "n_units": float(len(profiles)),
    }


# Allen literature-ish target bands for cortical cells (honest ranges)
CORTICAL_BANDS: Dict[str, Tuple[float, float]] = {
    "firing_rate_evoked_Hz": (5.0, 80.0),
    "firing_rate_spontaneous_Hz": (0.1, 15.0),  # quiet cortex → mild in-vivo bombardment
    "vrest_mV": (-85.0, -55.0),
    "adaptation_index": (-0.2, 0.5),
    "isi_cv": (0.1, 1.5),
    "tau_ms": (5.0, 50.0),
    "input_resistance_mohm": (40.0, 400.0),
}


def in_band(value: float, band: Tuple[float, float]) -> bool:
    if value != value:
        return False
    return band[0] <= value <= band[1]


def band_report(metrics: Dict[str, float], mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    mapping: metric_key -> CORTICAL_BANDS key
    """
    rows = []
    for mk, bk in mapping.items():
        val = metrics.get(mk, float("nan"))
        band = CORTICAL_BANDS[bk]
        rows.append(
            {
                "metric": mk,
                "value": val,
                "band": band,
                "in_band": in_band(val, band),
            }
        )
    n_ok = sum(1 for r in rows if r["in_band"])
    return {
        "rows": rows,
        "pass_rate": n_ok / len(rows) if rows else 0.0,
        "n_pass": n_ok,
        "n_total": len(rows),
    }
