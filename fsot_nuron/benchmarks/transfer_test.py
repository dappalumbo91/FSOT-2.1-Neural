"""
Transfer test: teach on document/episode A, probe with paraphrased content B.

Rules:
  - Probe queries must **not** share title tokens with A
  - Success = recall of *shared symbols / 5W1H slots / mechanism*, not title match
  - Stays compositional (lexicon + teach cards), not an LLM paraphrase engine

This attacks the remaining limit: inflated learning that only works when
query and title share strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..paths import ARTIFACTS, DATA, ROOT
from ..knowledge.document_read import discover_documents, read_document
from ..knowledge.teach_5w1h import build_5w1h, Teach5W1H
from ..knowledge.episode_memory import (
    EpisodeMemory,
    save_episode,
    retrieve_by_query,
    _eid,
)
from ..knowledge.curiosity import run_curiosity_loop


def _tokens(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]{3,}", (s or "").lower()) if t}


def _paraphrase_queries(lesson: Teach5W1H, banned_title_tokens: set) -> List[Tuple[str, str]]:
    """
    Build probes that avoid banned title tokens in the *query string*.
    Expected answers may still be content symbols (not title words).
    """
    out: List[Tuple[str, str]] = []

    def clean_q(q: str) -> str:
        words = q.split()
        kept = [w for w in words if w.lower().strip(".,?!") not in banned_title_tokens]
        return " ".join(kept) if kept else q

    # Symbol / domain / mechanism probes (content-level)
    if lesson.domain:
        out.append((clean_q("what domain mechanism applies here"), lesson.domain))
    if lesson.mechanism:
        # expect a distinctive fragment of mechanism id
        frag = lesson.mechanism.replace("_", " ").split()[0]
        out.append((clean_q("what mechanism label is used"), frag))
    for w in lesson.who[:2]:
        if _tokens(w).isdisjoint(banned_title_tokens):
            out.append((clean_q(f"who is {w}"), w))
    for w in lesson.what[:3]:
        # skip if what is basically the title
        if _tokens(w).issubset(banned_title_tokens):
            continue
        out.append((clean_q(f"what pattern involves {w}"), w))
    if lesson.why:
        # probe WHY without pasting title
        out.append((clean_q("why do these patterns bind"), "mechanism"))
        out.append((clean_q("explain the why of co-occurrence"), lesson.why[0][:30]))
    if lesson.how:
        out.append((clean_q("how is knowledge stored in the body"), "trit"))
    return out[:10]


@dataclass
class TransferPairResult:
    teach_title: str
    probe_label: str
    n_probes: int
    n_hits: int
    hit_rate: float
    curiosity_resolved: float
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TransferTestReport:
    ok: bool
    n_pairs: int
    mean_hit_rate: float
    mean_curiosity: float
    pairs: List[TransferPairResult]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _teach_episode(
    title: str,
    text: str,
    *,
    path: str,
    kind: str,
    symbols: Sequence[str],
    mem_root: Path,
) -> Teach5W1H:
    lesson = build_5w1h(
        title=title,
        text=text,
        symbols=list(symbols),
        path=path,
        kind=kind,
    )
    # curiosity fill before save
    cur = run_curiosity_loop(lesson, root=mem_root)
    if cur.n_resolved:
        lesson.plain += f" Curiosity resolved {cur.n_resolved}/{cur.n_questions}."
        for a in cur.answers:
            if a.resolved and a.slot == "who" and a.answer not in lesson.who:
                # don't parse freeform; keep as note
                pass
    mem = EpisodeMemory(
        episode_id=_eid(title, path),
        title=title,
        path=path,
        kind=kind,
        symbols=list(symbols),
        caption_text=text[:500],
        plain_english=lesson.as_teach_text(),
        knowledge_keys=list(symbols)[:8],
        sample_lines=text.split(". ")[:4],
        notes=["transfer_teach", "5w1h", f"domain={lesson.domain}"],
    )
    save_episode(mem, root=mem_root)
    return lesson


def run_transfer_tests(
    *,
    max_pairs: int = 3,
    mem_root: Optional[Path] = None,
) -> TransferTestReport:
    """
    Teach on literature docs; probe with paraphrased questions that ban title tokens.
    """
    notes: List[str] = []
    mem_root = mem_root or (ARTIFACTS / "transfer_test_memory")
    mem_root.mkdir(parents=True, exist_ok=True)

    # Built-in teach pairs: (title, text, symbols) — second is paraphrase probe set
    pairs_src: List[Tuple[str, str, List[str], str]] = []

    # From real files when present
    docs = discover_documents(None, max_files=30)

    def prefer(p: Path) -> int:
        s = str(p).lower()
        return (
            (12 if "thesis" in s else 0)
            + (10 if "literature" in s else 0)
            + (6 if "shakespeare" in s else 0)
            + (4 if p.suffix == ".md" else 0)
            - (20 if p.suffix == ".py" else 0)
        )

    docs = sorted(set(docs), key=prefer, reverse=True)
    for p in docs[: max_pairs + 2]:
        try:
            rep, _ = read_document(p, max_chunks=5, chunk_chars=700)
            pairs_src.append(
                (
                    rep.title,
                    (rep.sample_text or rep.plain_english or "")[:2000],
                    list(rep.symbols_guessed or [])[:8],
                    str(p),
                )
            )
        except Exception as e:
            notes.append(f"skip {p.name}: {e}")

    # Synthetic controlled pair (always available)
    pairs_src.append(
        (
            "Allen PV rate motif",
            "Parvalbumin interneurons fire faster than pyramidal cells in Allen FI data. "
            "This cortical order (PV much faster than Pyr) is a wet-lab constraint. "
            "FSOT scalpel locks class rates without free-fit S.",
            ["neuron", "brain", "science"],
            "synthetic://allen_pv_motif",
        )
    )
    pairs_src.append(
        (
            "FSOT scalar spine",
            "The scalar S equals K times the sum of T1 T2 T3. "
            "No free parameters. Machine body uses UTF-8 to trits. "
            "Neuroscience domain uses elevated D_eff relative to biology.",
            ["fsot", "scalar", "trinary", "codon"],
            "synthetic://fsot_spine",
        )
    )

    results: List[TransferPairResult] = []
    for title, text, symbols, path in pairs_src[:max_pairs]:
        banned = _tokens(title)
        # also ban path stem tokens
        banned |= _tokens(Path(path).stem.replace("_", " "))
        lesson = _teach_episode(
            title,
            text,
            path=path,
            kind="document:transfer",
            symbols=symbols,
            mem_root=mem_root,
        )
        probes = _paraphrase_queries(lesson, banned)
        # filter any probe whose query still contains banned tokens
        clean_probes = []
        for q, exp in probes:
            qtok = _tokens(q)
            # allow domain/mechanism words even if overlap; ban if query is mostly title
            if len(qtok & banned) >= max(2, len(qtok) // 2) and len(banned) > 0:
                continue
            clean_probes.append((q, exp))
        if not clean_probes:
            clean_probes = [
                ("what domain mechanism applies here", lesson.domain),
                ("how is knowledge stored in the body", "trit"),
            ]

        hits = 0
        for q, exp in clean_probes:
            retrieved = retrieve_by_query(q, root=mem_root, top_k=4)
            blob = " ".join(
                (h.plain_english or "")
                + " "
                + " ".join(h.symbols or [])
                + " "
                + (h.caption_text or "")
                for h in retrieved
            ).lower()
            # Do NOT score title match alone
            if exp.lower() in blob:
                hits += 1
            elif lesson.mechanism and exp.lower() in lesson.mechanism.replace("_", " "):
                # mechanism fragment in teach card
                if any(exp.lower() in (h.plain_english or "").lower() for h in retrieved):
                    hits += 1

        rate = hits / max(1, len(clean_probes))
        cur = run_curiosity_loop(lesson, root=mem_root, max_questions=4)
        cur_rate = cur.n_resolved / max(1, cur.n_questions)
        results.append(
            TransferPairResult(
                teach_title=title,
                probe_label="paraphrase_no_title_tokens",
                n_probes=len(clean_probes),
                n_hits=hits,
                hit_rate=rate,
                curiosity_resolved=cur_rate,
                notes=[
                    f"banned_title_tokens={sorted(list(banned))[:8]}",
                    f"domain={lesson.domain} mechanism={lesson.mechanism}",
                    f"open_q={lesson.open_questions[:3]}",
                ],
            )
        )

    mean_h = sum(r.hit_rate for r in results) / max(1, len(results))
    mean_c = sum(r.curiosity_resolved for r in results) / max(1, len(results))
    ok = mean_h >= 0.45 and len(results) >= 2
    rep = TransferTestReport(
        ok=ok,
        n_pairs=len(results),
        mean_hit_rate=mean_h,
        mean_curiosity=mean_c,
        pairs=results,
        notes=notes
        + [
            "Transfer = teach A, probe without title-token shortcuts.",
            "Success is content/mechanism recall, not string match to title.",
        ],
    )

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    import json
    from datetime import datetime, timezone

    (ARTIFACTS / "transfer_test_last.json").write_text(
        json.dumps(rep.to_dict(), indent=2, default=str), encoding="utf-8"
    )
    md = DATA / "results" / "TRANSFER_TEST.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Transfer test (teach A → probe paraphrase B)",
        "",
        f"OK: **{rep.ok}**  pairs={rep.n_pairs}  mean_hit=**{rep.mean_hit_rate:.3f}**  "
        f"mean_curiosity=**{rep.mean_curiosity:.3f}**",
        "",
        "| Teach title | probes | hits | hit_rate | curiosity |",
        "|-------------|-------:|-----:|---------:|----------:|",
    ]
    for p in results:
        lines.append(
            f"| {p.teach_title[:40]} | {p.n_probes} | {p.n_hits} | {p.hit_rate:.3f} | "
            f"{p.curiosity_resolved:.3f} |"
        )
    lines += ["", "## Notes", ""]
    for n in rep.notes:
        lines.append(f"- {n}")
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")
    return rep
