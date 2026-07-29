"""
Lexicon teacher — grows English role vocabulary for the Zig mind codec.

Student = FSOT mind (machine language + lexicon_en).
Teacher = offline word lists and/or optional xAI chat (not part of the organism).

Output: data/lexicon/en_roles.tsv  (word\\trole)
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .paths import ROOT, DATA

LEX_DIR = DATA / "lexicon"
TSV_PATH = LEX_DIR / "en_roles.tsv"

ROLES = ("who", "verb", "what", "where", "when", "how", "adj", "link")

# Core seed (matches Zig embedded inventory spirit)
SEED: List[Tuple[str, str]] = [
    ("I", "who"), ("you", "who"), ("self", "who"), ("agent", "who"), ("mind", "who"),
    ("we", "who"), ("they", "who"), ("he", "who"), ("she", "who"), ("it", "who"),
    ("see", "verb"), ("hear", "verb"), ("say", "verb"), ("know", "verb"), ("learn", "verb"),
    ("want", "verb"), ("feel", "verb"), ("think", "verb"), ("speak", "verb"),
    ("encode", "verb"), ("recall", "verb"), ("go", "verb"), ("come", "verb"),
    ("make", "verb"), ("find", "verb"), ("give", "verb"), ("take", "verb"),
    ("look", "verb"), ("listen", "verb"), ("remember", "verb"), ("ask", "verb"),
    ("light", "what"), ("sound", "what"), ("person", "what"), ("place", "what"),
    ("thing", "what"), ("frame", "what"), ("machine", "what"), ("word", "what"),
    ("pattern", "what"), ("noise", "what"), ("voice", "what"), ("scene", "what"),
    ("memory", "what"), ("signal", "what"), ("color", "what"), ("shape", "what"),
    ("face", "what"), ("hand", "what"), ("door", "what"), ("window", "what"),
    ("water", "what"), ("fire", "what"), ("air", "what"), ("earth", "what"),
    ("food", "what"), ("book", "what"), ("music", "what"), ("time", "what"),
    ("number", "what"), ("name", "what"), ("idea", "what"), ("body", "what"),
    ("brain", "what"), ("eye", "what"), ("ear", "what"), ("path", "what"),
    ("here", "where"), ("host", "where"), ("room", "where"), ("world", "where"),
    ("home", "where"), ("outside", "where"), ("inside", "where"), ("there", "where"),
    ("now", "when"), ("before", "when"), ("again", "when"), ("today", "when"),
    ("later", "when"), ("always", "when"), ("never", "when"), ("soon", "when"),
    ("well", "how"), ("clearly", "how"), ("softly", "how"), ("loudly", "how"),
    ("quickly", "how"), ("slowly", "how"), ("carefully", "how"),
    ("good", "adj"), ("bad", "adj"), ("new", "adj"), ("own", "adj"), ("live", "adj"),
    ("big", "adj"), ("small", "adj"), ("hot", "adj"), ("cold", "adj"), ("bright", "adj"),
    ("dark", "adj"), ("loud", "adj"), ("quiet", "adj"), ("happy", "adj"), ("sad", "adj"),
    ("the", "link"), ("a", "link"), ("and", "link"), ("to", "link"), ("of", "link"),
    ("in", "link"), ("on", "link"), ("with", "link"), ("for", "link"), ("is", "link"),
    ("are", "link"), ("not", "link"), ("yes", "link"), ("no", "link"),
]

# Extra offline bulk (still free — no API)
OFFLINE_BULK: Dict[str, List[str]] = {
    "who": [
        "someone", "anyone", "everyone", "child", "adult", "friend", "teacher",
        "student", "human", "robot", "animal", "bird", "dog", "cat",
    ],
    "verb": [
        "move", "stop", "start", "open", "close", "write", "read", "draw",
        "play", "work", "rest", "help", "need", "like", "love", "hate",
        "try", "use", "show", "hide", "build", "break", "hold", "drop",
        "walk", "run", "sit", "stand", "sleep", "wake", "eat", "drink",
        "touch", "point", "count", "measure", "choose", "change", "keep",
        "send", "get", "put", "call", "answer", "wait", "watch", "notice",
    ],
    "what": [
        "table", "chair", "wall", "floor", "sky", "sun", "moon", "star",
        "tree", "flower", "grass", "stone", "metal", "glass", "paper", "code",
        "message", "story", "song", "picture", "screen", "key", "lock", "box",
        "line", "point", "circle", "square", "map", "list", "group", "part",
        "whole", "side", "edge", "center", "top", "bottom", "left", "right",
        "front", "back", "space", "system", "network", "data", "file", "bit",
        "byte", "frame", "spike", "wave", "tone", "pitch", "volume", "level",
        "force", "speed", "weight", "size", "age", "life", "death", "truth",
        "lie", "question", "answer", "problem", "solution", "rule", "game",
        "tool", "power", "energy", "heat", "cold", "pain", "pleasure", "fear",
        "hope", "dream", "plan", "goal", "task", "job", "play", "art",
    ],
    "where": [
        "above", "below", "near", "far", "left", "right", "north", "south",
        "east", "west", "school", "city", "country", "street", "park", "lab",
    ],
    "when": [
        "yesterday", "tomorrow", "morning", "night", "early", "late", "first",
        "last", "next", "then", "once", "often", "sometimes", "already",
    ],
    "how": [
        "hard", "easy", "better", "worse", "together", "alone", "maybe",
        "really", "almost", "enough", "too", "very", "just", "only",
    ],
    "adj": [
        "red", "blue", "green", "yellow", "white", "black", "old", "young",
        "long", "short", "high", "low", "strong", "weak", "fast", "slow",
        "full", "empty", "open", "closed", "real", "false", "same", "other",
        "first", "last", "many", "few", "all", "some", "any", "each",
        "clear", "fuzzy", "sharp", "soft", "hard", "smooth", "rough", "safe",
        "dangerous", "important", "simple", "complex", "free", "busy",
    ],
    "link": [
        "or", "but", "if", "because", "when", "while", "as", "at", "by",
        "from", "into", "about", "over", "under", "this", "that", "these",
        "those", "my", "your", "our", "their", "his", "her", "its",
    ],
}


def _norm_word(w: str) -> Optional[str]:
    w = w.strip().lower()
    if not w or not re.fullmatch(r"[a-z][a-z'\-]{0,30}", w):
        return None
    # drop pure links noise
    return w


def load_tsv(path: Path = TSV_PATH) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        w = _norm_word(parts[0])
        role = parts[1].strip().lower()
        if w and role in ROLES:
            out[w] = role
    return out


def save_tsv(entries: Dict[str, str], path: Path = TSV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# FSOT English lexicon roles — teacher→student codec",
        "# word\\trole   roles: " + " ".join(ROLES),
        "# LLM is teacher only; mind runtime does not call the model.",
    ]
    for role in ROLES:
        for w in sorted(k for k, r in entries.items() if r == role):
            lines.append(f"{w}\t{role}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_seed(entries: Dict[str, str]) -> Dict[str, str]:
    for w, role in SEED:
        wn = _norm_word(w)
        if wn and wn not in entries:
            entries[wn] = role
    return entries


def expand_offline(entries: Dict[str, str], target: int) -> Dict[str, str]:
    entries = merge_seed(entries)
    for role, words in OFFLINE_BULK.items():
        for w in words:
            wn = _norm_word(w)
            if not wn or wn in entries:
                continue
            entries[wn] = role
            if len(entries) >= target:
                return entries
    return entries


def _xai_propose(role: str, existing: List[str], n: int = 40) -> List[str]:
    """Optional teacher: xAI OpenAI-compatible chat. Env XAI_API_KEY."""
    key = os.environ.get("XAI_API_KEY") or os.environ.get("XAI_KEY")
    if not key:
        raise RuntimeError("XAI_API_KEY not set (teacher LLM optional)")

    sample = ", ".join(existing[:40])
    prompt = (
        f"You are a lexicon teacher for a small embodied AI. "
        f"Propose {n} common English words for grammatical role '{role}'. "
        f"Output ONLY a JSON array of lowercase strings, no commentary. "
        f"Avoid duplicates of: {sample}"
    )
    body = {
        "model": os.environ.get("XAI_MODEL", "grok-4.5"),
        "messages": [
            {"role": "system", "content": "You label English words by role for a fixed dictionary."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }
    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data["choices"][0]["message"]["content"]
    # extract JSON array
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        return []
    arr = json.loads(m.group(0))
    out = []
    for x in arr:
        wn = _norm_word(str(x))
        if wn:
            out.append(wn)
    return out


def expand_llm(entries: Dict[str, str], target: int) -> Dict[str, str]:
    entries = expand_offline(entries, target)  # free base first
    if len(entries) >= target:
        return entries
    for role in ROLES:
        if len(entries) >= target:
            break
        have = [w for w, r in entries.items() if r == role]
        try:
            props = _xai_propose(role, have, n=50)
        except Exception as e:
            # fail soft — offline progress still saved
            entries["_teacher_error"] = str(e)  # type: ignore
            break
        for w in props:
            if w not in entries:
                entries[w] = role
            if len(entries) >= target:
                break
    entries.pop("_teacher_error", None)
    return entries


def teach(offline: bool = True, llm: bool = False, target: int = 500) -> Dict[str, object]:
    LEX_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_tsv()
    before = len(entries)
    if llm:
        entries = expand_llm(entries, target)
    else:
        entries = expand_offline(entries, target)
    # strip non-role keys
    clean = {w: r for w, r in entries.items() if r in ROLES}
    save_tsv(clean)
    by_role = {r: sum(1 for x in clean.values() if x == r) for r in ROLES}
    return {
        "path": str(TSV_PATH),
        "before": before,
        "after": len(clean),
        "added": len(clean) - before,
        "by_role": by_role,
        "mode": "llm" if llm else "offline",
        "target": target,
        "doctrine": "teacher proposes; student mind owns machine language + TSV codec",
    }
