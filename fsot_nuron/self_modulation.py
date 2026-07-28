"""
Self-modulation policies — organism homeostasis on the computer body.

When host load is high, POOF (dispersal / T3 valve) damps drive.
When load is low, SUCTION (inflow dual) allows recovery / exploration.

All gains are seed-derived (SEEDS.poof, SEEDS.suction, φ-gate) — not free fits.
Not permanently tuned to one PC: policies act on *discovered* metrics each cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

from .seeds import SEEDS
from .sensory.packets import MetricPacket
from .hardware_body import HardwareProfile


@dataclass
class ModulationState:
    """How the mind should scale its own activity this cycle."""

    load: float = 0.0  # 0..1 interoceptive blend
    stim_scale: float = 1.0  # multiplies external drive
    syn_scale: float = 1.0  # multiplies recurrent W contribution (soft)
    poof_gain: float = 0.0  # dispersal pressure
    suction_gain: float = 0.0  # recovery / inflow
    n_units_cap: Optional[int] = None  # soft cap recommendation for next rebuild
    dt_ms_scale: float = 1.0  # >1 → coarser steps when overloaded
    mode: str = "balanced"  # dampen | balanced | explore
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _gate() -> float:
    """Consciousness gate φ/(1+φ)."""
    return SEEDS.phi / (1.0 + SEEDS.phi)


def modulate_from_metrics(
    metric: MetricPacket,
    profile: Optional[HardwareProfile] = None,
    *,
    fire_frac: float = 0.0,
    base_n_units: Optional[int] = None,
) -> ModulationState:
    """
    Map host plant + own firing into autonomic scales.

    High load or runaway fire → POOF dampen.
    Low load and quiet fire → SUCTION explore (slightly raise stim).
    """
    load = float(metric.as_drive_scalar())
    cpu = float(metric.cpu_util)
    mem = float(metric.mem_util)
    # Peak of plant stress (cardiovascular analog)
    stress = max(load, cpu, mem * 0.9)
    fire = max(0.0, min(1.0, float(fire_frac)))

    poof = float(SEEDS.poof)  # ~0.153
    suction = float(SEEDS.suction)  # ~0.147
    gate = _gate()

    st = ModulationState(load=load)
    base_n = base_n_units or (profile.recommended_n_units if profile else 32)

    # --- POOF branch: overload / hyper-activity ---
    if stress > 0.65 or fire > 0.35:
        excess = max(0.0, stress - 0.5) + max(0.0, fire - 0.25)
        st.poof_gain = min(1.0, poof * 4.0 * excess)
        st.stim_scale = max(0.35, 1.0 - st.poof_gain * gate)
        st.syn_scale = max(0.45, 1.0 - 0.5 * st.poof_gain)
        st.dt_ms_scale = 1.0 + 0.5 * st.poof_gain  # coarser when stressed
        st.mode = "dampen"
        st.notes.append(f"POOF dampen stress={stress:.2f} fire={fire:.2f}")
        # Soft shrink recommendation (never below 16)
        if stress > 0.8 and base_n > 16:
            st.n_units_cap = max(16, int(base_n * (1.0 - poof)))
            st.notes.append(f"recommend n_units_cap={st.n_units_cap}")
    # --- SUCTION branch: quiet / spare capacity ---
    elif stress < 0.25 and fire < 0.08:
        spare = (0.25 - stress) + (0.08 - fire)
        st.suction_gain = min(1.0, suction * 5.0 * spare)
        st.stim_scale = min(1.35, 1.0 + st.suction_gain * gate * 0.5)
        st.syn_scale = min(1.2, 1.0 + 0.25 * st.suction_gain)
        st.dt_ms_scale = max(0.75, 1.0 - 0.15 * st.suction_gain)
        st.mode = "explore"
        st.notes.append(f"SUCTION explore spare={spare:.2f}")
        if profile and profile.cuda_available and base_n < 64:
            st.n_units_cap = min(128, int(base_n * (1.0 + suction)))
            st.notes.append(f"headroom n_units_cap={st.n_units_cap}")
    else:
        st.mode = "balanced"
        st.stim_scale = 1.0
        st.syn_scale = 1.0
        st.notes.append("homeostasis balanced")

    # Thermal / mem emergency hard clamp (still seed-scaled)
    if mem > 0.92 or (metric.temp_norm and metric.temp_norm > 0.85):
        st.stim_scale = min(st.stim_scale, 1.0 - poof)
        st.mode = "dampen"
        st.notes.append("emergency mem/temp clamp")

    return st


def apply_modulation_to_drive(
    drive,  # torch.Tensor
    mod: ModulationState,
):
    """In-place scale external drive by stim_scale (autonomic gain)."""
    return drive * float(mod.stim_scale)
