#!/usr/bin/env python3
"""Download/import public math curricula → teach bank + multihop organism.

Sources (public):
  - GSM8K train (local D: or data path)
  - SVAMP (downloaded to data/curriculum/public_math/)
  - MATH.jsonl arithmetic-friendly subset (local)
  - Math-generator rulebook (data/math_rulebook)
  - Existing rule drills

Doctrine: curriculum depth for *learning* (encode facts + equations + atomics).
Not LLM. Not test stuffing — train/public only into teach bank.

  python scripts/import_public_math_curricula.py
  python scripts/import_public_math_curricula.py --teach --sleep
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))

OUT_DIR = ROOT / "data" / "curriculum" / "public_math"
BANK = OUT_DIR / "UNIFIED_TEACH_BANK.tsv"
MANIFEST = OUT_DIR / "IMPORT_MANIFEST.json"
EPISODE_DIR = ROOT / "data" / "math_learn"

FINAL_RE = re.compile(r"####\s*(.+)\s*$", re.M)
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _norm_ans(a: str) -> str:
    a = str(a).strip().replace(",", "").replace("$", "")
    if re.fullmatch(r"-?\d+\.0+", a):
        return a.split(".")[0]
    try:
        f = float(a)
        if abs(f - round(f)) < 1e-9:
            return str(int(round(f)))
        return f"{f:.10g}"
    except ValueError:
        return a


def fetch(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 500:
        return True
    try:
        urllib.request.urlretrieve(url, dest)
        return dest.is_file() and dest.stat().st_size > 100
    except Exception as e:
        print(f"  fetch fail {dest.name}: {e}", flush=True)
        return False


def load_svamp() -> List[Tuple[str, str, str, str]]:
    """(question, answer, source, equation)"""
    path = OUT_DIR / "svamp.json"
    url = "https://raw.githubusercontent.com/arkilpatel/SVAMP/main/SVAMP.json"
    fetch(url, path)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for o in data if isinstance(data, list) else []:
        body = str(o.get("Body") or "").strip()
        q = str(o.get("Question") or "").strip()
        full = f"{body} {q}".strip()
        ans = _norm_ans(o.get("Answer", ""))
        eq = str(o.get("Equation") or "").strip()
        if full and ans:
            rows.append((full, ans, "svamp", eq))
    return rows


def load_gsm8k_train(limit: Optional[int] = None) -> List[Tuple[str, str, str, str]]:
    paths = [
        Path(r"D:\training data\gsm8k\train.jsonl"),
        Path(r"D:\fsot_training\curriculum\gsm8k\train.jsonl"),
        ROOT / "data" / "gsm8k" / "train.jsonl",
    ]
    path = next((p for p in paths if p.is_file()), None)
    if path is None:
        return []
    rows = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if limit is not None and len(rows) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(o.get("question", "")).strip()
            ans_body = str(o.get("answer", ""))
            m = FINAL_RE.search(ans_body)
            if not q or not m:
                continue
            ans = _norm_ans(m.group(1))
            # capture last equation as optional
            eqs = re.findall(r"<<([^>]+)>>", ans_body)
            eq = eqs[-1] if eqs else ""
            rows.append((q, ans, "gsm8k_train", eq))
    return rows


def load_math_jsonl(limit: int = 500) -> List[Tuple[str, str, str, str]]:
    """Competition MATH — keep only simple numeric answers."""
    path = Path(r"D:\training data\math\math.jsonl")
    if not path.is_file():
        return []
    rows = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(rows) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            ans = str(o.get("answer", "")).strip()
            # skip latex-heavy answers
            if "\\" in ans or "{" in ans or "frac" in ans:
                # try extract simple number
                nums = NUM_RE.findall(ans.replace(",", ""))
                if len(nums) != 1:
                    continue
                ans = _norm_ans(nums[0])
            else:
                ans = _norm_ans(ans)
            q = str(o.get("problem", "")).strip()
            if not q or not ans:
                continue
            # prefer lower levels
            try:
                lvl = int(o.get("level") or 99)
            except Exception:
                lvl = 99
            if lvl > 3:
                continue
            rows.append((q, ans, f"math_{o.get('subject','x')}", ""))
    return rows


def load_rulebook_examples() -> List[Tuple[str, str, str, str]]:
    path = ROOT / "data" / "math_rulebook" / "MASTER_RULEBOOK.json"
    if not path.is_file():
        return []
    try:
        master = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = []
    for r in master.get("rules") or []:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or "")
        formula = str(r.get("output_form") or r.get("input_form") or r.get("operation") or "")
        name = str(r.get("name") or rid)
        for ex in (r.get("examples") or [])[:4]:
            exs = str(ex)
            # "4 denotes four" / "half of 8 is 4"
            m = re.search(
                r"(?:half of|twice|what is)?\s*([^=]+?)\s*(?:=|is|denotes)\s*([^=]+)$",
                exs,
                re.I,
            )
            if m:
                q = m.group(1).strip()
                a = _norm_ans(m.group(2))
                if q and a and re.search(r"\d", a + q):
                    rows.append((f"What is {q}?", a, f"rulebook_{rid}", formula))
            # pure arithmetic in examples
            m2 = re.search(r"(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)\s*=\s*(\d+(?:\.\d+)?)", exs)
            if m2:
                a, op, b, res = m2.groups()
                rows.append((f"What is {a} {op} {b}?", _norm_ans(res), f"rulebook_{rid}", exs))
        # teach formula as fact cue
        if formula and rid:
            rows.append((f"formula {name}", formula[:80], f"rulebook_meta_{rid}", formula))
    return rows


def load_drills() -> List[Tuple[str, str, str, str]]:
    rows = []
    try:
        from fsot_nuron.math_rules import build_rule_drills
        from fsot_nuron.math_binding import binding_drills

        for it in build_rule_drills():
            rows.append((it.question, it.answer, "drill", it.rule_focus))
        for q, a, f in binding_drills():
            rows.append((q, a, "binding_drill", f))
    except Exception as e:
        print("drills skip", e)
    return rows


def equation_to_atomics(eq: str, answer: str) -> List[Tuple[str, str]]:
    """Turn '( 76.0 - 25.0 )' into teachable atomics."""
    out: List[Tuple[str, str]] = []
    if not eq:
        return out
    # simplify spaces
    e = re.sub(r"\s+", " ", eq.strip())
    nums = NUM_RE.findall(e)
    if re.search(r"\-", e) and len(nums) >= 2:
        out.append((f"{nums[0]} minus {nums[1]}", _norm_ans(answer)))
        out.append((f"what is {nums[0]} - {nums[1]}", _norm_ans(answer)))
    if re.search(r"\*", e) and len(nums) >= 2:
        out.append((f"{nums[0]} times {nums[1]}", _norm_ans(answer)))
    if re.search(r"\/", e) and len(nums) >= 2:
        out.append((f"{nums[0]} divided by {nums[1]}", _norm_ans(answer)))
    if re.search(r"\+", e) and len(nums) >= 2:
        out.append((f"{nums[0]} plus {nums[1]}", _norm_ans(answer)))
    return out


def write_bank(rows: List[Tuple[str, str, str, str]]) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # dedupe by question
    seen = set()
    lines = ["# source\tquestion\tanswer\tmeta\n"]
    n = 0
    for q, a, src, meta in rows:
        q1 = q.replace("\t", " ").replace("\n", " ").strip()
        a1 = a.replace("\t", " ").strip()
        key = q1.lower()[:200]
        if key in seen or not q1 or not a1:
            continue
        seen.add(key)
        lines.append(f"{src}\t{q1}\t{a1}\t{meta.replace(chr(9), ' ')}\n")
        n += 1
    BANK.write_text("".join(lines), encoding="utf-8")
    return n


def teach_organism(rows: List[Tuple[str, str, str, str]], *, sleep: bool) -> Dict[str, Any]:
    from fsot_nuron.math_multihop_organism import get_organism

    org = get_organism()
    n = 0
    for q, a, src, meta in rows:
        # skip non-numeric meta formulas as answers
        if not re.search(r"\d", a) and src.startswith("rulebook_meta"):
            continue
        org.teach(q[:120], a, rule_id=src[:40], hops=1 if "drill" in src else 2)
        n += 1
        # atomics from equations
        for cq, ca in equation_to_atomics(meta, a):
            org.teach(cq, ca, rule_id="eq_atomic", hops=1)
            n += 1
        if n % 500 == 0 and sleep:
            org.sleep_replay(1)
    if sleep:
        org.sleep_replay(5)
    org.save()
    return {"taught_cues": n, "n_episodes": len(org.episodes)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--teach", action="store_true", help="Encode into multihop organism")
    ap.add_argument("--sleep", action="store_true", help="Replay densify during teach")
    ap.add_argument("--gsm8k-limit", type=int, default=None)
    args = ap.parse_args()

    print("=== Import public / local math curricula ===", flush=True)
    bundles = {
        "svamp": load_svamp(),
        "gsm8k_train": load_gsm8k_train(limit=args.gsm8k_limit),
        "math_jsonl": load_math_jsonl(400),
        "rulebook": load_rulebook_examples(),
        "drills": load_drills(),
    }
    all_rows: List[Tuple[str, str, str, str]] = []
    counts = {}
    for k, v in bundles.items():
        counts[k] = len(v)
        all_rows.extend(v)
        print(f"  {k}: {len(v)}", flush=True)

    n_bank = write_bank(all_rows)
    print(f"UNIFIED bank rows: {n_bank} → {BANK}", flush=True)

    teach_stats = {}
    if args.teach:
        print("=== Teach multihop organism (encode curriculum) ===", flush=True)
        teach_stats = teach_organism(all_rows, sleep=args.sleep)
        print(json.dumps(teach_stats, indent=2), flush=True)

    man = {
        "counts": counts,
        "n_unified_bank": n_bank,
        "bank_path": str(BANK),
        "teach": teach_stats,
        "doctrine": (
            "Public + local curricula imported for learning depth. "
            "SVAMP + GSM8K train + MATH + rulebook + drills. "
            "Encoded into episode bank when --teach."
        ),
    }
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")
    print(json.dumps(man, indent=2), flush=True)
    return 0 if n_bank > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
