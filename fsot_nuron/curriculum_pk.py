"""
Preschool / Kindergarten / Grade-1 curriculum for FSOT student mind.

Not word=word drills. Facts + simple problems; keywords must land in lexicon.
Teacher (Ollama) can expand more lessons; mind practices encode/retrieve/solve.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .paths import DATA
from .lexicon_teacher import (
    load_tsv,
    save_tsv,
    expand_offline,
    TSV_PATH,
    resolve_ollama_model,
    OLLAMA_HOST,
    _norm_word,
    ROLES,
)

CUR_DIR = DATA / "curriculum" / "pk_k_g1"
FACTS_PATH = CUR_DIR / "facts.jsonl"
PROBLEMS_PATH = CUR_DIR / "problems.jsonl"


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")


def load_curriculum() -> Dict[str, List[Dict[str, Any]]]:
    return {
        "facts": _read_jsonl(FACTS_PATH),
        "problems": _read_jsonl(PROBLEMS_PATH),
    }


def collect_keywords(cur: Dict[str, List[Dict[str, Any]]]) -> Set[str]:
    keys: Set[str] = set()
    for bucket in ("facts", "problems"):
        for row in cur[bucket]:
            for k in row.get("keywords") or []:
                wn = _norm_word(str(k))
                if wn:
                    keys.add(wn)
            for slot_v in (row.get("slots") or {}).values():
                wn = _norm_word(str(slot_v))
                if wn:
                    keys.add(wn)
            for field in ("answer", "question", "fact", "prompt"):
                if field in row:
                    for tok in re.findall(r"[A-Za-z][A-Za-z']{0,24}", str(row[field])):
                        wn = _norm_word(tok)
                        if wn and wn not in ("what", "how", "when", "where", "who", "the", "a", "an", "is", "do", "you", "our"):
                            keys.add(wn)
    return keys


def ensure_lexicon_for_curriculum(target_lex: int = 2000) -> Dict[str, Any]:
    """Expand en_roles.tsv to cover curriculum keywords + productive target."""
    cur = load_curriculum()
    need = collect_keywords(cur)
    entries = load_tsv()
    before = len(entries)
    # mark unknown curriculum words as what/verb heuristics
    for w in sorted(need):
        if w in entries:
            continue
        # crude role guess
        if w in ("yes", "no"):
            entries[w] = "link"
        elif w.endswith("ly"):
            entries[w] = "how"
        elif w in ("i", "we", "he", "she", "they", "you", "friend", "teacher", "family", "people", "dog", "cat"):
            entries[w] = "who"
        elif w in ("red", "blue", "green", "cold", "hot", "sunny", "soft", "round", "safe"):
            entries[w] = "adj"
        elif w in ("day", "night", "winter", "today", "tomorrow"):
            entries[w] = "when"
        elif w in ("here", "school", "world", "home", "park"):
            entries[w] = "where"
        elif w in ("see", "hear", "stop", "go", "share", "grow", "live", "care", "add", "make", "need"):
            entries[w] = "verb"
        else:
            entries[w] = "what"
    entries = expand_offline(entries, target_lex)
    clean = {w: r for w, r in entries.items() if r in ROLES}
    save_tsv(clean)
    missing = sorted(w for w in need if w not in clean)
    return {
        "lexicon_before": before,
        "lexicon_after": len(clean),
        "curriculum_keywords": len(need),
        "missing_keywords": missing[:30],
        "n_missing": len(missing),
        "path": str(TSV_PATH),
    }


def _ollama_generate(prompt: str, model: Optional[str] = None) -> str:
    model_id = resolve_ollama_model(model)
    body = {
        "model": model_id,
        "stream": False,
        "prompt": prompt,
        "options": {"temperature": 0.35, "num_predict": 500},
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
    return data.get("response") or ""


def expand_facts_ollama(n: int = 10, grade: str = "kindergarten", model: Optional[str] = None) -> Dict[str, Any]:
    """Teacher proposes more PK/K/G1 facts as JSON array."""
    existing = _read_jsonl(FACTS_PATH)
    ids = {str(x.get("id")) for x in existing}
    prompt = f"""You teach {grade} children real facts (not nonsense).
Propose {n} new simple facts as a JSON array only. Each object:
  "id": unique string like "k-fact-12"
  "grade": "{grade}"
  "domain": one of science, math, life, body, social, safety, literacy, time, geo, health
  "fact": one short true sentence a child can learn
  "keywords": 3-6 simple words from the fact
  "question": one question whose answer is a single simple word
  "answer": single lowercase word answer
  "slots": object with optional who/what/where/when/how keys (simple words)

Use only common preschool words. Output ONLY the JSON array."""
    text = _ollama_generate(prompt, model=model)
    m = re.search(r"\[[\s\S]*\]", text)
    added = 0
    if m:
        try:
            arr = json.loads(m.group(0))
        except json.JSONDecodeError:
            arr = []
        for obj in arr:
            if not isinstance(obj, dict):
                continue
            oid = str(obj.get("id") or f"auto-{added}")
            if oid in ids:
                continue
            obj["id"] = oid
            obj.setdefault("grade", grade)
            existing.append(obj)
            ids.add(oid)
            added += 1
    _write_jsonl(FACTS_PATH, existing)
    return {"added_facts": added, "total_facts": len(existing), "path": str(FACTS_PATH)}


def report() -> Dict[str, Any]:
    cur = load_curriculum()
    lex = load_tsv()
    keys = collect_keywords(cur)
    covered = sum(1 for k in keys if k in lex)
    return {
        "n_facts": len(cur["facts"]),
        "n_problems": len(cur["problems"]),
        "n_keywords": len(keys),
        "keywords_in_lexicon": covered,
        "keyword_coverage_pct": round(100.0 * covered / len(keys), 1) if keys else 0.0,
        "lexicon_size": len(lex),
        "grades": sorted({str(f.get("grade")) for f in cur["facts"]}),
        "targets": {
            "lexicon_productive": 2000,
            "fact_foundation": "preschool → kindergarten → grade1",
            "fluency_test": "teach facts then quiz answers; solve simple problems",
        },
        "doctrine": "teach facts & problems; lexicon supports meaning; not ugga-dugga labels",
    }
