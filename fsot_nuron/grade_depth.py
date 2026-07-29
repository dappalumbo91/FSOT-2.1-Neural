"""
Grade-school *depth* — paraphrase / open questions over the open curriculum.

Doctrine:
  - STEM + literacy only (no history).
  - Does not invent new falsehoods; only rephrases what is already in bank.tsv.
  - Held-out exam: natural questions whose exact string is NOT a taught key.
  - Goal: claimability = understand questions, not only memorize cue strings.

Outputs under data/curriculum/pk_to_g8/:
  paraphrase_exam.tsv   domain  grade  question  answer  source_key
  paraphrase_exam.jsonl
  DEPTH_MANIFEST.json
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .paths import DATA

CUR = DATA / "curriculum" / "pk_to_g8"
BANK = CUR / "bank.tsv"
EXAM_TSV = CUR / "paraphrase_exam.tsv"
EXAM_JSONL = CUR / "paraphrase_exam.jsonl"
MANIFEST = CUR / "DEPTH_MANIFEST.json"
GAME = Path("D:/fsot_training/curriculum/pk_to_g8")

STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "in", "on", "for",
    "and", "or", "what", "which", "who", "how", "many", "do", "does", "did", "you",
    "we", "i", "it", "its", "this", "that", "with", "from", "as", "at", "by", "if",
}


def load_bank(path: Path) -> List[Tuple[str, str, str, str, str]]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        rows.append((parts[0], parts[1], parts[2], parts[3], parts[4]))
    return rows


def templates_for(domain: str, q: str, a: str) -> List[str]:
    """Generate natural questions that are NOT the exact key q."""
    out: List[str] = []
    ql = q.lower().strip()
    al = str(a).lower().strip()

    # generic paraphrases
    out.append(f"What is the answer to: {ql}?")
    out.append(f"Tell me: {ql}")
    out.append(f"Please recall {ql}")

    if domain == "math":
        # "3 plus 4" / "3+4" / "3 times 4"
        m = re.match(r"^(\d+)\s*plus\s*(\d+)$", ql)
        if m:
            x, y = m.group(1), m.group(2)
            out += [
                f"What is {x} plus {y}?",
                f"How much is {x} + {y}?",
                f"Add {x} and {y}.",
                f"{x} + {y} equals what?",
            ]
        m = re.match(r"^(\d+)\+(\d+)$", ql)
        if m:
            x, y = m.group(1), m.group(2)
            out += [f"What is {x} plus {y}?", f"Compute {x}+{y}"]
        m = re.match(r"^(\d+)\s*minus\s*(\d+)$", ql)
        if m:
            x, y = m.group(1), m.group(2)
            out += [f"What is {x} minus {y}?", f"Subtract {y} from {x}."]
        m = re.match(r"^(\d+)\s*times\s*(\d+)$", ql)
        if m:
            x, y = m.group(1), m.group(2)
            out += [f"What is {x} times {y}?", f"Multiply {x} by {y}."]
        m = re.match(r"^(\d+)\s*divided by\s*(\d+)$", ql)
        if m:
            x, y = m.group(1), m.group(2)
            out += [f"What is {x} divided by {y}?", f"Divide {x} by {y}."]
        if ql.startswith("number "):
            n = ql.split()[-1]
            out.append(f"What word means the number {n}?")
        if ql.startswith("make ten with "):
            n = ql.split()[-1]
            out.append(f"What plus {n} makes ten?")

    if domain == "science":
        if "color" in ql:
            subj = ql.replace("color", "").replace("of", "").strip()
            out += [f"What color is {subj}?", f"The color of {subj} is?"]
        if ql.endswith(" need") or " need" in ql:
            out.append(f"What do {ql.replace(' need', '')} need?")
        if ql in ("see with", "hear with", "smell with"):
            sense = ql.split()[0]
            out.append(f"What do we use to {sense}?")
        if "is" in ql.split():
            out.append(f"Complete: {ql} ___")
        out.append(f"According to science class, {ql}?")

    if domain == "literacy":
        if ql.startswith("sight word "):
            w = ql.replace("sight word ", "")
            out.append(f"Is '{w}' a sight word we read?")
            out.append(f"Read this sight word: {w}")
        if ql.startswith("letter starts "):
            w = ql.replace("letter starts ", "")
            out.append(f"What letter starts the word {w}?")
        if ql.startswith("sound of "):
            L = ql.replace("sound of ", "")
            out.append(f"What sound does letter {L} make?")
        if "sentence" in ql:
            out.append(f"In writing class: {ql}?")

    if domain == "vision":
        if "digit" in ql and "name" in ql:
            m = re.search(r"digit\s+(\d+)", ql)
            if m:
                d = m.group(1)
                out += [f"What is the name of digit {d}?", f"Digit {d} is called?"]

    # de-dupe and drop exact key
    seen = set()
    clean = []
    for p in out:
        p2 = re.sub(r"\s+", " ", p.strip())
        if not p2 or p2.lower() == ql or p2.lower() in seen:
            continue
        # never use answer alone as question
        if p2.lower() == al:
            continue
        seen.add(p2.lower())
        clean.append(p2)
    return clean


def build_exam(max_per_domain: int = 120) -> Dict[str, Any]:
    bank = load_bank(BANK)
    if not bank:
        raise FileNotFoundError(f"missing bank {BANK}; run run_curriculum_open.py")

    # taught keys set for held-out check
    keys = {(d, g, q.lower()) for d, g, _, q, _ in bank}

    exam: List[Dict[str, Any]] = []
    per_dom: Counter = Counter()

    # prefer fact rows for paraphrases
    facts = [r for r in bank if r[2] in ("fact", "problem")]
    # stable order
    for domain, grade, kind, q, a in facts:
        if per_dom[domain] >= max_per_domain:
            continue
        # skip tiny/noisy
        if len(q) < 3 or len(str(a)) < 1:
            continue
        paras = templates_for(domain, q, a)
        for p in paras:
            if (domain, grade, p.lower()) in keys:
                continue  # not held-out if already a key
            # also skip if paraphrase equals another key string globally
            if any(p.lower() == k[2] for k in keys):
                continue
            exam.append(
                {
                    "id": f"depth-{len(exam)}",
                    "domain": domain,
                    "grade": grade,
                    "kind": "paraphrase",
                    "question": p,
                    "answer": str(a),
                    "source_key": q,
                    "source_kind": kind,
                }
            )
            per_dom[domain] += 1
            break  # one solid paraphrase per bank fact for balance
        if sum(per_dom.values()) >= max_per_domain * 4:
            break

    CUR.mkdir(parents=True, exist_ok=True)
    with EXAM_TSV.open("w", encoding="utf-8") as f:
        f.write("# domain\tgrade\tquestion\tanswer\tsource_key\n")
        for row in exam:
            f.write(
                f"{row['domain']}\t{row['grade']}\t{row['question']}\t{row['answer']}\t{row['source_key']}\n"
            )
    with EXAM_JSONL.open("w", encoding="utf-8") as f:
        for row in exam:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    man = {
        "n_exam": len(exam),
        "by_domain": dict(per_dom),
        "paths": {"tsv": str(EXAM_TSV), "jsonl": str(EXAM_JSONL)},
        "doctrine": "held-out natural questions over taught STEM/literacy only; no history",
        "claim": "depth = understand paraphrases of known curriculum, not new untaught claims",
    }
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")

    try:
        if Path("D:/").exists():
            GAME.mkdir(parents=True, exist_ok=True)
            for src, name in ((EXAM_TSV, "paraphrase_exam.tsv"), (EXAM_JSONL, "paraphrase_exam.jsonl"), (MANIFEST, "DEPTH_MANIFEST.json")):
                (GAME / name).write_bytes(src.read_bytes())
            man["game_mirror"] = str(GAME)
    except OSError:
        pass

    return man
