"""
Symbolic association layer — pattern → meaning anchors.

Stage honesty
-------------
We are **not** claiming ImageNet-level "this is a cat" vision.
We *are* building the substrate humans use later for that:

  1. Sensory signature (how the stream looked/sounded — numbers)
  2. Metadata label (what the file *is* — movie title, music track)
  3. Symbolic anchors (shared cultural prototypes: person, place, cat,
     face, music, action, cartoon, …)
  4. Bind them: co-encode label + sensory stats through FSOT machine path;
     retrieve nearest anchors and nearest other media memories.

Biological analogs:
  - Pareidolia / face-in-clouds: always match to *nearest known symbol*
  - Prototype categories: lion/tiger/Garfield → "cat" neighborhood
  - Cross-modal binding: sound of score + dark luma → "drama/dark"

Accuracy we can pin *now*:
  - Same-file segments associate to **own metadata** better than random files
  - Sensory signatures cluster by kind (music vs movie) above chance
  - Anchor ranking is deterministic and seed-lawful (no free neural net)

Full open-world object recognition = later stage (learned templates / more data).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch

from ..seeds import SEEDS
from ..learning_memory import make_fsot_item_patterns, _cosine
from .media_meta import MediaMetadata, extract_media_metadata


# Core symbolic vocabulary — prototypes for association (not a closed world)
DEFAULT_SYMBOLS: Tuple[str, ...] = (
    "person",
    "face",
    "place",
    "thing",
    "animal",
    "cat",
    "dog",
    "monster",
    "cartoon",
    "animation",
    "drawing",
    "movie",
    "tv_show",
    "episode",
    "music",
    "sound",
    "action",
    "comedy",
    "horror",
    "fantasy",
    "science_fiction",
    "space",
    "war",
    "indoor",
    "outdoor",
    "night",
    "day",
    "energy",
    "calm",
    "dark",
    "bright",
    "moving_image",
    "scene",
    "dialogue",
    "crowd",
    "vehicle",
    "building",
    "nature",
    "emotion",
    "rock",
    "adventure",
)


@dataclass
class SensorySignature:
    """Compressed 'how it felt' from vision/audio stats + brain state."""

    vector: List[float]
    luma: float = 0.0
    motion: float = 0.0
    contrast: float = 0.0
    edge: float = 0.0
    audio_rms: float = 0.0
    audio_centroid: float = 0.0
    mean_S: float = 0.0
    region_abs: Dict[str, float] = field(default_factory=dict)
    n_vision_packets: int = 0
    n_audio_packets: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class AssociationHit:
    symbol: str
    score: float
    kind: str  # anchor | media_meta | sensory_rule
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MediaAssociationReport:
    metadata: Dict[str, Any]
    signature: Dict[str, Any]
    top_anchors: List[Dict[str, Any]]
    rule_tags: List[Dict[str, Any]]
    meta_bind_score: float  # cosine(sensory, machine-encoded metadata label)
    self_label_rank: int  # 1 = best among candidates if multi-media
    notes: List[str] = field(default_factory=list)
    stage: str = "association_substrate_v0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_sensory_signature(
    *,
    vision_stats: Sequence[Dict[str, float]],
    audio_rms: Sequence[float],
    audio_centroids: Optional[Sequence[float]] = None,
    mean_S: float = 0.0,
    region_abs: Optional[Dict[str, float]] = None,
    n_vision: int = 0,
    n_audio: int = 0,
) -> SensorySignature:
    def avg(key: str) -> float:
        if not vision_stats:
            return 0.0
        return sum(float(s.get(key, 0.0)) for s in vision_stats) / len(vision_stats)

    luma = avg("luma")
    motion = avg("motion")
    contrast = avg("contrast")
    edge = avg("edge")
    r = avg("r")
    g = avg("g")
    b = avg("b")
    rms = sum(audio_rms) / len(audio_rms) if audio_rms else 0.0
    ac = (
        sum(audio_centroids) / len(audio_centroids)
        if audio_centroids
        else 0.0
    )
    reg = region_abs or {}
    # Fixed-layout vector for association (seed-stable dimensions)
    vec = [
        luma,
        contrast,
        motion,
        edge,
        r,
        g,
        b,
        abs(r - g),
        abs(g - b),
        abs(r - b),
        rms,
        ac,
        min(1.0, rms * 4.0),
        min(1.0, motion * 3.0),
        min(1.0, edge * 5.0),
        1.0 if luma > 0.45 else 0.0,  # day-ish
        1.0 if luma < 0.25 else 0.0,  # night-ish
        1.0 if motion > 0.08 else 0.0,  # action-ish
        1.0 if rms > 0.05 else 0.0,  # loud-ish
        reg.get("thal", 0.0),
        reg.get("sens", 0.0),
        reg.get("assoc", 0.0),
        reg.get("hipp", 0.0),
        float(mean_S),
        min(1.0, n_vision / 40.0),
        min(1.0, n_audio / 16.0),
    ]
    # L2 normalize
    t = torch.tensor(vec, dtype=torch.float64)
    t = t / (t.norm() + 1e-8)
    return SensorySignature(
        vector=t.tolist(),
        luma=luma,
        motion=motion,
        contrast=contrast,
        edge=edge,
        audio_rms=rms,
        audio_centroid=ac,
        mean_S=mean_S,
        region_abs=dict(reg),
        n_vision_packets=n_vision,
        n_audio_packets=n_audio,
    )


def _text_embedding(label: str, feat_dim: int = 24, seed: int = 7) -> torch.Tensor:
    """FSOT machine-bridged text → unit vector (same path as memory items)."""
    items = make_fsot_item_patterns(1, feat_dim=feat_dim, seed=seed)
    # force our label through same pipeline
    from ..machine_encode import text_to_utf8_trits, trits_to_drive_features
    from ..fsot_bridge import bridge_machine_payload, couple_features_with_S

    br = bridge_machine_payload(label)
    mods = br["modulators"]
    trits = text_to_utf8_trits(label)
    feats = trits_to_drive_features(trits, n_features=feat_dim)
    feats = couple_features_with_S(feats, mods)
    t = torch.tensor(feats, dtype=torch.float64)
    return t / (t.norm() + 1e-8)


def rule_based_symbol_scores(sig: SensorySignature) -> List[AssociationHit]:
    """
    Deterministic sensory→symbol heuristics (pareidolia / prototype bias).
    Not learned — explicit, inspectable, comparable across runs.
    """
    hits: List[AssociationHit] = []
    # brightness
    if sig.luma >= 0.45:
        hits.append(AssociationHit("day", min(1.0, sig.luma), "sensory_rule", "high luma"))
        hits.append(AssociationHit("bright", min(1.0, sig.luma), "sensory_rule", "high luma"))
    if sig.luma <= 0.28:
        hits.append(AssociationHit("night", min(1.0, 1.0 - sig.luma), "sensory_rule", "low luma"))
        hits.append(AssociationHit("dark", min(1.0, 1.0 - sig.luma), "sensory_rule", "low luma"))
    # motion / action
    if sig.motion >= 0.06:
        hits.append(
            AssociationHit("action", min(1.0, sig.motion * 4), "sensory_rule", "high motion")
        )
        hits.append(
            AssociationHit("moving_image", min(1.0, sig.motion * 3), "sensory_rule", "motion")
        )
    if sig.motion < 0.03 and sig.n_vision_packets > 0:
        hits.append(AssociationHit("calm", 0.55, "sensory_rule", "low motion"))
        hits.append(AssociationHit("scene", 0.5, "sensory_rule", "static-ish"))
    # edges ~ drawing / animation sometimes (high edge + mid luma)
    if sig.edge > 0.05 and 0.2 < sig.luma < 0.7:
        hits.append(
            AssociationHit("cartoon", min(0.85, sig.edge * 8), "sensory_rule", "edge structure")
        )
        hits.append(
            AssociationHit("drawing", min(0.75, sig.edge * 7), "sensory_rule", "edge structure")
        )
    # audio
    if sig.audio_rms >= 0.04:
        hits.append(
            AssociationHit("music", min(1.0, sig.audio_rms * 6), "sensory_rule", "audio energy")
        )
        hits.append(
            AssociationHit("sound", min(1.0, sig.audio_rms * 5), "sensory_rule", "audio energy")
        )
        hits.append(
            AssociationHit("energy", min(1.0, sig.audio_rms * 5), "sensory_rule", "loud")
        )
    if sig.audio_centroid > 0.35 and sig.audio_rms > 0.02:
        hits.append(AssociationHit("dialogue", 0.45, "sensory_rule", "higher spectral mass"))
    # always mild scene/person prior when video present (pareidolia-lite)
    if sig.n_vision_packets > 0:
        hits.append(AssociationHit("face", 0.22 + 0.15 * sig.contrast, "sensory_rule", "face prior"))
        hits.append(AssociationHit("person", 0.20 + 0.1 * sig.contrast, "sensory_rule", "person prior"))
        hits.append(AssociationHit("thing", 0.25, "sensory_rule", "object prior"))
        hits.append(AssociationHit("place", 0.18 + 0.2 * (1.0 - sig.motion), "sensory_rule", "place prior"))
    # sort unique best score per symbol
    best: Dict[str, AssociationHit] = {}
    for h in hits:
        if h.symbol not in best or h.score > best[h.symbol].score:
            best[h.symbol] = h
    return sorted(best.values(), key=lambda x: -x.score)


def associate_media_episode(
    meta: MediaMetadata,
    sig: SensorySignature,
    *,
    symbols: Sequence[str] = DEFAULT_SYMBOLS,
    seed: int = 7,
    rival_metas: Optional[Sequence[MediaMetadata]] = None,
) -> MediaAssociationReport:
    """
    Bind one chewed media episode to symbols + its own metadata label.

    meta_bind_score: similarity of sensory vector to FSOT-encoded metadata text
    (cross-signal pattern binding — not free fit).
    """
    notes: List[str] = [
        "Stage: association substrate — not full object recognition.",
        "Metadata labels are file-grounded; anchors are cultural prototypes.",
        "Rule tags are inspectable sensory→symbol heuristics (pareidolia bias).",
    ]

    # Project sensory into same dim as text embeddings for cosine
    sens_t = torch.tensor(sig.vector, dtype=torch.float64)
    # pad/truncate to 24
    feat_dim = 24
    if sens_t.numel() < feat_dim:
        sens_t = torch.cat([sens_t, torch.zeros(feat_dim - sens_t.numel(), dtype=torch.float64)])
    else:
        sens_t = sens_t[:feat_dim]
    sens_t = sens_t / (sens_t.norm() + 1e-8)

    label = meta.label_line()
    meta_emb = _text_embedding(label, feat_dim=feat_dim, seed=seed)
    meta_bind = _cosine(sens_t, meta_emb)

    # Anchor ranking: blend text-embedding of symbol with rule scores
    rules = {h.symbol: h for h in rule_based_symbol_scores(sig)}
    # metadata symbols get a boost (known tags from path)
    meta_syms = set(meta.symbols) | set(meta.tags)

    anchor_hits: List[AssociationHit] = []
    for sym in symbols:
        emb = _text_embedding(f"symbol {sym}", feat_dim=feat_dim, seed=seed + hash(sym) % 97)
        # mix: sensory·symbol_text + rule prior + metadata agreement
        c = _cosine(sens_t, emb)
        rule = rules.get(sym)
        rule_s = rule.score if rule else 0.0
        meta_boost = 0.25 if sym in meta_syms else 0.0
        # φ-weighted blend (seed-only weights)
        gate = SEEDS.phi / (1.0 + SEEDS.phi)
        score = (1.0 - gate) * max(0.0, c) + gate * rule_s + meta_boost
        note = []
        if rule:
            note.append(f"rule={rule.note}")
        if sym in meta_syms:
            note.append("meta_tag")
        note.append(f"text_cos={c:.3f}")
        anchor_hits.append(
            AssociationHit(sym, float(score), "anchor", "; ".join(note))
        )
    anchor_hits.sort(key=lambda x: -x.score)
    top = anchor_hits[:12]

    # Self-label rank among rivals (metadata discrimination)
    self_rank = 1
    if rival_metas:
        scores = []
        for m in list(rival_metas) + [meta]:
            emb = _text_embedding(m.label_line(), feat_dim=feat_dim, seed=seed)
            scores.append((m.title, _cosine(sens_t, emb)))
        scores.sort(key=lambda x: -x[1])
        for i, (title, _) in enumerate(scores, start=1):
            if title == meta.title:
                self_rank = i
                break
        notes.append(f"metadata discrimination rank {self_rank}/{len(scores)} among rivals")

    return MediaAssociationReport(
        metadata=meta.to_dict(),
        signature=sig.to_dict(),
        top_anchors=[h.to_dict() for h in top],
        rule_tags=[h.to_dict() for h in rule_based_symbol_scores(sig)[:10]],
        meta_bind_score=float(meta_bind),
        self_label_rank=self_rank,
        notes=notes,
    )


def summarize_associations(reports: List[MediaAssociationReport]) -> Dict[str, Any]:
    """Aggregate accuracy-ish metrics for the stage report."""
    if not reports:
        return {"n": 0}
    binds = [r.meta_bind_score for r in reports]
    ranks = [r.self_label_rank for r in reports]
    # How often top-3 anchors intersect metadata tags/symbols
    hits = 0
    for r in reports:
        meta_set = set(r.metadata.get("symbols") or []) | set(r.metadata.get("tags") or [])
        top = {a["symbol"] for a in r.top_anchors[:5]}
        if meta_set & top:
            hits += 1
    return {
        "n_episodes": len(reports),
        "mean_meta_bind": sum(binds) / len(binds),
        "mean_self_label_rank": sum(ranks) / len(ranks),
        "top5_anchor_hits_meta_frac": hits / len(reports),
        "note": (
            "meta_bind = sensory·metadata_text cosine; "
            "anchor_hits = path tags appear in top-5 symbols; "
            "not object-detection accuracy"
        ),
    }
