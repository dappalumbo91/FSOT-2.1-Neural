"""
Lexicon distillation — teacher (local Ollama) fills definition / usage / meaning cues.

Student mind keeps machine language + en_roles.tsv.
This module writes en_distill.jsonl: one JSON object per word.

Human-like learning pipeline:
  1) Teacher proposes / labels words (roles) → en_roles.tsv
  2) Teacher distills definition + how-to-use → en_distill.jsonl
  3) Student practices utter → self-hear (re-ingest) → score
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .lexicon_teacher import (
    LEX_DIR,
    TSV_PATH,
    ROLES,
    load_tsv,
    ollama_list_models,
    resolve_ollama_model,
    OLLAMA_HOST,
    _norm_word,
)

DISTILL_PATH = LEX_DIR / "en_distill.jsonl"


def load_distill(path: Path = DISTILL_PATH) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        w = _norm_word(str(obj.get("word", "")))
        if w:
            out[w] = obj
    return out


def save_distill(entries: Dict[str, Dict[str, Any]], path: Path = DISTILL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # stable order: by role then word
    items = sorted(
        entries.values(),
        key=lambda o: (str(o.get("role", "zz")), str(o.get("word", ""))),
    )
    with path.open("w", encoding="utf-8") as f:
        for obj in items:
            f.write(json.dumps(obj, ensure_ascii=True) + "\n")


def _ollama_generate(prompt: str, model: Optional[str] = None, num_predict: int = 400) -> str:
    model_id = resolve_ollama_model(model)
    body = {
        "model": model_id,
        "stream": False,
        "prompt": prompt,
        "options": {"temperature": 0.3, "num_predict": num_predict},
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
        text = data["message"].get("content") or ""
    return text


def _extract_json_obj(text: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        # try fix trailing commas lightly
        cleaned = re.sub(r",\s*}", "}", m.group(0))
        cleaned = re.sub(r",\s*]", "]", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def distill_one(
    word: str,
    role: str,
    *,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ask local Ollama for a compact teaching card:
      definition, usage (example sentence), related words, child-friendly note.
    """
    prompt = f"""You are a language teacher for a child-like embodied AI.
Word: "{word}"
Role: {role}

Return ONLY one JSON object (no markdown) with keys:
  "word": lowercase string
  "role": one of {list(ROLES)}
  "definition": one short plain-English definition (max 20 words)
  "usage": one simple example sentence using the word
  "related": array of up to 5 related simple words
  "hint": how a learner should use this word (max 15 words)

Keep vocabulary simple. No lectures."""
    text = _ollama_generate(prompt, model=model, num_predict=280)
    obj = _extract_json_obj(text)
    if not obj:
        # honest fallback card so pipeline never blocks
        return {
            "word": word,
            "role": role,
            "definition": f"A {role}-class word: {word}.",
            "usage": f"I use {word} now.",
            "related": [],
            "hint": f"Use as {role}.",
            "source": "fallback",
            "teacher": "offline_fallback",
        }
    out = {
        "word": _norm_word(str(obj.get("word", word))) or word,
        "role": str(obj.get("role", role)).lower() if str(obj.get("role", role)).lower() in ROLES else role,
        "definition": str(obj.get("definition", ""))[:160].strip(),
        "usage": str(obj.get("usage", ""))[:120].strip(),
        "related": [],
        "hint": str(obj.get("hint", ""))[:120].strip(),
        "source": "ollama",
        "teacher": f"ollama:{resolve_ollama_model(model)}",
    }
    rel = obj.get("related") or []
    if isinstance(rel, list):
        for x in rel[:5]:
            wn = _norm_word(str(x))
            if wn:
                out["related"].append(wn)
    if not out["definition"]:
        out["definition"] = f"A {role}-class word: {word}."
    if not out["usage"]:
        out["usage"] = f"I use {word} now."
    return out


def distill_batch(
    *,
    limit: int = 50,
    model: Optional[str] = None,
    only_missing: bool = True,
    roles: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Distill teaching cards for words in en_roles.tsv.
    Writes/merges en_distill.jsonl.
    """
    roles_map = load_tsv()
    existing = load_distill()
    role_filter = set(roles) if roles else set(ROLES)

    todo: List[Tuple[str, str]] = []
    for w, role in sorted(roles_map.items(), key=lambda kv: (kv[1], kv[0])):
        if role not in role_filter:
            continue
        if only_missing and w in existing:
            continue
        todo.append((w, role))
        if len(todo) >= limit:
            break

    added = 0
    errors = 0
    last_teacher = None
    for w, role in todo:
        try:
            card = distill_one(w, role, model=model)
            existing[card["word"]] = card
            last_teacher = card.get("teacher")
            added += 1
        except Exception:
            errors += 1
            continue

    save_distill(existing)
    return {
        "path": str(DISTILL_PATH),
        "roles_path": str(TSV_PATH),
        "n_roles": len(roles_map),
        "n_distill": len(existing),
        "batch_todo": len(todo),
        "batch_added": added,
        "batch_errors": errors,
        "teacher": last_teacher,
        "only_missing": only_missing,
        "doctrine": "Ollama teacher distills definition/usage; mind practices separately",
    }


def coverage_report() -> Dict[str, Any]:
    roles = load_tsv()
    dist = load_distill()
    missing = [w for w in roles if w not in dist]
    by_role = {r: 0 for r in ROLES}
    for w, r in roles.items():
        by_role[r] = by_role.get(r, 0) + 1
    distilled_by_role = {r: 0 for r in ROLES}
    for o in dist.values():
        r = str(o.get("role", ""))
        if r in distilled_by_role:
            distilled_by_role[r] += 1
    n = len(roles)
    # Fluency targets (productive core for embodied mind)
    return {
        "n_role_words": n,
        "n_distilled": len(dist),
        "n_missing_distill": len(missing),
        "pct_distilled": round(100.0 * len(dist) / n, 1) if n else 0.0,
        "by_role": by_role,
        "distilled_by_role": distilled_by_role,
        "targets": {
            "survival_chat": 500,
            "everyday_fluid": 2000,
            "strong_productive": 5000,
            "note": "Adult receptive is 20k+; productive core for fluid speech is smaller. Grammar is separate from lexicon size.",
        },
        "missing_sample": missing[:20],
    }
