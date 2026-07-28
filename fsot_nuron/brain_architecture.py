"""
FSOT multi-region brain design on genetic / cell-typed neurons.

Ladder:
  codon → cell-type gene programs → local microcircuit motifs
  → named regions → inter-region projections → dynamics + local vault

Biological motifs (simplified neocortex + loop):
  - Local E→E recurrent (weak)
  - E→I feedforward (strong)
  - I→E feedback inhibition
  - I→I (PV/SST lateral); VIP → other I (disinhibition)
  - Long-range E→E between regions (feedforward / feedback)

Honesty: computational architecture inspired by cortical microcircuit literature
and FSOT genetics — not a medical whole-brain model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import torch

from .cell_types import (
    CELL_TYPES,
    build_typed_population,
    population_type_report,
)
from .genetic_genotype import NeuronGenotype
from .genetic_network import (
    GeneticNetworkConfig,
    electrostatic_term,
    geometric_scale,
    trinary_pair_interaction,
)
from .neuron_batch import FSOTNeuronBatch, NeuronConfig
from .seeds import SEEDS
from .bio_metrics import population_profiles, summarize_profiles
from .modes import OperatingMode
from .calibrate import analytical_lock


@dataclass
class RegionSpec:
    id: str
    label: str
    n_units: int
    # cortical-like mix unless overridden
    mix: Optional[Dict[str, float]] = None
    role: str = "cortex"  # cortex | hippocampus | thalamus | association


@dataclass
class ProjectionSpec:
    """Directed region → region long-range projection."""

    src: str
    dst: str
    kind: str  # feedforward | feedback | recurrent_long
    density: float = 0.15  # fraction of src E → dst E
    strength: float = 0.35  # relative to local scale


# Wetware-reference mini-brain: compare to biology (not a size goal for AI)
DEFAULT_REGIONS: List[RegionSpec] = [
    RegionSpec("thal", "thalamus_relay", n_units=8, role="thalamus",
               mix={"Pyr": 0.85, "PV": 0.15, "SST": 0.0, "VIP": 0.0}),
    RegionSpec("sens", "sensory_cortex_column", n_units=24, role="cortex"),
    RegionSpec("assoc", "association_cortex", n_units=20, role="association"),
    RegionSpec("hipp", "hippocampus_ca_proxy", n_units=12, role="hippocampus",
               mix={"Pyr": 0.75, "PV": 0.12, "SST": 0.08, "VIP": 0.05}),
]

# Computer-native efficient profile: same motifs / regions, fewer units
# (digital speed + no vegetative load — see docs/EFFICIENCY_DOCTRINE.md)
AI_EFFICIENT_REGIONS: List[RegionSpec] = [
    RegionSpec("thal", "thalamus_relay", n_units=4, role="thalamus",
               mix={"Pyr": 0.85, "PV": 0.15, "SST": 0.0, "VIP": 0.0}),
    RegionSpec("sens", "sensory_cortex_column", n_units=12, role="cortex"),
    RegionSpec("assoc", "association_cortex", n_units=10, role="association"),
    RegionSpec("hipp", "hippocampus_ca_proxy", n_units=6, role="hippocampus",
               mix={"Pyr": 0.75, "PV": 0.12, "SST": 0.08, "VIP": 0.05}),
]

BRAIN_PROFILES = {
    "wetware_ref": {
        "regions": DEFAULT_REGIONS,
        "timing": "bio_match",
        "isi_scale": 1.0,
        "intent": "Biological comparison layout; Allen-style timing when locked",
    },
    "ai_efficient": {
        "regions": AI_EFFICIENT_REGIONS,
        "timing": "efficient",
        "isi_scale": 1.0 / 3.0,
        "intent": "Computer-native AI: fewer units, faster trains, same motifs",
    },
}

DEFAULT_PROJECTIONS: List[ProjectionSpec] = [
    ProjectionSpec("thal", "sens", "feedforward", density=0.35, strength=0.55),
    ProjectionSpec("sens", "assoc", "feedforward", density=0.25, strength=0.45),
    ProjectionSpec("assoc", "sens", "feedback", density=0.12, strength=0.25),
    ProjectionSpec("assoc", "hipp", "feedforward", density=0.20, strength=0.40),
    ProjectionSpec("hipp", "assoc", "feedback", density=0.15, strength=0.30),
    ProjectionSpec("sens", "thal", "feedback", density=0.10, strength=0.20),
]


@dataclass
class BrainDesignConfig:
    regions: List[RegionSpec] = field(default_factory=lambda: list(DEFAULT_REGIONS))
    projections: List[ProjectionSpec] = field(
        default_factory=lambda: list(DEFAULT_PROJECTIONS)
    )
    seed: int = 42
    local_syn_scale: float = 0.14
    device: str = "cpu"
    dt_ms: float = 1.0
    # Motif gains — seed-structured cortical FF/FB (φ-gate); not free-fit to data
    # E→I strong, E→E weaker, I→E feedback, moderate I→I, VIP→I disinhibition
    gain_ee: float = 0.085   # sparse E→E (directed local)
    gain_ei: float = 0.55    # strong E→I feedforward
    gain_ie: float = 0.42    # I→E feedback (balances E/I mass into ~1–5 band)
    gain_ii: float = 0.22    # I→I / lateral inhibition
    gain_vip_i: float = 0.30  # VIP→I disinhibition
    # Local wiring sparsity / directedness (fly-motif + cortical FF bias)
    # 0 → auto from SEEDS (φ, e). Not free-fit to Allen rates.
    local_k_ff: int = 0      # feedforward local out-degree (0=auto ~e)
    local_k_fb: int = 0      # feedback local out-degree (0=auto ~φ/2)
    recip_attenuate: float = 0.0  # 0 → 1/φ on weaker of reciprocal pairs


@dataclass
class UnitMeta:
    global_id: int
    region_id: str
    region_local_id: int
    cell_type: str
    synapse_sign: int
    transmitter: str


def _motif_gain(
    pre_type: str,
    post_type: str,
    pre_sign: int,
    post_sign: int,
    cfg: BrainDesignConfig,
) -> float:
    """Biological microcircuit motif multiplier."""
    # VIP preferentially inhibits other interneurons (disinhibition)
    if pre_type == "VIP" and post_sign < 0:
        return cfg.gain_vip_i
    if pre_sign > 0 and post_sign > 0:
        return cfg.gain_ee
    if pre_sign > 0 and post_sign < 0:
        return cfg.gain_ei
    if pre_sign < 0 and post_sign > 0:
        return cfg.gain_ie
    if pre_sign < 0 and post_sign < 0:
        return cfg.gain_ii
    return 0.3


def _fsot_pair_weight(gi: NeuronGenotype, gj: NeuronGenotype, dist: int) -> float:
    s = SEEDS
    base = trinary_pair_interaction(gi.composite_spin, gj.composite_spin)
    geom = s.phi * (max(1, dist) ** (-1.0 / s.pi))
    elec = electrostatic_term(gi.composite_charge, gj.composite_charge)
    env = dist / (dist + s.pi * s.e)
    return geom * (base + 0.15 * elec) * (0.35 + 0.65 * env)


class FSOTBrainDesign:
    """
    Multi-region brain: typed genetic neurons + motif-aware W + FSOT dynamics.
    """

    def __init__(self, cfg: Optional[BrainDesignConfig] = None):
        self.cfg = cfg or BrainDesignConfig()
        self.units: List[UnitMeta] = []
        self.genotypes: List[NeuronGenotype] = []
        self.region_index: Dict[str, List[int]] = {}
        self._build_population()
        self.device = torch.device(self.cfg.device)
        ncfg = NeuronConfig(n_units=len(self.genotypes), dt_ms=self.cfg.dt_ms)
        self.net = FSOTNeuronBatch(ncfg, device=str(self.device))
        self._apply_phenotypes()
        self.W = self._build_weight_matrix()
        self.last_fired = torch.zeros(len(self.genotypes), device=self.device, dtype=torch.bool)

    def _build_population(self) -> None:
        gid = 0
        for r_i, region in enumerate(self.cfg.regions):
            pop = build_typed_population(
                region.n_units,
                mix=region.mix,
                seed=self.cfg.seed + 17 * r_i,
                diversity=True,
            )
            ids: List[int] = []
            for local_i, g in enumerate(pop):
                g.unit_id = gid
                ct = getattr(g, "cell_type", "Pyr")
                sign = int(getattr(g, "synapse_sign", CELL_TYPES.get(ct, CELL_TYPES["Pyr"]).sign))
                tx = getattr(g, "transmitter", "glutamate")
                self.genotypes.append(g)
                self.units.append(
                    UnitMeta(
                        global_id=gid,
                        region_id=region.id,
                        region_local_id=local_i,
                        cell_type=ct,
                        synapse_sign=sign,
                        transmitter=tx,
                    )
                )
                ids.append(gid)
                gid += 1
            self.region_index[region.id] = ids
        self.n_units = len(self.genotypes)

    def _apply_phenotypes(self) -> None:
        phs = [g.phenotype for g in self.genotypes]
        self.net.apply_bio_params(
            d_eff=torch.tensor([p["d_eff"] for p in phs], device=self.device, dtype=self.net.dtype),
            fire_threshold=torch.tensor(
                [p["fire_threshold"] for p in phs], device=self.device, dtype=self.net.dtype
            ),
            vrest_mV=torch.tensor(
                [p["vrest_mV"] for p in phs], device=self.device, dtype=self.net.dtype
            ),
            adapt_gain=torch.tensor(
                [p["adapt_gain"] for p in phs], device=self.device, dtype=self.net.dtype
            ),
            adapt_decay=torch.tensor(
                [p["adapt_decay"] for p in phs], device=self.device, dtype=self.net.dtype
            ),
            refractory_steps=torch.tensor(
                [int(round(float(p["refractory_steps"]))) for p in phs],
                device=self.device,
                dtype=torch.int32,
            ),
            fi_stim=torch.tensor(
                [p["fi_stim"] for p in phs], device=self.device, dtype=self.net.dtype
            ),
            adapt_step=torch.tensor(
                [p["adapt_step"] for p in phs], device=self.device, dtype=self.net.dtype
            ),
            mode_name="brain_design",
        )

    def _build_weight_matrix(self) -> torch.Tensor:
        n = self.n_units
        W = torch.zeros(n, n, device=self.device, dtype=self.net.dtype)
        s = SEEDS
        meta = self.units
        gens = self.genotypes

        # Seed-auto local out-degrees (computer-centric sparse motifs ≈ fly band)
        k_ff = int(self.cfg.local_k_ff) or max(2, int(round(s.e)))          # ~3
        k_fb = int(self.cfg.local_k_fb) or max(1, int(round(s.phi / 2.0)))  # ~1
        recip_scale = float(self.cfg.recip_attenuate) or (1.0 / s.phi)       # weaker of pair

        # --- local (within-region) wiring ---
        # 1) Dense E↔I / I↔I / VIP motifs (cortical microcircuit literature)
        # 2) Sparse directed E→E (computer-centric / fly density band)
        for _region_id, ids in self.region_index.items():
            ordered = sorted(ids, key=lambda i: meta[i].region_local_id)
            e_ids = [i for i in ordered if meta[i].synapse_sign > 0]
            i_ids = [i for i in ordered if meta[i].synapse_sign < 0]

            def _set_edge(post: int, pre: int, ff_boost: bool = False) -> None:
                if post == pre:
                    return
                mp, mq = meta[post], meta[pre]
                dist = abs(mp.region_local_id - mq.region_local_id) + 1
                w = _fsot_pair_weight(gens[post], gens[pre], dist)
                gain = _motif_gain(
                    mq.cell_type, mp.cell_type, mq.synapse_sign, mp.synapse_sign, self.cfg
                )
                if ff_boost and mp.region_local_id > mq.region_local_id:
                    gain = gain * (s.phi / (s.phi + 1.0 / s.phi))
                elif ff_boost:
                    gain = gain * (1.0 / s.phi)
                polarity = float(mq.synapse_sign)
                W[post, pre] = w * gain * polarity

            # E→I and I→E: full bipartite (preserves E/I mass band)
            for pre in e_ids:
                for post in i_ids:
                    _set_edge(post, pre)
            for pre in i_ids:
                for post in e_ids:
                    _set_edge(post, pre)
            # I→I / VIP→I: sparse directed (VIP disinhibition still via motif gain)
            for pre in i_ids:
                higher = [i for i in i_ids if meta[i].region_local_id > meta[pre].region_local_id]
                lower = [i for i in i_ids if meta[i].region_local_id < meta[pre].region_local_id]
                for post in higher[:k_ff] + lower[: max(1, k_fb)]:
                    _set_edge(post, pre)

            # E→E: sparse directed k-nearest (not all-to-all)
            for pre in e_ids:
                higher = [i for i in e_ids if meta[i].region_local_id > meta[pre].region_local_id]
                lower = [i for i in e_ids if meta[i].region_local_id < meta[pre].region_local_id]
                for post in higher[:k_ff] + lower[:k_fb]:
                    _set_edge(post, pre, ff_boost=True)

        # --- long-range projections (E→E preferred, directed src→dst only) ---
        for proj in self.cfg.projections:
            src_ids = self.region_index.get(proj.src, [])
            dst_ids = self.region_index.get(proj.dst, [])
            src_e = [i for i in src_ids if meta[i].synapse_sign > 0]
            dst_e = [i for i in dst_ids if meta[i].synapse_sign > 0]
            if not src_e or not dst_e:
                continue
            k = max(1, int(proj.density * len(dst_e)))
            for si, pre in enumerate(src_e):
                for j in range(k):
                    kind_h = sum((i + 1) * ord(c) for i, c in enumerate(proj.kind))
                    post = dst_e[(si * 7 + j * 3 + kind_h % 5) % len(dst_e)]
                    if post == pre:
                        continue
                    dist = 8 + abs(si - j)
                    w = _fsot_pair_weight(gens[post], gens[pre], dist)
                    # directed long-range: only src→dst, no automatic reverse
                    W[post, pre] = W[post, pre] + w * proj.strength

        # Reciprocal attenuation on *same-sign* pairs (E↔E, I↔I).
        # E↔I loops stay dense (cortical recurrent inhibition). Same-sign
        # directedness pushes whole-graph reciprocity toward fly band.
        with torch.no_grad():
            for i in range(n):
                for j in range(i + 1, n):
                    if meta[i].synapse_sign != meta[j].synapse_sign:
                        continue
                    a = float(W[i, j].item())
                    b = float(W[j, i].item())
                    if a == 0.0 or b == 0.0:
                        continue
                    # stronger same-sign attenuation (1/φ² if default)
                    scale = recip_scale * recip_scale if recip_scale < 1.0 else recip_scale
                    if abs(a) >= abs(b):
                        W[j, i] = W[j, i] * scale
                    else:
                        W[i, j] = W[i, j] * scale

        # Drop near-zero edges (sparsity toward fly density band)
        mask = W != 0
        if mask.any():
            thr = float(W[mask].abs().mean().item()) / (s.phi * s.e)  # ~ mean/(φ·e)
            W = torch.where(W.abs() >= thr, W, torch.zeros_like(W))

        # Normalize nonzero mean |W|
        mask = W != 0
        if mask.any():
            mean_abs = W[mask].abs().mean().clamp(min=1e-6)
            W = W / mean_abs * float(self.cfg.local_syn_scale)
        return W

    def reset(self) -> None:
        self.net.reset()
        self.last_fired.zero_()

    @torch.no_grad()
    def step(self, external: torch.Tensor | float = 0.0):
        if not isinstance(external, torch.Tensor):
            ext = torch.full(
                (self.n_units,), float(external), device=self.device, dtype=self.net.dtype
            )
        else:
            ext = external.to(self.device, self.net.dtype)
            if ext.ndim == 0:
                ext = ext.expand(self.n_units)
        syn = self.W @ self.last_fired.to(self.net.dtype)
        stim = (ext + syn).clamp(-0.8, 1.5)
        S, fired, phase, ternary = self.net.step(stim)
        self.last_fired = fired
        return S, fired, phase, ternary, syn

    @torch.no_grad()
    def run(
        self,
        steps: int,
        drive_region: str = "thal",
        drive_amp: float = 0.65,
        drive_duty: float = 0.25,
        period: int = 80,
        sensory_bus: Any = None,
        sensory_every: int = 40,
    ) -> Dict[str, torch.Tensor]:
        """
        Thalamo-cortical style drive: periodic bursts into drive_region.

        Optional sensory_bus (fsot_nuron.sensory.SensoryBus):
          injects vision/text/metric packets as regional external drive.
          Features are host floats; bare-metal path quantizes to trits
          (see trinary_substrate.quantize_features_to_trits).
        """
        self.reset()
        n = self.n_units
        drive_ids = set(self.region_index.get(drive_region, []))
        hist_S = torch.empty(steps, n, device=self.device, dtype=self.net.dtype)
        hist_f = torch.empty(steps, n, device=self.device, dtype=torch.bool)
        hist_syn = torch.empty(steps, n, device=self.device, dtype=self.net.dtype)
        hist_tern = torch.empty(steps, n, device=self.device, dtype=torch.int8)
        sensory_injections = 0

        for t in range(steps):
            ext = torch.zeros(n, device=self.device, dtype=self.net.dtype)
            on = (t % period) < int(period * drive_duty)
            if on and drive_ids:
                for i in drive_ids:
                    # drive excitatory cells harder
                    if self.units[i].synapse_sign > 0:
                        ext[i] = drive_amp
                    else:
                        ext[i] = drive_amp * 0.25
            # Sensory / interoception overlay (subconscious + cortex)
            if sensory_bus is not None and sensory_every > 0 and (t % sensory_every) == 0:
                # Caller may push packets each tick; we also accept pre-queued
                se = sensory_bus.build_external(
                    n, self.region_index, device=self.device, dtype=self.net.dtype
                )
                if float(se.abs().sum().item()) > 0:
                    sensory_injections += 1
                ext = (ext + se).clamp(-0.8, 1.5)
            S, fired, _, tern, syn = self.step(ext)
            hist_S[t] = S
            hist_f[t] = fired
            hist_syn[t] = syn
            hist_tern[t] = tern

        rates = hist_f.float().sum(0) / (steps * self.cfg.dt_ms / 1000.0)
        out: Dict[str, torch.Tensor] = {
            "S": hist_S,
            "fired": hist_f,
            "synaptic": hist_syn,
            "ternary": hist_tern,
            "firing_rate_Hz": rates,
            "steps": torch.tensor(steps, device=self.device),
        }
        # attach non-tensor meta for reports
        self._last_run_meta = {
            "sensory_injections": sensory_injections,
            "sensory_enabled": sensory_bus is not None,
        }
        return out

    def structure_report(self) -> Dict[str, Any]:
        W = self.W.detach().cpu()
        nz = int((W != 0).sum().item())
        # E/I synaptic mass
        exc_mass = 0.0
        inh_mass = 0.0
        for pre in range(self.n_units):
            col = W[:, pre]
            mass = float(col.abs().sum().item())
            if self.units[pre].synapse_sign > 0:
                exc_mass += mass
            else:
                inh_mass += mass
        type_rep = population_type_report(self.genotypes)
        regions = {}
        for rid, ids in self.region_index.items():
            cts: Dict[str, int] = {}
            for i in ids:
                ct = self.units[i].cell_type
                cts[ct] = cts.get(ct, 0) + 1
            regions[rid] = {"n": len(ids), "cell_types": cts}

        return {
            "n_units": self.n_units,
            "n_synapses": nz,
            "synapse_density": nz / max(1, self.n_units * (self.n_units - 1)),
            "excitatory_synaptic_mass": exc_mass,
            "inhibitory_synaptic_mass": inh_mass,
            "ei_mass_ratio": exc_mass / max(1e-9, inh_mass),
            "population": type_rep,
            "regions": regions,
            "projections": [
                {"src": p.src, "dst": p.dst, "kind": p.kind, "density": p.density}
                for p in self.cfg.projections
            ],
        }

    def dynamics_report(self, hist: Dict[str, torch.Tensor]) -> Dict[str, Any]:
        profiles = population_profiles(hist["fired"], hist["S"])
        summary = summarize_profiles(profiles)
        rates = hist["firing_rate_Hz"].detach().cpu()
        by_region: Dict[str, float] = {}
        by_type: Dict[str, float] = {}
        for i, u in enumerate(self.units):
            by_region.setdefault(u.region_id, [])
            by_region[u.region_id].append(float(rates[i]))
            by_type.setdefault(u.cell_type, [])
            by_type[u.cell_type].append(float(rates[i]))
        by_region = {k: sum(v) / len(v) for k, v in by_region.items() if v}
        by_type = {k: sum(v) / len(v) for k, v in by_type.items() if v}
        co = float((hist["fired"].sum(1) >= 2).float().mean().item())
        return {
            "population": summary,
            "mean_rate_Hz": float(rates.mean().item()),
            "rate_by_region": by_region,
            "rate_by_cell_type": by_type,
            "coactive_fraction": co,
            "mean_syn": float(hist["synaptic"].mean().item()),
        }

    def connectivity_edges(
        self, top_k_out: int = 5, min_abs_w: float = 0.02
    ) -> List[Tuple[int, int, float]]:
        """(post, pre, w) strongest outgoing for export."""
        edges: List[Tuple[int, int, float]] = []
        Wc = self.W.detach().cpu()
        n = self.n_units
        for pre in range(n):
            col = Wc[:, pre].abs()
            col = col.clone()
            col[pre] = 0.0
            k = min(top_k_out, n - 1)
            vals, idx = torch.topk(col, k=k)
            for v, post in zip(vals.tolist(), idx.tolist()):
                if v < min_abs_w:
                    continue
                edges.append((int(post), int(pre), float(Wc[int(post), pre].item())))
        return edges


def apply_timing_profile(brain: "FSOTBrainDesign", isi_scale: float) -> None:
    """Scale refractory / adapt_step for efficient (computer-native) timing."""
    if abs(isi_scale - 1.0) < 1e-9:
        return
    brain.net.ref_steps = (
        (brain.net.ref_steps.float() * isi_scale).round().clamp(2, 200).to(torch.int32)
    )
    brain.net.adapt_step = (brain.net.adapt_step * isi_scale).clamp(0.0, 12.0)


def _demo_sensory_bus(steps: int, every: int = 40):
    """Build a bus and schedule vision + interoception packets for a run."""
    from .sensory import MetricPacket, SensoryBus, SensoryModality, SensoryPacket
    from .trinary_substrate import quantize_features_to_trits

    bus = SensoryBus()
    # Pre-queue a few pattern packets; run() drains on sensory_every ticks,
    # so we re-push inside a thin wrapper via brain hook — use scheduled list.
    scheduled = []
    for t in range(0, steps, every):
        # Dummy vision features (U-Net placeholder) → will be trit-quantized at edge
        vis = [0.8, -0.3, 0.5, 0.1, -0.6, 0.4]
        scheduled.append(
            (
                t,
                SensoryPacket(
                    modality=SensoryModality.VISION,
                    target_region="sens",
                    features=vis,
                    strength=0.45,
                    timestamp_ms=float(t),
                    meta={
                        "trit_preview": quantize_features_to_trits(vis),
                        "note": "U-Net placeholder; edge quantizes to trits for bare metal",
                    },
                ),
            )
        )
        scheduled.append(
            (
                t,
                MetricPacket(
                    cpu_util=0.35 + 0.2 * ((t // every) % 3) / 3.0,
                    mem_util=0.4,
                    disk_util=0.15,
                    net_util=0.1,
                    temp_norm=0.3,
                    timestamp_ms=float(t),
                ),
            )
        )
    return bus, scheduled


def run_brain_design_suite(
    steps: int = 800,
    device: str = "cpu",
    scale: float = 1.0,
    profile: str = "ai_efficient",
    sensory: bool = False,
) -> Dict[str, Any]:
    """
    profile: ai_efficient (default, computer-native) | wetware_ref
    scale: multiplies region sizes after profile base counts.
    sensory: inject vision + system-metric interoception during run
    """
    if profile not in BRAIN_PROFILES:
        raise ValueError(f"unknown profile {profile!r}; use {list(BRAIN_PROFILES)}")
    prof = BRAIN_PROFILES[profile]
    base_regions: List[RegionSpec] = list(prof["regions"])  # type: ignore
    isi_scale = float(prof["isi_scale"])

    regions = []
    for r in base_regions:
        regions.append(
            RegionSpec(
                id=r.id,
                label=r.label,
                n_units=max(3, int(round(r.n_units * scale))),
                mix=r.mix,
                role=r.role,
            )
        )
    cfg = BrainDesignConfig(regions=regions, device=device, seed=42)
    brain = FSOTBrainDesign(cfg)
    apply_timing_profile(brain, isi_scale)

    bus = None
    sensory_meta: Dict[str, Any] = {"enabled": False}
    if sensory:
        from .sensory import MetricPacket, SensoryBus, SensoryPacket

        bus = SensoryBus()
        every = 40
        # Custom run loop with scheduled sensory so queue refills each inject
        brain.reset()
        n = brain.n_units
        hist_S = torch.empty(steps, n, device=brain.device, dtype=brain.net.dtype)
        hist_f = torch.empty(steps, n, device=brain.device, dtype=torch.bool)
        hist_syn = torch.empty(steps, n, device=brain.device, dtype=brain.net.dtype)
        hist_tern = torch.empty(steps, n, device=brain.device, dtype=torch.int8)
        drive_ids = set(brain.region_index.get("thal", []))
        injections = 0
        from .trinary_substrate import quantize_features_to_trits

        for t in range(steps):
            if t % every == 0:
                vis = [0.8, -0.3, 0.5, 0.1, -0.6, 0.4]
                bus.push(
                    SensoryPacket(
                        modality=__import__(
                            "fsot_nuron.sensory.packets", fromlist=["SensoryModality"]
                        ).SensoryModality.VISION,
                        target_region="sens",
                        features=vis,
                        strength=0.45,
                        timestamp_ms=float(t),
                        meta={"trit_preview": quantize_features_to_trits(vis)},
                    )
                )
                bus.push_metric(
                    MetricPacket(
                        cpu_util=0.35 + 0.15 * ((t // every) % 4) / 4.0,
                        mem_util=0.42,
                        disk_util=0.12,
                        net_util=0.08,
                        temp_norm=0.28,
                        timestamp_ms=float(t),
                    )
                )
            ext = torch.zeros(n, device=brain.device, dtype=brain.net.dtype)
            on = (t % 80) < 20
            if on and drive_ids:
                for i in drive_ids:
                    ext[i] = 0.65 if brain.units[i].synapse_sign > 0 else 0.16
            se = bus.build_external(
                n, brain.region_index, device=brain.device, dtype=brain.net.dtype
            )
            if float(se.abs().sum().item()) > 0:
                injections += 1
            ext = (ext + se).clamp(-0.8, 1.5)
            S, fired, _, tern, syn = brain.step(ext)
            hist_S[t] = S
            hist_f[t] = fired
            hist_syn[t] = syn
            hist_tern[t] = tern
        rates = hist_f.float().sum(0) / (steps * brain.cfg.dt_ms / 1000.0)
        hist = {
            "S": hist_S,
            "fired": hist_f,
            "synaptic": hist_syn,
            "ternary": hist_tern,
            "firing_rate_Hz": rates,
            "steps": torch.tensor(steps, device=brain.device),
        }
        sensory_meta = {
            "enabled": True,
            "injections": injections,
            "modalities": ["vision", "sys_metric"],
            "trinary_edge": True,
            "note": "features quantized to trits at edge for bare-metal path",
        }
    else:
        hist = brain.run(steps=steps, drive_region="thal", drive_amp=0.65)

    structure = brain.structure_report()
    dynamics = brain.dynamics_report(hist)

    # Gates toward "brain-like" design (honest, not human brain claims)
    pop = structure["population"]
    gates = {
        "has_excitatory": pop["n_excitatory"] > 0,
        "has_inhibitory": pop["n_inhibitory"] > 0,
        "multi_region": len(structure["regions"]) >= 3,
        "has_projections": len(structure["projections"]) >= 3,
        "has_synapses": structure["n_synapses"] > 0,
        "ei_mass_finite": math.isfinite(structure["ei_mass_ratio"]),
        "thal_drive_active": dynamics["rate_by_region"].get("thal", 0) > 0.01
        or dynamics["mean_rate_Hz"] > 0.01,
        "efficiency_profile_ok": profile in BRAIN_PROFILES,
    }

    gates["sensory_path_ok"] = (not sensory) or bool(sensory_meta.get("injections", 0) > 0)

    return {
        "mission": (
            "FSOT multi-region brain design — mechanism fidelity, "
            "computer-native scale, trinary bare-metal destination"
        ),
        "profile": profile,
        "profile_intent": prof["intent"],
        "isi_scale": isi_scale,
        "structure": structure,
        "dynamics": dynamics,
        "gates": gates,
        "brain": brain,  # caller may use for Obsidian export
        "n_units": brain.n_units,
        "sensory": sensory_meta,
        "formulas_ref": "docs/FORMULAS.md",
        "thesis_ref": "docs/THESIS.md",
        "efficiency_ref": "docs/EFFICIENCY_DOCTRINE.md",
        "trinary_ref": "docs/TRINARY_BARE_METAL.md",
    }
