#!/usr/bin/env python3
"""Build pointed language-depth bank from dictionary cards.

Questions the mind must answer after teaching (not mere echo):
  - is X a verb? / is X a noun?
  - what does X mean? (short gloss)
  - X is a? (role: verb/what/who/adj/how)

  python scripts/build_language_depth_bank.py
  → data/lexicon/en_depth.tsv + copy to fsot-neuron-zig
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEX = ROOT / "data" / "lexicon"
ZIG = Path(r"I:\fsot-neuron-zig\data\lexicon")

STOP = {
    "a", "an", "the", "of", "or", "and", "to", "in", "on", "for", "with", "as",
    "by", "from", "that", "which", "who", "whom", "this", "these", "those",
    "is", "are", "was", "were", "be", "been", "being", "not", "no", "used",
    "having", "having", "very", "more", "most", "than", "into", "also",
    "any", "all", "some", "such", "other", "its", "their", "his", "her",
}


def gloss_from_def(defn: str) -> str:
    words = re.findall(r"[a-zA-Z\-]+", (defn or "").lower())
    keep = [w for w in words if w not in STOP and len(w) > 2]
    if not keep:
        keep = words[:2] if words else ["unknown"]
    # 1-2 content words as stable answer token
    g = keep[0]
    if len(keep) > 1 and len(keep[0]) < 5:
        g = keep[0] + "-" + keep[1]
    return g[:24]


def role_to_pos_label(role: str) -> str:
    return {
        "verb": "verb",
        "what": "noun",
        "who": "noun",
        "adj": "adjective",
        "how": "adverb",
        "where": "adverb",
        "when": "adverb",
        "link": "function",
    }.get(role, "word")


def main() -> int:
    cards_path = LEX / "en_dictionary.jsonl"
    roles_path = LEX / "en_roles.tsv"
    if not cards_path.is_file():
        print("Missing en_dictionary.jsonl — run build_lexicon_from_dictionary.py first")
        return 1

    # Prefer common/short words for depth teaching (tractable answers)
    cards = []
    for line in cards_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        w = (o.get("word") or "").strip().lower()
        if not w or len(w) < 3 or len(w) > 14:
            continue
        if "-" in w or not w.isalpha():
            continue
        role = o.get("role") or "what"
        if role == "link":
            continue
        defn = o.get("definition") or ""
        usage = o.get("usage") or ""
        gloss = gloss_from_def(defn)
        cards.append(
            {
                "word": w,
                "role": role,
                "pos": role_to_pos_label(role),
                "gloss": gloss,
                "definition": defn[:120],
                "usage": usage[:100],
                "synonyms": o.get("synonyms") or [],
            }
        )

    # diversity sample: balance roles, cap
    by_role: dict[str, list] = {}
    for c in cards:
        by_role.setdefault(c["role"], []).append(c)
    selected = []
    # order roles by teaching priority
    for r in ("verb", "what", "who", "adj", "how", "where", "when"):
        pool = by_role.get(r, [])
        # prefer shorter words
        pool.sort(key=lambda x: (len(x["word"]), x["word"]))
        selected.extend(pool[:120])
    # unique by word
    seen = set()
    uniq = []
    for c in selected:
        if c["word"] in seen:
            continue
        seen.add(c["word"])
        uniq.append(c)
        if len(uniq) >= 600:
            break

    # Hand-curated pointed set (must-pass everyday English)
    curated = [
        ("run", "verb", "verb", "move", "move fast on foot"),
        ("dog", "what", "noun", "animal", "a domestic animal"),
        ("teacher", "who", "noun", "person", "a person who teaches"),
        ("happy", "adj", "adjective", "glad", "feeling pleasure"),
        ("quickly", "how", "adverb", "fast", "with speed"),
        ("water", "what", "noun", "liquid", "clear liquid we drink"),
        ("think", "verb", "verb", "reason", "use the mind"),
        ("book", "what", "noun", "pages", "pages bound to read"),
        ("eat", "verb", "verb", "food", "take food"),
        ("beautiful", "adj", "adjective", "pretty", "pleasing to see"),
        ("remember", "verb", "verb", "recall", "bring back to mind"),
        ("house", "what", "noun", "home", "place where people live"),
        ("friend", "who", "noun", "person", "person you like"),
        ("slowly", "how", "adverb", "slow", "not fast"),
        ("red", "adj", "adjective", "color", "color of blood"),
        ("speak", "verb", "verb", "talk", "use words aloud"),
        ("listen", "verb", "verb", "hear", "pay attention to sound"),
        ("child", "who", "noun", "person", "young human"),
        ("city", "what", "noun", "place", "large town"),
        ("learn", "verb", "verb", "study", "gain knowledge"),
    ]
    for w, role, pos, gloss, defn in curated:
        if w not in seen:
            uniq.insert(0, {
                "word": w, "role": role, "pos": pos, "gloss": gloss,
                "definition": defn, "usage": "", "synonyms": [],
            })
            seen.add(w)

    # Write depth bank for Zig
    # columns: word \t role \t pos \t gloss \t definition
    lines = [
        "# word\trole\tpos\tgloss\tdefinition",
        "# Pointed language depth — POS + short meaning (not word salad)",
    ]
    for c in uniq:
        d = (c["definition"] or "").replace("\t", " ").replace("\n", " ")
        lines.append(f"{c['word']}\t{c['role']}\t{c['pos']}\t{c['gloss']}\t{d}")

    out = LEX / "en_depth.tsv"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(uniq)} depth cards → {out}")

    # Also probe question list for reporting
    probe = LEX / "en_depth_probes.txt"
    plines = []
    for c in uniq[:80]:
        w, pos, gloss = c["word"], c["pos"], c["gloss"]
        plines.append(f"Q: is {w} a verb?  A: {'yes' if c['role']=='verb' else 'no'}")
        plines.append(f"Q: {w} is a?  A: {pos}")
        plines.append(f"Q: what does {w} mean?  A: {gloss}")
    probe.write_text("\n".join(plines) + "\n", encoding="utf-8")
    print(f"Wrote probe list → {probe}")

    if ZIG.exists() or ZIG.parent.exists():
        ZIG.mkdir(parents=True, exist_ok=True)
        (ZIG / "en_depth.tsv").write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
        (ZIG / "en_depth_probes.txt").write_text(probe.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Copied to {ZIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
