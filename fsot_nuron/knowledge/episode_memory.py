"""
Episodic memory store — compact experiences for later plain-English recall.

Each episode: path, symbols, captions (subtitle-style dialogue), knowledge
cross-feed summary, trinary stats. Stored as local JSON under artifacts/
(or data/memory). No cloud. Standalone transplant keeps this optional.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..paths import ARTIFACTS, DATA


def default_memory_dir() -> Path:
    d = ARTIFACTS / "episode_memory"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class EpisodeMemory:
    episode_id: str
    title: str
    path: str
    kind: str
    symbols: List[str] = field(default_factory=list)
    caption_source: str = ""  # srt | vtt | stt | none
    caption_text: str = ""
    caption_cues_n: int = 0
    plain_english: str = ""
    knowledge_keys: List[str] = field(default_factory=list)
    n_trits: int = 0
    S_couple: Optional[float] = None
    av_mean_bind: float = 0.0
    av_speech_band: float = 0.0
    mean_luma: float = 0.0
    mean_motion: float = 0.0
    created_at: str = ""
    notes: List[str] = field(default_factory=list)
    # compact dialogue samples (subtitle lines)
    sample_lines: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EpisodeMemory":
        return EpisodeMemory(**{k: d[k] for k in EpisodeMemory.__dataclass_fields__ if k in d})


def _eid(title: str, path: str) -> str:
    import hashlib

    h = hashlib.sha256(f"{path}|{title}".encode("utf-8")).hexdigest()[:12]
    safe = re_safe(title)[:40]
    return f"{safe}_{h}"


def re_safe(s: str) -> str:
    out = []
    for c in s:
        if c.isalnum() or c in ("-", "_"):
            out.append(c)
        elif c in (" ", ".",):
            out.append("_")
    return "".join(out) or "episode"


def save_episode(mem: EpisodeMemory, root: Optional[Path] = None) -> Path:
    root = root or default_memory_dir()
    root.mkdir(parents=True, exist_ok=True)
    if not mem.created_at:
        mem.created_at = datetime.now(timezone.utc).isoformat()
    if not mem.episode_id:
        mem.episode_id = _eid(mem.title, mem.path)
    path = root / f"{mem.episode_id}.json"
    path.write_text(json.dumps(mem.to_dict(), indent=2), encoding="utf-8")
    # index
    idx_path = root / "index.jsonl"
    with idx_path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "episode_id": mem.episode_id,
                    "title": mem.title,
                    "path": mem.path,
                    "created_at": mem.created_at,
                    "symbols": mem.symbols[:12],
                    "caption_source": mem.caption_source,
                }
            )
            + "\n"
        )
    return path


def load_episode(episode_id: str, root: Optional[Path] = None) -> Optional[EpisodeMemory]:
    root = root or default_memory_dir()
    path = root / f"{episode_id}.json"
    if not path.is_file():
        # try prefix match
        for p in root.glob("*.json"):
            if p.name.startswith(episode_id) or episode_id in p.stem:
                path = p
                break
        else:
            return None
    try:
        return EpisodeMemory.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return None


def list_episodes(root: Optional[Path] = None, limit: int = 50) -> List[Dict[str, Any]]:
    root = root or default_memory_dir()
    rows = []
    for p in sorted(root.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.name == "index.jsonl":
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            rows.append(
                {
                    "episode_id": d.get("episode_id"),
                    "title": d.get("title"),
                    "symbols": d.get("symbols"),
                    "caption_source": d.get("caption_source"),
                    "created_at": d.get("created_at"),
                }
            )
        except Exception:
            continue
        if len(rows) >= limit:
            break
    return rows


def retrieve_by_query(query: str, root: Optional[Path] = None, top_k: int = 5) -> List[EpisodeMemory]:
    """
    Simple lexical retrieval over stored episodes (title, symbols, captions, plain_english).
    Later: cosine over trinary/machine fingerprints.
    """
    root = root or default_memory_dir()
    q = query.lower().strip()
    scored: List[Tuple[float, EpisodeMemory]] = []
    for p in root.glob("*.json"):
        try:
            mem = EpisodeMemory.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
        blob = " ".join(
            [
                mem.title,
                " ".join(mem.symbols),
                mem.caption_text,
                mem.plain_english,
                " ".join(mem.knowledge_keys),
            ]
        ).lower()
        score = 0.0
        for tok in q.split():
            if tok and tok in blob:
                score += 1.0
        if query.lower() in blob:
            score += 2.0
        if score > 0:
            scored.append((score, mem))
    scored.sort(key=lambda x: -x[0])
    return [m for _, m in scored[:top_k]]


def recall_plain_english(query: str, root: Optional[Path] = None) -> str:
    hits = retrieve_by_query(query, root=root, top_k=3)
    if not hits:
        return f"No stored episode matches “{query}”. Watch/chew media first to form memories."
    lines = [f"Recall for “{query}” ({len(hits)} episode(s)):", ""]
    for mem in hits:
        lines.append(f"### {mem.title}")
        lines.append(f"- symbols: {', '.join(mem.symbols[:10])}")
        lines.append(f"- dialogue source: {mem.caption_source} ({mem.caption_cues_n} cues)")
        if mem.sample_lines:
            lines.append("- sample lines: " + " | ".join(mem.sample_lines[:4]))
        if mem.plain_english:
            lines.append(mem.plain_english)
        lines.append("")
    return "\n".join(lines)
