"""
Cross-modal temporal binding — see + hear at the same time → one pattern.

Doctrine (infant / animal word learning analog):
  When movies/shows stream, **audio and vision co-occur**. The brain does not
  need filename metadata first. It binds:

      vision signature @ t  ⊗  audio signature @ t  →  joint episode token

  Later, either channel can retrieve the joint (and the other modality).
  Speech-band energy acts as a *dialogue prior* (full ASR is optional later).

Stage honesty:
  - Not Whisper-level transcription yet (optional later if installed).
  - Is real **time-aligned A/V co-encoding** + association to symbols.
  - Metadata remains an optional tutor label, not the only path to meaning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np
import torch

from ..seeds import SEEDS
from ..learning_memory import _cosine
from .packets import SensoryModality, SensoryPacket
from .media_stream import (
    iter_video_frames,
    vision_packet_from_frame,
    _rgb_to_features,
    sample_audio_window,
)
from .symbol_assoc import (
    DEFAULT_SYMBOLS,
    SensorySignature,
    AssociationHit,
    rule_based_symbol_scores,
    _text_embedding,
)


def load_video_audio_mono(path: Path, sr: int = 16000) -> Tuple[Optional[np.ndarray], int]:
    """Extract full mono soundtrack from a video/muxed file (PyAV)."""
    try:
        import av  # type: ignore

        container = av.open(str(path))
        if not container.streams.audio:
            container.close()
            return None, sr
        resampler = av.audio.resampler.AudioResampler(
            format="flt", layout="mono", rate=sr
        )
        chunks: List[np.ndarray] = []

        def _consume(frames) -> None:
            if frames is None:
                return
            if not isinstance(frames, list):
                frames = [frames]
            for f in frames:
                if f is None:
                    continue
                arr = f.to_ndarray()
                if arr.ndim == 2:
                    # (channels, samples) or (1, n)
                    arr = arr.reshape(-1) if arr.shape[0] == 1 else arr.mean(axis=0)
                chunks.append(np.asarray(arr, dtype=np.float32).ravel())

        for frame in container.decode(audio=0):
            _consume(resampler.resample(frame))
        try:
            _consume(resampler.resample(None))
        except Exception:
            pass
        container.close()
        if not chunks:
            return None, sr
        return np.concatenate(chunks), sr
    except Exception:
        return None, sr


def audio_slice_features(
    mono: np.ndarray,
    sr: int,
    t_sec: float,
    half_s: float = 0.45,
) -> Tuple[List[float], Dict[str, float]]:
    """Feature window of soundtrack centered on visual time t."""
    if mono is None or mono.size == 0:
        return [], {"rms": 0.0, "speech_band": 0.0, "music_band": 0.0}
    n = mono.size
    c = int(t_sec * sr)
    half = int(half_s * sr)
    a, b = max(0, c - half), min(n, c + half)
    if b <= a:
        return [], {"rms": 0.0, "speech_band": 0.0, "music_band": 0.0}
    win = mono[a:b].astype(np.float32)
    if win.size < 32:
        return [], {"rms": 0.0, "speech_band": 0.0, "music_band": 0.0}
    rms = float(np.sqrt(np.mean(win ** 2)))
    peak = float(np.max(np.abs(win)))
    w = win * np.hanning(len(win))
    spec = np.abs(np.fft.rfft(w))
    freqs = np.fft.rfftfreq(len(w), d=1.0 / sr)
    # Speech band ~300–3400 Hz; music-ish low/high residual
    speech_m = (freqs >= 300) & (freqs <= 3400)
    low_m = freqs < 300
    high_m = freqs > 3400
    speech = float(spec[speech_m].mean()) if speech_m.any() else 0.0
    low = float(spec[low_m].mean()) if low_m.any() else 0.0
    high = float(spec[high_m].mean()) if high_m.any() else 0.0
    tot = speech + low + high + 1e-9
    speech_n, low_n, high_n = speech / tot, low / tot, high / tot
    # log bands for binding richness
    edges = np.logspace(np.log10(40), np.log10(min(8000, sr / 2 - 1)), 9)
    bands = []
    for i in range(8):
        m = (freqs >= edges[i]) & (freqs < edges[i + 1])
        bands.append(float(spec[m].mean()) if m.any() else 0.0)
    bs = sum(bands) + 1e-9
    bands = [x / bs for x in bands]
    denom = float(spec.sum()) + 1e-9
    centroid = float((freqs * spec).sum() / denom) / (sr / 2)
    feats = [rms, peak, centroid, speech_n, low_n, high_n] + bands
    stats = {
        "rms": rms,
        "peak": peak,
        "centroid_norm": centroid,
        "speech_band": speech_n,
        "music_band": low_n + high_n * 0.5,
        "dialogue_prior": float(speech_n * min(1.0, rms * 8)),
    }
    return feats, stats


@dataclass
class AVMoment:
    """One time-aligned audiovisual sample (the co-occurrence atom)."""

    t_sec: float
    vision_feats: List[float]
    audio_feats: List[float]
    joint_feats: List[float]
    vision_stats: Dict[str, float]
    audio_stats: Dict[str, float]
    bind_strength: float  # how strongly V and A co-activate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "t_sec": self.t_sec,
            "vision_stats": self.vision_stats,
            "audio_stats": self.audio_stats,
            "bind_strength": self.bind_strength,
            "n_joint": len(self.joint_feats),
        }


def _joint_features(v: List[float], a: List[float]) -> List[float]:
    """Cross-modal binding vector: concat + elementwise products of heads."""
    vh = (v + [0.0] * 12)[:12]
    ah = (a + [0.0] * 12)[:12]
    prods = [vh[i] * ah[i] for i in range(12)]
    # seed-scaled mix weight
    gate = SEEDS.phi / (1.0 + SEEDS.phi)
    joint = vh + ah + [gate * p for p in prods]
    # normalize for stable cosine later
    t = np.asarray(joint, dtype=np.float64)
    nrm = np.linalg.norm(t) + 1e-8
    return (t / nrm).tolist()


def _bind_strength(vstats: Dict[str, float], astats: Dict[str, float]) -> float:
    """
    High when modalities co-activate *and* co-vary in the biological sense:
    classic Hebbian gate — joint activity with congruence, not just energy.

    FSOT-lawful weights: φ-gate and ψ_con only.
    """
    gate = SEEDS.phi / (1.0 + SEEDS.phi)
    v_on = min(1.0, float(vstats.get("contrast", 0)) * 2 + float(vstats.get("motion", 0)) * 3)
    a_on = min(
        1.0,
        float(astats.get("rms", 0)) * 6 + float(astats.get("dialogue_prior", 0)),
    )
    # Congruence: motion/energy vs audio energy (normalized same scale)
    v_sig = min(1.0, float(vstats.get("motion", 0)) * 4)
    a_sig = min(1.0, float(astats.get("rms", 0)) * 5 + float(astats.get("speech_band", 0)))
    # high when both high or both low; penalize anti-correlated energy
    match = 1.0 - abs(v_sig - a_sig)
    co_high = v_sig * a_sig
    co_low = (1.0 - v_sig) * (1.0 - a_sig)
    congruence = gate * match + (1.0 - gate) * (co_high + co_low)
    joint = math.sqrt(max(1e-6, v_on * a_on))
    # Hebbian-ish: co-occurrence × congruence; φ / ψ_con only
    raw = joint * (0.35 + 0.65 * congruence) * (SEEDS.psi_con + gate) / 1.5
    return float(min(1.0, max(0.0, raw)))


def iter_audiovisual_moments(
    path: Path,
    *,
    max_moments: int = 24,
    frame_stride: int = 20,
    max_side: int = 96,
    audio_half_s: float = 0.45,
) -> Iterator[AVMoment]:
    """
    Stream time-aligned (vision frame, soundtrack window) moments from a movie/show.
    """
    mono, sr = load_video_audio_mono(path, sr=16000)
    prev_gray = None
    for rgb, t_sec in iter_video_frames(
        path, max_frames=max_moments, stride=frame_stride, max_side=max_side
    ):
        v_feats, prev_gray, v_stats = _rgb_to_features(rgb, prev_gray)
        if mono is not None:
            a_feats, a_stats = audio_slice_features(mono, sr, t_sec, half_s=audio_half_s)
        else:
            a_feats, a_stats = [], {"rms": 0.0, "speech_band": 0.0, "music_band": 0.0, "dialogue_prior": 0.0}
        joint = _joint_features(v_feats, a_feats if a_feats else [0.0] * 14)
        bs = _bind_strength(v_stats, a_stats)
        yield AVMoment(
            t_sec=t_sec,
            vision_feats=v_feats,
            audio_feats=a_feats,
            joint_feats=joint,
            vision_stats=v_stats,
            audio_stats=a_stats,
            bind_strength=bs,
        )


def moment_to_packets(moment: AVMoment, source: str = "") -> List[SensoryPacket]:
    """Vision → sens, audio → sens, joint bind → assoc (meaning cortex)."""
    gate = SEEDS.phi / (1.0 + SEEDS.phi)
    tms = moment.t_sec * 1000.0
    pkts: List[SensoryPacket] = []
    sal_v = min(1.0, 0.35 + 0.5 * moment.vision_stats.get("contrast", 0) + 0.8 * moment.vision_stats.get("motion", 0))
    pkts.append(
        SensoryPacket(
            modality=SensoryModality.VISION,
            target_region="sens",
            features=moment.vision_feats,
            strength=0.55 * gate * sal_v,
            timestamp_ms=tms,
            meta={"kind": "av_vision", "source": source, "t_sec": moment.t_sec, "stats": moment.vision_stats},
        )
    )
    if moment.audio_feats:
        sal_a = min(1.0, 0.3 + 5.0 * moment.audio_stats.get("rms", 0))
        pkts.append(
            SensoryPacket(
                modality=SensoryModality.AUDIO,
                target_region="sens",
                features=moment.audio_feats,
                strength=0.5 * gate * sal_a,
                timestamp_ms=tms,
                meta={
                    "kind": "av_audio",
                    "source": source,
                    "t_sec": moment.t_sec,
                    "stats": moment.audio_stats,
                    "dialogue_prior": moment.audio_stats.get("dialogue_prior"),
                },
            )
        )
    # Joint pattern lands in association — the co-occurrence symbol slot
    pkts.append(
        SensoryPacket(
            modality=SensoryModality.CUSTOM,
            target_region="assoc",
            features=moment.joint_feats,
            strength=0.45 * gate * (0.4 + 0.6 * moment.bind_strength),
            timestamp_ms=tms,
            meta={
                "kind": "cross_modal_bind",
                "source": source,
                "t_sec": moment.t_sec,
                "bind_strength": moment.bind_strength,
                "decode": "vision⊗audio temporal co-occurrence",
            },
        )
    )
    # Dialogue + face-ish prior → hipp episodic tag (word-object learning niche)
    if moment.audio_stats.get("dialogue_prior", 0) > 0.08 and moment.vision_stats.get("contrast", 0) > 0.05:
        pkts.append(
            SensoryPacket(
                modality=SensoryModality.CUSTOM,
                target_region="hipp",
                features=[
                    moment.audio_stats.get("dialogue_prior", 0),
                    moment.vision_stats.get("contrast", 0),
                    moment.vision_stats.get("luma", 0),
                    moment.bind_strength,
                ],
                strength=0.35 * gate,
                timestamp_ms=tms,
                meta={"kind": "dialogue_visual_bind", "source": source, "t_sec": moment.t_sec},
            )
        )
    return pkts


def cluster_joint_patterns(
    moments: Sequence[AVMoment],
    n_clusters: int = 6,
) -> List[Dict[str, Any]]:
    """
    Soft k-means on joint features — recurring AV patterns without labels.
    These are the pre-symbolic 'that again' tokens.
    """
    if not moments:
        return []
    X = np.array([m.joint_feats for m in moments], dtype=np.float64)
    if X.ndim != 2 or X.shape[0] < 2:
        return [{"id": 0, "n": len(moments), "mean_bind": float(moments[0].bind_strength)}]
    k = min(n_clusters, X.shape[0])
    # init: spread along first PCA-ish axis (mean-centered)
    mu = X.mean(axis=0)
    Xc = X - mu
    # random-stable from data
    rng = np.random.RandomState(int(abs(mu[0]) * 1e6) % (2**31 - 1) or 7)
    centers = X[rng.choice(X.shape[0], size=k, replace=False)]
    for _ in range(12):
        # assign
        d = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = d.argmin(axis=1)
        for j in range(k):
            mask = labels == j
            if mask.any():
                centers[j] = X[mask].mean(axis=0)
    clusters = []
    for j in range(k):
        mask = labels == j
        if not mask.any():
            continue
        idxs = np.where(mask)[0]
        memb = [moments[int(i)] for i in idxs]
        mean_v = {
            "luma": float(np.mean([m.vision_stats.get("luma", 0) for m in memb])),
            "motion": float(np.mean([m.vision_stats.get("motion", 0) for m in memb])),
            "speech": float(np.mean([m.audio_stats.get("speech_band", 0) for m in memb])),
            "rms": float(np.mean([m.audio_stats.get("rms", 0) for m in memb])),
            "bind": float(np.mean([m.bind_strength for m in memb])),
        }
        # map cluster centroid to nearest symbols via rules on synthetic signature
        syn = SensorySignature(
            vector=centers[j].tolist(),
            luma=mean_v["luma"],
            motion=mean_v["motion"],
            contrast=0.1,
            edge=0.05,
            audio_rms=mean_v["rms"],
            audio_centroid=0.3,
            n_vision_packets=len(memb),
            n_audio_packets=len(memb),
        )
        rules = rule_based_symbol_scores(syn)[:5]
        # dialogue cluster
        if mean_v["speech"] > 0.25 and mean_v["rms"] > 0.02:
            rules.insert(0, AssociationHit("dialogue", 0.7, "cross_modal", "speech-band+vision"))
            rules.insert(1, AssociationHit("person", 0.55, "cross_modal", "speech co-occur"))
        clusters.append(
            {
                "id": j,
                "n_moments": int(mask.sum()),
                "mean_stats": mean_v,
                "top_symbols": [h.to_dict() for h in rules[:6]],
                "t_sec_samples": [round(m.t_sec, 2) for m in memb[:5]],
            }
        )
    clusters.sort(key=lambda c: -c["n_moments"])
    return clusters


def cross_modal_association(
    moments: Sequence[AVMoment],
    *,
    seed: int = 7,
) -> Dict[str, Any]:
    """
    Associate from A/V co-occurrence alone (metadata optional).

    Returns recurring joint patterns + symbol rankings driven by joint stats.
    """
    if not moments:
        return {
            "n_moments": 0,
            "mean_bind": 0.0,
            "has_soundtrack": False,
            "clusters": [],
            "global_symbols": [],
            "note": "no AV moments",
        }
    has_audio = any(m.audio_feats for m in moments)
    mean_bind = float(np.mean([m.bind_strength for m in moments]))
    clusters = cluster_joint_patterns(moments, n_clusters=min(6, max(2, len(moments) // 3)))

    # Global signature from all moments
    vstats = [m.vision_stats for m in moments]
    arms = [m.audio_stats.get("rms", 0.0) for m in moments]
    acent = [m.audio_stats.get("centroid_norm", 0.0) for m in moments]
    from .symbol_assoc import build_sensory_signature, associate_media_episode
    from .media_meta import MediaMetadata

    sig = build_sensory_signature(
        vision_stats=vstats,
        audio_rms=arms,
        audio_centroids=acent,
        n_vision=len(moments),
        n_audio=len(moments) if has_audio else 0,
    )
    # Minimal meta — kind only (no title dependency)
    bare = MediaMetadata(
        path="",
        title="av_stream",
        kind="video",
        root_hint="shows" if has_audio else "movies",
        tags=["moving_image", "sound"] if has_audio else ["moving_image"],
        symbols=["moving_image", "scene", "sound"] if has_audio else ["moving_image", "scene"],
    )
    # Still call associate for anchor ranking; bind score less critical
    arep = associate_media_episode(bare, sig, seed=seed, rival_metas=None)

    # Promote cross-modal rules
    extra = []
    mean_speech = float(np.mean([m.audio_stats.get("speech_band", 0) for m in moments]))
    mean_motion = float(np.mean([m.vision_stats.get("motion", 0) for m in moments]))
    if mean_speech > 0.2 and has_audio:
        extra.append({"symbol": "dialogue", "score": mean_speech, "kind": "cross_modal"})
        extra.append({"symbol": "person", "score": 0.4 + 0.3 * mean_speech, "kind": "cross_modal"})
    if mean_motion > 0.08:
        extra.append({"symbol": "action", "score": min(1.0, mean_motion * 5), "kind": "cross_modal"})

    return {
        "n_moments": len(moments),
        "mean_bind": mean_bind,
        "has_soundtrack": has_audio,
        "mean_speech_band": mean_speech,
        "mean_motion": mean_motion,
        "clusters": clusters,
        "global_symbols": arep.top_anchors[:8],
        "cross_modal_symbols": extra,
        "note": (
            "Patterns from simultaneous audio+visual co-occurrence. "
            "Metadata not required for binding; optional tutor only."
        ),
    }
