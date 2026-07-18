"""
Operating modes for FSOT micro-neurons.

bio_match  — match Allen ISI / adaptation as closely as practical
efficient  — same fluid intelligence substrate, shorter trains (compute-friendly)

Biological wetware is not the efficiency ceiling. When structure (scalar, phase,
AHP shape, rate bands, rest silence) holds, faster ISI is a *feature* for
simulating more thought per wall-clock second — not a failure of fidelity.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict


class OperatingMode(str, Enum):
    BIO_MATCH = "bio_match"
    EFFICIENT = "efficient"

    @classmethod
    def parse(cls, value: str | None) -> "OperatingMode":
        if value is None:
            return cls.BIO_MATCH
        v = value.strip().lower().replace("-", "_")
        if v in ("bio", "bio_match", "match", "allen"):
            return cls.BIO_MATCH
        if v in ("eff", "efficient", "fast", "compute"):
            return cls.EFFICIENT
        raise ValueError(f"unknown mode {value!r}; use bio_match|efficient")


def mode_philosophy() -> Dict[str, Any]:
    return {
        "bio_match": (
            "Calibrate refractory / AHP / FI drive so mean ISI and adaptation "
            "track Allen sample targets. Use when validating against wetware."
        ),
        "efficient": (
            "Same FSOT dynamics and band structure; shorter ISI (higher rate) "
            "so the substrate does more cognitive work per second. Biology is "
            "the reference, not the speed limit."
        ),
        "default_for_intelligence": "efficient",
        "default_for_validation": "bio_match",
    }
