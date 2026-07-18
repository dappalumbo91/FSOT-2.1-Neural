"""
Batched FSOT active neurons — one tensor state for N units on CPU or CUDA.

Mirrors animal/human cortical dynamics via:
  phase, refractory, trinary emergence, S-threshold spike.
Small by design: Tesla-scale nets, not free-parameter theater.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import torch

from .scalar import compute_scalar_torch, trinary_from_S
from .seeds import NEURO_D_EFF, NEURO_N_CHANNELS, NEURO_P, RESTING_S


@dataclass
class NeuronConfig:
    n_units: int = 64
    n_channels: float = NEURO_N_CHANNELS
    d_eff: float = NEURO_D_EFF
    p_props: float = NEURO_P
    observed: bool = True
    # Scalar rest attractor is ~0.9 at low phase; threshold sits above that
    # so rest is silent and current (stim) lowers thr into the fire band.
    fire_threshold: float = 1.05
    refractory_steps: int = 12  # ~cortical absolute+relative refractory proxy
    resting_S: float = RESTING_S
    dt_ms: float = 1.0
    # Map S → proxy membrane potential (mV) for bio comparison
    vrest_mV: float = -70.0
    vpeak_mV: float = 40.0
    s_to_mV_scale: float = 80.0  # (S - resting) * scale + vrest approx


class FSOTNeuronBatch:
    """
    Vectorized FSOTActiveNeuron.

    State shapes: [B] where B = n_units.
    step(stimulus): stimulus is [B] or scalar broadcast.
    """

    def __init__(
        self,
        config: Optional[NeuronConfig] = None,
        device: Optional[str] = None,
        dtype: torch.dtype = torch.float32,
    ):
        self.cfg = config or NeuronConfig()
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.dtype = dtype
        B = self.cfg.n_units

        self.S = torch.full((B,), self.cfg.resting_S, device=self.device, dtype=dtype)
        self.phase = torch.full((B,), 0.05, device=self.device, dtype=dtype)
        self.refractory = torch.zeros(B, device=self.device, dtype=torch.int32)
        self.ternary = torch.zeros(B, device=self.device, dtype=torch.int8)
        self.spike_count = torch.zeros(B, device=self.device, dtype=torch.int64)
        # AHP state + train counter for controlled adaptation index
        self.adapt = torch.zeros(B, device=self.device, dtype=dtype)
        self.train_count = torch.zeros(B, device=self.device, dtype=torch.int32)
        self.quiet_count = torch.zeros(B, device=self.device, dtype=torch.int32)
        self.steps_run = 0

        # Per-unit bio tuning (defaults; Allen / modes overwrite)
        self.d_eff = torch.full((B,), self.cfg.d_eff, device=self.device, dtype=dtype)
        self.fire_thr = torch.full((B,), self.cfg.fire_threshold, device=self.device, dtype=dtype)
        self.vrest = torch.full((B,), self.cfg.vrest_mV, device=self.device, dtype=dtype)
        self.adapt_gain = torch.full((B,), 0.02, device=self.device, dtype=dtype)
        self.adapt_decay = torch.full((B,), 0.988, device=self.device, dtype=dtype)
        # Per-unit absolute refractory (ms) — primary ISI floor
        self.ref_steps = torch.full(
            (B,), int(self.cfg.refractory_steps), device=self.device, dtype=torch.int32
        )
        # Per-spike ISI lengthening (ms) → sets Allen adaptation index analytically
        self.adapt_step = torch.full((B,), 0.7, device=self.device, dtype=dtype)
        self.fi_stim = torch.full((B,), 0.50, device=self.device, dtype=dtype)
        self.mode_name = "default"
        # Sub-ms residual: fractional refractory debt (efficient timing beyond 1 ms grid)
        self.ref_residual = torch.zeros(B, device=self.device, dtype=dtype)
        self.dt_ms = float(self.cfg.dt_ms)
        self.subms_enabled = True

    def reset(self) -> None:
        self.S.fill_(self.cfg.resting_S)
        self.phase.fill_(0.05)
        self.refractory.zero_()
        self.ternary.zero_()
        self.spike_count.zero_()
        self.adapt.zero_()
        self.train_count.zero_()
        self.quiet_count.zero_()
        self.ref_residual.zero_()
        self.steps_run = 0

    def apply_bio_params(
        self,
        d_eff: Optional[torch.Tensor] = None,
        fire_threshold: Optional[torch.Tensor] = None,
        vrest_mV: Optional[torch.Tensor] = None,
        adapt_gain: Optional[torch.Tensor] = None,
        adapt_decay: Optional[torch.Tensor] = None,
        refractory_steps: Optional[torch.Tensor] = None,
        fi_stim: Optional[torch.Tensor] = None,
        adapt_step: Optional[torch.Tensor] = None,
        mode_name: Optional[str] = None,
    ) -> None:
        """Apply per-unit bio-derived parameters (from Allen mapping + mode)."""
        if d_eff is not None:
            self.d_eff = d_eff.to(self.device, self.dtype)
        if fire_threshold is not None:
            self.fire_thr = fire_threshold.to(self.device, self.dtype)
        if vrest_mV is not None:
            self.vrest = vrest_mV.to(self.device, self.dtype)
        if adapt_gain is not None:
            self.adapt_gain = adapt_gain.to(self.device, self.dtype)
        if adapt_decay is not None:
            self.adapt_decay = adapt_decay.to(self.device, self.dtype)
        if refractory_steps is not None:
            self.ref_steps = refractory_steps.to(self.device, dtype=torch.int32)
        if fi_stim is not None:
            self.fi_stim = fi_stim.to(self.device, self.dtype)
        if adapt_step is not None:
            self.adapt_step = adapt_step.to(self.device, self.dtype)
        if mode_name is not None:
            self.mode_name = mode_name

    @torch.no_grad()
    def step(
        self, stimulus: torch.Tensor | float
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        One ms-proxy step for all units.

        Returns: S, fired (bool), phase, ternary
        """
        if not isinstance(stimulus, torch.Tensor):
            stim = torch.full_like(self.S, float(stimulus))
        else:
            stim = stimulus.to(self.device, self.dtype)
            if stim.ndim == 0:
                stim = stim.expand_as(self.S)
            elif stim.shape[0] != self.S.shape[0]:
                raise ValueError(f"stimulus batch {stim.shape} != units {self.S.shape}")

        # Sub-ms: consume residual first, then integer refractory steps
        if self.subms_enabled:
            self.ref_residual = (self.ref_residual - self.dt_ms).clamp(min=0.0)
            residual_block = self.ref_residual > 1e-6
            in_ref = (self.refractory > 0) | residual_block
            can_tick = (self.refractory > 0) & (~residual_block)
        else:
            in_ref = self.refractory > 0
            can_tick = self.refractory > 0
        self.refractory = torch.where(can_tick, self.refractory - 1, self.refractory)

        # Decay adaptation (AHP) every step — per-unit decay
        self.adapt = self.adapt * self.adapt_decay

        # Stimulus = injected current proxy (not a permanent recent_hits lock).
        stim_eff = (stim - self.adapt).clamp(min=-0.5, max=1.5)
        recent_hits = torch.where(
            in_ref,
            torch.full_like(self.S, 2.0),
            (self.adapt * 2.5).clamp(0.0, 2.0),
        )
        delta_psi = torch.where(
            in_ref,
            self.phase * 0.4,
            self.phase * 0.85 + 0.05 + stim_eff * 0.04,
        )
        delta_theta = 1.0 + stim_eff.abs() * 0.8
        rho = 1.0 + (self.S - self.cfg.resting_S) * 0.08 + 0.55 * stim_eff - 0.2 * self.adapt

        S = compute_scalar_torch(
            N=self.cfg.n_channels,
            P=self.cfg.p_props,
            D_eff=self.d_eff,
            recent_hits=recent_hits.clamp(0.0, 3.0),
            delta_psi=delta_psi,
            delta_theta=delta_theta,
            rho=rho,
            observed=self.cfg.observed,
        )
        self.S = S
        self.ternary = trinary_from_S(S)
        dphase = 0.0015 + 0.10 * stim_eff.clamp(min=0.0) + 0.02 * self.adapt
        self.phase = (self.phase + dphase) % (2 * torch.pi)

        thr = self.fire_thr + 0.35 * self.adapt - 0.50 * stim_eff.clamp(min=0)
        can_fire = (~in_ref) & (S > thr)
        fired = can_fire

        # Reset train after long silence so each FI epoch has clean first ISI
        self.quiet_count = torch.where(fired, torch.zeros_like(self.quiet_count), self.quiet_count + 1)
        self.train_count = torch.where(
            self.quiet_count > 150, torch.zeros_like(self.train_count), self.train_count
        )

        if fired.any():
            # Analytical adaptation: ISI_k ≈ ref + train_count * adapt_step
            self.train_count = torch.where(fired, self.train_count + 1, self.train_count)
            total_ref_ms = self.ref_steps.float() + self.train_count.float() * self.adapt_step
            # Integer part + sub-ms residual (efficient fine timing)
            int_ref = total_ref_ms.floor().to(torch.int32).clamp(0, 250)
            frac = (total_ref_ms - int_ref.float()).clamp(0.0, 0.999)
            self.refractory = torch.where(fired, int_ref, self.refractory)
            if self.subms_enabled:
                self.ref_residual = torch.where(fired, frac * self.dt_ms, self.ref_residual)
            self.phase = torch.where(fired, torch.zeros_like(self.phase), self.phase)
            self.spike_count = self.spike_count + fired.to(torch.int64)
            self.adapt = torch.where(
                fired,
                (self.adapt + self.adapt_gain).clamp(max=0.35),
                self.adapt,
            )

        self.steps_run += 1
        return self.S, fired, self.phase, self.ternary

    def _build_stimulus_track(
        self,
        steps: int,
        stimulus_fn=None,
        stimulus_pattern: str = "periodic",
    ) -> torch.Tensor:
        """Precompute [T, B] stimulus on device — fewer host branches in the hot loop."""
        B = self.cfg.n_units
        if stimulus_fn is not None:
            frames = []
            for t in range(steps):
                st = stimulus_fn(t)
                if not isinstance(st, torch.Tensor):
                    st = torch.full((B,), float(st), device=self.device, dtype=self.dtype)
                else:
                    st = st.to(self.device, self.dtype)
                    if st.ndim == 0:
                        st = st.expand(B)
                frames.append(st)
            return torch.stack(frames, dim=0)

        t = torch.arange(steps, device=self.device)
        if stimulus_pattern == "periodic":
            # ~80 ms cycle, 20 ms burst — theta-like sensory packet
            burst = (t % 80) < 20
            track = torch.where(
                burst,
                torch.full_like(t, 0.65, dtype=self.dtype),
                torch.full_like(t, 0.05, dtype=self.dtype),
            )
            return track.unsqueeze(1).expand(steps, B).contiguous()
        if stimulus_pattern == "constant":
            # Per-unit FI amplitude (Allen rheobase-scaled when mapped)
            return self.fi_stim.unsqueeze(0).expand(steps, B).contiguous()
        if stimulus_pattern == "fi_step":
            # 100 ms rest + sustained current (classic step protocol)
            track = torch.zeros(steps, B, device=self.device, dtype=self.dtype)
            amp = self.fi_stim.unsqueeze(0).expand(max(1, steps - 100), B)
            if steps > 100:
                track[100:] = amp
            else:
                track[:] = self.fi_stim.unsqueeze(0).expand(steps, B)
            return track
        if stimulus_pattern == "rest":
            return torch.zeros(steps, B, device=self.device, dtype=self.dtype)
        if stimulus_pattern == "random":
            # Sparse synaptic-like bombardment (~8% active bins, weak amps)
            r = torch.rand(steps, B, device=self.device, dtype=self.dtype)
            amp = 0.25 + 0.35 * torch.rand(steps, B, device=self.device, dtype=self.dtype)
            return torch.where(r > 0.92, amp, torch.zeros_like(amp))
        return torch.zeros(steps, B, device=self.device, dtype=self.dtype)

    @torch.no_grad()
    def run(
        self,
        steps: int,
        stimulus_fn=None,
        stimulus_pattern: str = "periodic",
        record: bool = True,
    ) -> Dict[str, torch.Tensor]:
        """
        Run T steps. Precomputes stimulus track then steps with tensor [B] each ms.
        For large B, CUDA wins; for tiny B, prefer CPU (launch overhead).
        """
        B = self.cfg.n_units
        stim_track = self._build_stimulus_track(steps, stimulus_fn, stimulus_pattern)

        if record:
            hist_S = torch.empty(steps, B, device=self.device, dtype=self.dtype)
            hist_fire = torch.empty(steps, B, device=self.device, dtype=torch.bool)
            hist_tern = torch.empty(steps, B, device=self.device, dtype=torch.int8)
        else:
            hist_S = hist_fire = hist_tern = None

        for t in range(steps):
            S, fired, _, tern = self.step(stim_track[t])
            if record:
                hist_S[t] = S
                hist_fire[t] = fired
                hist_tern[t] = tern

        out: Dict[str, torch.Tensor] = {
            "spike_count": self.spike_count.clone(),
            "steps": torch.tensor(steps, device=self.device),
            "firing_rate_Hz": self.spike_count.float() / (steps * self.cfg.dt_ms / 1000.0),
        }
        if record:
            out["S"] = hist_S
            out["fired"] = hist_fire
            out["ternary"] = hist_tern
        return out

    def s_to_vm(self, S: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Proxy membrane potential (mV) from S for bio comparison.

        S is a fluid coherence field — not a voltage ODE. We map the
        *relative* excursion of S onto [vrest, vpeak] using a softplus-style
        lift so mean rest stays near configured vrest (Allen), and spikes
        pull toward vpeak.
        """
        s = self.S if S is None else S
        # Relative to instantaneous batch median (robust rest anchor)
        anchor = s.median() if s.numel() > 1 else s.mean()
        # If recording history [T,B], median over all is fine for proxy display
        u = torch.sigmoid((s - anchor) * 2.5)
        # Mix configured rest with dynamic excursion
        return self.vrest * (1.0 - 0.35 * u) + (
            self.vrest + 0.65 * (self.cfg.vpeak_mV - self.vrest) * u
        )

    @staticmethod
    def recommend_device(n_units: int, steps: int = 1000) -> str:
        """
        Workload-aware device pick (same spirit as FSOT-GPU competitive track):
        tiny nets → CPU (kernel launch overhead); large populations → CUDA.
        """
        if not torch.cuda.is_available():
            return "cpu"
        # Empirical crossover ~ few hundred units for this recurrent step kernel
        unit_steps = n_units * steps
        return "cuda" if n_units >= 256 or unit_steps >= 250_000 else "cpu"

    def metrics_summary(self, hist: Dict[str, torch.Tensor]) -> Dict[str, float]:
        fr = hist["firing_rate_Hz"]
        S = hist.get("S")
        fired = hist.get("fired")
        summary = {
            "n_units": float(self.cfg.n_units),
            "mean_firing_rate_Hz": float(fr.mean().item()),
            "std_firing_rate_Hz": float(fr.std(unbiased=False).item()) if self.cfg.n_units > 1 else 0.0,
            "median_firing_rate_Hz": float(fr.median().item()),
            "mean_spikes": float(hist["spike_count"].float().mean().item()),
            "device": str(self.device),
        }
        if S is not None:
            summary["mean_S"] = float(S.mean().item())
            summary["std_S"] = float(S.std(unbiased=False).item())
            summary["mean_Vm_proxy_mV"] = float(self.s_to_vm(S).mean().item())
        if fired is not None:
            # Adaptation proxy: early vs late half spike rate
            T = fired.shape[0]
            mid = T // 2
            early = fired[:mid].float().sum(0)
            late = fired[mid:].float().sum(0)
            adapt = (early - late) / (early + late + 1e-6)
            summary["mean_adaptation_proxy"] = float(adapt.mean().item())
            # Emergent fraction
            tern = hist["ternary"]
            summary["emergent_fraction"] = float((tern == 1).float().mean().item())
        return summary
