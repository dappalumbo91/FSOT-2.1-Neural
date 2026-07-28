"""
Dialogue-as-subtitles — timed text aligned to AV moments.

Doctrine:
  Treat speech like captions on a TV: lightweight, time-stamped lines.
  Prefer sidecar .srt / .vtt next to the media file.
  Fall back to STT segments (same shape as subtitles) when no sidecar.

Not required for standalone boot. Missing captions → empty cue list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass
class CaptionCue:
    """One timed dialogue line (subtitle / closed-caption unit)."""

    start_s: float
    end_s: float
    text: str
    source: str = "srt"  # srt | vtt | stt

    def mid_s(self) -> float:
        return 0.5 * (self.start_s + self.end_s)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _ts_srt(ts: str) -> float:
    # 00:01:02,500
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    if len(parts) != 3:
        return 0.0
    h, m, s = parts
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_srt(text: str) -> List[CaptionCue]:
    cues: List[CaptionCue] = []
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip())
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip() != ""]
        if len(lines) < 2:
            continue
        # optional index line
        i = 0
        if re.match(r"^\d+$", lines[0].strip()):
            i = 1
        if i >= len(lines):
            continue
        m = re.match(
            r"(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})",
            lines[i],
        )
        if not m:
            continue
        start, end = _ts_srt(m.group(1)), _ts_srt(m.group(2))
        body = " ".join(lines[i + 1 :])
        body = re.sub(r"<[^>]+>", "", body)
        body = re.sub(r"\s+", " ", body).strip()
        if body:
            cues.append(CaptionCue(start, end, body, source="srt"))
    return cues


def parse_vtt(text: str) -> List[CaptionCue]:
    # strip WEBVTT header
    text = text.replace("\r\n", "\n")
    if text.lstrip().upper().startswith("WEBVTT"):
        text = re.sub(r"^WEBVTT.*?\n\n", "", text.lstrip(), count=1, flags=re.I | re.S)
    cues: List[CaptionCue] = []
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip() != ""]
        if not lines:
            continue
        time_line = None
        body_start = 0
        for j, ln in enumerate(lines):
            if "-->" in ln:
                time_line = ln
                body_start = j + 1
                break
        if not time_line:
            continue
        m = re.match(
            r"(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3}|\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*"
            r"(\d{1,2}:\d{2}:\d{2}[.,]\d{1,3}|\d{1,2}:\d{2}[.,]\d{1,3})",
            time_line.strip(),
        )
        if not m:
            continue

        def vtt_ts(x: str) -> float:
            x = x.replace(",", ".")
            p = x.split(":")
            if len(p) == 2:
                return int(p[0]) * 60 + float(p[1])
            return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])

        start, end = vtt_ts(m.group(1)), vtt_ts(m.group(2))
        body = " ".join(lines[body_start:])
        body = re.sub(r"<[^>]+>", "", body)
        body = re.sub(r"\s+", " ", body).strip()
        if body:
            cues.append(CaptionCue(start, end, body, source="vtt"))
    return cues


def find_sidecar_subtitles(media_path: Path) -> Optional[Path]:
    """Locate .srt/.vtt next to media or in Subs/ subfolder."""
    media_path = Path(media_path)
    stem = media_path.stem
    parent = media_path.parent
    stem_l = stem.lower()
    exact = [
        parent / f"{stem}.srt",
        parent / f"{stem}.en.srt",
        parent / f"{stem}.eng.srt",
        parent / f"{stem}.en.vtt",
        parent / f"{stem}.vtt",
        parent / "Subs" / f"{stem}.srt",
        parent / "subs" / f"{stem}.srt",
        parent / "Subtitles" / f"{stem}.srt",
    ]
    for p in exact:
        if p.is_file():
            return p
    # fuzzy: same folder, longest common prefix with video stem
    pool: List[Path] = []
    try:
        pool.extend(parent.glob("*.srt"))
        pool.extend(parent.glob("*.vtt"))
        for sub in ("Subs", "subs", "Subtitles"):
            d = parent / sub
            if d.is_dir():
                pool.extend(d.glob("*.srt"))
                pool.extend(d.glob("*.vtt"))
    except OSError:
        pass
    best: Optional[Path] = None
    best_score = 0
    for p in pool:
        if not p.is_file():
            continue
        ps = p.stem.lower()
        # score by shared prefix length
        n = 0
        for a, b in zip(stem_l, ps):
            if a != b:
                break
            n += 1
        if "english" in p.name.lower() or ps.endswith(".en") or ".en." in p.name.lower():
            n += 5
        if n >= 8 and n > best_score:
            best_score = n
            best = p
    return best


def load_subtitles(media_path: Path | str) -> List[CaptionCue]:
    path = Path(media_path)
    sub = find_sidecar_subtitles(path)
    if sub is None:
        return []
    try:
        raw = sub.read_text(encoding="utf-8", errors="replace")
    except OSError:
        try:
            raw = sub.read_text(encoding="latin-1", errors="replace")
        except OSError:
            return []
    if sub.suffix.lower() == ".vtt" or raw.lstrip().upper().startswith("WEBVTT"):
        cues = parse_vtt(raw)
    else:
        cues = parse_srt(raw)
    for c in cues:
        c.source = sub.suffix.lower().lstrip(".")
    return cues


def cues_from_stt_segments(segments: Sequence[Dict[str, Any]]) -> List[CaptionCue]:
    """Normalize STT segments into the same caption shape."""
    out: List[CaptionCue] = []
    for s in segments:
        text = str(s.get("text") or "").strip()
        if not text:
            continue
        out.append(
            CaptionCue(
                start_s=float(s.get("start") or 0.0),
                end_s=float(s.get("end") or (float(s.get("start") or 0.0) + 1.0)),
                text=text,
                source="stt",
            )
        )
    return out


def captions_near(
    cues: Sequence[CaptionCue],
    t_sec: float,
    *,
    window_s: float = 1.25,
) -> List[CaptionCue]:
    """
    Captions overlapping or near a visual moment (subtitle sync).

    Prefer strict temporal overlap, then mid-time proximity, then window.
    Order hits by distance so bind takes the best line first.
    """
    # FSOT-lawful default window if caller leaves classic default
    try:
        from ..seeds import SEEDS

        if abs(window_s - 1.25) < 1e-9:
            # φ + 1/e ≈ 1.986 → ~2s dialogue tolerance without free fit
            window_s = float(SEEDS.phi + 1.0 / SEEDS.e)
    except Exception:
        pass

    scored: List[Tuple[float, CaptionCue]] = []
    for c in cues:
        # strict overlap (caption covers t)
        if c.start_s <= t_sec <= c.end_s:
            dist = 0.0
        elif c.start_s - window_s <= t_sec <= c.end_s + window_s:
            # outside interval but within pad
            if t_sec < c.start_s:
                dist = c.start_s - t_sec
            else:
                dist = t_sec - c.end_s
        elif abs(c.mid_s() - t_sec) <= window_s:
            dist = abs(c.mid_s() - t_sec)
        else:
            continue
        scored.append((dist, c))
    scored.sort(key=lambda x: x[0])
    return [c for _d, c in scored]


def captions_in_range(
    cues: Sequence[CaptionCue],
    t0: float,
    t1: float,
) -> List[CaptionCue]:
    out = []
    for c in cues:
        if c.end_s >= t0 and c.start_s <= t1:
            out.append(c)
    return out


def flatten_caption_text(cues: Sequence[CaptionCue], max_chars: int = 800) -> str:
    parts = []
    n = 0
    for c in cues:
        t = c.text.strip()
        if not t:
            continue
        parts.append(t)
        n += len(t)
        if n >= max_chars:
            break
    return " ".join(parts)[:max_chars]
