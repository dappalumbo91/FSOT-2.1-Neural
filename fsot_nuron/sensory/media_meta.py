"""
Media metadata for optional world libraries.

Extracts person/place/thing-ish **labels from path and probes**, not from
neural vision yet. This is the ground-truth *side channel* we associate with
sensory signatures so the mind can bind "what I saw" to "what this file is."

Standalone: missing files → empty meta. No external project required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".m4v", ".wmv", ".mov", ".webm", ".mpg", ".mpeg"}
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".aac", ".wma"}

# Keyword → symbolic tags (human cultural categories for association)
_TAG_LEXICON: Dict[str, List[str]] = {
    # media kind
    "movie": ["movie", "cinema", "film"],
    "film": ["movie", "cinema"],
    "season": ["tv_show", "episode", "series"],
    "episode": ["tv_show", "episode"],
    "s0": ["tv_show", "episode"],
    "pilot": ["tv_show", "episode", "cartoon"],
    "soundtrack": ["music", "soundtrack"],
    "ost": ["music", "soundtrack"],
    "album": ["music", "album"],
    "live": ["music", "live_performance"],
    "mixtape": ["music"],
    "demo": ["music"],
    # genres / content
    "cartoon": ["cartoon", "animation", "drawing"],
    "anime": ["cartoon", "animation"],
    "animation": ["animation", "cartoon"],
    "pony": ["cartoon", "animal", "horse"],
    "simpsons": ["cartoon", "tv_show", "comedy"],
    "south park": ["cartoon", "tv_show", "comedy"],
    "adventure time": ["cartoon", "tv_show", "fantasy"],
    "stargate": ["tv_show", "science_fiction", "space"],
    "harry potter": ["movie", "fantasy", "magic"],
    "jurassic": ["movie", "dinosaur", "animal", "action"],
    "back to the future": ["movie", "science_fiction", "time"],
    "brave": ["movie", "animation", "adventure"],
    "despicable": ["movie", "animation", "comedy"],
    "looper": ["movie", "science_fiction", "action"],
    "hotel transylvania": ["movie", "animation", "monster", "comedy"],
    "chucky": ["movie", "horror", "doll"],
    "american ultra": ["movie", "action", "comedy"],
    "monsters university": ["movie", "animation", "monster"],
    "cats and dogs": ["movie", "animal", "cat", "dog", "comedy"],
    "epic": ["movie", "animation", "adventure"],
    "getaway": ["movie", "action"],
    "300": ["movie", "action", "war", "history"],
    "rise of an empire": ["movie", "action", "war"],
    "vampire": ["music", "dark", "emotion"],
    "drug": ["music", "emotion"],
    "rage": ["music", "emotion", "energy"],
    "star power": ["music", "energy"],
    "hybrid theory": ["music", "rock", "energy"],
    "meteora": ["music", "rock"],
    "linkin": ["music", "rock"],
    "falling in reverse": ["music", "rock"],
    # things / beings (for symbolic association targets)
    "cat": ["cat", "animal", "face"],
    "dog": ["dog", "animal", "face"],
    "horse": ["animal", "horse"],
    "monster": ["monster", "face", "creature"],
    "space": ["space", "place"],
    "park": ["place", "outdoor"],
    "hotel": ["place", "building"],
    "university": ["place", "building"],
    "texas": ["place"],
    "london": ["place"],
    "revolution": ["event", "energy"],
}


@dataclass
class MediaMetadata:
    path: str
    title: str
    kind: str  # video | audio | unknown
    root_hint: str  # movies | shows | music | other
    year: Optional[int] = None
    duration_s: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)  # human-readable anchors
    parent_album: str = ""
    probe_ok: bool = False
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def label_line(self) -> str:
        """Compact label for FSOT machine encode / memory binding."""
        bits = [self.kind, self.root_hint, self.title]
        if self.year:
            bits.append(str(self.year))
        if self.tags:
            bits.append("tags:" + ",".join(self.tags[:8]))
        return " | ".join(bits)


def _clean_title(name: str) -> str:
    stem = Path(name).stem
    # strip common rip tags
    stem = re.sub(
        r"[.\s_-]*(1080p|720p|480p|BluRay|BRRip|HDRip|DVDRip|x264|XviD|YIFY|REMO|ETRG|UNRATED|AAC).*$",
        "",
        stem,
        flags=re.I,
    )
    stem = stem.replace(".", " ").replace("_", " ")
    stem = re.sub(r"\s+", " ", stem).strip(" -[]()")
    return stem or name


def _year_from_text(text: str) -> Optional[int]:
    m = re.search(r"\b(19|20)\d{2}\b", text)
    if m:
        y = int(m.group(0))
        if 1900 <= y <= 2035:
            return y
    return None


def _root_hint(path: Path) -> str:
    low = str(path).lower().replace("/", "\\")
    if "\\movies" in low or low.endswith("movies"):
        return "movies"
    if "showes" in low or "\\shows" in low:
        return "shows"
    if "debut" in low or "music" in low or "album" in low:
        return "music"
    return "other"


def _tags_from_text(text: str) -> List[str]:
    low = text.lower()
    tags: Set[str] = set()
    for key, vals in _TAG_LEXICON.items():
        if key in low:
            tags.update(vals)
    # episode pattern SxxExx
    if re.search(r"\b\d{1,2}\.\d{2}\b", low) or re.search(r"s\d{1,2}e\d{1,2}", low):
        tags.update(["tv_show", "episode"])
    return sorted(tags)


def _symbols_from_tags(tags: List[str], kind: str, root: str) -> List[str]:
    """Map tags → prototype symbols the association layer can bind."""
    sym: Set[str] = set(tags)
    if kind == "video":
        sym.add("moving_image")
        sym.add("scene")
    if kind == "audio":
        sym.add("sound")
        sym.add("music" if root == "music" else "audio_stream")
    if root == "movies":
        sym.add("movie")
    if root == "shows":
        sym.add("tv_show")
    # always allow generic open-world anchors
    for g in ("person", "place", "thing", "face", "animal", "indoor", "outdoor", "action"):
        if g in tags:
            sym.add(g)
    return sorted(sym)


def probe_duration_s(path: Path) -> Optional[float]:
    try:
        import av  # type: ignore

        with av.open(str(path)) as c:
            if c.duration is not None:
                return float(c.duration) / 1_000_000.0
            for s in c.streams:
                if s.duration is not None and s.time_base is not None:
                    return float(s.duration * s.time_base)
    except Exception:
        return None
    return None


def extract_media_metadata(path: Path | str) -> MediaMetadata:
    path = Path(path)
    ext = path.suffix.lower()
    if ext in VIDEO_EXTS:
        kind = "video"
    elif ext in AUDIO_EXTS:
        kind = "audio"
    else:
        kind = "unknown"

    title = _clean_title(path.name)
    parent = path.parent.name
    root = _root_hint(path)
    blob = f"{title} {parent} {path}"
    year = _year_from_text(blob)
    tags = _tags_from_text(blob)
    if root == "movies" and "movie" not in tags:
        tags = sorted(set(tags) | {"movie"})
    if root == "shows" and "tv_show" not in tags:
        tags = sorted(set(tags) | {"tv_show", "episode"})
    if root == "music" and "music" not in tags:
        tags = sorted(set(tags) | {"music"})

    notes: List[str] = []
    dur = probe_duration_s(path)
    probe_ok = dur is not None
    if not probe_ok:
        notes.append("duration probe unavailable")

    symbols = _symbols_from_tags(tags, kind, root)
    return MediaMetadata(
        path=str(path),
        title=title,
        kind=kind,
        root_hint=root,
        year=year,
        duration_s=dur,
        tags=tags,
        symbols=symbols,
        parent_album=parent,
        probe_ok=probe_ok,
        notes=notes,
    )
