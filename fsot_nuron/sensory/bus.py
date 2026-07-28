"""
Sensory bus: queue packets and fold them into per-unit external drive.

Biological / FSOT doctrine:
  - Optional bio routing (thalamic relay → primary cortex) via bio_pathways.
  - Prefer excitatory units for feedforward sensory drive.
  - Strength gains seed-derived; clamp band matches neuron_batch stimulus range.
  - Free parameters: **0** on pathway law.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, List, Optional, Sequence

import torch

from .packets import MetricPacket, SensoryPacket, SensoryModality
from .bio_pathways import (
    apply_bio_routing,
    pathway_gain,
    prefer_excitatory_ids,
    consciousness_gate,
)


class SensoryBus:
    """Local-only queue — no network server."""

    def __init__(self, max_queue: int = 256, *, bio_route: bool = True):
        self.queue: Deque[SensoryPacket] = deque(maxlen=max_queue)
        self.last_metric: Optional[MetricPacket] = None
        self.bio_route = bool(bio_route)

    def push(self, packet: SensoryPacket) -> None:
        self.queue.append(packet)

    def push_metric(self, metric: MetricPacket) -> None:
        """Interoception → thalamus with seed-lawful intero gain (not free 0.35)."""
        self.last_metric = metric
        strength = pathway_gain(SensoryModality.SYS_METRIC.value, "intero")
        # normalize drive scalar into strength band
        drive = float(metric.as_drive_scalar())
        self.push(
            SensoryPacket(
                modality=SensoryModality.SYS_METRIC,
                target_region="thal",
                features=[drive, metric.cpu_util, metric.mem_util, metric.temp_norm],
                strength=float(strength) * (0.5 + 0.5 * drive),
                timestamp_ms=metric.timestamp_ms,
                meta={
                    "kind": "interoception",
                    "bio_map": "autonomic plant → thalamus",
                    "pathway_gain": strength,
                },
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
        *,
        units: Optional[Sequence[Any]] = None,
        couple_S: Optional[float] = None,
        prefer_excitatory: bool = True,
    ) -> torch.Tensor:
        """
        Collapse pending packets into external drive [n_units].

        When bio_route=True, each packet expands to thalamic relay + primary
        cortical inject with seed-derived gains.
        """
        device = device or torch.device("cpu")
        ext = torch.zeros(n_units, device=device, dtype=dtype)
        packets = self.drain()
        expanded: List[SensoryPacket] = []
        for pkt in packets:
            if self.bio_route:
                expanded.extend(apply_bio_routing(pkt, couple_S=couple_S))
            else:
                expanded.append(pkt)

        gate = consciousness_gate()
        for pkt in expanded:
            ids = list(region_index.get(pkt.target_region) or list(range(n_units)))
            if not ids:
                continue
            if prefer_excitatory and units is not None:
                ids = prefer_excitatory_ids(ids, units)
            feats = pkt.features or [pkt.strength]
            # strength already pathway-scaled; soft clamp
            s = float(max(0.0, min(1.5, pkt.strength)))
            # mild φ-gate on inject amplitude (same for all — not free per-channel)
            s *= float(0.85 + 0.15 * gate)
            for i, uid in enumerate(ids):
                if uid < 0 or uid >= n_units:
                    continue
                f = feats[i % len(feats)]
                ext[uid] = ext[uid] + s * float(f)
        # match FSOTNeuronBatch stimulus clamp band
        return ext.clamp(-0.8, 1.5)
