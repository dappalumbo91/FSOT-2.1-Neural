"""
Optional speech → text (STT) for dialogue co-stream.

Doctrine:
  - Not required for boot or AV binding.
  - Prefer local models (faster-whisper) when installed.
  - Graceful empty result if no backend / no speech.

This is the bridge from continuous audio to the same text channel humans
use for definitions — then machine/trinary encode can compact it.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class STTResult:
    ok: bool
    text: str = ""
    backend: str = "none"
    language: str = ""
    segments: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _extract_wav_snippet(path: Path, max_s: float = 45.0) -> Optional[Path]:
    """Decode a short mono wav via PyAV for STT backends that need a file."""
    try:
        import av  # type: ignore
        import numpy as np  # type: ignore
        import wave

        container = av.open(str(path))
        if not container.streams.audio:
            container.close()
            return None
        resampler = av.audio.resampler.AudioResampler(
            format="s16", layout="mono", rate=16000
        )
        chunks: List[np.ndarray] = []
        n_max = int(16000 * max_s)

        def consume(frames) -> None:
            if frames is None:
                return
            if not isinstance(frames, list):
                frames = [frames]
            for f in frames:
                if f is None:
                    continue
                arr = f.to_ndarray()
                if arr.ndim == 2:
                    arr = arr[0] if arr.shape[0] == 1 else arr.mean(axis=0)
                chunks.append(np.asarray(arr, dtype=np.int16).ravel())

        total = 0
        for frame in container.decode(audio=0):
            consume(resampler.resample(frame))
            total = sum(c.size for c in chunks)
            if total >= n_max:
                break
        try:
            consume(resampler.resample(None))
        except Exception:
            pass
        container.close()
        if not chunks:
            return None
        audio = np.concatenate(chunks)[:n_max]
        fd, name = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        out = Path(name)
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(audio.tobytes())
        return out
    except Exception:
        return None


def transcribe_audio_file(
    path: Path | str,
    *,
    max_s: float = 45.0,
    language: Optional[str] = None,
) -> STTResult:
    """
    Transcribe speech from audio/video file if a local STT backend exists.
    """
    path = Path(path)
    notes: List[str] = []
    if not path.is_file():
        return STTResult(ok=False, notes=["file missing"])

    # faster-whisper (local)
    try:
        from faster_whisper import WhisperModel  # type: ignore

        wav = _extract_wav_snippet(path, max_s=max_s)
        src = str(wav or path)
        # tiny/base for speed on host
        model_size = os.environ.get("FSOT_WHISPER_MODEL", "tiny")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments_iter, info = model.transcribe(
            src, language=language, beam_size=1, vad_filter=True
        )
        segs = []
        texts = []
        for s in segments_iter:
            segs.append(
                {
                    "start": float(s.start),
                    "end": float(s.end),
                    "text": (s.text or "").strip(),
                }
            )
            if s.text:
                texts.append(s.text.strip())
        if wav and wav.is_file():
            try:
                wav.unlink()
            except OSError:
                pass
        text = " ".join(texts).strip()
        return STTResult(
            ok=bool(text),
            text=text,
            backend=f"faster_whisper:{model_size}",
            language=getattr(info, "language", "") or "",
            segments=segs[:40],
            notes=notes if text else ["empty transcript"],
        )
    except Exception as e:
        notes.append(f"faster_whisper unavailable: {e}")

    return STTResult(
        ok=False,
        text="",
        backend="none",
        notes=notes
        + [
            "No STT backend produced text. Install faster-whisper for local speech→text. "
            "AV co-stream binding still works without STT."
        ],
    )
