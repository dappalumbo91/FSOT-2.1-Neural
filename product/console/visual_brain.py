"""
Obsidian-style second-brain visual for FSOT genetic network.

Tk Canvas graph: neurons as nodes, strongest genetic synapses as edges,
live activity (S / fire) as glow. Cell-type clusters mimic vault hubs.
Local only — no web.
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk

import torch


# Cell-type cluster anchors (Obsidian-like "hubs") in unit square
_CLUSTER_ANCHORS: Dict[str, Tuple[float, float]] = {
    "Pyr": (0.50, 0.28),
    "PV": (0.22, 0.62),
    "SST": (0.78, 0.62),
    "VIP": (0.50, 0.78),
    "Other": (0.50, 0.50),
}

_TYPE_COLORS = {
    "Pyr": "#61afef",  # pyramidal / principal
    "PV": "#c678dd",  # fast-spiking interneuron
    "SST": "#e06c75",  # somatostatin
    "VIP": "#98c379",  # VIP
    "Other": "#56b6c2",
}


def _cell_prefix(label: str) -> str:
    for k in ("Pyr", "PV", "SST", "VIP"):
        if label.startswith(k) or k in label:
            return k
    return "Other"


class VisualBrainCanvas(tk.Canvas):
    """
    Graph layout of genetic units (clustered by cell type — second-brain hubs).
    Call set_network() / attach_live_net() then start_live().
    """

    def __init__(self, master, **kwargs):
        bg = kwargs.pop("bg", "#0d1117")
        super().__init__(master, bg=bg, highlightthickness=0, **kwargs)
        self._pos: Dict[int, Tuple[float, float]] = {}
        self._edges: List[Tuple[int, int, float]] = []  # i, j, weight
        self._S: List[float] = []
        self._fired: List[bool] = []
        self._syn: List[float] = []
        self._labels: List[str] = []
        self._n = 0
        self._net = None
        self._running = False
        self._after_id: Optional[str] = None
        self._step = 0
        self._stim = 0.45
        self._intero_drive = 0.0  # 0..1 host metric blend
        self._mean_fire_ema = 0.0
        self._mean_S_ema = 0.0
        self._hud_extra = ""
        self.bind("<Configure>", lambda e: self.redraw())

    def set_network(
        self,
        n: int,
        edges: List[Tuple[int, int, float]],
        labels: Optional[List[str]] = None,
        seed: int = 42,
    ) -> None:
        self._n = n
        self._edges = edges
        self._labels = labels or [f"N{i:02d}" for i in range(n)]
        self._S = [0.0] * n
        self._fired = [False] * n
        self._syn = [0.0] * n
        self._layout_clusters(seed)
        self.redraw()

    def _layout_clusters(self, seed: int) -> None:
        """Place nodes near cell-type hubs (Obsidian graph clusters)."""
        rng = random.Random(seed)
        buckets: Dict[str, List[int]] = {k: [] for k in _CLUSTER_ANCHORS}
        for i, lab in enumerate(self._labels):
            buckets[_cell_prefix(lab)].append(i)

        self._pos = {}
        for ct, ids in buckets.items():
            ax, ay = _CLUSTER_ANCHORS[ct]
            m = len(ids)
            if m == 0:
                continue
            for k, i in enumerate(ids):
                # Ring within cluster + small jitter
                ang = 2 * math.pi * k / max(1, m) + rng.uniform(-0.12, 0.12)
                r = 0.08 + 0.04 * min(1.0, m / 12.0) + rng.uniform(-0.015, 0.015)
                if m == 1:
                    r = 0.0
                self._pos[i] = (
                    max(0.06, min(0.94, ax + r * math.cos(ang))),
                    max(0.08, min(0.92, ay + r * math.sin(ang))),
                )

        # Light separation pass so edges don't pile
        for _ in range(18):
            for i in range(self._n):
                x, y = self._pos[i]
                fx = fy = 0.0
                for j in range(self._n):
                    if i == j:
                        continue
                    xj, yj = self._pos[j]
                    dx, dy = x - xj, y - yj
                    d2 = dx * dx + dy * dy + 1e-6
                    if d2 < 0.012:
                        fx += dx / d2 * 0.00008
                        fy += dy / d2 * 0.00008
                # mild pull back to cluster hub
                hub = _CLUSTER_ANCHORS[_cell_prefix(self._labels[i])]
                fx += (hub[0] - x) * 0.02
                fy += (hub[1] - y) * 0.02
                self._pos[i] = (
                    max(0.05, min(0.95, x + fx)),
                    max(0.07, min(0.93, y + fy)),
                )

    def set_activity(
        self,
        S: List[float],
        fired: Optional[List[bool]] = None,
        syn: Optional[List[float]] = None,
    ) -> None:
        self._S = list(S)
        if fired is not None:
            self._fired = list(fired)
        else:
            self._fired = [s > 0.5 for s in self._S]
        if syn is not None:
            self._syn = list(syn)
        self.redraw()

    def set_interoception(self, drive: float, label: str = "") -> None:
        """Host body metric 0..1 modulates live stimulation (autonomic plant)."""
        self._intero_drive = max(0.0, min(1.0, float(drive)))
        self._hud_extra = label

    def redraw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 40)
        h = max(self.winfo_height(), 40)

        def xy(i: int) -> Tuple[int, int]:
            px, py = self._pos.get(i, (0.5, 0.5))
            return int(px * w), int(py * h)

        # Soft hub discs (scientific region map)
        for ct, (ax, ay) in _CLUSTER_ANCHORS.items():
            if ct == "Other":
                continue
            cx, cy = int(ax * w), int(ay * h)
            col = _TYPE_COLORS.get(ct, "#30363d")
            r = int(min(w, h) * 0.11)
            self.create_oval(
                cx - r, cy - r, cx + r, cy + r, outline=col, width=1, dash=(3, 4)
            )
            self.create_text(
                cx,
                cy - r - 6,
                text=ct,
                fill=col,
                font=("Segoe UI", 8, "bold"),
            )

        # Edges (synapse routes) — highlight if pre recently fired
        for i, j, wt in self._edges:
            x0, y0 = xy(i)
            x1, y1 = xy(j)
            a = min(1.0, abs(wt) / 0.45)
            pre_fire = self._fired[i] if i < len(self._fired) else False
            if wt >= 0:
                col = "#e5c07b" if pre_fire else "#3d5a80"
            else:
                col = "#f85149" if pre_fire else "#6e2c2c"
            width = max(1, int(1 + 2.5 * a + (1.5 if pre_fire else 0)))
            self.create_line(x0, y0, x1, y1, fill=col, width=width)

        # Nodes
        for i in range(self._n):
            x, y = xy(i)
            s = self._S[i] if i < len(self._S) else 0.0
            fire = self._fired[i] if i < len(self._fired) else False
            lab = self._labels[i] if i < len(self._labels) else f"N{i}"
            ct = _cell_prefix(lab)
            base = _TYPE_COLORS.get(ct, "#56b6c2")
            snorm = max(0.0, min(1.0, (s + 1.0) / 2.0))
            r = 7 + int(7 * snorm)
            if fire:
                # glow ring
                self.create_oval(
                    x - r - 5, y - r - 5, x + r + 5, y + r + 5,
                    outline="#e5c07b", width=2,
                )
                base = "#e5c07b"
                r += 2
            self.create_oval(
                x - r, y - r, x + r, y + r, fill=base, outline="#e6edf3", width=1
            )
            if self._n <= 56:
                self.create_text(
                    x, y + r + 9, text=lab[:7], fill="#8b949e", font=("Segoe UI", 7)
                )

        fire_frac = (
            sum(1 for f in self._fired if f) / max(1, len(self._fired)) if self._fired else 0.0
        )
        mean_s = sum(self._S) / max(1, len(self._S)) if self._S else 0.0
        self._mean_fire_ema = 0.85 * self._mean_fire_ema + 0.15 * fire_frac
        self._mean_S_ema = 0.85 * self._mean_S_ema + 0.15 * mean_s

        hud = (
            f"step {self._step}  ·  units {self._n}  ·  edges {len(self._edges)}  ·  "
            f"⟨fire⟩ {self._mean_fire_ema:.2%}  ·  ⟨S⟩ {self._mean_S_ema:+.3f}  ·  "
            f"intero {self._intero_drive:.2f}"
        )
        if self._hud_extra:
            hud += f"  ·  {self._hud_extra}"
        self.create_text(
            8,
            12,
            anchor="w",
            text=hud,
            fill="#8b949e",
            font=("Consolas", 9),
        )
        self.create_text(
            8,
            h - 12,
            anchor="w",
            text="Obsidian-style local graph  ·  genetic synapses  ·  computer body interoception",
            fill="#484f58",
            font=("Segoe UI", 8),
        )

    def attach_live_net(self, net, labels: List[str], top_k: int = 3) -> None:
        """Bind a GeneticNeuralNetwork with W [n,n] and step()."""
        self._net = net
        n = int(net.cfg.n_units) if hasattr(net, "cfg") else int(net.W.shape[0])
        W = net.W.detach().cpu()
        edges: List[Tuple[int, int, float]] = []
        for i in range(n):
            row = W[i]
            abs_w = row.abs()
            k = min(top_k, n - 1)
            if k <= 0:
                continue
            vals, idx = torch.topk(abs_w, k=min(k + 1, n))
            for v, j in zip(vals.tolist(), idx.tolist()):
                j = int(j)
                if j == i or v < 0.02:
                    continue
                edges.append((i, j, float(row[j])))
        self.set_network(n, edges, labels=labels)

    def start_live(self, interval_ms: int = 80, stim: float = 0.55) -> None:
        if self._net is None:
            return
        self._stim = float(stim)
        self._running = True
        self._live_tick(interval_ms)

    def stop_live(self) -> None:
        self._running = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _live_tick(self, interval_ms: int) -> None:
        if not self._running or self._net is None:
            return
        try:
            n = self._n
            dtype = getattr(self._net, "dtype", None) or self._net.net.dtype
            device = self._net.device
            # Base stim + interoceptive plant (host CPU/mem as thalamic bias)
            base = float(self._stim) + 0.35 * float(self._intero_drive)
            drive = torch.full((n,), base, device=device, dtype=dtype)
            # Slight spatial structure so clusters "think" differently
            if n >= 4:
                drive[0 : n // 4] += 0.08 * math.sin(self._step * 0.07)
                drive[n // 2 :] -= 0.05 * math.cos(self._step * 0.05)
            out = self._net.step(drive)
            S, fired = out[0], out[1]
            syn = out[4] if len(out) > 4 else None
            self._step += 1
            self.set_activity(
                S.detach().cpu().tolist(),
                fired.detach().cpu().tolist(),
                syn.detach().cpu().tolist() if syn is not None else None,
            )
        except Exception as e:
            self.create_text(20, 40, anchor="w", text=f"live error: {e}", fill="#f85149")
            self._running = False
            return
        self._after_id = self.after(interval_ms, lambda: self._live_tick(interval_ms))


def build_small_genetic_visual(
    n_units: int = 32,
    device: str = "cpu",
    seed: int = 7,
    dt_ms: float = 0.5,
):
    """Factory: typed genetic net + labels for the Visual tab (hardware-sized)."""
    from fsot_nuron.genetic_network import GeneticNeuralNetwork, GeneticNetworkConfig
    from fsot_nuron.cell_types import build_typed_population

    gens = build_typed_population(n_units, seed=seed, diversity=True)
    labels: List[str] = []
    for i, g in enumerate(gens):
        ct = getattr(g, "cell_type", "Pyr")
        labels.append(f"{ct}{i:02d}")
    cfg = GeneticNetworkConfig(
        n_units=n_units,
        connectivity="genetic_sparse",
        sparse_keep=0.12,
        seed=seed,
        dt_ms=float(dt_ms),
        diversity=True,
    )
    net = GeneticNeuralNetwork(cfg, device=device, genotypes=gens)
    return net, labels
