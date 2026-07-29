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


def load_bulk_tsv(path: Path) -> Dict[str, str]:
    """Load extra free word lists (e.g. preschool_bulk.tsv)."""
    return load_tsv(path) if path.is_file() else {}


def expand_offline(entries: Dict[str, str], target: int) -> Dict[str, str]:
    entries = merge_seed(entries)
    # Preschool–G1 bulk file (free, productive core)
    for w, role in load_bulk_tsv(LEX_DIR / "preschool_bulk.tsv").items():
        if w not in entries:
            entries[w] = role
        if len(entries) >= target:
            return entries
    for role, words in OFFLINE_BULK.items():
        for w in words:
            wn = _norm_word(w)
            if not wn or wn in entries:
                continue
            entries[wn] = role
            if len(entries) >= target:
                return entries
    return entries


# Local teacher first — Ollama on this machine (free). No paid API required.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
# Prefer smaller/faster local models for bulk word lists; override with OLLAMA_MODEL.
# Prefer models that return text promptly (some "thinking" builds return empty /api/generate).
OLLAMA_PREFERRED = [
    "gemma:7b",
    "fsot-gemma:latest",
    "qwen2.5:14b",
    "phi4:14b",
    "fsot-articulation-test:latest",
    "qwen3.5:4b",
    "qwen3.5:9b",
    "nemotron-3-nano:4b",
    "qwen3.5:0.8b",
]


def ollama_list_models() -> List[str]:
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def resolve_ollama_model(explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("OLLAMA_MODEL") or os.environ.get("FSOT_TEACHER_MODEL")
    if env:
        return env
    have = set(ollama_list_models())
    for pref in OLLAMA_PREFERRED:
        if pref in have:
            return pref
    if have:
        return sorted(have)[0]
    raise RuntimeError(
        f"No Ollama models at {OLLAMA_HOST}. Start Ollama and pull a model "
        f"(e.g. ollama pull qwen3.5:4b)."
    )


def _parse_word_array(text: str) -> List[str]:
    m = re.search(r"\[[\s\S]*\]", text)
    if not m:
        # fallback: lines / commas
        raw = re.findall(r"[a-zA-Z][a-zA-Z'\-]{0,30}", text)
        out = []
        for x in raw:
            wn = _norm_word(x)
            if wn and wn not in ("json", "array", "role", "words", "word"):
                out.append(wn)
        return out
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for x in arr:
        wn = _norm_word(str(x))
        if wn:
            out.append(wn)
    return out


def _teacher_prompt(role: str, existing: List[str], n: int) -> str:
    sample = ", ".join(existing[:40])
    return (
        f"You are a lexicon teacher for a small embodied AI (not the AI itself). "
        f"Propose {n} common everyday English words for grammatical role '{role}'. "
        f"Output ONLY a JSON array of lowercase strings, no markdown, no commentary. "
        f"Avoid duplicates of: {sample}"
    )


def ollama_propose(
    role: str,
    existing: List[str],
    n: int = 40,
    model: Optional[str] = None,
) -> List[str]:
    """Local teacher via Ollama /api/generate — free, on your machine."""
    model_id = resolve_ollama_model(model)
    prompt = (
        "System: Output ONLY a JSON array of lowercase English words.\n\n"
        + _teacher_prompt(role, existing, n)
    )
    # /api/generate is more reliable than /api/chat for short JSON dumps
    # (some local "thinking" chat models stall on chat).
    body = {
        "model": model_id,
        "stream": False,
        "prompt": prompt,
        "options": {"temperature": 0.4, "num_predict": 512},
    }
    timeout = int(os.environ.get("OLLAMA_TIMEOUT", "180"))
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data.get("response") or ""
    if not text and isinstance(data.get("message"), dict):
        text = data["message"].get("content") or data["message"].get("thinking") or ""
    # some builds put chain-of-thought only; still try thinking field
    if not text:
        text = data.get("thinking") or ""
    words = _parse_word_array(text)
    if not words and text:
        # last resort: any alphabetic tokens
        for tok in re.findall(r"[A-Za-z][A-Za-z'\-]{1,24}", text):
            wn = _norm_word(tok)
            if wn:
                words.append(wn)
    return words


def openai_compatible_propose(
    role: str,
    existing: List[str],
    n: int = 40,
    *,
    base_url: str,
    api_key: str,
    model: str,
) -> List[str]:
    """Optional remote OpenAI-compatible endpoint (only if you choose — not default)."""
    prompt = _teacher_prompt(role, existing, n)
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You label English words by role for a fixed dictionary."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data["choices"][0]["message"]["content"]
    return _parse_word_array(text)


def propose_words(
    role: str,
    existing: List[str],
    n: int = 50,
    *,
    provider: str = "ollama",
    model: Optional[str] = None,
) -> Tuple[List[str], str]:
    """
    Returns (words, teacher_id).
    Default provider=ollama (local free). Remote only if provider explicitly set.
    """
    provider = (provider or "ollama").lower()
    if provider in ("ollama", "local"):
        mid = resolve_ollama_model(model)
        return ollama_propose(role, existing, n=n, model=mid), f"ollama:{mid}"
    if provider in ("xai", "openai", "remote"):
        key = os.environ.get("XAI_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        if not key:
            raise RuntimeError(
                "Remote teacher needs XAI_API_KEY or OPENAI_API_KEY — "
                "prefer --provider ollama (local, free)."
            )
        base = os.environ.get("OPENAI_BASE_URL", "https://api.x.ai/v1")
        mid = model or os.environ.get("XAI_MODEL") or os.environ.get("OPENAI_MODEL") or "grok-4.5"
        return (
            openai_compatible_propose(role, existing, n=n, base_url=base, api_key=key, model=mid),
            f"remote:{mid}",
        )
    raise RuntimeError(f"Unknown teacher provider: {provider} (use ollama)")


def expand_llm(
    entries: Dict[str, str],
    target: int,
    *,
    provider: str = "ollama",
    model: Optional[str] = None,
) -> Tuple[Dict[str, str], str, Optional[str]]:
    """Expand with local (or optional remote) teacher. Returns entries, teacher_id, error."""
    entries = expand_offline(entries, min(target, 10_000))  # free base first
    teacher_id = f"{provider}:pending"
    err: Optional[str] = None
    if len(entries) >= target:
        return entries, f"{provider}:offline_enough", None
    for role in ROLES:
        if len(entries) >= target:
            break
        have = [w for w, r in entries.items() if r == role]
        try:
            props, teacher_id = propose_words(
                role, have, n=50, provider=provider, model=model
            )
        except Exception as e:
            err = str(e)
            break
        for w in props:
            if w not in entries:
                entries[w] = role
            if len(entries) >= target:
                break
    return entries, teacher_id, err


def teach(
    offline: bool = True,
    llm: bool = False,
    target: int = 500,
    *,
    provider: str = "ollama",
    model: Optional[str] = None,
) -> Dict[str, object]:
    LEX_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_tsv()
    before = len(entries)
    teacher_id = "offline"
    err = None
    if llm:
        entries, teacher_id, err = expand_llm(
            entries, target, provider=provider, model=model
        )
    else:
        entries = expand_offline(entries, target)
    clean = {w: r for w, r in entries.items() if r in ROLES}
    save_tsv(clean)
    by_role = {r: sum(1 for x in clean.values() if x == r) for r in ROLES}
    mode = "offline"
    if llm:
        mode = f"llm:{provider}"
    return {
        "path": str(TSV_PATH),
        "before": before,
        "after": len(clean),
        "added": len(clean) - before,
        "by_role": by_role,
        "mode": mode,
        "teacher": teacher_id,
        "teacher_error": err,
        "ollama_host": OLLAMA_HOST,
        "target": target,
        "doctrine": "local Ollama teacher by default; student mind owns machine language + TSV",
    }
