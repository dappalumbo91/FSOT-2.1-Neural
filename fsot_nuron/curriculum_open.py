"""
Open PK→K→G1 curriculum packer — public knowledge, not hand-toy packs.

Sources (no paywall, no proprietary textbooks):
  - Arithmetic tables 0–10 / count 0–20  → pure math (public domain)
  - Dolch sight-word lists (pre-primer, primer, 1st) → widely published public lists
  - Letter–sound phonics (standard English mappings) → public educational practice
  - Core science / body / safety facts → short seed OERs (same spirit as public primers)
  - MNIST digit labels (local Kaggle CSV if present) → open digit vision pack

Outputs (under data/curriculum/pk_k_g1/):
  facts.jsonl, problems.jsonl, bank.tsv, MANIFEST.json

bank.tsv columns (tab-separated, # comments ok):
  domain  grade  kind  question  answer  [id]

Zig grade ladder loads bank.tsv when present; otherwise falls back to embedded seed.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .paths import DATA

CUR_DIR = DATA / "curriculum" / "pk_k_g1"
FACTS_PATH = CUR_DIR / "facts.jsonl"
PROBLEMS_PATH = CUR_DIR / "problems.jsonl"
BANK_PATH = CUR_DIR / "bank.tsv"
MANIFEST_PATH = CUR_DIR / "MANIFEST.json"

# ---------------------------------------------------------------------------
# Number words (English; public)
# ---------------------------------------------------------------------------
NUM = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
}

# Dolch sight words — classic public lists used in US elementary literacy.
# (Pre-primer, Primer, First Grade; no proper nouns.)
DOLCH_PREPRIMER = [
    "a", "and", "away", "big", "blue", "can", "come", "down", "find", "for",
    "funny", "go", "help", "here", "I", "in", "is", "it", "jump", "little",
    "look", "make", "me", "my", "not", "one", "play", "red", "run", "said",
    "see", "the", "three", "to", "two", "up", "we", "where", "yellow", "you",
]
DOLCH_PRIMER = [
    "all", "am", "are", "at", "ate", "be", "black", "brown", "but", "came",
    "did", "do", "eat", "four", "get", "good", "have", "he", "into", "like",
    "must", "new", "no", "now", "on", "our", "out", "please", "pretty", "ran",
    "ride", "saw", "say", "she", "so", "soon", "that", "there", "they", "this",
    "too", "under", "want", "was", "well", "went", "what", "white", "who", "will",
    "with", "yes",
]
DOLCH_FIRST = [
    "after", "again", "an", "any", "as", "ask", "by", "could", "every", "fly",
    "from", "give", "giving", "had", "has", "her", "him", "his", "how", "just",
    "know", "let", "live", "may", "of", "old", "once", "open", "over", "put",
    "round", "some", "stop", "take", "thank", "them", "then", "think", "walk",
    "were", "when",
]

# Letter → common first sound (early phonics; public practice)
LETTER_SOUND = {
    "a": "ah",
    "b": "buh",
    "c": "kuh",
    "d": "duh",
    "e": "eh",
    "f": "fuh",
    "g": "guh",
    "h": "huh",
    "i": "ih",
    "j": "juh",
    "k": "kuh",
    "l": "luh",
    "m": "muh",
    "n": "nuh",
    "o": "ah",
    "p": "puh",
    "q": "kwuh",
    "r": "ruh",
    "s": "sss",
    "t": "tuh",
    "u": "uh",
    "v": "vuh",
    "w": "wuh",
    "x": "ks",
    "y": "yuh",
    "z": "zzz",
}

LETTER_STARTS = {
    "a": "apple",
    "b": "ball",
    "c": "cat",
    "d": "dog",
    "e": "egg",
    "f": "fish",
    "g": "goat",
    "h": "hat",
    "i": "igloo",
    "j": "jam",
    "k": "kite",
    "l": "leaf",
    "m": "moon",
    "n": "nest",
    "o": "octopus",
    "p": "pig",
    "q": "queen",
    "r": "rain",
    "s": "sun",
    "t": "tree",
    "u": "umbrella",
    "v": "van",
    "w": "water",
    "x": "xray",
    "y": "yarn",
    "z": "zoo",
}

# Short science / body / safety / time facts (primer-style public knowledge)
SCIENCE_FACTS: List[Tuple[str, str, str, str, str, str]] = [
    # grade, id, fact, question, answer, alt_q
    ("preschool", "pk-sky", "The sky is blue on a sunny day.", "sky color", "blue", "color of sky"),
    ("preschool", "pk-grass", "Grass is green.", "grass color", "green", "color of grass"),
    ("preschool", "pk-sun-day", "The sun is out in the day.", "sun when", "day", "when is sun out"),
    ("preschool", "pk-moon-night", "The moon is out at night.", "moon when", "night", "when is moon out"),
    ("preschool", "pk-eyes", "We see with our eyes.", "see with", "eyes", "what sees"),
    ("preschool", "pk-ears", "We hear with our ears.", "hear with", "ears", "what hears"),
    ("preschool", "pk-nose", "We smell with our nose.", "smell with", "nose", "what smells"),
    ("preschool", "pk-hands", "We touch with our hands.", "touch with", "hands", "what touches"),
    ("preschool", "pk-dog", "A dog is an animal.", "dog is", "animal", "is dog animal"),
    ("preschool", "pk-cat", "A cat is an animal.", "cat is", "animal", "is cat animal"),
    ("preschool", "pk-bird", "A bird can fly.", "bird can", "fly", "what birds do"),
    ("preschool", "pk-fish", "A fish lives in water.", "fish lives", "water", "where fish live"),
    ("preschool", "pk-apple-red", "An apple can be red.", "apple color", "red", "color of apple"),
    ("preschool", "pk-water-drink", "We drink water.", "we drink", "water", "what do we drink"),
    ("preschool", "pk-circle", "A circle is round.", "round shape", "circle", "what is round"),
    ("kindergarten", "k-plant-sun", "Plants need sun to grow.", "plants need", "sun", "what plants need"),
    ("kindergarten", "k-plant-water", "Plants need water to grow.", "plants drink", "water", "plants water"),
    ("kindergarten", "k-people-water", "People need water to live.", "people need", "water", "what people need"),
    ("kindergarten", "k-people-food", "People need food to live.", "people eat need", "food", "what people eat need"),
    ("kindergarten", "k-people-air", "People need air to breathe.", "people breathe", "air", "what people breathe"),
    ("kindergarten", "k-stop", "Stop at a red light.", "red light", "stop", "red light do"),
    ("kindergarten", "k-go-green", "Go at a green light.", "green light", "go", "green light do"),
    ("kindergarten", "k-share", "Friends share.", "friends do", "share", "what friends do"),
    ("kindergarten", "k-winter", "Winter is cold.", "winter is", "cold", "is winter cold"),
    ("kindergarten", "k-summer", "Summer is hot.", "summer is", "hot", "is summer hot"),
    ("kindergarten", "k-rain-wet", "Rain makes things wet.", "rain makes", "wet", "what rain does"),
    ("kindergarten", "k-square", "A square has four sides.", "square sides", "four", "how many sides square"),
    ("kindergarten", "k-triangle", "A triangle has three sides.", "triangle sides", "three", "how many sides triangle"),
    ("kindergarten", "k-book", "We read a book.", "we read", "book", "what do we read"),
    ("kindergarten", "k-write", "We write with a pencil.", "write with", "pencil", "what writes"),
    ("kindergarten", "k-day-sun", "Day is when the sun is out.", "day means", "sun", "day has"),
    ("grade1", "g1-earth", "Earth is a planet we live on.", "we live on", "earth", "home planet"),
    ("grade1", "g1-map", "A map shows where places are.", "shows places", "map", "find places tool"),
    ("grade1", "g1-living-water", "Living things need water.", "living need", "water", "living things need"),
    ("grade1", "g1-living-air", "Living things need air.", "living need air", "air", "living things air"),
    ("grade1", "g1-solid", "Ice is solid water.", "ice is", "solid", "ice form"),
    ("grade1", "g1-liquid", "Water can be liquid.", "water form liquid", "liquid", "liquid water"),
    ("grade1", "g1-gas", "Steam is water as gas.", "steam is", "gas", "steam form"),
    ("grade1", "g1-plant-day", "Plants grow better in the day.", "plants grow when", "day", "when plants grow"),
    ("grade1", "g1-magnet", "A magnet pulls iron.", "magnet pulls", "iron", "what magnet pulls"),
    ("grade1", "g1-shadow", "A shadow needs light.", "shadow needs", "light", "what shadow needs"),
    ("grade1", "g1-seed", "A seed can grow into a plant.", "seed grows", "plant", "seed becomes"),
    ("grade1", "g1-week", "A week has seven days.", "days in week", "seven", "how many days week"),
    ("grade1", "g1-month-approx", "A year has twelve months.", "months in year", "twelve", "how many months year"),
]

RELATIONS: List[Tuple[str, str, str, str, str]] = [
    # grade, src, rel, dst, cue
    ("preschool", "sun", "out_in", "day", "sun out_in"),
    ("preschool", "moon", "out_in", "night", "moon out_in"),
    ("preschool", "sky", "color", "blue", "sky color_rel"),
    ("preschool", "grass", "color", "green", "grass color_rel"),
    ("preschool", "see", "uses", "eyes", "see uses"),
    ("preschool", "hear", "uses", "ears", "hear uses"),
    ("preschool", "smell", "uses", "nose", "smell uses"),
    ("preschool", "dog", "is_a", "animal", "dog is_a"),
    ("preschool", "cat", "is_a", "animal", "cat is_a"),
    ("preschool", "bird", "can", "fly", "bird can_rel"),
    ("preschool", "fish", "lives_in", "water", "fish lives_in"),
    ("preschool", "circle", "shape", "round", "circle shape_rel"),
    ("kindergarten", "plant", "needs", "sun", "plant needs"),
    ("kindergarten", "plant", "needs_water", "water", "plant needs_water"),
    ("kindergarten", "people", "needs", "water", "people needs"),
    ("kindergarten", "people", "needs_food", "food", "people needs_food"),
    ("kindergarten", "people", "needs_air", "air", "people needs_air"),
    ("kindergarten", "red_light", "means", "stop", "red_light means"),
    ("kindergarten", "green_light", "means", "go", "green_light means"),
    ("kindergarten", "friend", "does", "share", "friend does"),
    ("kindergarten", "winter", "is", "cold", "winter is_rel"),
    ("kindergarten", "summer", "is", "hot", "summer is_rel"),
    ("kindergarten", "read", "uses", "book", "read uses"),
    ("kindergarten", "write", "uses", "pencil", "write uses"),
    ("kindergarten", "square", "sides", "four", "square sides_rel"),
    ("kindergarten", "triangle", "sides", "three", "triangle sides_rel"),
    ("grade1", "earth", "is_a", "planet", "earth is_a"),
    ("grade1", "map", "shows", "place", "map shows"),
    ("grade1", "living", "needs", "water", "living needs"),
    ("grade1", "ice", "is", "solid", "ice is_rel"),
    ("grade1", "steam", "is", "gas", "steam is_rel"),
    ("grade1", "plant", "grows_in", "day", "plant grows_in"),
    ("grade1", "magnet", "pulls", "iron", "magnet pulls_rel"),
    ("grade1", "shadow", "needs", "light", "shadow needs_rel"),
    ("grade1", "seed", "becomes", "plant", "seed becomes"),
    ("grade1", "week", "has_days", "seven", "week has_days"),
    ("grade1", "year", "has_months", "twelve", "year has_months"),
    ("grade1", "sentence", "starts", "capital", "sentence starts_rel"),
    ("grade1", "sentence", "ends", "period", "sentence ends_rel"),
]


def _kw(*words: str) -> List[str]:
    out = []
    for w in words:
        w = re.sub(r"[^a-z0-9']", "", w.lower())
        if w and w not in out:
            out.append(w)
    return out


def _fact(
    grade: str,
    domain: str,
    fid: str,
    fact: str,
    question: str,
    answer: str,
    alt_q: str = "",
    keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "id": fid,
        "grade": grade,
        "domain": domain,
        "fact": fact,
        "question": question,
        "answer": answer.lower() if answer.isalpha() or answer.isdigit() else answer,
        "keywords": keywords or _kw(answer, *question.split(), *fact.split()[:6]),
        "source": "open_curriculum",
    }
    if alt_q:
        row["alt_q"] = alt_q
    return row


def _problem(
    grade: str,
    domain: str,
    pid: str,
    prompt: str,
    answer: str,
    kind: str = "fact",
) -> Dict[str, Any]:
    return {
        "id": pid,
        "grade": grade,
        "domain": domain,
        "prompt": prompt,
        "answer": answer,
        "kind": kind,
        "keywords": _kw(answer, *prompt.split()[:8]),
        "source": "open_curriculum",
    }


def build_math() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Tuple[str, str, str, str, str]]]:
    """Full public-domain arithmetic tables + count/compare/make-10."""
    facts: List[Dict[str, Any]] = []
    problems: List[Dict[str, Any]] = []
    bank: List[Tuple[str, str, str, str, str]] = []  # domain, grade, kind, q, a

    def put(grade: str, q: str, a: str, kind: str = "fact", fid: str = "") -> None:
        bank.append(("math", grade, kind, q, a))
        if kind == "fact":
            facts.append(
                _fact(
                    grade,
                    "math",
                    fid or f"math-{grade}-{len(facts)}",
                    f"{q} is {a}.",
                    q,
                    a,
                    keywords=_kw(a, *q.split()),
                )
            )
        else:
            problems.append(_problem(grade, "math", fid or f"math-p-{len(problems)}", q, a, kind=kind))

    # Count: name of n, next/prev
    for n in range(0, 21):
        w = NUM[n]
        grade = "preschool" if n <= 5 else ("kindergarten" if n <= 10 else "grade1")
        put(grade, f"number {n}", w, "fact", f"count-name-{n}")
        put(grade, f"count word {w}", str(n), "fact", f"count-digit-{n}")
        if n < 20:
            put(grade, f"after {w}", NUM[n + 1], "fact", f"count-after-{n}")
            put(grade, f"next after {n}", str(n + 1), "problem", f"count-next-{n}")
        if n > 0:
            put(grade, f"before {w}", NUM[n - 1], "fact", f"count-before-{n}")

    # Addition 0–10 (sum ≤ 20)
    for a in range(0, 11):
        for b in range(0, 11):
            s = a + b
            if s > 20:
                continue
            wa, wb, ws = NUM[a], NUM[b], NUM[s]
            grade = "preschool" if s <= 5 and a <= 3 and b <= 3 else (
                "kindergarten" if s <= 10 else "grade1"
            )
            put(grade, f"{a} plus {b}", ws, "fact", f"add-{a}-{b}")
            put(grade, f"{wa} and {wb}", ws, "fact", f"addw-{a}-{b}")
            put(grade, f"{a}+{b}", str(s), "problem", f"addp-{a}-{b}")
            # also word answer for digit prompt on small set
            if s <= 10:
                put(grade, f"{a} plus {b} word", ws, "problem", f"addpw-{a}-{b}")

    # Subtraction a−b ≥ 0, a ≤ 10
    for a in range(0, 11):
        for b in range(0, a + 1):
            d = a - b
            wa, wb, wd = NUM[a], NUM[b], NUM[d]
            grade = "preschool" if a <= 5 else ("kindergarten" if a <= 8 else "grade1")
            put(grade, f"{a} minus {b}", wd, "fact", f"sub-{a}-{b}")
            put(grade, f"{wa} take away {wb}", wd, "fact", f"subw-{a}-{b}")
            put(grade, f"{a}-{b}", str(d), "problem", f"subp-{a}-{b}")

    # Make ten
    for a in range(0, 11):
        need = 10 - a
        put("kindergarten" if a <= 5 else "grade1", f"make ten with {a}", NUM[need], "fact", f"make10-{a}")
        put("kindergarten" if a <= 5 else "grade1", f"{a} and what make ten", NUM[need], "problem", f"make10p-{a}")

    # Compare
    for a in range(0, 11):
        for b in range(0, 11):
            if a == b:
                continue
            bigger = a if a > b else b
            smaller = a if a < b else b
            grade = "kindergarten" if max(a, b) <= 5 else "grade1"
            put(grade, f"bigger {a} or {b}", NUM[bigger], "fact", f"cmp-big-{a}-{b}")
            put(grade, f"smaller {a} or {b}", NUM[smaller], "fact", f"cmp-sm-{a}-{b}")

    # Concept facts
    put("grade1", "add means", "together", "fact", "g1-add-means")
    put("grade1", "subtract means", "take", "fact", "g1-sub-means")
    put("preschool", "one and one", "two", "fact", "pk-1-1")
    put("kindergarten", "two and one", "three", "fact", "k-2-1")
    put("grade1", "two and three", "five", "fact", "g1-2-3")
    put("grade1", "five and five", "ten", "fact", "g1-5-5")

    # Word problems (transfer-style prompts matching taught keys where possible)
    problems.append(
        _problem("preschool", "math", "wp-apples", "one apple and one apple how many", "two", "word")
    )
    bank.append(("math", "preschool", "problem", "one and one", "two"))
    problems.append(
        _problem("kindergarten", "math", "wp-birds", "two birds and one bird how many", "three", "word")
    )
    bank.append(("math", "kindergarten", "problem", "two and one", "three"))
    problems.append(
        _problem("grade1", "math", "wp-blocks", "three plus two equals what", "five", "word")
    )
    bank.append(("math", "grade1", "problem", "3 plus 2", "five"))
    bank.append(("math", "grade1", "problem", "two and three", "five"))

    return facts, problems, bank


def build_literacy() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Tuple[str, str, str, str, str]]]:
    facts: List[Dict[str, Any]] = []
    problems: List[Dict[str, Any]] = []
    bank: List[Tuple[str, str, str, str, str]] = []

    # Letter starts + sounds
    for letter, word in LETTER_STARTS.items():
        grade = "preschool" if letter <= "m" else "kindergarten"
        q = f"letter starts {word}"
        facts.append(
            _fact(grade, "literacy", f"letter-start-{letter}", f"{letter.upper()} starts {word}.", q, letter, f"what starts {word}")
        )
        bank.append(("literacy", grade, "fact", q, letter))
        bank.append(("literacy", grade, "fact", f"what starts {word}", letter))
        sound = LETTER_SOUND[letter]
        qs = f"sound of {letter}"
        facts.append(
            _fact(grade, "literacy", f"letter-sound-{letter}", f"Letter {letter} sounds like {sound}.", qs, sound)
        )
        bank.append(("literacy", grade, "fact", qs, sound))

    # Dolch: word is a sight word / read word
    for grade, words in (
        ("preschool", DOLCH_PREPRIMER),
        ("kindergarten", DOLCH_PRIMER),
        ("grade1", DOLCH_FIRST),
    ):
        for w in words:
            wl = w.lower()
            q = f"sight word {wl}"
            facts.append(
                _fact(
                    grade,
                    "literacy",
                    f"dolch-{grade}-{wl}",
                    f"{w} is a sight word.",
                    q,
                    wl,
                    keywords=_kw(wl, "sight", "word", "read"),
                )
            )
            bank.append(("literacy", grade, "fact", q, wl))
            # read cue
            bank.append(("literacy", grade, "fact", f"read {wl}", wl))

    # Sentence mechanics
    for grade, q, a, fact, fid in (
        ("grade1", "sentence starts", "capital", "A sentence starts with a capital.", "g1-cap"),
        ("grade1", "sentence ends", "period", "A sentence ends with a period.", "g1-period"),
        ("grade1", "question ends", "mark", "A question ends with a question mark.", "g1-qmark"),
        ("kindergarten", "we read", "book", "We read a book.", "k-book"),
        ("kindergarten", "write with", "pencil", "We write with a pencil.", "k-pencil"),
        ("preschool", "we see words", "eyes", "We see words with our eyes.", "pk-see-words"),
    ):
        facts.append(_fact(grade, "literacy", fid, fact, q, a))
        bank.append(("literacy", grade, "fact", q, a))
        problems.append(_problem(grade, "literacy", f"p-{fid}", q, a))

    return facts, problems, bank


def build_science() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Tuple[str, str, str, str, str]]]:
    facts: List[Dict[str, Any]] = []
    problems: List[Dict[str, Any]] = []
    bank: List[Tuple[str, str, str, str, str]] = []

    for grade, fid, fact, q, a, alt in SCIENCE_FACTS:
        facts.append(_fact(grade, "science", fid, fact, q, a, alt))
        bank.append(("science", grade, "fact", q, a))
        if alt:
            bank.append(("science", grade, "fact", alt, a))
        problems.append(_problem(grade, "science", f"p-{fid}", alt or q, a))

    for grade, src, rel, dst, cue in RELATIONS:
        bank.append(("science", grade, "rel", cue, dst))
        bank.append(("science", grade, "rel", f"{src} {rel}", dst))

    # Multi-hop path transfer keys (must already be taught as fact/rel)
    paths = [
        ("preschool", "sun when", "day"),
        ("preschool", "see with", "eyes"),
        ("preschool", "dog is", "animal"),
        ("kindergarten", "plants need", "sun"),
        ("kindergarten", "red light", "stop"),
        ("kindergarten", "friends do", "share"),
        ("grade1", "we live on", "earth"),
        ("grade1", "shows places", "map"),
        ("grade1", "living need", "water"),
        ("grade1", "plants grow when", "day"),
        ("grade1", "ice is", "solid"),
        ("grade1", "days in week", "seven"),
    ]
    for grade, cue, ans in paths:
        bank.append(("science", grade, "path", cue, ans))

    return facts, problems, bank


def build_vision_meta() -> List[Dict[str, Any]]:
    """Digit identity lessons (text side); Zig vision probe uses features separately."""
    rows = []
    for d in range(10):
        rows.append(
            _fact(
                "kindergarten" if d <= 5 else "grade1",
                "vision",
                f"digit-name-{d}",
                f"The digit {d} is called {NUM[d]}.",
                f"digit {d} name",
                NUM[d],
                f"name of digit {d}",
                keywords=_kw(str(d), NUM[d], "digit", "number"),
            )
        )
    return rows


def _dedupe_bank(rows: List[Tuple[str, str, str, str, str]]) -> List[Tuple[str, str, str, str, str]]:
    seen = set()
    out = []
    for domain, grade, kind, q, a in rows:
        key = (domain, grade, kind, q.lower().strip(), a.lower().strip())
        if key in seen:
            continue
        seen.add(key)
        out.append((domain, grade, kind, q.strip(), a.strip().lower() if a.isalpha() else a.strip()))
    return out


def build_all(merge_existing: bool = True) -> Dict[str, Any]:
    CUR_DIR.mkdir(parents=True, exist_ok=True)

    facts: List[Dict[str, Any]] = []
    problems: List[Dict[str, Any]] = []
    bank: List[Tuple[str, str, str, str, str]] = []

    for builder in (build_math, build_literacy, build_science):
        f, p, b = builder()
        facts.extend(f)
        problems.extend(p)
        bank.extend(b)

    facts.extend(build_vision_meta())
    for d in range(10):
        bank.append(
            (
                "vision",
                "kindergarten" if d <= 5 else "grade1",
                "fact",
                f"digit {d} name",
                NUM[d],
            )
        )
        bank.append(
            (
                "vision",
                "kindergarten" if d <= 5 else "grade1",
                "fact",
                f"name of digit {d}",
                NUM[d],
            )
        )

    if merge_existing:
        # keep any hand/Ollama rows not colliding on id
        existing_f = []
        if FACTS_PATH.is_file():
            for line in FACTS_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    existing_f.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        ids = {str(x.get("id")) for x in facts}
        for row in existing_f:
            rid = str(row.get("id") or "")
            if rid and rid not in ids:
                facts.append(row)
                ids.add(rid)
                if row.get("question") and row.get("answer"):
                    bank.append(
                        (
                            str(row.get("domain") or "science"),
                            str(row.get("grade") or "preschool"),
                            "fact",
                            str(row["question"]),
                            str(row["answer"]),
                        )
                    )

    bank = _dedupe_bank(bank)

    # write JSONL
    with FACTS_PATH.open("w", encoding="utf-8") as f:
        for row in facts:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
    with PROBLEMS_PATH.open("w", encoding="utf-8") as f:
        for row in problems:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    # bank.tsv for Zig
    with BANK_PATH.open("w", encoding="utf-8") as f:
        f.write("# domain\tgrade\tkind\tquestion\tanswer\n")
        f.write("# Open PK-K-G1 curriculum bank — generated by curriculum_open.py\n")
        for domain, grade, kind, q, a in bank:
            # tabs cannot appear in fields
            q = q.replace("\t", " ").replace("\n", " ")
            a = a.replace("\t", " ").replace("\n", " ")
            f.write(f"{domain}\t{grade}\t{kind}\t{q}\t{a}\n")

    by_domain = Counter(d for d, _, _, _, _ in bank)
    by_grade = Counter(g for _, g, _, _, _ in bank)
    by_kind = Counter(k for _, _, k, _, _ in bank)

    manifest = {
        "n_facts_jsonl": len(facts),
        "n_problems_jsonl": len(problems),
        "n_bank_rows": len(bank),
        "by_domain": dict(by_domain),
        "by_grade": dict(by_grade),
        "by_kind": dict(by_kind),
        "paths": {
            "facts": str(FACTS_PATH),
            "problems": str(PROBLEMS_PATH),
            "bank": str(BANK_PATH),
        },
        "sources": [
            "public-domain arithmetic tables 0-10 / count 0-20",
            "Dolch pre-primer + primer + first grade sight words",
            "standard English letter-sound phonics mappings",
            "primer-style science/body/safety facts (OER spirit)",
            "digit name map 0-9 (vision label side)",
        ],
        "doctrine": "download/generate open curriculum → bank.tsv → Zig teach/quiz; ≥95% domain gates",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def report() -> Dict[str, Any]:
    if MANIFEST_PATH.is_file():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return build_all()
