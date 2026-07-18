"""
Vectorized FSOT scalar S = K·(T1+T2+T3) for CPU and CUDA.

Same structure as the neuron prototype / FSOT-GPU scalar; all ops are
elementwise so one kernel launch path handles B or B×T batches.
"""

from __future__ import annotations

import math
from typing import Optional, Union

import torch

from .seeds import SEEDS, COLLAPSE_THRESHOLD

Number = Union[float, torch.Tensor]


def _as_tensor(x: Number, ref: torch.Tensor) -> torch.Tensor:
    if isinstance(x, torch.Tensor):
        return x.to(device=ref.device, dtype=ref.dtype)
    return torch.full((), float(x), device=ref.device, dtype=ref.dtype)


def compute_scalar_torch(
    N: Number = 4.0,
    P: Number = 3.0,
    D_eff: Number = 13.0,
    recent_hits: Number = 0.0,
    delta_psi: Number = 0.1,
    delta_theta: Number = 1.0,
    rho: Number = 1.0,
    scale: Number = 1.0,
    amplitude: Number = 1.0,
    trend_bias: Number = 0.0,
    observed: bool = True,
    *,
    device: Optional[torch.device] = None,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """
    Full fluid scalar, vectorized. Any argument may be a tensor of matching shape.
    """
    s = SEEDS
    # Pick a reference tensor for device/dtype/broadcast shape
    candidates = [N, P, D_eff, recent_hits, delta_psi, delta_theta, rho]
    ref = None
    for c in candidates:
        if isinstance(c, torch.Tensor):
            ref = c
            break
    if ref is None:
        ref = torch.zeros((), device=device or "cpu", dtype=dtype)
    else:
        if device is not None:
            ref = ref.to(device=device, dtype=dtype)
        else:
            ref = ref.to(dtype=dtype)

    N_t = _as_tensor(N, ref)
    P_t = _as_tensor(P, ref)
    D_t = _as_tensor(D_eff, ref).clamp(min=1e-6)
    rh = _as_tensor(recent_hits, ref)
    dpsi = _as_tensor(delta_psi, ref)
    dth = _as_tensor(delta_theta, ref)
    rho_t = _as_tensor(rho, ref)
    sc = _as_tensor(scale, ref)
    amp = _as_tensor(amplitude, ref)
    tb = _as_tensor(trend_bias, ref)

    growth = torch.exp(s.alpha * (1.0 - rh / N_t.clamp(min=1e-6)) * s.gamma / s.phi)
    base = (
        (N_t * P_t / torch.sqrt(D_t))
        * torch.cos((s.psi_con + dpsi) / s.eta_eff)
        * torch.exp(-s.alpha * rh / N_t.clamp(min=1e-6) + rho_t + s.b_in * dpsi)
        * (1.0 + growth * s.c_eff)
    )
    t1 = base * (1.0 + s.p_new * torch.log(D_t / 25.0))
    if observed:
        t1 = t1 * torch.exp(torch.tensor(s.c_factor * s.p_var, device=ref.device, dtype=ref.dtype)) * torch.cos(
            dpsi + s.p_var
        )

    t2 = sc * amp + tb

    valve = (
        s.beta
        * torch.cos(dpsi)
        * (N_t * P_t / torch.sqrt(D_t))
        * (1.0 + s.chaos * (D_t - 25.0) / 25.0)
        * (1.0 + s.poof * math.cos(s.theta_s + s.pi) + s.suction * math.sin(s.theta_s))
    )
    acoustic = (
        1.0
        + (s.a_bleed * torch.sin(dth) ** 2) / s.phi
        + (s.a_in * torch.cos(dth) ** 2) / s.phi
    )
    phase = 1.0 + s.b_in * s.p_var
    t3 = valve * acoustic * phase

    S = s.k * (t1 + t2 + t3)
    return torch.clamp(S, -3.0, 3.0)


def compute_scalar_float(**kwargs) -> float:
    """Scalar float path (no GPU)."""
    out = compute_scalar_torch(**kwargs, device=torch.device("cpu"), dtype=torch.float64)
    return float(out.item())


def trinary_from_S(S: torch.Tensor, lo: float = -0.4, hi: float = 0.4) -> torch.Tensor:
    """-1 damped, 0 stable, +1 emergent."""
    out = torch.zeros_like(S, dtype=torch.int8)
    out = torch.where(S < lo, torch.full_like(out, -1), out)
    out = torch.where(S > hi, torch.full_like(out, 1), out)
    return out


def collapse_codes(S: torch.Tensor, threshold: float = COLLAPSE_THRESHOLD) -> torch.Tensor:
    """0=down, 1=superposed, 2=up — matches FSOT-GPU trinary pack."""
    codes = torch.ones_like(S, dtype=torch.int8)
    codes = torch.where(S > threshold, torch.full_like(codes, 2), codes)
    codes = torch.where(S < -threshold, torch.full_like(codes, 0), codes)
    return codes
