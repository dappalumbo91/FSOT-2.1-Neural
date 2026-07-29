"""
5W1H scientific teaching breakdown — human-like instruction packing.

When we *teach* the organism, we do not dump free text only. We structure
experience into:

  WHO   — agents / characters / actors
  WHAT  — event, object, claim, pattern
  WHY   — cause, purpose, mechanism (when known)
  WHERE — place, context, file/media locus
  WHEN  — time, order, caption timestamps
  HOW   — method, process, measurement path (FSOT / sensory / trit)

This is compositional (lexicon + captions + symbols + path), not an LLM.
Used by short-horizon encode and multi-domain stress probes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence

from .lexicon import load_lexicon, KnowledgeLexicon
from .vision_caption_bind import tokenize_caption, _CHAR_LEX


@dataclass
class Teach5W1H:
    who: List[str] = field(default_factory=list)
    what: List[str] = field(default_factory=list)
    why: List[str] = field(default_factory=list)
    where: List[str] = field(default_factory=list)
    when: List[str] = field(default_factory=list)
    how: List[str] = field(default_factory=list)
    source: str = ""
    plain: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def as_teach_text(self) -> str:
        """Compact host-readable lesson card."""
        lines = [f"Lesson from: {self.source}" if self.source else "Lesson:"]
        if self.who:
            lines.append(f"WHO: {', '.join(self.who[:8])}")
        if self.what:
            lines.append(f"WHAT: {', '.join(self.what[:8])}")
        if self.why:
            lines.append(f"WHY: {'; '.join(self.why[:6])}")
        if self.where:
            lines.append(f"WHERE: {', '.join(self.where[:6])}")
        if self.when:
            lines.append(f"WHEN: {', '.join(self.when[:6])}")
        if self.how:
            lines.append(f"HOW: {'; '.join(self.how[:6])}")
        if self.plain:
            lines.append(f"NOTES: {self.plain[:400]}")
        return "\n".join(lines)

    def query_bank(self) -> List[tuple]:
        """
        (query, expected_field_value) probes that are *not* trivial title copies.
        expected is a substring that should appear in recall of this lesson.
        """
        out: List[tuple] = []
        if self.who:
            out.append((f"who is involved in {self.source or 'this'}", self.who[0]))
            out.append((f"WHO {self.who[0]}", self.who[0]))
        if self.what:
            out.append((f"what happens regarding {self.what[0]}", self.what[0]))
            out.append((f"WHAT {self.what[0]}", self.what[0]))
        if self.why:
            out.append((f"why {self.what[0] if self.what else 'this'}", self.why[0][:40]))
        if self.where:
            out.append((f"where {self.where[0]}", self.where[0]))
        if self.when:
            out.append((f"when {self.when[0]}", self.when[0]))
        if self.how:
            out.append((f"how is this encoded", self.how[0]))
        return out


_WHY_CUES = (
    "because",
    "cause",
    "reason",
    "therefore",
    "so that",
    "in order to",
    "purpose",
    "mechanism",
    "due to",
    "leads to",
)
_WHERE_CUES = (
    "in the",
    "at the",
    "location",
    "place",
    "room",
    "city",
    "forest",
    "planet",
    "land of",
    "setting",
)
_WHEN_CUES = (
    "when",
    "after",
    "before",
    "during",
    "then",
    "year",
    "morning",
    "night",
    "day",
)


def _sentences(text: str, max_n: int = 12) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 12][:max_n]


def build_5w1h(
    *,
    title: str = "",
    text: str = "",
    symbols: Optional[Sequence[str]] = None,
    path: str = "",
    kind: str = "",
    caption_source: str = "",
    sample_lines: Optional[Sequence[str]] = None,
    lexicon: Optional[KnowledgeLexicon] = None,
) -> Teach5W1H:
    """
    Compose a 5W1H card from available evidence (compositional, not generative).
    """
    lex = lexicon or load_lexicon()
    symbols = list(symbols or [])
    blob = f"{title}\n{text}\n{' '.join(sample_lines or [])}"
    low = blob.lower()
    card = Teach5W1H(source=title or path or kind)

    # WHO — lexicon characters + speaker-ish tokens
    for name in _CHAR_LEX:
        if name in low:
            card.who.append(name)
    for e in lex.match_text(blob):
        if (e.kind or "").lower() in ("character", "person"):
            if e.key not in card.who:
                card.who.append(e.key)
    for tok in tokenize_caption(blob[:500], path_hint="", character_bias=True)[:8]:
        ent = lex.get(tok)
        if tok in _CHAR_LEX or (
            ent is not None and (ent.kind or "").lower() == "character"
        ):
            if tok not in card.who:
                card.who.append(tok)

    # WHAT — symbols + content nouns from lexicon categories/events
    for s in symbols:
        if s and s not in card.what:
            card.what.append(str(s))
    for e in lex.match_text(blob):
        if (e.kind or "").lower() in ("event", "category", "medium", "structure", "percept"):
            if e.key not in card.what and e.key not in card.who:
                card.what.append(e.key)
    if title and title.lower() not in [w.lower() for w in card.what]:
        # title as weak WHAT anchor
        card.what.append(title[:80])

    # WHY — sentences containing causal cues
    for sent in _sentences(text or " ".join(sample_lines or [])):
        sl = sent.lower()
        if any(c in sl for c in _WHY_CUES):
            card.why.append(sent[:160])
        if len(card.why) >= 4:
            break
    if not card.why and symbols:
        card.why.append(
            f"Associated patterns {', '.join(list(symbols)[:4])} co-occur in this episode "
            f"(co-occurrence mechanism, not free causal claim)."
        )

    # WHERE — place lexicon + path context
    for e in lex.match_text(blob):
        if (e.kind or "").lower() in ("place", "scene") or e.key in ("place", "indoor", "outdoor"):
            if e.key not in card.where:
                card.where.append(e.key)
    for sent in _sentences(text):
        if any(c in sent.lower() for c in _WHERE_CUES):
            card.where.append(sent[:120])
            if len(card.where) >= 4:
                break
    if path:
        card.where.append(f"source:{path[-80:]}")
    if kind:
        card.where.append(f"kind:{kind}")

    # WHEN — temporal cues + caption source timing note
    for sent in _sentences(text or " ".join(sample_lines or [])):
        if any(c in sent.lower() for c in _WHEN_CUES):
            card.when.append(sent[:120])
            if len(card.when) >= 4:
                break
    if caption_source and caption_source != "none":
        card.when.append(f"captions_via:{caption_source}")
    if not card.when:
        card.when.append("encode_window:short_horizon")

    # HOW — always explicit FSOT / machine path (scientific method of the body)
    card.how = [
        "UTF-8→trits machine body language (not next-token LLM)",
        "RF cascade vision / speech-band audio when media present",
        "episode memory + lexicon cross-feed",
        "FSOT seeds only (no free-fit S)",
    ]
    if "document" in (kind or ""):
        card.how.insert(0, "document chunk→teach text→assoc/hipp packets")
    if "media" in (kind or "") or "video" in (kind or ""):
        card.how.insert(0, "frame sample→retina features→thal/sens inject")

    card.plain = (
        f"Structured 5W1H teach card for “{title or 'episode'}”. "
        f"WHO={len(card.who)} WHAT={len(card.what)} WHY={len(card.why)} "
        f"WHERE={len(card.where)} WHEN={len(card.when)} HOW={len(card.how)}."
    )
    # dedupe lists
    for attr in ("who", "what", "why", "where", "when", "how"):
        seen = set()
        uniq = []
        for x in getattr(card, attr):
            k = x.lower() if isinstance(x, str) else str(x)
            if k in seen:
                continue
            seen.add(k)
            uniq.append(x)
        setattr(card, attr, uniq[:10])
    return card
