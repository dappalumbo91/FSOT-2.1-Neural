"""
Small Fluid Reservoir U-Net — batched on GPU/CPU.

Encoder → bottleneck → decoder with FluidLink skips
(bleed_in_factor + acoustic_bleed blend). Kept small on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import torch
import torch.nn.functional as F

from .neuron_batch import FSOTNeuronBatch, NeuronConfig
from .seeds import SEEDS


@dataclass
class ReservoirConfig:
    n_units: int = 64
    n_layers: int = 3  # enc, mid, dec
    d_eff_enc: float = 12.0
    d_eff_mid: float = 14.0
    d_eff_dec: float = 12.0
    fire_threshold: float = 1.05
    device: Optional[str] = None


class FluidReservoir:
    """
    Minimal multi-layer FSOT reservoir.

    Each layer is a batch of FSOT neurons. Skip = FluidLink blend of S maps.
    Input sequence shape: [T] or [T, B] stimulus drive per step.
    """

    def __init__(self, config: Optional[ReservoirConfig] = None):
        self.cfg = config or ReservoirConfig()
        device = self.cfg.device
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)

        def make(d_eff: float, thr: float) -> FSOTNeuronBatch:
            return FSOTNeuronBatch(
                NeuronConfig(
                    n_units=self.cfg.n_units,
                    d_eff=d_eff,
                    fire_threshold=thr,
                ),
                device=str(self.device),
            )

        # Slightly lower thresholds deeper in the net so FluidLink can propagate spikes
        base = self.cfg.fire_threshold
        self.enc = make(self.cfg.d_eff_enc, base)
        self.mid = make(self.cfg.d_eff_mid, max(0.90, base - 0.08))
        self.dec = make(self.cfg.d_eff_dec, max(0.88, base - 0.12))

        s = SEEDS
        self.bleed = s.b_in
        self.acoustic = s.a_bleed
        self.mix = float(0.5 * (self.bleed + min(1.0, self.acoustic / 2.0)))

    def reset(self) -> None:
        self.enc.reset()
        self.mid.reset()
        self.dec.reset()

    def fluid_link(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        """Coherent skip blend (FluidLink)."""
        return (1.0 - self.mix) * a + self.mix * b

    def _s_as_drive(self, S: torch.Tensor, stim_floor: torch.Tensor | float) -> torch.Tensor:
        """
        Map fluid S into a stimulus-like drive in ~[0, 1].
        Without this, raw S (~0–0.4) under-drives deeper layers.
        """
        if not isinstance(stim_floor, torch.Tensor):
            stim_floor = torch.full_like(S, float(stim_floor))
        # Positive / emergent S boosts drive; keep external stim as floor
        boost = torch.sigmoid((S - 0.1) * 6.0)
        return torch.clamp(0.55 * stim_floor + 0.90 * boost, 0.0, 1.3)

    @torch.no_grad()
    def step(self, stimulus: torch.Tensor | float) -> Dict[str, torch.Tensor]:
        S_e, f_e, _, t_e = self.enc.step(stimulus)
        # Bottleneck: keep a strong copy of external drive + encoder emergence
        drive_m = self._s_as_drive(S_e, stimulus)
        if isinstance(stimulus, torch.Tensor):
            drive_m = 0.45 * stimulus.to(drive_m) + 0.55 * drive_m
        else:
            drive_m = 0.45 * float(stimulus) + 0.55 * drive_m
        S_m, f_m, _, t_m = self.mid.step(drive_m)
        # Decoder: FluidLink skip + residual external path (skip death fix)
        linked = self.fluid_link(S_m, S_e)
        drive_d = self._s_as_drive(linked, drive_m)
        if isinstance(stimulus, torch.Tensor):
            drive_d = 0.35 * stimulus.to(drive_d) + 0.65 * drive_d
        else:
            drive_d = 0.35 * float(stimulus) + 0.65 * drive_d
        S_d, f_d, _, t_d = self.dec.step(drive_d)
        return {
            "S_enc": S_e,
            "S_mid": S_m,
            "S_dec": S_d,
            "fired_enc": f_e,
            "fired_mid": f_m,
            "fired_dec": f_d,
            "ternary_dec": t_d,
        }

    @torch.no_grad()
    def run_sequence(
        self,
        stimulus: torch.Tensor,
        record: bool = True,
    ) -> Dict[str, torch.Tensor]:
        """
        stimulus: [T] or [T, B] float drive.
        """
        if stimulus.ndim == 1:
            T = stimulus.shape[0]
            stim_t = stimulus.to(self.device)
            broadcast = True
        else:
            T, B = stimulus.shape
            if B != self.cfg.n_units:
                raise ValueError(f"stimulus B={B} != n_units={self.cfg.n_units}")
            stim_t = stimulus.to(self.device)
            broadcast = False

        if record:
            S_out = torch.empty(T, self.cfg.n_units, device=self.device)
            fire_out = torch.empty(T, self.cfg.n_units, device=self.device, dtype=torch.bool)
        else:
            S_out = fire_out = None

        for t in range(T):
            st = float(stim_t[t].item()) if broadcast else stim_t[t]
            out = self.step(st)
            if record:
                S_out[t] = out["S_dec"]
                fire_out[t] = out["fired_dec"]

        spikes = fire_out.sum(0) if record else self.dec.spike_count
        result = {
            "spike_count": spikes.long() if record else spikes,
            "firing_rate_Hz": spikes.float() / (T / 1000.0),
            "S_dec": S_out,
            "fired_dec": fire_out,
        }
        return result

    @torch.no_grad()
    def inject_and_pool(self, x: torch.Tensor) -> torch.Tensor:
        """
        One-shot feature path for tiny nets: map input vector through
        reservoir for len(x) steps, return mean decoder S (pooled).
        """
        self.reset()
        out = self.run_sequence(x.flatten().float())
        return out["S_dec"].mean(0)  # [B]
