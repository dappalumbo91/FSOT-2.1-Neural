"""Stable sensory / interoception packet shapes (host + future ABI)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class SensoryModality(str, Enum):
    VISION = "vision"  # U-Net / frame features
    AUDIO = "audio"
    TEXT = "text"
    # Computer-native (not human-identical)
    SYS_METRIC = "sys_metric"  # CPU, mem, disk, net — subconscious plant
    HID = "hid"  # keyboard/mouse/gamepad
    LOG = "log"  # structured log stream
    NETWORK = "network"
    CUSTOM = "custom"


@dataclass
class SensoryPacket:
    """
    One sensory event into a named brain region.

    features: flat float list (length flexible; host resamples to region size).
    strength: 0..1 overall gate into external drive.
    """

    modality: SensoryModality
    target_region: str = "sens"  # thal | sens | assoc | hipp
    features: List[float] = field(default_factory=list)
    strength: float = 1.0
    timestamp_ms: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["modality"] = self.modality.value
        return d


@dataclass
class MetricPacket:
    """
    Subconscious / autonomic plant sample (computer interoception).

    Maps later through preregistered bridges → FSOT fold drives.
    """

    cpu_util: float = 0.0  # 0..1
    mem_util: float = 0.0
    disk_util: float = 0.0
    net_util: float = 0.0
    temp_norm: float = 0.0  # 0..1 normalized thermal if available
    custom: Dict[str, float] = field(default_factory=dict)
    timestamp_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def as_drive_scalar(self) -> float:
        """
        Seed-free interoceptive blend into [0, 1] for thalamic bias.
        Not a free-fit health model — preregistered equal mix of core channels.
        """
        core = [self.cpu_util, self.mem_util, self.disk_util, self.net_util, self.temp_norm]
        vals = [max(0.0, min(1.0, float(v))) for v in core]
        if self.custom:
            vals.extend(max(0.0, min(1.0, float(v))) for v in self.custom.values())
        if not vals:
            return 0.0
        return sum(vals) / len(vals)
