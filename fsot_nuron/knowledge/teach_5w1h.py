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
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .lexicon import load_lexicon, KnowledgeLexicon
from .vision_caption_bind import tokenize_caption, _CHAR_LEX


# Domain tags for mechanism templates (bio-honest interpretation modes)
DOMAIN_BIOLOGY = "biology"
DOMAIN_PHYSICS = "physics_fsot"
DOMAIN_NARRATIVE = "narrative"
DOMAIN_MEDIA = "media"
DOMAIN_LEARNING = "learning"
DOMAIN_GENERIC = "generic"


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
    domain: str = DOMAIN_GENERIC
    mechanism: str = ""  # primary WHY mechanism label
    empty_slots: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def as_teach_text(self) -> str:
        """Compact host-readable lesson card."""
        lines = [f"Lesson from: {self.source}" if self.source else "Lesson:"]
        if self.domain:
            lines.append(f"DOMAIN: {self.domain}")
        if self.who:
            lines.append(f"WHO: {', '.join(self.who[:8])}")
        if self.what:
            lines.append(f"WHAT: {', '.join(self.what[:8])}")
        if self.why:
            lines.append(f"WHY: {'; '.join(self.why[:6])}")
        if self.mechanism:
            lines.append(f"MECHANISM: {self.mechanism}")
        if self.where:
            lines.append(f"WHERE: {', '.join(self.where[:6])}")
        if self.when:
            lines.append(f"WHEN: {', '.join(self.when[:6])}")
        if self.how:
            lines.append(f"HOW: {'; '.join(self.how[:6])}")
        if self.open_questions:
            lines.append("OPEN: " + " | ".join(self.open_questions[:6]))
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
        if self.mechanism:
            out.append((f"what mechanism explains this", self.mechanism[:48]))
        if self.where:
            out.append((f"where {self.where[0]}", self.where[0]))
        if self.when:
            out.append((f"when {self.when[0]}", self.when[0]))
        if self.how:
            out.append((f"how is this encoded", self.how[0]))
        if self.domain:
            out.append((f"what domain is this lesson", self.domain))
        return out

    def filled_slots(self) -> List[str]:
        filled = []
        for name, vals in (
            ("who", self.who),
            ("what", self.what),
            ("why", self.why),
            ("where", self.where),
            ("when", self.when),
            ("how", self.how),
        ):
            if vals:
                filled.append(name)
        return filled


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


def infer_domain(
    *,
    title: str = "",
    text: str = "",
    kind: str = "",
    symbols: Optional[Sequence[str]] = None,
    path: str = "",
) -> str:
    """
    Domain for mechanism templates — bio-faithful interpretation mode,
    not free classification.
    """
    low = f"{title} {text} {kind} {path} {' '.join(symbols or [])}".lower()
    if any(
        k in low
        for k in (
            "neuron",
            "allen",
            "pv ",
            "spike",
            "eeg",
            "hippocamp",
            "sme",
            "cell-class",
            "cre ",
            "physiology",
            "synapse",
        )
    ):
        return DOMAIN_BIOLOGY
    if any(
        k in low
        for k in (
            "fsot",
            "scalar",
            "photon",
            "trinary",
            "codon",
            "formula",
            "theorem",
            "physics",
            "domainconfig",
            "d_eff",
        )
    ):
        return DOMAIN_PHYSICS
    if "media" in kind or "video" in kind or any(
        k in low for k in ("movie", "mp4", "bluray", "caption", "srt", "dialogue")
    ):
        return DOMAIN_MEDIA
    if any(k in low for k in ("shakespeare", "scene", "act ", "play", "narrative", "story")):
        return DOMAIN_NARRATIVE
    if any(k in low for k in ("learn", "memory", "recall", "encode", "consolidat")):
        return DOMAIN_LEARNING
    if "document" in kind:
        return DOMAIN_PHYSICS if "fsot" in low or "thesis" in low else DOMAIN_GENERIC
    return DOMAIN_GENERIC


def mechanism_templates(domain: str, symbols: Sequence[str]) -> Tuple[str, List[str]]:
    """
    Domain-specific WHY mechanisms (honest FSOT/bio mappings).

    Returns (primary_mechanism_label, why_lines).
    These are *interpretation templates*, not free causal invention.
    """
    sym = ", ".join(list(symbols)[:4]) if symbols else "observed patterns"
    if domain == DOMAIN_BIOLOGY:
        return (
            "cell-class_rate_and_circuit_motif",
            [
                f"Biology mode: rates/order (e.g. PV≫Pyr) and E/I motifs explain {sym} "
                f"under Allen-locked scalpel dynamics — not a tissue identity claim.",
                "Learning bands (theta/gamma SME direction) mark encode vs rest when present.",
                "Mechanism is wet-lab-constrained spike statistics + seed-lawful gains.",
            ],
        )
    if domain == DOMAIN_PHYSICS:
        return (
            "fsot_scalar_spine_S=K(T1+T2+T3)",
            [
                f"Physics/FSOT mode: S=K(T1+T2+T3) with zero free parameters gates {sym}.",
                "Machine path packs meaning as UTF-8→trits (body language), not next-token LM.",
                "Domain scalars (Biology/Neuroscience D_eff) set operating point without refit.",
            ],
        )
    if domain == DOMAIN_NARRATIVE:
        return (
            "narrative_co_occurrence_and_role",
            [
                f"Narrative mode: roles and dialogue lines co-occur as {sym}; "
                f"story causality is textual order + character lexicon, not physical law.",
                "WHY from text is extractive (because/therefore) when present; else role co-occurrence.",
            ],
        )
    if domain == DOMAIN_MEDIA:
        return (
            "av_co_occurrence_and_rf_bind",
            [
                f"Media mode: vision RF cascade + speech/caption tokens co-occur for {sym}.",
                "Pixel→name uses tutor-ablated RF prototypes + caption co-occurrence "
                "(not claimed open-world character ID).",
                "Thalamic relay gain < primary (seed φ) filters afferents before cortex proxy.",
            ],
        )
    if domain == DOMAIN_LEARNING:
        return (
            "encode_delay_retrieve_sme",
            [
                f"Learning mode: encode→delay→retrieve on {sym}; success tied to SME θ/γ direction.",
                "Episodic tags (hipp) bind teach cards; consolidation is offline replay proxy.",
                "Accuracy is discrimination margin (sim+ > sim−), not free language fluency.",
            ],
        )
    return (
        "hebbian_co_occurrence",
        [
            f"Generic mode: patterns {sym} bind by co-occurrence in episode memory "
            f"(Hebbian-style association; not free causal claim).",
        ],
    )


def empty_slot_questions(card: "Teach5W1H") -> List[str]:
    """
    Active curiosity: questions the organism should ask when a 5W1H slot is empty.
    Biologically: like uncertainty-driven sampling / attention to missing afferents.
    """
    q: List[str] = []
    src = card.source or "this episode"
    if not card.who:
        q.append(f"WHO acted or spoke in {src}?")
    if not card.what:
        q.append(f"WHAT pattern or event defines {src}?")
    if not card.why:
        q.append(f"WHY did these patterns co-occur in {src} (mechanism)?")
    if not card.where:
        q.append(f"WHERE (place/source/kind) is {src} located?")
    if not card.when:
        q.append(f"WHEN did {src} occur (time/order/caption stream)?")
    if not card.how:
        q.append(f"HOW was {src} encoded into the organism body?")
    # Always allow a depth question when mechanism is co-occurrence only
    if card.mechanism in ("hebbian_co_occurrence", "narrative_co_occurrence_and_role"):
        q.append(
            f"What stronger mechanism (rate, scalar, bind) could replace weak WHY for {src}?"
        )
    return q[:8]


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
    Domain mechanism templates supply richer WHY; empty slots → open questions.
    """
    lex = lexicon or load_lexicon()
    symbols = list(symbols or [])
    blob = f"{title}\n{text}\n{' '.join(sample_lines or [])}"
    low = blob.lower()
    domain = infer_domain(
        title=title, text=text, kind=kind, symbols=symbols, path=path
    )
    card = Teach5W1H(source=title or path or kind, domain=domain)

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
        card.what.append(title[:80])

    # WHY — extractive causal sentences + domain mechanism templates
    for sent in _sentences(text or " ".join(sample_lines or [])):
        sl = sent.lower()
        if any(c in sl for c in _WHY_CUES):
            card.why.append(sent[:160])
        if len(card.why) >= 3:
            break
    mech_label, mech_lines = mechanism_templates(domain, symbols)
    card.mechanism = mech_label
    for line in mech_lines:
        if line not in card.why:
            card.why.append(line)

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
        f"domain_mechanism:{mech_label}",
    ]
    if "document" in (kind or ""):
        card.how.insert(0, "document chunk→teach text→assoc/hipp packets")
    if "media" in (kind or "") or "video" in (kind or ""):
        card.how.insert(0, "frame sample→retina features→thal/sens inject")

    # Active curiosity on empty slots
    card.empty_slots = [
        s
        for s in ("who", "what", "why", "where", "when", "how")
        if not getattr(card, s)
    ]
    card.open_questions = empty_slot_questions(card)

    card.plain = (
        f"5W1H teach card domain={domain} mechanism={mech_label} "
        f"for “{title or 'episode'}”. "
        f"WHO={len(card.who)} WHAT={len(card.what)} WHY={len(card.why)} "
        f"WHERE={len(card.where)} WHEN={len(card.when)} HOW={len(card.how)} "
        f"OPEN={len(card.open_questions)}."
    )
    # dedupe lists
    for attr in ("who", "what", "why", "where", "when", "how", "open_questions"):
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

