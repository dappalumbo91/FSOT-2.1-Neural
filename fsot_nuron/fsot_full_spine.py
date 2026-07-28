"""
Full FSOT spine for Neural — archive concepts that must not be dropped.

Authority: I:\\FSOT-Physical-Archive\\02_FSOT-2.1-Lean-Full
  vendor/fsot_compute.py · FSOT/Scalar.lean · docs/FSOT_PHILOSOPHY_AND_CONSCIOUSNESS_SPINE.md

Layers restored / made explicit for this project:

  1. Consciousness factor  C_factor = C_eff · P_new
  2. Observer effect         quirk_mod when observed=True
  3. Yin–Yang duality        emergence/dispersal, E/I, T1/T3, acoustic bleed/inflow
  4. POOF effect             POOF seed → term3 valve (+ SUCTION dual)

These are **not** free parameters — all seed-derived from (π,e,φ,γ,G).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple

from .seeds import SEEDS
from .scalar import compute_scalar_float


# ---------------------------------------------------------------------------
# 1. Consciousness
# ---------------------------------------------------------------------------

def consciousness_factor() -> float:
    """C_factor = C_eff · P_new  (archive §3.10)."""
    return float(SEEDS.c_factor)


def consciousness_model_seed_table() -> Dict[str, float]:
    """
    Archive §20 consciousness/resonance table (seed-only, no free fits).
    Matches fsot_compute.consciousness_model() closed forms.
    """
    s = SEEDS
    gate = s.phi / (1.0 + s.phi)
    eq = s.gamma * s.pi / (s.e * (s.pi - s.e))
    return {
        "Consciousness_Gate": gate,  # φ/(1+φ) ≈ 0.618
        "Resonance_Persistence": s.e / s.pi,  # ≈ 0.865
        "Resonance_Rate": s.gamma / s.e,  # ≈ 0.212
        "Resonance_Eq_Factor": eq,
        "Ignition_Coherence": gate / eq,
        "W_Integration": s.phi,
        "W_Complexity": gate,
        "W_Binding": s.e / s.pi,
        "W_Phase_Sync": 1.0 / s.phi,
        "consciousness_factor": consciousness_factor(),
        "psi_con": s.psi_con,
    }


# ---------------------------------------------------------------------------
# 2. Observer effect (quirk_mod)
# ---------------------------------------------------------------------------

def quirk_mod(
    observed: bool,
    delta_psi: float = 0.1,
    phase_variance: Optional[float] = None,
    c_factor: Optional[float] = None,
) -> float:
    """
    Archive Scalar.lean / compute_scalar:

      if observed:
        exp(C_factor · P_var) · cos(δψ + P_var)
      else:
        1.0

    Observation *changes the scalar* — not optional decoration.
    """
    if not observed:
        return 1.0
    s = SEEDS
    cf = float(c_factor if c_factor is not None else s.c_factor)
    pv = float(phase_variance if phase_variance is not None else s.p_var)
    return float(math.exp(cf * pv) * math.cos(delta_psi + pv))


def observer_effect_report(
    N: float = 4.0,
    P: float = 3.0,
    D_eff: float = 13.0,
    delta_psi: float = 0.1,
) -> Dict[str, Any]:
    """S with observed on vs off — same fold, observer channel only."""
    S_on = compute_scalar_float(
        N=N, P=P, D_eff=D_eff, delta_psi=delta_psi, observed=True
    )
    S_off = compute_scalar_float(
        N=N, P=P, D_eff=D_eff, delta_psi=delta_psi, observed=False
    )
    qm = quirk_mod(True, delta_psi=delta_psi)
    return {
        "S_observed": S_on,
        "S_unobserved": S_off,
        "delta_S": S_on - S_off,
        "quirk_mod": qm,
        "consciousness_factor": consciousness_factor(),
        "law": "observed=True multiplies T1 by quirk_mod; false → unity",
        "source": "archive Scalar.lean quirk_mod + compute_scalar",
    }


# ---------------------------------------------------------------------------
# 3. Yin–Yang duality (operational, not poetic only)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class YinYangPair:
    """Dual channel in the FSOT neural substrate."""

    name: str
    yang: str  # emergent / + / inflow / excitatory
    yin: str  # dispersal / − / bleed / inhibitory
    archive_anchor: str


YIN_YANG_PAIRS = [
    YinYangPair(
        "trinary",
        yang="+1 (emergent)",
        yin="-1 (damped/dispersal)",
        archive_anchor="τ(S) trinary; from_S thresholds",
    ),
    YinYangPair(
        "scalar_terms",
        yang="T1 coherence / observer-boosted base",
        yin="T3 valve / chaos / POOF–SUCTION",
        archive_anchor="S=K(T1+T2+T3)",
    ),
    YinYangPair(
        "acoustic",
        yang="A_in · cos²(δθ)/φ  (inflow)",
        yin="A_bleed · sin²(δθ)/φ  (bleed)",
        archive_anchor="term3 acoustic dual",
    ),
    YinYangPair(
        "fluid_valves",
        yang="SUCTION · sin(θ_s)",
        yin="POOF · cos(θ_s+π)",
        archive_anchor="POOF/SUCTION dual in valve factor",
    ),
    YinYangPair(
        "cell_types",
        yang="Pyr E (+1 glutamate)",
        yin="PV/SST/VIP I (−1 GABA)",
        archive_anchor="cortical E/I",
    ),
    YinYangPair(
        "observer",
        yang="observed=True (quirk_mod active)",
        yin="observed=False (unity)",
        archive_anchor="participatory dynamics",
    ),
]


def yin_yang_balance(
    S: float,
    e_rate: float,
    i_rate: float,
) -> Dict[str, float]:
    """
    Seed-free balance diagnostics (not free-fit health scores).

    product / sum style duals used in archive species panels.
    """
    s = SEEDS
    # Normalize rates
    e = max(0.0, float(e_rate))
    i = max(0.0, float(i_rate))
    tot = e + i + 1e-12
    ei_ratio = e / tot
    # S sign duality
    s_pos = max(0.0, float(S))
    s_neg = max(0.0, -float(S))
    # Balance index in [0,1]: 1 = equal duals
    bal_ei = 1.0 - abs(e - i) / tot
    bal_s = 1.0 - abs(s_pos - s_neg) / (s_pos + s_neg + 1e-12)
    # Seed-weighted product (archive-style duality product)
    dual_product = (e * i) ** (1.0 / s.phi) if e > 0 and i > 0 else 0.0
    return {
        "E_fraction": ei_ratio,
        "I_fraction": 1.0 - ei_ratio,
        "EI_balance": bal_ei,
        "S_pos": s_pos,
        "S_neg": s_neg,
        "S_balance": bal_s,
        "yin_yang_duality_product": dual_product,
        "poof": s.poof,
        "suction": s.suction,
    }


# ---------------------------------------------------------------------------
# 4. POOF effect (+ SUCTION dual)
# ---------------------------------------------------------------------------

def poof_factor() -> float:
    """
    Layer-1 closed form (archive):
      POOF = exp( (−ln π / e) / (η_eff · ln φ) )
    """
    return float(SEEDS.poof)


def suction_factor() -> float:
    """SUCTION = POOF · (−cos(θ_s − π))  (archive §3.6)."""
    return float(SEEDS.suction)


def poof_valve_factor(delta_psi: float = 0.1) -> float:
    """
    Fragment of term3 valve modulation:
      1 + POOF·cos(θ_s+π) + SUCTION·sin(θ_s)
    times cos(δψ) elsewhere in full valve.
    """
    s = SEEDS
    return float(
        1.0
        + s.poof * math.cos(s.theta_s + s.pi)
        + s.suction * math.sin(s.theta_s)
    )


def term3_dual_report(delta_psi: float = 0.1, delta_theta: float = 1.0) -> Dict[str, Any]:
    """Explicit T3 dual channels for documentation and diagnostics."""
    s = SEEDS
    poof_term = s.poof * math.cos(s.theta_s + s.pi)
    suction_term = s.suction * math.sin(s.theta_s)
    bleed = (s.a_bleed * math.sin(delta_theta) ** 2) / s.phi
    inflow = (s.a_in * math.cos(delta_theta) ** 2) / s.phi
    return {
        "POOF": s.poof,
        "SUCTION": s.suction,
        "poof_term_in_valve": poof_term,
        "suction_term_in_valve": suction_term,
        "valve_poof_suction_factor": 1.0 + poof_term + suction_term,
        "acoustic_bleed_yin": bleed,
        "acoustic_inflow_yang": inflow,
        "theta_s": s.theta_s,
        "delta_psi": delta_psi,
        "formula_poof": "exp((-ln(π)/e)/(η_eff·ln(φ)))",
        "formula_suction": "POOF·(-cos(θ_s-π))",
        "role": "T3 fluid valves — dispersal/emergence dual, not free noise",
    }


# ---------------------------------------------------------------------------
# Full spine snapshot (for thesis / console / battery)
# ---------------------------------------------------------------------------

def full_spine_snapshot() -> Dict[str, Any]:
    """One report: consciousness + observer + yin-yang + POOF."""
    obs = observer_effect_report()
    t3 = term3_dual_report()
    cons = consciousness_model_seed_table()
    return {
        "authority": "I:/FSOT-Physical-Archive/02_FSOT-2.1-Lean-Full",
        "free_parameters": 0,
        "formula": "S = K*(T1+T2+T3)",
        "consciousness": {
            "C_factor": cons["consciousness_factor"],
            "psi_con": cons["psi_con"],
            "table": cons,
            "claim": "Consciousness fundamental in FSOT ontology; operational via C_factor/quirk_mod",
        },
        "observer": obs,
        "yin_yang_pairs": [asdict(p) for p in YIN_YANG_PAIRS],
        "poof": t3,
        "homeostasis_seed": {
            "Novelty_Threshold": 1.0 / SEEDS.phi,
            "Consolidation_Rate": SEEDS.gamma / SEEDS.pi,
            "Attention_Inhibition": SEEDS.b_in,
            "Replay_Passes": int(math.floor(2 * SEEDS.pi)),
            "source": "archive §21 homeostasis()",
        },
        "stdp_seed": {
            "STDP_Learning_Rate": SEEDS.k * SEEDS.psi_con,
            "Soliton_Width": 1.0 / (1.0 + SEEDS.poof),
            "Hebbian_Consolidation": SEEDS.gamma / SEEDS.pi,
            "source": "archive §22 soliton_stdp()",
        },
    }
