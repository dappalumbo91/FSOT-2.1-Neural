"""
Sensory injectors for the FSOT brain (Python host scaffold).

Computer-native senses can exceed human modalities (GPU load, syscalls, etc.).
Implementation detail is temporary Python; the *packet shape* is the stable
contract for Zig/Rust/Ada embodiment later (see docs/EMBODIMENT_ROADMAP.md).
"""

from .packets import SensoryModality, SensoryPacket, MetricPacket
from .bus import SensoryBus

__all__ = [
    "SensoryModality",
    "SensoryPacket",
    "MetricPacket",
    "SensoryBus",
]
