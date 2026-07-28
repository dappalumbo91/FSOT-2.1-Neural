"""
Local symbolic knowledge lexicon — definitions the mind can cross-feed.

Standalone: ships in `data/knowledge/lexicon.json`.
Optional online expand only if FSOT_KNOWLEDGE_ONLINE=1 (never required to boot).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..paths import ROOT, DATA


@dataclass
class KnowledgeEntry:
    key: str
    kind: str
    definition: str
    examples: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    show: str = ""
    source: str = "local_lexicon"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def as_teach_text(self) -> str:
        ex = ", ".join(self.examples[:4]) if self.examples else ""
        rel = ", ".join(self.related[:4]) if self.related else ""
        parts = [f"{self.key}: {self.definition}"]
        if ex:
            parts.append(f"Examples: {ex}.")
        if rel:
            parts.append(f"Related: {rel}.")
        if self.show:
            parts.append(f"Context: {self.show}.")
        return " ".join(parts)


class KnowledgeLexicon:
    def __init__(self, entries: Optional[Dict[str, KnowledgeEntry]] = None):
        self.entries: Dict[str, KnowledgeEntry] = entries or {}

    def get(self, key: str) -> Optional[KnowledgeEntry]:
        k = key.strip().lower()
        if k in self.entries:
            return self.entries[k]
        # fuzzy: strip underscores
        k2 = k.replace("_", " ")
        if k2 in self.entries:
            return self.entries[k2]
        return None

    def lookup_many(self, keys: Sequence[str]) -> List[KnowledgeEntry]:
        out: List[KnowledgeEntry] = []
        seen = set()
        for key in keys:
            e = self.get(key)
            if e and e.key not in seen:
                out.append(e)
                seen.add(e.key)
            # also related one-hop
            if e:
                for r in e.related[:3]:
                    e2 = self.get(r)
                    if e2 and e2.key not in seen:
                        out.append(e2)
                        seen.add(e2.key)
        return out

    def match_text(self, text: str) -> List[KnowledgeEntry]:
        """Find lexicon keys mentioned in free text (title, transcript)."""
        low = (text or "").lower()
        hits: List[KnowledgeEntry] = []
        for key, e in self.entries.items():
            if len(key) < 3:
                continue
            if re.search(rf"\b{re.escape(key)}\b", low):
                hits.append(e)
        # multiword titles
        if "adventure time" in low and "adventure time" in self.entries:
            hits.append(self.entries["adventure time"])
        # dedupe
        seen = set()
        uniq = []
        for h in hits:
            if h.key not in seen:
                uniq.append(h)
                seen.add(h.key)
        return uniq

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self.entries.items()}


def default_lexicon_path() -> Path:
    return DATA / "knowledge" / "lexicon.json"


def load_lexicon(path: Optional[Path] = None) -> KnowledgeLexicon:
    path = path or default_lexicon_path()
    entries: Dict[str, KnowledgeEntry] = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        raw = data.get("entries") or {}
        for k, v in raw.items():
            if not isinstance(v, dict):
                continue
            key = str(k).lower()
            entries[key] = KnowledgeEntry(
                key=key,
                kind=str(v.get("kind") or "category"),
                definition=str(v.get("definition") or ""),
                examples=list(v.get("examples") or []),
                related=list(v.get("related") or []),
                show=str(v.get("show") or ""),
                source="local_lexicon",
            )
    return KnowledgeLexicon(entries)


def optional_online_snippet(query: str) -> Optional[str]:
    """
    Optional knowledge expand — ONLY if FSOT_KNOWLEDGE_ONLINE=1.
    Uses a minimal public search page scrape if tools exist; else None.
    Never blocks standalone.
    """
    if os.environ.get("FSOT_KNOWLEDGE_ONLINE", "0").strip() not in ("1", "true", "yes"):
        return None
    # Intentionally conservative: no hard dependency. Placeholder for API hooks.
    # User can later wire SerpAPI / Wikipedia REST etc.
    try:
        import urllib.request
        import urllib.parse

        # Wikipedia REST summary (public, no key) — still opt-in via env
        title = urllib.parse.quote(query.replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
        req = urllib.request.Request(url, headers={"User-Agent": "FSOT-Neural/0.7 (standalone research)"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        extract = payload.get("extract") or payload.get("description")
        if extract:
            return str(extract)[:500]
    except Exception:
        return None
    return None
