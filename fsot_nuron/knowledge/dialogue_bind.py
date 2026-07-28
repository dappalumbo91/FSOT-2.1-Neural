"""
Dialogue-heavy clusters as subtitles — bind caption lines to AV moments.

Like watching with captions on:
  visual moment @ t  +  caption overlapping t  →  joint meaning token

Lightweight: no continuous STT required if .srt/.vtt exists.
STT segments are converted to the same CaptionCue shape when needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..sensory.cross_modal import AVMoment
from ..sensory.packets import SensoryPacket, SensoryModality
from ..machine_encode import encode_to_sensory_packet, EncodePath
from ..seeds import SEEDS
from .subtitles import (
    CaptionCue,
    load_subtitles,
    captions_near,
    flatten_caption_text,
    cues_from_stt_segments,
)
from .speech_text import transcribe_audio_file
from .cross_feed import cross_feed_episode, CrossFeedReport
from .episode_memory import EpisodeMemory, save_episode, _eid


@dataclass
class DialogueBindReport:
    caption_source: str
    n_cues: int
    n_moments_with_dialogue: int
    sample_lines: List[str]
    full_dialogue_text: str
    moment_bindings: List[Dict[str, Any]] = field(default_factory=list)
    cross_feed: Dict[str, Any] = field(default_factory=dict)
    plain_english: str = ""
    episode_id: str = ""
    memory_path: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def resolve_captions(
    media_path: Path,
    *,
    prefer_stt: bool = False,
    stt_max_s: float = 60.0,
) -> tuple[List[CaptionCue], str, List[str]]:
    """
    Prefer sidecar subtitles; optionally STT as synthetic subtitles.
    Returns (cues, source, notes).
    """
    notes: List[str] = []
    if not prefer_stt:
        cues = load_subtitles(media_path)
        if cues:
            notes.append(f"sidecar subtitles: {len(cues)} cues")
            return cues, cues[0].source if cues else "srt", notes
        notes.append("no sidecar .srt/.vtt")
    # STT fallback (or forced)
    stt = transcribe_audio_file(media_path, max_s=stt_max_s)
    if stt.ok and stt.segments:
        cues = cues_from_stt_segments(stt.segments)
        notes.append(f"STT-as-subtitles: {stt.backend} cues={len(cues)}")
        return cues, "stt", notes
    if stt.ok and stt.text:
        # single blob as one cue
        cues = [CaptionCue(0.0, stt_max_s, stt.text, source="stt")]
        notes.append(f"STT blob: {stt.backend}")
        return cues, "stt", notes
    notes.extend(stt.notes[:2])
    return [], "none", notes


def bind_dialogue_to_moments(
    moments: Sequence[AVMoment],
    cues: Sequence[CaptionCue],
    *,
    window_s: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Pair each moment with caption lines at that time.

    Default temporal window is seed-structured: φ + 1/e (via captions_near).
    Best-matching cue (strict overlap preferred) is listed first.
    """
    # None → captions_near applies φ-window; keep optional explicit override
    near_kw: Dict[str, Any] = {}
    if window_s is not None:
        near_kw["window_s"] = float(window_s)
    bindings = []
    for m in moments:
        near = captions_near(cues, m.t_sec, **near_kw)
        # Prefer the nearest cue's text first, then any additional overlaps
        if near:
            primary = near[0].text.strip()
            extras = [c.text.strip() for c in near[1:] if c.text.strip() and c.text.strip() != primary]
            line = primary if not extras else (primary + " " + " ".join(extras[:2])).strip()
        else:
            line = ""
        bindings.append(
            {
                "t_sec": m.t_sec,
                "bind_strength": m.bind_strength,
                "dialogue": line,
                "n_cues": len(near),
                "vision": {
                    "luma": m.vision_stats.get("luma"),
                    "motion": m.vision_stats.get("motion"),
                },
                "audio": {
                    "rms": m.audio_stats.get("rms"),
                    "speech_band": m.audio_stats.get("speech_band"),
                },
            }
        )
    return bindings


def dialogue_packets_for_bindings(
    bindings: Sequence[Dict[str, Any]],
    *,
    source: str = "",
    max_lines: int = 24,
) -> List[SensoryPacket]:
    """Caption lines → machine TEXT packets (assoc + hipp), subtitle style."""
    gate = SEEDS.phi / (1.0 + SEEDS.phi)
    pkts: List[SensoryPacket] = []
    n = 0
    for b in bindings:
        line = (b.get("dialogue") or "").strip()
        if not line:
            continue
        n += 1
        if n > max_lines:
            break
        # short caption teach text
        text = f"[subtitle t={b.get('t_sec', 0):.1f}s] {line}"
        try:
            pkt = encode_to_sensory_packet(
                text,
                path=EncodePath.MACHINE,
                target_region="assoc",
                strength=0.45 * gate,
            )
            pkt.meta["kind"] = "subtitle_dialogue"
            pkt.meta["t_sec"] = b.get("t_sec")
            pkt.meta["source"] = source
            pkt.timestamp_ms = float(b.get("t_sec") or 0) * 1000.0
            pkts.append(pkt)
            hip = encode_to_sensory_packet(
                text,
                path=EncodePath.MACHINE,
                target_region="hipp",
                strength=0.35 * gate,
            )
            hip.meta["kind"] = "subtitle_episodic"
            hip.meta["t_sec"] = b.get("t_sec")
            pkts.append(hip)
        except Exception:
            continue
    return pkts


def moments_at_caption_times(
    media_path: Path,
    cues: Sequence[CaptionCue],
    *,
    max_moments: int = 16,
) -> List[AVMoment]:
    """
    Sample AV moments at subtitle midpoints — dialogue-heavy cluster strategy.
    Much more efficient than uniform frame stride when captions exist.
    """
    from ..sensory.cross_modal import (
        load_video_audio_mono,
        audio_slice_features,
        _joint_features,
        _bind_strength,
        AVMoment,
    )
    from ..sensory.media_stream import iter_video_frames, _rgb_to_features
    import numpy as np

    if not cues:
        return []
    # spread across film: take evenly spaced cues
    step = max(1, len(cues) // max_moments)
    chosen = list(cues[::step][:max_moments])
    mono, sr = load_video_audio_mono(media_path, sr=16000)
    # build a coarse frame index by decoding with large stride then nearest t
    # For efficiency: decode a limited set of frames and map by time
    frame_bank: List[tuple] = []
    prev = None
    # estimate: sample ~max_moments*3 frames across file
    for rgb, t in iter_video_frames(
        media_path, max_frames=max(max_moments * 3, 24), stride=max(8, 48 // max(1, max_moments // 4)), max_side=96
    ):
        v_feats, prev, v_stats = _rgb_to_features(rgb, prev)
        frame_bank.append((t, v_feats, v_stats))
    if not frame_bank:
        return []

    def nearest_frame(t_sec: float):
        best = min(frame_bank, key=lambda x: abs(x[0] - t_sec))
        return best

    out: List[AVMoment] = []
    for c in chosen:
        t = c.mid_s()
        t_f, v_feats, v_stats = nearest_frame(t)
        if mono is not None:
            a_feats, a_stats = audio_slice_features(mono, sr, t, half_s=0.5)
        else:
            a_feats, a_stats = [], {"rms": 0.0, "speech_band": 0.0, "dialogue_prior": 0.0}
        joint = _joint_features(v_feats, a_feats if a_feats else [0.0] * 14)
        bs = _bind_strength(v_stats, a_stats)
        # boost bind when we know caption is present
        bs = min(1.0, bs + 0.25)
        out.append(
            AVMoment(
                t_sec=t,
                vision_feats=v_feats,
                audio_feats=a_feats,
                joint_feats=joint,
                vision_stats=v_stats,
                audio_stats=a_stats,
                bind_strength=bs,
            )
        )
    return out


def process_episode_with_subtitles(
    media_path: Path | str,
    *,
    moments: Sequence[AVMoment],
    symbols: Sequence[str],
    title: str = "",
    prefer_stt: bool = False,
    save_memory: bool = True,
    av_stats: Optional[Dict[str, Any]] = None,
    align_to_captions: bool = True,
) -> DialogueBindReport:
    """
    Full subtitle-style dialogue bind + knowledge cross-feed + optional memory save.
    """
    media_path = Path(media_path)
    notes: List[str] = []
    cues, source, n0 = resolve_captions(media_path, prefer_stt=prefer_stt)
    notes.extend(n0)

    # Prefer moments sampled at caption times (dialogue clusters)
    use_moments: List[AVMoment] = list(moments)
    if align_to_captions and cues:
        try:
            cap_moments = moments_at_caption_times(
                media_path, cues, max_moments=max(8, min(20, len(moments) or 12))
            )
            if cap_moments:
                use_moments = cap_moments
                notes.append(
                    f"aligned {len(cap_moments)} AV moments to subtitle timestamps"
                )
        except Exception as e:
            notes.append(f"caption-time sample fallback: {e}")

    bindings = bind_dialogue_to_moments(use_moments, cues) if cues else []
    # force-attach caption text at midpoints even if window miss
    if cues and bindings:
        for i, b in enumerate(bindings):
            if b.get("dialogue"):
                continue
            # nearest cue by time
            t = float(b.get("t_sec") or 0)
            nearest = min(cues, key=lambda c: abs(c.mid_s() - t))
            if abs(nearest.mid_s() - t) <= 3.0:
                b["dialogue"] = nearest.text
                b["n_cues"] = 1
    with_d = sum(1 for b in bindings if b.get("dialogue"))
    sample = [b["dialogue"] for b in bindings if b.get("dialogue")][:6]
    full_text = flatten_caption_text(cues, max_chars=1200)

    # knowledge with dialogue as "transcript"
    cf = cross_feed_episode(
        symbols=list(symbols),
        title=title or media_path.stem,
        transcript=full_text,
        path_hint=str(media_path),
        sensory_notes=(
            f"Subtitle-style dialogue ({source}): {with_d}/{len(bindings)} moments have lines. "
            f"AV bind={float((av_stats or {}).get('mean_bind') or 0):.2f}."
        ),
    )
    notes.extend(cf.notes)

    mem_path = ""
    eid = _eid(title or media_path.stem, str(media_path))
    if save_memory:
        av_stats = av_stats or {}
        mem = EpisodeMemory(
            episode_id=eid,
            title=title or media_path.stem,
            path=str(media_path),
            kind="video",
            symbols=list(dict.fromkeys([str(s) for s in symbols]))[:20],
            caption_source=source,
            caption_text=full_text,
            caption_cues_n=len(cues),
            plain_english=cf.plain_english,
            knowledge_keys=[e.get("key") for e in cf.entries_used if isinstance(e, dict)],
            n_trits=cf.n_trits,
            S_couple=cf.S_couple,
            av_mean_bind=float(av_stats.get("mean_bind") or 0.0),
            av_speech_band=float(av_stats.get("mean_speech_band") or 0.0),
            sample_lines=sample,
            notes=notes[:12],
        )
        p = save_episode(mem)
        mem_path = str(p)
        notes.append(f"episode memory saved: {p.name}")

    return DialogueBindReport(
        caption_source=source,
        n_cues=len(cues),
        n_moments_with_dialogue=with_d,
        sample_lines=sample,
        full_dialogue_text=full_text,
        moment_bindings=bindings[:40],
        cross_feed=cf.to_dict(),
        plain_english=cf.plain_english,
        episode_id=eid,
        memory_path=mem_path,
        notes=notes,
    )
