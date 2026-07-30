#!/usr/bin/env python3
"""Build FSOT English lexicon from dictionary + thesaurus (WordNet).

Foundation: Princeton WordNet via NLTK — lemma, POS, definition, example usage,
synonyms (thesaurus). Offline, free for research; no cloud LLM required.

Outputs (data/lexicon/):
  en_roles.tsv          word\\trole          — mind loads this for recognition
  en_dictionary.jsonl   full cards          — definition + usage + synonyms
  en_synonyms.tsv       word\\tsyn1,syn2     — thesaurus links
  dictionary_lessons.tsv  for brain-teach   — "X means Y" style facts

Also copies en_roles.tsv into fsot-neuron-zig when present.

  python scripts/build_lexicon_from_dictionary.py
  python scripts/build_lexicon_from_dictionary.py --max-words 25000
  python scripts/build_lexicon_from_dictionary.py --ensure-wordnet
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LEX_DIR = ROOT / "data" / "lexicon"
ZIG_LEX = Path(r"I:\fsot-neuron-zig\data\lexicon")
ZIG_TEACH = Path(r"I:\fsot-neuron-zig\data\curriculum\brain_teach")

# POS → mind role (generation stays on core; extras = recognition + teaching)
POS_ROLE = {
    "n": "what",  # refined to who for persons
    "v": "verb",
    "a": "adj",
    "s": "adj",  # adjective satellite
    "r": "how",  # adverb
}

# Function words (closed class) — English grammar glue
LINKS: List[Tuple[str, str]] = [
    ("the", "link"), ("a", "link"), ("an", "link"), ("and", "link"), ("or", "link"),
    ("to", "link"), ("of", "link"), ("in", "link"), ("on", "link"), ("at", "link"),
    ("with", "link"), ("for", "link"), ("from", "link"), ("by", "link"), ("as", "link"),
    ("is", "link"), ("are", "link"), ("was", "link"), ("were", "link"), ("be", "link"),
    ("been", "link"), ("being", "link"), ("am", "link"), ("not", "link"), ("no", "link"),
    ("yes", "link"), ("but", "link"), ("if", "link"), ("then", "link"), ("so", "link"),
    ("that", "link"), ("this", "link"), ("these", "link"), ("those", "link"),
    ("my", "link"), ("your", "link"), ("his", "link"), ("her", "link"), ("its", "link"),
    ("our", "link"), ("their", "link"), ("can", "link"), ("will", "link"), ("would", "link"),
    ("could", "link"), ("should", "link"), ("may", "link"), ("might", "link"),
    ("do", "link"), ("does", "link"), ("did", "link"), ("have", "link"), ("has", "link"),
    ("had", "link"), ("about", "link"), ("into", "link"), ("over", "link"), ("under", "link"),
    ("up", "link"), ("down", "link"), ("out", "link"), ("off", "link"), ("than", "link"),
    ("too", "link"), ("very", "link"), ("just", "link"), ("also", "link"), ("only", "link"),
]

PRONOUNS_WHO = [
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "someone", "anyone", "everyone", "nobody", "who", "whom", "whose",
]

WORD_RE = re.compile(r"^[a-z][a-z\-']{0,22}$")


def ensure_wordnet() -> None:
    import nltk

    try:
        from nltk.corpus import wordnet as wn

        _ = wn.synsets("test")
    except LookupError:
        print("Downloading WordNet…", flush=True)
        nltk.download("wordnet", quiet=False)
        nltk.download("omw-1.4", quiet=True)


def is_person_noun(syn) -> bool:
    """WordNet hypernym walk: person / human / living_thing person-like."""
    try:
        for path in syn.hypernym_paths():
            for s in path:
                name = s.name().lower()
                if name.startswith("person.") or name.startswith("human."):
                    return True
                if "individual.n." in name:
                    return True
    except Exception:
        pass
    return False


def clean_lemma(name: str) -> Optional[str]:
    # WordNet: dog.n.01 → dog; multi-word use first token or join with space
    base = name.split(".", 1)[0].replace("_", " ").strip().lower()
    if " " in base:
        # multi-word: keep as hyphenated single token for codec (max 24)
        base = base.replace(" ", "-")
    if not WORD_RE.match(base):
        return None
    if len(base) > 24:
        return None
    # skip pure function-looking if weird
    if base in ("s", "o", "x"):
        return None
    return base


def role_for_synset(syn) -> str:
    pos = syn.pos()
    if pos == "n":
        return "who" if is_person_noun(syn) else "what"
    return POS_ROLE.get(pos, "what")


def build_from_wordnet(
    *,
    max_words: int,
    min_len: int,
    max_def: int,
) -> Tuple[Dict[str, str], List[dict], Dict[str, List[str]]]:
    from nltk.corpus import wordnet as wn

    roles: Dict[str, str] = {}
    cards: List[dict] = []
    syn_map: Dict[str, Set[str]] = defaultdict(set)

    # Priority buckets so common structure fills first
    # 1) links + pronouns  2) shorter lemmas  3) rest
    for w, r in LINKS:
        roles[w] = r
    for w in PRONOUNS_WHO:
        roles.setdefault(w, "who")

    # Collect candidates with a simple usefulness score
    scored: List[Tuple[int, str, str, object]] = []
    for syn in wn.all_synsets():
        role = role_for_synset(syn)
        for lem in syn.lemmas():
            w = clean_lemma(lem.name())
            if w is None or len(w) < min_len:
                continue
            # prefer shorter, more common-looking (no hyphens heavy)
            score = 100 - len(w)
            if "-" in w:
                score -= 20
            if lem.count() and lem.count() > 0:
                score += min(lem.count(), 50)
            scored.append((score, w, role, syn))

    scored.sort(key=lambda x: -x[0])
    seen_card: Set[str] = set()

    for score, w, role, syn in scored:
        if w not in roles:
            if len(roles) >= max_words:
                break
            roles[w] = role

        # one definition card per word (first best sense)
        if w in seen_card:
            continue
        seen_card.add(w)
        definition = (syn.definition() or "").strip()
        if len(definition) > max_def:
            definition = definition[: max_def - 1] + "…"
        examples = list(syn.examples() or [])
        usage = examples[0].strip() if examples else ""
        if len(usage) > 160:
            usage = usage[:159] + "…"
        # thesaurus: synonyms from same synset
        syns: List[str] = []
        for lem in syn.lemmas():
            sw = clean_lemma(lem.name())
            if sw and sw != w and sw not in syns:
                syns.append(sw)
            if len(syns) >= 8:
                break
        # also antonyms lightly
        ants: List[str] = []
        for lem in syn.lemmas():
            for ant in lem.antonyms():
                aw = clean_lemma(ant.name())
                if aw and aw not in ants:
                    ants.append(aw)

        for s in syns:
            syn_map[w].add(s)
            syn_map[s].add(w)

        cards.append(
            {
                "word": w,
                "role": roles.get(w, role),
                "pos": syn.pos(),
                "definition": definition,
                "usage": usage,
                "synonyms": syns,
                "antonyms": ants[:4],
                "source": "wordnet",
                "synset": syn.name(),
            }
        )
        if len(roles) >= max_words and len(cards) >= max_words:
            break

    syn_out = {k: sorted(v)[:12] for k, v in syn_map.items() if v}
    return roles, cards, syn_out


def write_outputs(
    roles: Dict[str, str],
    cards: List[dict],
    syn_map: Dict[str, List[str]],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # en_roles.tsv
    tsv = out_dir / "en_roles.tsv"
    lines = [
        "# word\trole",
        "# Built from Princeton WordNet (dictionary + thesaurus).",
        "# roles: who verb what where when how adj link",
        "# Generation (TTS templates) uses core embedded words; this file expands recognition + teaching.",
    ]
    # stable order: by role then word
    role_order = ["link", "who", "verb", "what", "where", "when", "how", "adj"]
    by_role: Dict[str, List[str]] = defaultdict(list)
    for w, r in roles.items():
        by_role[r].append(w)
    for r in role_order:
        for w in sorted(by_role.get(r, [])):
            lines.append(f"{w}\t{r}")
    # any leftover roles
    for r, ws in sorted(by_role.items()):
        if r in role_order:
            continue
        for w in sorted(ws):
            lines.append(f"{w}\t{r}")
    tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # dictionary jsonl
    dict_path = out_dir / "en_dictionary.jsonl"
    with dict_path.open("w", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # thesaurus
    syn_path = out_dir / "en_synonyms.tsv"
    syn_lines = ["# word\tsynonyms (comma-separated)"]
    for w in sorted(syn_map.keys()):
        syn_lines.append(f"{w}\t{','.join(syn_map[w])}")
    syn_path.write_text("\n".join(syn_lines) + "\n", encoding="utf-8")

    # definition lessons for brain-teach (compact subset: words with short defs)
    lessons = out_dir / "dictionary_lessons.tsv"
    less_lines = [
        "# question\tanswer\tfact",
        "# Dictionary foundation lessons for fsot_mind brain-learn",
    ]
    n_less = 0
    for c in cards:
        if n_less >= 400:
            break
        w = c["word"]
        d = c.get("definition") or ""
        if len(d) < 8 or len(d) > 100:
            continue
        # answer = first content word of definition or "defined"
        ans = re.sub(r"[^a-z\- ]", "", d.lower()).split()
        ans = ans[0] if ans else "defined"
        if len(ans) > 24:
            ans = ans[:24]
        fact = f"{w} means {d}."
        if c.get("usage"):
            fact = f"{w} means {d}. Example: {c['usage']}"
        if len(fact) > 180:
            fact = fact[:179] + "…"
        q = f"what does {w} mean"
        less_lines.append(f"{q}\t{ans}\t{fact}")
        n_less += 1
    lessons.write_text("\n".join(less_lines) + "\n", encoding="utf-8")

    # MANIFEST
    counts = defaultdict(int)
    for r in roles.values():
        counts[r] += 1
    man = {
        "source": "Princeton WordNet via NLTK",
        "n_roles": len(roles),
        "n_dictionary_cards": len(cards),
        "n_synonym_entries": len(syn_map),
        "n_definition_lessons": n_less,
        "by_role": dict(counts),
        "doctrine": "Dictionary/thesaurus foundation; TTS generation stays on core grammar templates; extras = recognition + teaching.",
        "files": [
            "en_roles.tsv",
            "en_dictionary.jsonl",
            "en_synonyms.tsv",
            "dictionary_lessons.tsv",
        ],
    }
    (out_dir / "DICTIONARY_MANIFEST.json").write_text(
        json.dumps(man, indent=2), encoding="utf-8"
    )
    print(json.dumps(man, indent=2), flush=True)
    print(f"Wrote {tsv}", flush=True)
    print(f"Wrote {dict_path} ({len(cards)} cards)", flush=True)
    print(f"Wrote {syn_path}", flush=True)
    print(f"Wrote {lessons} ({n_less} lessons)", flush=True)


def copy_to_zig(out_dir: Path) -> None:
    if not ZIG_LEX.parent.exists():
        print("Zig repo not found; skip copy", flush=True)
        return
    ZIG_LEX.mkdir(parents=True, exist_ok=True)
    for name in (
        "en_roles.tsv",
        "en_dictionary.jsonl",
        "en_synonyms.tsv",
        "dictionary_lessons.tsv",
        "DICTIONARY_MANIFEST.json",
    ):
        src = out_dir / name
        if src.is_file():
            dst = ZIG_LEX / name
            dst.write_bytes(src.read_bytes())
            print(f"Copied → {dst}", flush=True)
    # merge dictionary lessons into brain_teach if present
    if ZIG_TEACH.exists():
        dl = out_dir / "dictionary_lessons.tsv"
        if dl.is_file():
            # append unique lines to lessons.tsv (cap)
            dest = ZIG_TEACH / "lessons.tsv"
            existing = dest.read_text(encoding="utf-8", errors="replace") if dest.is_file() else ""
            add = []
            for line in dl.read_text(encoding="utf-8").splitlines():
                if not line or line.startswith("#"):
                    continue
                if line not in existing:
                    add.append(line)
            if add:
                with dest.open("a", encoding="utf-8") as f:
                    f.write("\n# --- dictionary foundation ---\n")
                    f.write("\n".join(add[:80]) + "\n")
                print(f"Appended {min(80, len(add))} dictionary lessons → {dest}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build lexicon from WordNet dictionary/thesaurus")
    ap.add_argument("--max-words", type=int, default=20000, help="cap on en_roles.tsv size")
    ap.add_argument("--min-len", type=int, default=2)
    ap.add_argument("--max-def", type=int, default=200)
    ap.add_argument("--ensure-wordnet", action="store_true", help="nltk.download wordnet if missing")
    ap.add_argument("--no-zig-copy", action="store_true")
    args = ap.parse_args()

    if args.ensure_wordnet:
        ensure_wordnet()
    else:
        try:
            ensure_wordnet()
        except Exception as e:
            print(f"WordNet setup issue: {e}", flush=True)
            print("Retry with: python scripts/build_lexicon_from_dictionary.py --ensure-wordnet", flush=True)
            return 1

    print("Building from WordNet…", flush=True)
    roles, cards, syn_map = build_from_wordnet(
        max_words=args.max_words,
        min_len=args.min_len,
        max_def=args.max_def,
    )
    write_outputs(roles, cards, syn_map, LEX_DIR)
    if not args.no_zig_copy:
        copy_to_zig(LEX_DIR)
    print("Done. Rebuild mind and run: fsot_mind english", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
