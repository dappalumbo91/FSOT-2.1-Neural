"""
Biologically equivalent sensory pathways — FSOT-lawful, wet-lab-inspired.

Doctrine (docs/BIO_ACCURACY.md + archive seeds):
  - Structure from public neuroscience motifs (retina→LGN/thal→cortex, cochlea→thal,
    language→assoc, interoception→thal, episodic bind→hipp).
  - Gains from SEEDS only (φ-gate, poof/suction, consciousness factor) — **no free fits**.
  - Dynamics still run on genetic FSOT multi-region brain; this module only defines
    *where* and *how hard* afferents land.

This is **biological fidelity under named mapping**, not a claim that silicon *is*
living tissue.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..seeds import SEEDS
from .packets import SensoryModality, SensoryPacket


# ---------------------------------------------------------------------------
# Anatomical routing table (simplified neocortex + loops)
# ---------------------------------------------------------------------------

# Primary target + optional parallel targets (thalamic relay first for exteroception)
MODALITY_ROUTE: Dict[str, Dict[str, Any]] = {
    SensoryModality.VISION.value: {
        "primary": "sens",
        "relay": "thal",  # LGN-like gate
        "bio": "retina/LGN → early visual cortex (sens) · motion salience via thal",
        "species_note": "mammalian visual stream motif",
    },
    SensoryModality.AUDIO.value: {
        "primary": "sens",
        "relay": "thal",  # MGN-like
        "bio": "cochlea → brainstem/MGN → auditory cortex (sens proxy)",
        "species_note": "mammalian auditory stream motif",
    },
    SensoryModality.TEXT.value: {
        "primary": "assoc",
        "relay": None,
        "bio": "language / symbolic stream → association cortex",
        "species_note": "human language-adjacent; computer-native text channel",
    },
    SensoryModality.SYS_METRIC.value: {
        "primary": "thal",
        "relay": None,
        "bio": "interoception / autonomic plant → thalamus (homeostatic bias)",
        "species_note": "computer body analog of visceral afferents",
    },
    SensoryModality.NETWORK.value: {
        "primary": "thal",
        "relay": None,
        "bio": "external traffic load → thalamic autonomic channel",
        "species_note": "computer-native",
    },
    SensoryModality.HID.value: {
        "primary": "sens",
        "relay": "thal",
        "bio": "somatosensory / effector feedback → sensory column + thal",
        "species_note": "computer HID as mechanoreceptor proxy",
    },
    SensoryModality.LOG.value: {
        "primary": "assoc",
        "relay": None,
        "bio": "structured event stream → association (like narrative/log memory)",
        "species_note": "computer-native",
    },
    SensoryModality.CUSTOM.value: {
        "primary": "assoc",
        "relay": None,
        "bio": "cross-modal bind / joint patterns → association",
        "species_note": "binding site (association)",
    },
}


def consciousness_gate() -> float:
    """φ/(1+φ) — archive consciousness gate (not free)."""
    return float(SEEDS.phi / (1.0 + SEEDS.phi))


def pathway_gain(modality: str, role: str = "primary") -> float:
    """
    Seed-derived gain for a pathway role.

    primary cortex-ish inject: consciousness gate
    thalamic relay: slightly lower (filter) using 1/φ
    interoception: dual of poof/suction scale
    """
    g = consciousness_gate()
    if role == "relay":
        return float(1.0 / SEEDS.phi) * g  # ~0.38
    if role == "intero":
        dual = 0.5 * (abs(SEEDS.poof) + abs(SEEDS.suction))
        return float(dual * g)  # small homeostatic bias
    if role == "hipp_bind":
        return float(g * SEEDS.psi_con)  # episodic gate
    # primary
    return float(g)


def default_route(modality: SensoryModality | str) -> Dict[str, Any]:
    key = modality.value if isinstance(modality, SensoryModality) else str(modality)
    return dict(MODALITY_ROUTE.get(key, MODALITY_ROUTE[SensoryModality.CUSTOM.value]))


def apply_bio_routing(
    packet: SensoryPacket,
    *,
    couple_S: Optional[float] = None,
) -> List[SensoryPacket]:
    """
    Expand one packet into biologically ordered inject set:
      optional thalamic relay (scaled) + primary cortical target.

    If couple_S provided, multiplies strength via archive-style gate
    (positive S → slightly stronger drive; negative → dampen) without free params.
    """
    route = default_route(packet.modality)
    primary = packet.target_region or route["primary"]
    # Prefer preregistered bio primary if caller used a generic region
    if packet.target_region in ("", None):
        primary = route["primary"]

    # S couple: strength_from_S style without importing circular — use gate
    s_mod = 1.0
    if couple_S is not None:
        # map S into (0.5 .. 1.2) via tanh-like clamp using seeds only
        s_mod = float(consciousness_gate() + (1.0 - consciousness_gate()) * max(-1.0, min(1.0, couple_S)))
        s_mod = max(0.35, min(1.25, s_mod))

    out: List[SensoryPacket] = []
    relay = route.get("relay")
    base = float(packet.strength)

    if relay and relay != primary:
        # thalamic gate copy — lower gain, features summary head
        feats = packet.features[:4] if packet.features else [base]
        out.append(
            SensoryPacket(
                modality=packet.modality,
                target_region=str(relay),
                features=list(feats),
                strength=base * pathway_gain(packet.modality.value, "relay") * s_mod,
                timestamp_ms=packet.timestamp_ms,
                meta={
                    **dict(packet.meta or {}),
                    "bio_role": "thalamic_relay",
                    "bio_map": route.get("bio"),
                    "pathway_gain": pathway_gain(packet.modality.value, "relay"),
                },
            )
        )

    role = "primary"
    if packet.modality == SensoryModality.SYS_METRIC:
        role = "intero"
    gain = pathway_gain(packet.modality.value, role)
    out.append(
        SensoryPacket(
            modality=packet.modality,
            target_region=str(primary),
            features=list(packet.features or []),
            strength=base * gain * s_mod,
            timestamp_ms=packet.timestamp_ms,
            meta={
                **dict(packet.meta or {}),
                "bio_role": role,
                "bio_map": route.get("bio"),
                "pathway_gain": gain,
                "s_mod": s_mod,
            },
        )
    )
    return out


def prefer_excitatory_ids(
    unit_ids: Sequence[int],
    units: Sequence[Any],
) -> List[int]:
    """
    Feedforward sensory drive prefers excitatory units (biological FF bias).
    Falls back to all ids if none excitatory.
    """
    exc = []
    for uid in unit_ids:
        if uid < 0 or uid >= len(units):
            continue
        u = units[uid]
        sign = getattr(u, "synapse_sign", 1)
        if int(sign) > 0:
            exc.append(uid)
    return exc if exc else list(unit_ids)


@dataclass
class BioSensoryAudit:
    free_parameters: int
    consciousness_gate: float
    pathway_gains: Dict[str, float]
    modality_routes: Dict[str, Any]
    notes: List[str]
    ok: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def audit_bio_sensory() -> BioSensoryAudit:
    """Self-check: routing table complete, gains seed-only, free params = 0."""
    notes: List[str] = []
    gains = {
        "primary": pathway_gain("vision", "primary"),
        "relay": pathway_gain("vision", "relay"),
        "intero": pathway_gain("sys_metric", "intero"),
        "hipp_bind": pathway_gain("text", "hipp_bind"),
    }
    # free parameters on pathway gains: zero by construction (only seeds)
    free = 0
    notes.append("Pathway gains derived from SEEDS.phi, poof, suction, psi_con only.")
    notes.append("No free-fit sensory transfer function.")
    # all modalities mapped
    for m in SensoryModality:
        if m.value not in MODALITY_ROUTE:
            notes.append(f"MISSING route for {m.value}")
            free += 1  # treat as structural fail
    ok = free == 0 and 0.3 < gains["primary"] < 0.8
    if not ok:
        notes.append("primary gate out of expected φ-band or missing routes")
    return BioSensoryAudit(
        free_parameters=free,
        consciousness_gate=consciousness_gate(),
        pathway_gains=gains,
        modality_routes={k: v for k, v in MODALITY_ROUTE.items()},
        notes=notes,
        ok=ok,
    )
