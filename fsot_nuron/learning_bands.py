"""
Population oscillatory band proxies from FSOT spike trains / S traces.

Biological time: samples at dt_ms (default 1 ms). Bands are in model-Hz,
independent of silicon wall-clock speed.

Targets from instrumental literature (see docs/LEARNING_ALIGNMENT.md):
  theta 4–8, alpha 8–12, sigma 12–16, gamma 28–64.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import torch


BANDS = {
    "theta": (4.0, 8.0),
    "alpha": (8.0, 12.0),
    "sigma": (12.0, 16.0),
    "gamma": (28.0, 64.0),
}


def population_rate_trace(fired: torch.Tensor, dt_ms: float = 1.0) -> torch.Tensor:
    """
    fired: [T, B] bool → rate [T] in Hz (fraction firing / dt).
    """
    # mean across units, convert to Hz
    frac = fired.float().mean(dim=1)
    return frac * (1000.0 / dt_ms)


def _bandpower_rfft(x: torch.Tensor, fs: float, f_lo: float, f_hi: float) -> float:
    """Simple periodogram band power (no external deps)."""
    x = x - x.mean()
    n = int(x.numel())
    if n < 16:
        return float("nan")
    # real FFT
    spec = torch.fft.rfft(x)
    psd = (spec.real**2 + spec.imag**2) / n
    freqs = torch.fft.rfftfreq(n, d=1.0 / fs)
    mask = (freqs >= f_lo) & (freqs < f_hi)
    if not bool(mask.any()):
        return 0.0
    return float(psd[mask].sum().item())


def band_powers_from_fired(
    fired: torch.Tensor,
    dt_ms: float = 1.0,
) -> Dict[str, float]:
    """
    fired [T, B] → band powers on population rate (model-Hz).
    """
    rate = population_rate_trace(fired, dt_ms)
    fs = 1000.0 / dt_ms
    out = {}
    for name, (lo, hi) in BANDS.items():
        out[name] = _bandpower_rfft(rate.cpu(), fs, lo, hi)
    out["total"] = _bandpower_rfft(rate.cpu(), fs, 1.0, min(fs / 2 - 1, 100.0))
    # relative
    tot = out["total"] if out["total"] and out["total"] == out["total"] else 1.0
    for name in BANDS:
        out[f"{name}_rel"] = out[name] / tot if tot > 0 else float("nan")
    return out


def band_powers_from_S(
    S: torch.Tensor,
    dt_ms: float = 1.0,
) -> Dict[str, float]:
    """Mean S over units as continuous proxy (for fluid coherence dynamics)."""
    x = S.float().mean(dim=1)
    fs = 1000.0 / dt_ms
    out = {}
    for name, (lo, hi) in BANDS.items():
        out[f"S_{name}"] = _bandpower_rfft(x.cpu(), fs, lo, hi)
    return out


def encoding_vs_rest_report(
    fired_encode: torch.Tensor,
    fired_rest: torch.Tensor,
    dt_ms: float = 1.0,
) -> Dict[str, Any]:
    """
    SME-style contrast: encoding epoch vs rest — expect theta/gamma elevation
    as a *direction* target (literature), not a hard clinical claim yet.
    """
    enc = band_powers_from_fired(fired_encode, dt_ms)
    rest = band_powers_from_fired(fired_rest, dt_ms)
    return {
        "encode": enc,
        "rest": rest,
        "theta_encode_gt_rest": enc.get("theta", 0) > rest.get("theta", 0),
        "gamma_encode_gt_rest": enc.get("gamma", 0) > rest.get("gamma", 0),
        "note": "Directional SME-style proxies; calibrate against literature later.",
    }
