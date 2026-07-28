"""
Obsidian-style second-brain visual for FSOT multi-region + genetic nets.

Tk Canvas graph:
  - Region hubs: thal / sens / assoc / hipp (scientific layout)
  - Strongest synapses as edges (light when pre fires)
  - Host interoception + extended senses → SensoryBus → regional drive
  - Self-modulation (POOF/SUCTION) scales activity

Local only — no web.
"""

from __future__ import annotations

import math
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

import tkinter as tk

import torch


# Anatomical-ish region anchors in unit square (second-brain hubs)
_REGION_ANCHORS: Dict[str, Tuple[float, float]] = {
    "thal": (0.50, 0.16),
    "sens": (0.20, 0.48),
    "assoc": (0.80, 0.48),
    "hipp": (0.50, 0.84),
}

_REGION_COLORS = {
    "thal": "#e5c07b",
    "sens": "#61afef",
    "assoc": "#c678dd",
    "hipp": "#98c379",
}

_TYPE_COLORS = {
    "Pyr": "#61afef",
    "PV": "#c678dd",
    "SST": "#e06c75",
    "VIP": "#98c379",
    "Other": "#56b6c2",
}


def _cell_prefix(label: str) -> str:
    for k in ("Pyr", "PV", "SST", "VIP"):
        if label.startswith(k) or f"/{k}" in label or label.endswith(k):
            return k
    return "Other"


def _region_of(label: str, region_of: Optional[Dict[int, str]], i: int) -> str:
    if region_of and i in region_of:
        return region_of[i]
    # label format "thal/Pyr00"
    if "/" in label:
        return label.split("/", 1)[0]
    return "assoc"


class VisualBrainCanvas(tk.Canvas):
    """
    Live graph of multi-region genetic brain.
    attach_brain() for FSOTBrainDesign; attach_live_net() for flat genetic nets.
    """

    def __init__(self, master, **kwargs):
        bg = kwargs.pop("bg", "#0d1117")
        super().__init__(master, bg=bg, highlightthickness=0, **kwargs)
        self._pos: Dict[int, Tuple[float, float]] = {}
        self._edges: List[Tuple[int, int, float]] = []
        self._S: List[float] = []
        self._fired: List[bool] = []
        self._syn: List[float] = []
        self._labels: List[str] = []
        self._region_of: Dict[int, str] = {}
        self._n = 0
        self._net = None  # GeneticNeuralNetwork or FSOTBrainDesign
        self._is_brain = False
        self._bus = None
        self._running = False
        self._after_id: Optional[str] = None
        self._step = 0
        self._stim = 0.55
        self._intero_drive = 0.0
        self._mod_stim = 1.0
        self._mod_syn = 1.0
        self._mod_mode = "balanced"
        self._mean_fire_ema = 0.0
        self._mean_S_ema = 0.0
        self._hud_extra = ""
        self._region_fire: Dict[str, float] = {}
        self._on_tick: Optional[Callable[[Dict[str, Any]], None]] = None
        self._tick_every = 15  # callback / vault period
        self.bind("<Configure>", lambda e: self.redraw())

    def set_tick_callback(self, fn: Optional[Callable[[Dict[str, Any]], None]], every: int = 15) -> None:
        self._on_tick = fn
        self._tick_every = max(1, int(every))

    def set_network(
        self,
        n: int,
        edges: List[Tuple[int, int, float]],
        labels: Optional[List[str]] = None,
        region_of: Optional[Dict[int, str]] = None,
        seed: int = 42,
    ) -> None:
        self._n = n
        self._edges = edges
        self._labels = labels or [f"N{i:02d}" for i in range(n)]
        self._region_of = dict(region_of or {})
        self._S = [0.0] * n
        self._fired = [False] * n
        self._syn = [0.0] * n
        self._layout(seed)
        self.redraw()

    def _layout(self, seed: int) -> None:
        rng = random.Random(seed)
        # Group by region if available
        has_regions = bool(self._region_of) or any("/" in lab for lab in self._labels)
        if has_regions:
            buckets: Dict[str, List[int]] = {k: [] for k in _REGION_ANCHORS}
            for i in range(self._n):
                rid = _region_of(self._labels[i] if i < len(self._labels) else "", self._region_of, i)
                if rid not in buckets:
                    buckets[rid] = []
                    if rid not in _REGION_ANCHORS:
                        # place unknown regions in center ring
                        _REGION_ANCHORS[rid] = (0.5, 0.5)
                buckets[rid].append(i)
            self._pos = {}
            for rid, ids in buckets.items():
                ax, ay = _REGION_ANCHORS.get(rid, (0.5, 0.5))
                m = len(ids)
                for k, i in enumerate(ids):
                    ang = 2 * math.pi * k / max(1, m) + rng.uniform(-0.1, 0.1)
                    r = 0.06 + 0.03 * min(1.0, m / 10.0) + rng.uniform(-0.01, 0.01)
                    if m == 1:
                        r = 0.0
                    self._pos[i] = (
                        max(0.05, min(0.95, ax + r * math.cos(ang))),
                        max(0.07, min(0.93, ay + r * math.sin(ang))),
                    )
        else:
            # cell-type clusters (legacy)
            from collections import defaultdict

            buckets2: Dict[str, List[int]] = defaultdict(list)
            for i, lab in enumerate(self._labels):
                buckets2[_cell_prefix(lab)].append(i)
            anchors = {
                "Pyr": (0.50, 0.28),
                "PV": (0.22, 0.62),
                "SST": (0.78, 0.62),
                "VIP": (0.50, 0.78),
                "Other": (0.50, 0.50),
            }
            self._pos = {}
            for ct, ids in buckets2.items():
                ax, ay = anchors.get(ct, (0.5, 0.5))
                m = len(ids)
                for k, i in enumerate(ids):
                    ang = 2 * math.pi * k / max(1, m) + rng.uniform(-0.08, 0.08)
                    r = 0.08 + rng.uniform(-0.02, 0.02)
                    if m == 1:
                        r = 0.0
                    self._pos[i] = (
                        max(0.05, min(0.95, ax + r * math.cos(ang))),
                        max(0.07, min(0.93, ay + r * math.sin(ang))),
                    )

        # mild separation
        for _ in range(12):
            for i in range(self._n):
                x, y = self._pos[i]
                fx = fy = 0.0
                for j in range(self._n):
                    if i == j:
                        continue
                    xj, yj = self._pos[j]
                    dx, dy = x - xj, y - yj
                    d2 = dx * dx + dy * dy + 1e-6
                    if d2 < 0.01:
                        fx += dx / d2 * 0.00006
                        fy += dy / d2 * 0.00006
                self._pos[i] = (max(0.04, min(0.96, x + fx)), max(0.06, min(0.94, y + fy)))

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
        # region fire fractions
        reg: Dict[str, List[bool]] = {}
        for i, f in enumerate(self._fired):
            rid = _region_of(self._labels[i] if i < len(self._labels) else "", self._region_of, i)
            reg.setdefault(rid, []).append(bool(f))
        self._region_fire = {k: sum(v) / max(1, len(v)) for k, v in reg.items()}
        self.redraw()

    def set_interoception(self, drive: float, label: str = "") -> None:
        self._intero_drive = max(0.0, min(1.0, float(drive)))
        self._hud_extra = label

    def set_modulation(self, stim_scale: float = 1.0, syn_scale: float = 1.0, mode: str = "balanced") -> None:
        self._mod_stim = float(stim_scale)
        self._mod_syn = float(syn_scale)
        self._mod_mode = mode

    def redraw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 40)
        h = max(self.winfo_height(), 40)

        def xy(i: int) -> Tuple[int, int]:
            px, py = self._pos.get(i, (0.5, 0.5))
            return int(px * w), int(py * h)

        # Region hub discs
        for rid, (ax, ay) in _REGION_ANCHORS.items():
            cx, cy = int(ax * w), int(ay * h)
            col = _REGION_COLORS.get(rid, "#30363d")
            rf = self._region_fire.get(rid, 0.0)
            r = int(min(w, h) * (0.10 + 0.04 * rf))
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline=col, width=1 + int(2 * rf), dash=(3, 3))
            self.create_text(
                cx, cy - r - 8,
                text=f"{rid}  {rf:.0%}" if self._region_fire else rid,
                fill=col, font=("Segoe UI", 9, "bold"),
            )

        # Edges
        for i, j, wt in self._edges:
            x0, y0 = xy(i)
            x1, y1 = xy(j)
            a = min(1.0, abs(wt) / 0.45)
            pre_fire = self._fired[i] if i < len(self._fired) else False
            if wt >= 0:
                col = "#e5c07b" if pre_fire else "#3d5a80"
            else:
                col = "#f85149" if pre_fire else "#6e2c2c"
            width = max(1, int(1 + 2.2 * a + (1.5 if pre_fire else 0)))
            self.create_line(x0, y0, x1, y1, fill=col, width=width)

        # Nodes
        for i in range(self._n):
            x, y = xy(i)
            s = self._S[i] if i < len(self._S) else 0.0
            fire = self._fired[i] if i < len(self._fired) else False
            lab = self._labels[i] if i < len(self._labels) else f"N{i}"
            ct = _cell_prefix(lab)
            rid = _region_of(lab, self._region_of, i)
            base = _TYPE_COLORS.get(ct, _REGION_COLORS.get(rid, "#56b6c2"))
            snorm = max(0.0, min(1.0, (s + 1.0) / 2.0))
            r = 6 + int(6 * snorm)
            if fire:
                self.create_oval(x - r - 4, y - r - 4, x + r + 4, y + r + 4, outline="#e5c07b", width=2)
                base = "#e5c07b"
                r += 2
            self.create_oval(x - r, y - r, x + r, y + r, fill=base, outline="#e6edf3", width=1)
            if self._n <= 40:
                short = lab.split("/")[-1][:6] if "/" in lab else lab[:6]
                self.create_text(x, y + r + 8, text=short, fill="#8b949e", font=("Segoe UI", 7))

        fire_frac = sum(1 for f in self._fired if f) / max(1, len(self._fired)) if self._fired else 0.0
        mean_s = sum(self._S) / max(1, len(self._S)) if self._S else 0.0
        self._mean_fire_ema = 0.85 * self._mean_fire_ema + 0.15 * fire_frac
        self._mean_S_ema = 0.85 * self._mean_S_ema + 0.15 * mean_s

        hud = (
            f"step {self._step}  ·  units {self._n}  ·  edges {len(self._edges)}  ·  "
            f"⟨fire⟩ {self._mean_fire_ema:.2%}  ·  ⟨S⟩ {self._mean_S_ema:+.3f}  ·  "
            f"intero {self._intero_drive:.2f}  ·  mod {self._mod_mode}×{self._mod_stim:.2f}"
        )
        if self._hud_extra:
            hud += f"  ·  {self._hud_extra}"
        self.create_text(8, 12, anchor="w", text=hud, fill="#8b949e", font=("Consolas", 9))
        self.create_text(
            8, h - 12, anchor="w",
            text="Multi-region Obsidian graph  ·  thal→sens→assoc↔hipp  ·  host senses + POOF/SUCTION",
            fill="#484f58", font=("Segoe UI", 8),
        )

    def _extract_edges(self, W, n: int, top_k: int = 3) -> List[Tuple[int, int, float]]:
        edges: List[Tuple[int, int, float]] = []
        Wc = W.detach().cpu()
        for i in range(n):
            row = Wc[i]
            abs_w = row.abs()
            k = min(top_k, n - 1)
            if k <= 0:
                continue
            vals, idx = torch.topk(abs_w, k=min(k + 1, n))
            for v, j in zip(vals.tolist(), idx.tolist()):
                j = int(j)
                if j == i or v < 0.015:
                    continue
                edges.append((i, j, float(row[j])))
        return edges

    def attach_live_net(self, net, labels: List[str], top_k: int = 3) -> None:
        """Flat GeneticNeuralNetwork."""
        self._net = net
        self._is_brain = False
        n = int(net.cfg.n_units) if hasattr(net, "cfg") else int(net.W.shape[0])
        edges = self._extract_edges(net.W, n, top_k=top_k)
        self.set_network(n, edges, labels=labels)

    def attach_brain(self, brain, top_k: int = 3) -> None:
        """FSOTBrainDesign multi-region."""
        self._net = brain
        self._is_brain = True
        n = int(brain.n_units)
        labels = []
        region_of: Dict[int, str] = {}
        for u in brain.units:
            labels.append(f"{u.region_id}/{u.cell_type}{u.region_local_id:02d}")
            region_of[u.global_id] = u.region_id
        edges = self._extract_edges(brain.W, n, top_k=top_k)
        # Prefer long-range edges visibility: boost inter-region edges in top list
        # (already in W; top_k per row captures them if strong)
        self.set_network(n, edges, labels=labels, region_of=region_of)

    def set_sensory_bus(self, bus) -> None:
        self._bus = bus

    def start_live(self, interval_ms: int = 80, stim: float = 0.75) -> None:
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

    def _build_external(self) -> torch.Tensor:
        n = self._n
        device = self._net.device
        dtype = getattr(self._net, "dtype", None)
        if dtype is None:
            dtype = self._net.net.dtype
        base = float(self._stim) * float(self._mod_stim)
        base += 0.30 * float(self._intero_drive)
        ext = torch.full((n,), base * 0.35, device=device, dtype=dtype)

        if self._is_brain and hasattr(self._net, "region_index"):
            # Thalamo-cortical style: burst into thalamus, milder cortex
            thal = self._net.region_index.get("thal", [])
            sens = self._net.region_index.get("sens", [])
            assoc = self._net.region_index.get("assoc", [])
            hipp = self._net.region_index.get("hipp", [])
            phase_on = (self._step % 40) < 12
            amp = base
            for i in thal:
                ext[i] = amp if phase_on else amp * 0.2
            for i in sens:
                ext[i] = amp * 0.55
            for i in assoc:
                ext[i] = amp * 0.40 + 0.08 * math.sin(self._step * 0.05)
            for i in hipp:
                ext[i] = amp * 0.35 + 0.06 * math.cos(self._step * 0.03)
            # Sensory bus overlay
            if self._bus is not None:
                se = self._bus.build_external(
                    n, self._net.region_index, device=device, dtype=dtype
                )
                ext = (ext + se).clamp(-0.8, 1.5)
        else:
            if n >= 4:
                ext[0 : n // 4] += 0.08 * math.sin(self._step * 0.07)
                ext[n // 2 :] -= 0.05 * math.cos(self._step * 0.05)

        return ext.clamp(-0.8, 1.5)

    def _live_tick(self, interval_ms: int) -> None:
        if not self._running or self._net is None:
            return
        try:
            ext = self._build_external()
            # Soft syn scale: blend external so high POOF reduces recurrent impact indirectly
            # by slightly lowering overall drive (already in mod_stim); optional W scale would
            # mutate state — avoid; use drive only.
            out = self._net.step(ext)
            S, fired = out[0], out[1]
            syn = out[4] if len(out) > 4 else None
            self._step += 1
            self.set_activity(
                S.detach().cpu().tolist(),
                fired.detach().cpu().tolist(),
                syn.detach().cpu().tolist() if syn is not None else None,
            )
            if self._on_tick and (self._step % self._tick_every == 0):
                fire_frac = float(fired.float().mean().item())
                payload = {
                    "step": self._step,
                    "fire_frac": fire_frac,
                    "mean_S": float(S.mean().item()),
                    "region_fire": dict(self._region_fire),
                    "mod_mode": self._mod_mode,
                    "mod_stim": self._mod_stim,
                    "intero": self._intero_drive,
                }
                try:
                    self._on_tick(payload)
                except Exception:
                    pass
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
    """Factory: typed genetic net + labels (flat, no regions)."""
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


def build_region_brain_visual(
    profile: str = "ai_efficient",
    device: str = "cpu",
    seed: int = 7,
    dt_ms: float = 0.5,
):
    """
    Factory: multi-region FSOTBrainDesign (thal/sens/assoc/hipp).
    profile: 'ai_efficient' (~32 units) or 'wetware_ref' (~64 units).
    """
    from fsot_nuron.brain_architecture import (
        FSOTBrainDesign,
        BrainDesignConfig,
        BRAIN_PROFILES,
        DEFAULT_PROJECTIONS,
    )

    prof = BRAIN_PROFILES.get(profile, BRAIN_PROFILES["ai_efficient"])
    regions = list(prof["regions"])
    cfg = BrainDesignConfig(
        regions=regions,
        projections=list(DEFAULT_PROJECTIONS),
        seed=seed,
        device=device,
        dt_ms=float(dt_ms),
    )
    brain = FSOTBrainDesign(cfg)
    return brain
