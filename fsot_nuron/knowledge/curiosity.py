"""
Active questioning — fill empty 5W1H slots (curiosity loop).

Biologically: attention / uncertainty sampling — when a teach card lacks WHO/WHAT/WHY/…
the organism emits questions and tries to answer from memory + lexicon (not external LLM).

Doctrine:
  - Questions are generated from empty_slot_questions(card)
  - Answers are compositional retrieval + domain mechanism templates
  - Unanswered slots stay listed as OPEN (honest uncertainty)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .teach_5w1h import Teach5W1H, build_5w1h, empty_slot_questions, mechanism_templates
from .episode_memory import retrieve_by_query, list_episodes, load_episode, default_memory_dir
from .lexicon import load_lexicon
from .monologue import _answer_from_memory, MonologueTurn


@dataclass
class CuriosityAnswer:
    question: str
    slot: str
    answer: str
    resolved: bool
    sources: List[str] = field(default_factory=list)
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CuriosityReport:
    n_questions: int
    n_resolved: int
    answers: List[CuriosityAnswer]
    remaining_open: List[str]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _slot_from_question(q: str) -> str:
    u = q.upper()
    for s in ("WHO", "WHAT", "WHY", "WHERE", "WHEN", "HOW"):
        if u.startswith(s) or f" {s} " in f" {u} ":
            return s.lower()
    if "mechanism" in q.lower():
        return "why"
    return "what"


def answer_open_question(
    question: str,
    card: Teach5W1H,
    *,
    root: Optional[Path] = None,
) -> CuriosityAnswer:
    """
    Try to fill one open question from memory + domain mechanism.
    """
    root = root or default_memory_dir()
    slot = _slot_from_question(question)
    lex = load_lexicon()
    hits = retrieve_by_query(question, root=root, top_k=4)
    sources = [h.episode_id for h in hits[:3]]
    evidence_bits: List[str] = []
    for h in hits[:3]:
        evidence_bits.append(
            " ".join(
                [
                    h.title or "",
                    " ".join(h.symbols or []),
                    (h.plain_english or "")[:200],
                ]
            )
        )
    evidence = " | ".join(evidence_bits)[:500]
    low_ev = evidence.lower()

    resolved = False
    answer_parts: List[str] = []

    if slot == "who":
        for name in card.who:
            answer_parts.append(name)
            resolved = True
        if not resolved:
            for h in hits:
                for s in h.symbols or []:
                    e = lex.get(s)
                    if e and (e.kind or "").lower() in ("character", "person"):
                        answer_parts.append(s)
                        resolved = True
        if not resolved:
            # Domain-honest: biology/physics episodes often have no person agents
            from .teach_5w1h import (
                DOMAIN_BIOLOGY,
                DOMAIN_PHYSICS,
                DOMAIN_LEARNING,
            )

            if card.domain in (DOMAIN_BIOLOGY, DOMAIN_PHYSICS, DOMAIN_LEARNING):
                answer_parts.append(
                    f"No person agent — domain={card.domain} acts via "
                    f"cell classes / scalars / patterns "
                    f"({', '.join((card.what or ['system'])[:4])})."
                )
                resolved = True
            else:
                answer_parts.append(
                    "No agent/character bound yet — need dialogue captions "
                    "or character lexicon hits."
                )
    elif slot == "what":
        if card.what:
            answer_parts.extend(card.what[:4])
            resolved = True
        elif hits:
            answer_parts.append(
                "Patterns: " + ", ".join((hits[0].symbols or [])[:6] or ["scene"])
            )
            resolved = bool(hits[0].symbols)
        else:
            answer_parts.append("WHAT slot empty — re-encode with clearer symbols.")
    elif slot == "why":
        if card.why:
            answer_parts.append(card.why[0][:200])
            resolved = True
        mech, lines = mechanism_templates(card.domain, card.what or card.who)
        answer_parts.append(f"Mechanism template ({mech}): {lines[0]}")
        # template counts as partial resolve (honest domain WHY)
        resolved = True
    elif slot == "where":
        if card.where:
            answer_parts.extend(card.where[:3])
            resolved = True
        elif hits and hits[0].path:
            answer_parts.append(f"source path: {hits[0].path[-80:]}")
            resolved = True
        else:
            answer_parts.append("WHERE unknown — missing path/place tags.")
    elif slot == "when":
        if card.when:
            answer_parts.extend(card.when[:3])
            resolved = True
        else:
            answer_parts.append("WHEN default: short-horizon encode window.")
            resolved = True  # default is always available
    elif slot == "how":
        if card.how:
            answer_parts.extend(card.how[:3])
            resolved = True
        else:
            answer_parts.append(
                "HOW: UTF-8→trits + RF cascade + FSOT seeds (default body path)."
            )
            resolved = True
    else:
        # fall back to monologue-style memory answer
        turn = _answer_from_memory(question, root=root, lexicon=lex)
        answer_parts.append(turn.answer[:400])
        resolved = turn.grounded_hits >= 2
        sources = turn.sources or sources

    return CuriosityAnswer(
        question=question,
        slot=slot,
        answer=" ".join(answer_parts)[:600],
        resolved=resolved,
        sources=sources,
        evidence=evidence[:300],
    )


def run_curiosity_loop(
    card: Optional[Teach5W1H] = None,
    *,
    title: str = "",
    text: str = "",
    symbols: Optional[Sequence[str]] = None,
    kind: str = "",
    path: str = "",
    root: Optional[Path] = None,
    max_questions: int = 6,
) -> CuriosityReport:
    """
    If card given, use its open_questions; else build from text then question gaps.
    """
    notes: List[str] = []
    if card is None:
        card = build_5w1h(
            title=title,
            text=text,
            symbols=list(symbols or []),
            kind=kind,
            path=path,
        )
        notes.append(f"built card domain={card.domain} mechanism={card.mechanism}")

    questions = list(card.open_questions or empty_slot_questions(card))[:max_questions]
    # always probe mechanism if weak
    if card.mechanism in ("hebbian_co_occurrence",) and not any(
        "mechanism" in q.lower() for q in questions
    ):
        questions.append(
            f"What stronger mechanism could explain {card.source or 'this episode'}?"
        )

    answers: List[CuriosityAnswer] = []
    for q in questions[:max_questions]:
        answers.append(answer_open_question(q, card, root=root))

    n_res = sum(1 for a in answers if a.resolved)
    remaining = [a.question for a in answers if not a.resolved]
    notes.append(f"resolved {n_res}/{len(answers)} curiosity questions")
    return CuriosityReport(
        n_questions=len(answers),
        n_resolved=n_res,
        answers=answers,
        remaining_open=remaining,
        notes=notes,
    )
