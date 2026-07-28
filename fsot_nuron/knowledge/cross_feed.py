"""
Cross-feed: symbols + speech text + lexicon → machine/trinary knowledge packets.

Human analog:
  Continuous experience is not stored as English sentences; it is compacted
  into physical patterns. We compact meaning into **machine/trinary** (the
  body's language), then can re-expand to plain English on retrieval
  ("regurgitate in our own words").

Pipeline:
  observed symbols / transcript
       → lexicon definitions (+ optional online)
       → teach text
       → FSOT machine encode (UTF-8 → trits → SensoryPacket)
       → assoc / hipp inject
       → plain-English summary for the host UI
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence

from ..machine_encode import encode_to_sensory_packet, EncodePath, text_to_utf8_trits
from ..fsot_bridge import bridge_machine_payload
from ..sensory.packets import SensoryPacket, SensoryModality
from .lexicon import KnowledgeLexicon, KnowledgeEntry, load_lexicon, optional_online_snippet


@dataclass
class CrossFeedReport:
    symbols_in: List[str]
    transcript: str
    knowledge_texts: List[str]
    teach_bundle: str
    plain_english: str
    n_trits: int
    S_couple: Optional[float]
    packets: List[Dict[str, Any]] = field(default_factory=list)
    entries_used: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def knowledge_to_machine_packets(
    texts: Sequence[str],
    *,
    target_region: str = "assoc",
    strength: float = 0.5,
) -> List[SensoryPacket]:
    """Each knowledge sentence → machine-path sensory packet (trinary body language)."""
    pkts: List[SensoryPacket] = []
    for t in texts:
        t = (t or "").strip()
        if not t:
            continue
        pkt = encode_to_sensory_packet(
            t,
            path=EncodePath.MACHINE,
            target_region=target_region,
            strength=strength,
        )
        pkt.meta["kind"] = "knowledge_cross_feed"
        pkt.meta["text_preview"] = t[:160]
        # also hipp copy for episodic bind
        hip = encode_to_sensory_packet(
            t,
            path=EncodePath.MACHINE,
            target_region="hipp",
            strength=strength * 0.7,
        )
        hip.meta["kind"] = "knowledge_episodic"
        hip.meta["text_preview"] = t[:160]
        pkts.extend([pkt, hip])
    return pkts


def regurgitate_plain_english(
    *,
    title: str,
    symbols: Sequence[str],
    entries: Sequence[KnowledgeEntry],
    transcript: str = "",
    sensory_notes: str = "",
) -> str:
    """
    Re-expand compacted knowledge into host-readable language
    (not a free LLM — compositional from definitions + observations).
    """
    lines = []
    if title:
        lines.append(f"While experiencing “{title}”, the stream activated patterns linked to: {', '.join(symbols[:8]) or 'general scene'}." )
    else:
        lines.append(
            f"The stream activated patterns linked to: {', '.join(symbols[:8]) or 'general scene'}."
        )
    if sensory_notes:
        lines.append(sensory_notes)
    if transcript:
        lines.append(f"Speech heard (voice→text): “{transcript[:280]}”")
    if entries:
        lines.append("Associated knowledge (compacted to machine/trinary for the body, expanded here in words):")
        for e in entries[:8]:
            lines.append(f"  • {e.key}: {e.definition}")
            if e.examples:
                lines.append(f"    examples: {', '.join(e.examples[:4])}")
    else:
        lines.append(
            "No lexicon entries matched yet — patterns still bind audiovisualy; "
            "add symbols or speech text to attach definitions."
        )
    lines.append(
        "Internal form is not English: text is UTF-8→trits (machine body language), "
        "like chemical/compact codes rather than inner speech."
    )
    return "\n".join(lines)


def cross_feed_episode(
    *,
    symbols: Sequence[str],
    title: str = "",
    transcript: str = "",
    sensory_notes: str = "",
    path_hint: str = "",
    lexicon: Optional[KnowledgeLexicon] = None,
    online: bool = False,
) -> CrossFeedReport:
    """
    Build knowledge teach-texts from symbols + speech, encode to machine packets.
    """
    lex = lexicon or load_lexicon()
    notes: List[str] = []
    keys = list(symbols)
    # pull keys from title / transcript / path (shows live in folder names)
    blob = f"{title} {transcript} {path_hint}"
    for e in lex.match_text(blob):
        keys.append(e.key)
    # normalize
    keys = [k.lower().replace(" ", "_") if " " not in k else k.lower() for k in keys]
    # adventure time special: spaces
    flat = []
    for k in keys:
        flat.append(k)
        flat.append(k.replace("_", " "))
    entries = lex.lookup_many(flat)
    # also direct get for multiword / characters when path implies show
    low = blob.lower()
    for phrase in ("adventure time", "finn", "jake", "cartoon", "tv_show", "dialogue", "person", "dog", "human"):
        if phrase in low or (phrase in ("finn", "jake") and "adventure time" in low):
            e = lex.get(phrase)
            if e and all(x.key != e.key for x in entries):
                entries.append(e)
    # If Adventure Time context, always teach Finn/Jake anchors (show-level prior)
    if "adventure time" in low:
        for phrase in ("adventure time", "finn", "jake", "human", "dog", "cartoon"):
            e = lex.get(phrase)
            if e and all(x.key != e.key for x in entries):
                entries.append(e)

    # Prefer characters / show-level knowledge in regurgitation order
    entries.sort(
        key=lambda e: (
            0 if e.kind in ("character", "show") else 1 if e.kind == "category" else 2,
            e.key,
        )
    )

    knowledge_texts = [e.as_teach_text() for e in entries]
    if online or __import__("os").environ.get("FSOT_KNOWLEDGE_ONLINE", "0") in (
        "1",
        "true",
        "yes",
    ):
        for e in entries[:3]:
            snip = optional_online_snippet(e.key)
            if snip:
                knowledge_texts.append(f"[online:{e.key}] {snip}")
                notes.append(f"online expand: {e.key}")

    if transcript:
        knowledge_texts.insert(
            0,
            f"Heard speech during scene: {transcript[:400]}",
        )

    teach_bundle = " || ".join(knowledge_texts)[:2000]
    # machine encode stats
    trits = text_to_utf8_trits(teach_bundle) if teach_bundle else []
    S = None
    try:
        br = bridge_machine_payload(teach_bundle or "empty")
        S = float((br.get("modulators") or {}).get("S"))
    except Exception as e:
        notes.append(f"bridge note: {e}")

    pkts = knowledge_to_machine_packets(knowledge_texts[:12] if knowledge_texts else [])
    plain = regurgitate_plain_english(
        title=title or path_hint,
        symbols=list(dict.fromkeys([str(s) for s in symbols])),
        entries=entries,
        transcript=transcript,
        sensory_notes=sensory_notes,
    )
    notes.append(
        f"cross-feed: {len(entries)} lexicon entries, {len(pkts)} machine packets, "
        f"n_trits={len(trits)}"
    )
    return CrossFeedReport(
        symbols_in=[str(s) for s in symbols],
        transcript=transcript or "",
        knowledge_texts=knowledge_texts,
        teach_bundle=teach_bundle,
        plain_english=plain,
        n_trits=len(trits),
        S_couple=S,
        packets=[p.to_dict() for p in pkts],
        entries_used=[e.to_dict() for e in entries],
        notes=notes,
    )
