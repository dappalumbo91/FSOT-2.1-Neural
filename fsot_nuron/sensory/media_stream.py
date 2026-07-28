"""
Optional media sensory stream — video/audio → VISION / AUDIO packets.

Doctrine:
  - **Not required** for standalone boot. Missing roots / codecs → empty packets.
  - Test libraries (movies, music, shows) are *afferent injectors*, like eyes/ears
    looking at the world — not part of the brain's identity.
  - Decode analogy: HDMI/TV pipeline = pixels over time; we do the *data-side*
    equivalent: sample frames → color/luma/motion features → sensory cortex.

Backends (graceful):
  - Video: PyAV (`av`) preferred; imageio fallback
  - Audio: soundfile + numpy FFT (librosa optional for mel)
"""

from __future__ import annotations

import math
import os
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np

from .packets import SensoryModality, SensoryPacket
from ..seeds import SEEDS

# Optional default test libraries (user machine) — never required
DEFAULT_MEDIA_ROOTS = (
    Path(r"G:\movies"),
    Path(r"G:\showes"),
    Path(r"G:\Debut"),
)

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".m4v", ".wmv", ".mov", ".webm", ".mpg", ".mpeg"}
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aac", ".wma"}


def media_roots_from_env() -> List[Path]:
    """
    FSOT_MEDIA_ROOTS=path1;path2  or empty → default G: test roots if present.
    Empty list if nothing exists (standalone still boots).
    """
    raw = os.environ.get("FSOT_MEDIA_ROOTS", "").strip()
    if raw:
        candidates = [Path(p.strip()) for p in raw.replace(",", ";").split(";") if p.strip()]
    else:
        candidates = list(DEFAULT_MEDIA_ROOTS)
    return [p for p in candidates if p.is_dir()]


def discover_media_files(
    roots: Optional[Sequence[Path]] = None,
    *,
    max_files: int = 200,
    kind: str = "any",  # video | audio | any
) -> List[Path]:
    roots = list(roots) if roots is not None else media_roots_from_env()
    out: List[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for dirpath, _dirnames, filenames in os.walk(root):
                # skip deep junk
                depth = Path(dirpath).relative_to(root).parts
                if len(depth) > 6:
                    continue
                for name in filenames:
                    ext = Path(name).suffix.lower()
                    if kind in ("video", "any") and ext in VIDEO_EXTS:
                        out.append(Path(dirpath) / name)
                    elif kind in ("audio", "any") and ext in AUDIO_EXTS:
                        out.append(Path(dirpath) / name)
                    if len(out) >= max_files:
                        return out
        except OSError:
            continue
    return out


# ---------------------------------------------------------------------------
# Pixel decode (eye / HDMI-like)
# ---------------------------------------------------------------------------

def _rgb_to_features(
    rgb: np.ndarray,
    prev_gray: Optional[np.ndarray] = None,
    grid: int = 8,
) -> Tuple[List[float], np.ndarray, Dict[str, float]]:
    """
    Frame → compact feature vector.

    Biological / display analogs:
      - Luma (Y) ~ rod brightness
      - RGB means ~ cone summary
      - Hue histogram ~ color spectrum bins
      - Spatial grid means ~ retinotopic coarse map
      - Motion energy ~ delta vs previous frame (optic flow proxy)
      - Edge energy ~ high-frequency / contour
    """
    if rgb.ndim == 2:
        rgb = np.stack([rgb, rgb, rgb], axis=-1)
    rgb = rgb.astype(np.float32)
    if rgb.max() > 1.5:
        rgb = rgb / 255.0
    h, w, _ = rgb.shape
    # Luma BT.601
    gray = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    r_m, g_m, b_m = float(rgb[:, :, 0].mean()), float(rgb[:, :, 1].mean()), float(rgb[:, :, 2].mean())
    luma = float(gray.mean())
    contrast = float(gray.std())

    # Hue histogram (8 bins) via atan2 on opponent channels
    rg = rgb[:, :, 0] - rgb[:, :, 1]
    yb = 0.5 * (rgb[:, :, 0] + rgb[:, :, 1]) - rgb[:, :, 2]
    hue = np.arctan2(yb, rg + 1e-6)  # -pi..pi
    hist, _ = np.histogram(hue, bins=8, range=(-math.pi, math.pi), density=True)
    hist = (hist / (hist.sum() + 1e-9)).astype(np.float32)

    # Coarse retinotopic grid
    gh, gw = max(1, h // grid), max(1, w // grid)
    tiles = []
    for i in range(grid):
        for j in range(grid):
            y0, y1 = i * gh, min(h, (i + 1) * gh) if i < grid - 1 else h
            x0, x1 = j * gw, min(w, (j + 1) * gw) if j < grid - 1 else w
            if y1 <= y0 or x1 <= x0:
                tiles.append(0.0)
            else:
                tiles.append(float(gray[y0:y1, x0:x1].mean()))

    # Edge energy (simple gradient)
    gy = np.diff(gray, axis=0)
    gx = np.diff(gray, axis=1)
    edge = float(np.mean(np.abs(gy)) + np.mean(np.abs(gx)))

    # Motion vs previous
    motion = 0.0
    if prev_gray is not None and prev_gray.shape == gray.shape:
        motion = float(np.mean(np.abs(gray - prev_gray)))

    feats = (
        [luma, contrast, r_m, g_m, b_m, edge, motion]
        + hist.tolist()
        + tiles
    )
    stats = {
        "luma": luma,
        "contrast": contrast,
        "r": r_m,
        "g": g_m,
        "b": b_m,
        "edge": edge,
        "motion": motion,
        "n_feats": float(len(feats)),
    }
    return feats, gray.astype(np.float32), stats


def _open_video_reader(path: Path):
    """Return (backend, reader) or (None, None)."""
    try:
        import av  # type: ignore

        container = av.open(str(path))
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        return "av", (container, stream)
    except Exception:
        pass
    try:
        import imageio.v3 as iio  # type: ignore

        return "imageio", path
    except Exception:
        return None, None


def iter_video_frames(
    path: Path,
    *,
    max_frames: int = 48,
    stride: int = 15,
    max_side: int = 96,
) -> Iterator[Tuple[np.ndarray, float]]:
    """
    Yield (rgb_uint8_or_float HxWx3, t_sec) subsampled along the file.
    """
    backend, reader = _open_video_reader(path)
    if backend is None:
        return
    if backend == "av":
        container, stream = reader
        try:
            fps = float(stream.average_rate) if stream.average_rate else 24.0
            n = 0
            kept = 0
            for frame in container.decode(video=0):
                if n % max(1, stride) != 0:
                    n += 1
                    continue
                img = frame.to_ndarray(format="rgb24")
                # downscale
                h, w = img.shape[:2]
                scale = max_side / max(h, w)
                if scale < 1.0:
                    nh, nw = max(1, int(h * scale)), max(1, int(w * scale))
                    # nearest-neighbor downsample
                    ys = (np.linspace(0, h - 1, nh)).astype(np.int32)
                    xs = (np.linspace(0, w - 1, nw)).astype(np.int32)
                    img = img[ys][:, xs]
                t = float(n) / max(fps, 1e-3)
                yield img, t
                kept += 1
                n += 1
                if kept >= max_frames:
                    break
        finally:
            try:
                container.close()
            except Exception:
                pass
        return
    # imageio
    try:
        import imageio.v3 as iio  # type: ignore

        props = iio.improps(str(path))
        # sequential read with stride
        kept = 0
        for i, frame in enumerate(iio.imiter(str(path))):
            if i % max(1, stride) != 0:
                continue
            img = np.asarray(frame)
            if img.ndim == 2:
                img = np.stack([img] * 3, axis=-1)
            if img.shape[-1] > 3:
                img = img[..., :3]
            h, w = img.shape[:2]
            scale = max_side / max(h, w)
            if scale < 1.0:
                nh, nw = max(1, int(h * scale)), max(1, int(w * scale))
                ys = (np.linspace(0, h - 1, nh)).astype(np.int32)
                xs = (np.linspace(0, w - 1, nw)).astype(np.int32)
                img = img[ys][:, xs]
            yield img, float(i) / 24.0
            kept += 1
            if kept >= max_frames:
                break
    except Exception:
        return


def vision_packet_from_frame(
    rgb: np.ndarray,
    prev_gray: Optional[np.ndarray] = None,
    *,
    strength: float = 0.55,
    source: str = "",
    t_sec: float = 0.0,
) -> Tuple[SensoryPacket, np.ndarray, Dict[str, float]]:
    feats, gray, stats = _rgb_to_features(rgb, prev_gray)
    gate = SEEDS.phi / (1.0 + SEEDS.phi)
    # Strength modulated by contrast + motion (salience)
    sal = min(1.0, 0.4 + 0.6 * stats["contrast"] + 0.8 * stats["motion"])
    pkt = SensoryPacket(
        modality=SensoryModality.VISION,
        target_region="sens",
        features=feats,
        strength=float(strength) * gate * sal,
        timestamp_ms=time.time() * 1000.0,
        meta={
            "kind": "media_vision",
            "source": source,
            "t_sec": t_sec,
            "stats": stats,
            "decode": "luma+rgb+hue8+grid8x8+edge+motion",
        },
    )
    return pkt, gray, stats


# ---------------------------------------------------------------------------
# Audio decode (ear / spectrum)
# ---------------------------------------------------------------------------

def sample_audio_window(
    path: Path,
    *,
    offset_s: float = 0.0,
    duration_s: float = 1.0,
    sr: int = 16000,
    n_bands: int = 12,
) -> Tuple[List[float], Dict[str, float]]:
    """
    Load a short window → RMS + band energies (FFT) + optional spectral centroid.
    """
    try:
        import soundfile as sf  # type: ignore

        info = sf.info(str(path))
        file_sr = int(info.samplerate)
        start = int(offset_s * file_sr)
        frames = int(duration_s * file_sr)
        data, file_sr = sf.read(str(path), start=start, frames=frames, always_2d=True)
        mono = data.mean(axis=1).astype(np.float32)
        if file_sr != sr and len(mono) > 0:
            # crude resample
            n_out = max(1, int(len(mono) * sr / file_sr))
            idx = (np.linspace(0, len(mono) - 1, n_out)).astype(np.int32)
            mono = mono[idx]
    except Exception as e:
        return [], {"error": str(e)[:120], "rms": 0.0}

    if mono.size == 0:
        return [], {"rms": 0.0}

    rms = float(np.sqrt(np.mean(mono ** 2)))
    # Hann FFT
    win = mono * np.hanning(len(mono))
    spec = np.abs(np.fft.rfft(win))
    freqs = np.fft.rfftfreq(len(win), d=1.0 / sr)
    # log-spaced bands 20Hz–8kHz
    edges = np.logspace(np.log10(20), np.log10(min(8000, sr / 2 - 1)), n_bands + 1)
    bands = []
    for i in range(n_bands):
        m = (freqs >= edges[i]) & (freqs < edges[i + 1])
        bands.append(float(spec[m].mean()) if m.any() else 0.0)
    bsum = sum(bands) + 1e-9
    bands = [b / bsum for b in bands]
    # centroid
    denom = float(spec.sum()) + 1e-9
    centroid = float((freqs * spec).sum() / denom) / (sr / 2)
    peak = float(np.max(np.abs(mono)))
    feats = [rms, peak, centroid] + bands
    stats = {"rms": rms, "peak": peak, "centroid_norm": centroid, "n_bands": float(n_bands)}
    return feats, stats


def audio_packet_from_file(
    path: Path,
    *,
    offset_s: float = 0.0,
    duration_s: float = 1.0,
    strength: float = 0.45,
) -> SensoryPacket:
    feats, stats = sample_audio_window(path, offset_s=offset_s, duration_s=duration_s)
    gate = SEEDS.phi / (1.0 + SEEDS.phi)
    sal = min(1.0, 0.3 + 4.0 * float(stats.get("rms", 0.0)))
    return SensoryPacket(
        modality=SensoryModality.AUDIO,
        target_region="sens",
        features=feats,
        strength=(float(strength) * gate * sal) if feats else 0.0,
        timestamp_ms=time.time() * 1000.0,
        meta={
            "kind": "media_audio",
            "source": str(path),
            "offset_s": offset_s,
            "stats": stats,
            "decode": "rms+peak+centroid+fft_bands12",
        },
    )


# ---------------------------------------------------------------------------
# Stream session: chew media through sensory bus
# ---------------------------------------------------------------------------

@dataclass
class MediaChewConfig:
    roots: List[str] = field(default_factory=list)
    max_video_files: int = 3
    max_audio_files: int = 3
    frames_per_video: int = 24
    frame_stride: int = 20
    audio_windows: int = 8
    audio_duration_s: float = 0.75
    brain_steps_per_packet: int = 4
    seed: int = 7
    profile: str = "ai_efficient"
    device: str = "cpu"
    associate: bool = True  # bind metadata + symbols after chew
    av_costream: bool = True  # movies/shows: simultaneous audio+visual binding
    use_metadata_tutor: bool = True  # optional labels; not required for AV binding
    knowledge_crossfeed: bool = True  # lexicon + machine/trinary knowledge packets
    speech_to_text: bool = False  # optional local STT (faster-whisper); slower


@dataclass
class MediaChewReport:
    ok: bool
    roots_found: List[str]
    n_video_files: int
    n_audio_files: int
    n_vision_packets: int
    n_audio_packets: int
    mean_vision_luma: float
    mean_motion: float
    mean_audio_rms: float
    region_rates: Dict[str, float]
    mean_S: float
    total_spikes: int
    sources: List[str]
    notes: List[str] = field(default_factory=list)
    # Meaning layer (metadata + symbolic association)
    episodes: List[Dict[str, Any]] = field(default_factory=list)
    association_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def chew_media(
    cfg: Optional[MediaChewConfig] = None,
    *,
    brain=None,
) -> MediaChewReport:
    """
    Sample real media → packets → multi-region brain steps.
    Standalone-safe: zero media files still returns ok=True with empty chew.
    """
    from .bus import SensoryBus
    from ..brain_architecture import (
        FSOTBrainDesign,
        BrainDesignConfig,
        BRAIN_PROFILES,
        DEFAULT_PROJECTIONS,
    )
    import torch

    cfg = cfg or MediaChewConfig()
    notes: List[str] = []
    if cfg.roots:
        roots = [Path(r) for r in cfg.roots if Path(r).is_dir()]
    else:
        roots = media_roots_from_env()
    roots_s = [str(r) for r in roots]
    if not roots:
        notes.append("No media roots found (optional). Set FSOT_MEDIA_ROOTS or use G: libraries.")
        return MediaChewReport(
            ok=True,
            roots_found=[],
            n_video_files=0,
            n_audio_files=0,
            n_vision_packets=0,
            n_audio_packets=0,
            mean_vision_luma=0.0,
            mean_motion=0.0,
            mean_audio_rms=0.0,
            region_rates={},
            mean_S=0.0,
            total_spikes=0,
            sources=[],
            notes=notes,
        )

    rng = random.Random(cfg.seed)
    videos = discover_media_files(roots, max_files=80, kind="video")
    audios = discover_media_files(roots, max_files=80, kind="audio")
    rng.shuffle(videos)
    rng.shuffle(audios)
    videos = videos[: cfg.max_video_files]
    audios = audios[: cfg.max_audio_files]

    if brain is None:
        prof = BRAIN_PROFILES.get(cfg.profile, BRAIN_PROFILES["ai_efficient"])
        brain = FSOTBrainDesign(
            BrainDesignConfig(
                regions=list(prof["regions"]),
                projections=list(DEFAULT_PROJECTIONS),
                seed=cfg.seed,
                device=cfg.device,
                dt_ms=0.5,
            )
        )

    from .bus import SensoryBus as _Bus
    from .media_meta import extract_media_metadata
    from .symbol_assoc import (
        build_sensory_signature,
        associate_media_episode,
        summarize_associations,
        MediaAssociationReport,
    )

    sources: List[str] = []
    vision_stats: List[Dict[str, float]] = []
    audio_rms: List[float] = []
    audio_centroids: List[float] = []
    n_vis = n_aud = 0
    total_spikes = 0
    last_S = None
    n = brain.n_units

    def _drive_packets(packets: List[SensoryPacket]) -> None:
        nonlocal total_spikes, last_S
        hold = max(3, int(cfg.brain_steps_per_packet))

        def _packet_external(pkt: SensoryPacket) -> torch.Tensor:
            tmp = _Bus()
            tmp.push(pkt)
            return tmp.build_external(
                n, brain.region_index, device=brain.device, dtype=brain.net.dtype
            )

        for pkt in packets:
            ext = _packet_external(pkt)
            energy = float(ext.abs().mean().item()) if ext.numel() else 0.0
            gain = 0.55 / max(0.05, energy)
            gain = min(4.0, max(1.2, gain))
            ext = (ext * gain).clamp(-0.5, 1.4)
            for i in brain.region_index.get("thal", []):
                if brain.units[i].synapse_sign > 0:
                    ext[i] = torch.clamp(ext[i] + 0.35, -0.5, 1.4)
            for _ in range(hold):
                S, fired, *_ = brain.step(ext)
                total_spikes += int(fired.sum().item())
                last_S = S
            for _ in range(2):
                S, fired, *_ = brain.step(ext * 0.4)
                total_spikes += int(fired.sum().item())
                last_S = S

    # Per-file episodes for metadata + association
    episode_raw: List[Dict[str, Any]] = []

    # --- video chew (per file) — prefer simultaneous A/V co-stream ---
    for vp in videos:
        sources.append(str(vp))
        notes.append(f"video: {vp.name}")
        meta = extract_media_metadata(vp)
        from ..machine_encode import encode_to_sensory_packet, EncodePath

        meta_pkt = None
        if cfg.use_metadata_tutor:
            try:
                meta_pkt = encode_to_sensory_packet(
                    meta.label_line(),
                    path=EncodePath.MACHINE,
                    target_region="assoc",
                    strength=0.35,
                )
                meta_pkt.meta["kind"] = "media_metadata_tutor"  # optional tutor, not required
                meta_pkt.meta["media_meta"] = meta.to_dict()
            except Exception:
                meta_pkt = None

        file_vis_stats: List[Dict[str, float]] = []
        file_rms: List[float] = []
        file_cent: List[float] = []
        file_pkts: List[SensoryPacket] = []
        av_report: Dict[str, Any] = {}
        if meta_pkt is not None:
            file_pkts.append(meta_pkt)

        used_av = False
        if cfg.av_costream:
            try:
                from .cross_modal import (
                    iter_audiovisual_moments,
                    moment_to_packets,
                    cross_modal_association,
                )

                moments = list(
                    iter_audiovisual_moments(
                        vp,
                        max_moments=cfg.frames_per_video,
                        frame_stride=cfg.frame_stride,
                    )
                )
                if moments:
                    used_av = True
                    for m in moments:
                        file_pkts.extend(moment_to_packets(m, source=str(vp)))
                        file_vis_stats.append(m.vision_stats)
                        vision_stats.append(m.vision_stats)
                        n_vis += 1
                        if m.audio_feats:
                            n_aud += 1
                            file_rms.append(float(m.audio_stats.get("rms", 0.0)))
                            file_cent.append(float(m.audio_stats.get("centroid_norm", 0.0)))
                            audio_rms.append(float(m.audio_stats.get("rms", 0.0)))
                            audio_centroids.append(
                                float(m.audio_stats.get("centroid_norm", 0.0))
                            )
                    av_report = cross_modal_association(moments, seed=cfg.seed)
                    notes.append(
                        f"AV co-stream {vp.name}: moments={av_report.get('n_moments')} "
                        f"soundtrack={av_report.get('has_soundtrack')} "
                        f"mean_bind={av_report.get('mean_bind', 0):.3f} "
                        f"speech={av_report.get('mean_speech_band', 0):.3f}"
                    )
            except Exception as e:
                notes.append(f"AV co-stream fallback ({vp.name}): {e}")
                used_av = False

        if not used_av:
            # vision-only fallback
            prev_gray = None
            for rgb, t_sec in iter_video_frames(
                vp,
                max_frames=cfg.frames_per_video,
                stride=cfg.frame_stride,
            ):
                pkt, prev_gray, st = vision_packet_from_frame(
                    rgb, prev_gray, source=str(vp), t_sec=t_sec
                )
                file_pkts.append(pkt)
                n_vis += 1
                vision_stats.append(st)
                file_vis_stats.append(st)

        _drive_packets(file_pkts)
        rates_ep: Dict[str, float] = {}
        if last_S is not None:
            s_cpu = last_S.detach().cpu()
            for rid, ids in brain.region_index.items():
                if ids:
                    rates_ep[rid] = float(s_cpu[ids].abs().mean().item())
        episode_raw.append(
            {
                "meta": meta,
                "vision_stats": file_vis_stats,
                "audio_rms": file_rms,
                "audio_centroids": file_cent,
                "region_abs": rates_ep,
                "mean_S": float(last_S.mean().item()) if last_S is not None else 0.0,
                "n_vision": len(file_vis_stats),
                "n_audio": len(file_rms),
                "av_cross_modal": av_report,
            }
        )

    # --- audio chew (per file) ---
    for ap in audios:
        sources.append(str(ap))
        notes.append(f"audio: {ap.name}")
        meta = extract_media_metadata(ap)
        from ..machine_encode import encode_to_sensory_packet, EncodePath

        try:
            meta_pkt = encode_to_sensory_packet(
                meta.label_line(),
                path=EncodePath.MACHINE,
                target_region="assoc",
                strength=0.4,
            )
            meta_pkt.meta["kind"] = "media_metadata_label"
            meta_pkt.meta["media_meta"] = meta.to_dict()
        except Exception:
            meta_pkt = None
        file_pkts = []
        if meta_pkt is not None:
            file_pkts.append(meta_pkt)
        file_rms: List[float] = []
        file_cent: List[float] = []
        for w in range(cfg.audio_windows):
            off = w * cfg.audio_duration_s * 1.5
            pkt = audio_packet_from_file(ap, offset_s=off, duration_s=cfg.audio_duration_s)
            if not pkt.features:
                continue
            file_pkts.append(pkt)
            n_aud += 1
            st = pkt.meta.get("stats") or {}
            file_rms.append(float(st.get("rms", 0.0)))
            file_cent.append(float(st.get("centroid_norm", 0.0)))
            audio_rms.append(float(st.get("rms", 0.0)))
            audio_centroids.append(float(st.get("centroid_norm", 0.0)))
        _drive_packets(file_pkts)
        rates_ep = {}
        if last_S is not None:
            s_cpu = last_S.detach().cpu()
            for rid, ids in brain.region_index.items():
                if ids:
                    rates_ep[rid] = float(s_cpu[ids].abs().mean().item())
        episode_raw.append(
            {
                "meta": meta,
                "vision_stats": [],
                "audio_rms": file_rms,
                "audio_centroids": file_cent,
                "region_abs": rates_ep,
                "mean_S": float(last_S.mean().item()) if last_S is not None else 0.0,
                "n_vision": 0,
                "n_audio": len(file_rms),
            }
        )

    if not videos and not audios:
        notes.append("No frames/windows decoded (codec or empty).")

    rates: Dict[str, float] = {}
    if last_S is not None:
        s_cpu = last_S.detach().cpu()
        for rid, ids in brain.region_index.items():
            if ids:
                rates[rid] = float(s_cpu[ids].abs().mean().item())

    mean_luma = (
        sum(s["luma"] for s in vision_stats) / len(vision_stats) if vision_stats else 0.0
    )
    mean_motion = (
        sum(s["motion"] for s in vision_stats) / len(vision_stats) if vision_stats else 0.0
    )
    mean_rms = sum(audio_rms) / len(audio_rms) if audio_rms else 0.0

    # --- Association / meaning layer ---
    episodes_out: List[Dict[str, Any]] = []
    assoc_summary: Dict[str, Any] = {}
    if cfg.associate and episode_raw:
        metas = [ep["meta"] for ep in episode_raw]
        reports: List[MediaAssociationReport] = []
        for ep in episode_raw:
            sig = build_sensory_signature(
                vision_stats=ep["vision_stats"],
                audio_rms=ep["audio_rms"],
                audio_centroids=ep["audio_centroids"],
                mean_S=ep["mean_S"],
                region_abs=ep["region_abs"],
                n_vision=ep["n_vision"],
                n_audio=ep["n_audio"],
            )
            rivals = [m for m in metas if m.path != ep["meta"].path]
            arep = associate_media_episode(
                ep["meta"], sig, seed=cfg.seed, rival_metas=rivals or None
            )
            reports.append(arep)
            # Knowledge cross-feed: symbols (+ optional STT) → definitions → trinary
            kf: Dict[str, Any] = {}
            if cfg.knowledge_crossfeed:
                try:
                    from ..knowledge.cross_feed import cross_feed_episode
                    from ..knowledge.speech_text import transcribe_audio_file

                    syms = [a["symbol"] for a in arep.top_anchors[:8]]
                    # pull AV cluster symbols
                    av = ep.get("av_cross_modal") or {}
                    for c in (av.get("clusters") or [])[:3]:
                        for s in c.get("top_symbols") or []:
                            if isinstance(s, dict) and s.get("symbol"):
                                syms.append(s["symbol"])
                    for s in av.get("cross_modal_symbols") or []:
                        if isinstance(s, dict) and s.get("symbol"):
                            syms.append(s["symbol"])
                    # path/title symbols (Finn/Jake if Adventure Time, etc.)
                    title = ep["meta"].title
                    transcript = ""
                    if cfg.speech_to_text and ep["meta"].kind in ("video", "audio"):
                        stt = transcribe_audio_file(ep["meta"].path, max_s=40.0)
                        if stt.ok:
                            transcript = stt.text
                            notes.append(f"STT {ep['meta'].title[:40]}: {stt.backend}")
                        else:
                            notes.append(
                                f"STT skip {ep['meta'].title[:40]}: {'; '.join(stt.notes[:1])}"
                            )
                    sensory_notes = (
                        f"Observed stream: luma/motion patterns; "
                        f"AV bind={float((av or {}).get('mean_bind') or 0):.2f}; "
                        f"speech_band={float((av or {}).get('mean_speech_band') or 0):.2f}."
                    )
                    cf = cross_feed_episode(
                        symbols=syms,
                        title=title,
                        transcript=transcript,
                        sensory_notes=sensory_notes,
                        path_hint=str(ep["meta"].path),
                    )
                    kf = cf.to_dict()
                    # inject knowledge packets into living brain
                    from ..sensory.packets import SensoryPacket as _SP
                    from ..sensory.packets import SensoryModality as _SM

                    kpkts = []
                    for pd in cf.packets[:16]:
                        try:
                            kpkts.append(
                                _SP(
                                    modality=_SM(pd["modality"])
                                    if not isinstance(pd["modality"], _SM)
                                    else pd["modality"],
                                    target_region=pd.get("target_region") or "assoc",
                                    features=list(pd.get("features") or []),
                                    strength=float(pd.get("strength") or 0.4),
                                    timestamp_ms=float(pd.get("timestamp_ms") or 0.0),
                                    meta=dict(pd.get("meta") or {}),
                                )
                            )
                        except Exception:
                            pass
                    if kpkts:
                        _drive_packets(kpkts)
                        notes.append(
                            f"knowledge cross-feed {title[:40]}: "
                            f"{len(cf.entries_used)} defs, {cf.n_trits} trits, S={cf.S_couple}"
                        )
                except Exception as e:
                    notes.append(f"knowledge cross-feed error: {e}")
                    kf = {"error": str(e)}

            episodes_out.append(
                {
                    "title": ep["meta"].title,
                    "kind": ep["meta"].kind,
                    "metadata": ep["meta"].to_dict(),
                    "association": arep.to_dict(),
                    "top_symbols": [a["symbol"] for a in arep.top_anchors[:6]],
                    "meta_bind_score": arep.meta_bind_score,
                    "av_cross_modal": ep.get("av_cross_modal") or {},
                    "knowledge_crossfeed": kf,
                    "plain_english": (kf or {}).get("plain_english") or "",
                }
            )
        assoc_summary = summarize_associations(reports)
        notes.append(
            f"association: mean_meta_bind={assoc_summary.get('mean_meta_bind', 0):.3f} "
            f"top5_meta_hit_frac={assoc_summary.get('top5_anchor_hits_meta_frac', 0):.2f}"
        )

    return MediaChewReport(
        ok=True,
        roots_found=roots_s,
        n_video_files=len(videos),
        n_audio_files=len(audios),
        n_vision_packets=n_vis,
        n_audio_packets=n_aud,
        mean_vision_luma=mean_luma,
        mean_motion=mean_motion,
        mean_audio_rms=mean_rms,
        region_rates=rates,
        mean_S=float(last_S.mean().item()) if last_S is not None else 0.0,
        total_spikes=total_spikes,
        sources=[Path(s).name for s in sources[:12]],
        notes=notes,
        episodes=episodes_out,
        association_summary=assoc_summary,
    )
