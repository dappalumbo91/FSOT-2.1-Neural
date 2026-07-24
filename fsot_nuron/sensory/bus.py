"""
Sensory bus: queue packets and fold them into per-unit external drive.

Works with FSOTBrainDesign region indices when provided.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Optional, Sequence

import torch

from .packets import MetricPacket, SensoryPacket


class SensoryBus:
    """Local-only queue — no network server."""

    def __init__(self, max_queue: int = 256):
        self.queue: Deque[SensoryPacket] = deque(maxlen=max_queue)
        self.last_metric: Optional[MetricPacket] = None

    def push(self, packet: SensoryPacket) -> None:
        self.queue.append(packet)

    def push_metric(self, metric: MetricPacket) -> None:
        self.last_metric = metric
        # Interoception also enters as a SYS_METRIC sensory packet → thalamus
        self.push(
            SensoryPacket(
                modality=__import__("fsot_nuron.sensory.packets", fromlist=["SensoryModality"]).SensoryModality.SYS_METRIC,
                target_region="thal",
                features=[metric.as_drive_scalar()],
                strength=0.35,
                timestamp_ms=metric.timestamp_ms,
                meta={"kind": "interoception"},
            )
        )

    def drain(self) -> List[SensoryPacket]:
        out = list(self.queue)
        self.queue.clear()
        return out

    def build_external(
        self,
        n_units: int,
        region_index: Dict[str, List[int]],
        device: Optional[torch.device] = None,
        dtype: torch.dtype = torch.float32,
    ) -> torch.Tensor:
        """
        Collapse pending packets into an external drive vector [n_units].

        Each packet spreads its features cyclically across the target region
        units, scaled by strength. Metrics already enqueued as thalamic packets.
        """
        device = device or torch.device("cpu")
        ext = torch.zeros(n_units, device=device, dtype=dtype)
        packets = self.drain()
        for pkt in packets:
            ids = region_index.get(pkt.target_region) or list(range(n_units))
            if not ids:
                continue
            feats = pkt.features or [pkt.strength]
            s = float(max(0.0, min(1.5, pkt.strength)))
            for i, uid in enumerate(ids):
                f = feats[i % len(feats)]
                ext[uid] = ext[uid] + s * float(f)
        return ext.clamp(-0.5, 1.5)
