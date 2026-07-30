#!/usr/bin/env python3
"""Unattended multi-hop school: experience → retain hop traces → practice → sleep.

Doctrine (pure-bio):
  Humans learn from information they are shown, retain methods, practice on new
  numbers, and sleep. We do NOT hand-expand multi-hop regex for benchmark points.

  Teacher (this script) has answer keys / worked solutions.
  Student (MathMultihopOrganism) only stores episodic hop traces + atomics.

Local only. No cloud API.

  python scripts/run_multihop_experience_learn.py
  python scripts/run_multihop_experience_learn.py --train-limit 800 --epochs 5
  python scripts/run_multihop_experience_learn.py --fresh --train-limit 300 --epochs 3
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))

TRAIN_PATHS = [
    Path(r"D:\training data\gsm8k\train.jsonl"),
    Path(r"D:\fsot_training\gsm8k\train.jsonl"),
    ROOT / "data" / "curriculum" / "gsm8k" / "train.jsonl",
]
FINAL_RE = re.compile(r"####\s*(.+)\s*$", re.M)
OUT = ROOT / "data" / "results" / "MATH_EXPERIENCE_LEARN.json"


def load_worked_lessons(limit: int | None) -> List[Tuple[str, str, str]]:
    """(question, answer_body, gold) from GSM8K train — teacher answer key."""
    path = next((p for p in TRAIN_PATHS if p.is_file()), None)
    lessons: List[Tuple[str, str, str]] = []
    if path is None:
        return synthetic_lessons()
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if limit is not None and len(lessons) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(o.get("question", "")).strip()
            ans = str(o.get("answer", "")).strip()
            if not q or not ans:
                continue
            m = FINAL_RE.search(ans)
            if not m:
                continue
            gold = m.group(1).strip()
            if "<<" not in ans:
                continue
            lessons.append((q, ans, gold))
    if not lessons:
        return synthetic_lessons()
    return lessons


def synthetic_lessons() -> List[Tuple[str, str, str]]:
    """Minimal worked demos if train.jsonl missing — still real hop traces."""
    return [
        (
            "Cara has 40 jewels. Bob has 5 more than half of Cara's jewels. "
            "Ann has 3 fewer than Bob. How many does Ann have?",
            "Half of 40 is <<40/2=20>>20. Bob has <<20+5=25>>25. Ann has <<25-3=22>>22.\n#### 22",
            "22",
        ),
        (
            "Sam has 5 sheep. Chris has 3 times as many sheep as Sam. "
            "Tom has twice as many sheep as Chris. How many do they have together?",
            "Chris <<3*5=15>>15. Tom <<2*15=30>>30. Together <<30+15+5=50>>50.\n#### 50",
            "50",
        ),
        (
            "Amir eats 5 cookies. Cody eats 3 times as many. How many together?",
            "Cody <<3*5=15>>15. Together <<15+5=20>>20.\n#### 20",
            "20",
        ),
        (
            "Brian has 10 games. Bobby has 5 fewer than 3 times Brian. How many does Bobby have?",
            "Three times <<3*10=30>>30. Bobby <<30-5=25>>25.\n#### 25",
            "25",
        ),
        (
            "Ducks lay 16 eggs. She eats 3 and bakes with 4. Sells remainder for 2 each. How much?",
            "Left <<16-3=13>>13 then <<13-4=9>>9. Money <<9*2=18>>18.\n#### 18",
            "18",
        ),
        (
            "What is half of 36?",
            "Half <<36/2=18>>18.\n#### 18",
            "18",
        ),
        (
            "What is twice 7?",
            "Twice <<2*7=14>>14.\n#### 14",
            "14",
        ),
        (
            "What is 25% of 80?",
            "<<25*80/100=20>>20.\n#### 20",
            "20",
        ),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Experience-learn multi-hop traces (pure-bio, no regex chase)"
    )
    ap.add_argument("--train-limit", type=int, default=500, help="max train lessons")
    ap.add_argument("--epochs", type=int, default=4, help="practice/sleep epochs")
    ap.add_argument("--practice-n", type=int, default=40, help="practice items/epoch")
    ap.add_argument("--sleep-rounds", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--fresh",
        action="store_true",
        help="ignore existing trace bank (in-memory clean student)",
    )
    ap.add_argument(
        "--probe-gsm8k",
        type=int,
        default=0,
        help="optional secondary GSM8K sample size (not the train target)",
    )
    args = ap.parse_args()

    from fsot_nuron.math_multihop_organism import (
        MathMultihopOrganism,
        TRACE_BANK_PATH,
        exact_num,
        solve_multihop,
    )
    from fsot_nuron.math_rules import _norm

    print("=== DOCTRINE ===", flush=True)
    print(
        "experience → episodic hop traces → WM atomics → sleep → prove transfer",
        flush=True,
    )
    print("NOT: hand multi-hop regex for benchmark points", flush=True)

    lessons = load_worked_lessons(args.train_limit)
    print(f"=== TEACHER LESSONS loaded={len(lessons)} ===", flush=True)

    if args.fresh and TRACE_BANK_PATH.is_file():
        # isolate: temporary rename not needed — new organism + empty traces
        bak = TRACE_BANK_PATH.with_suffix(".json.bak_exp")
        TRACE_BANK_PATH.replace(bak)
        print(f"fresh: moved old traces to {bak.name}", flush=True)

    org = MathMultihopOrganism()
    if args.fresh:
        org.traces.clear()

    print("=== ENCODE + PRACTICE + SLEEP ===", flush=True)
    print(f"lessons={len(lessons)}", flush=True)
    report = org.experience_session(
        lessons,
        epochs=args.epochs,
        practice_n=args.practice_n,
        sleep_rounds=args.sleep_rounds,
        seed=args.seed,
    )
    org.save()

    # retention: re-present taught lessons (original language) via experience only
    # = "do you still know the method you were shown?"
    ret_hit = 0
    ret_n = 0
    sample = lessons[:: max(1, len(lessons) // 40)][:40]
    for q, _body, gold in sample:
        ret_n += 1
        r = org.solve_from_experience(q)
        if r.ok and r.answer is not None and exact_num(r.answer, gold):
            ret_hit += 1
    report["retention_taught"] = {
        "n": ret_n,
        "hit": ret_hit,
        "acc": round(ret_hit / max(1, ret_n), 4),
        "note": "original wording of taught lessons; experience path only",
    }
    print(
        f"retention_taught {ret_hit}/{ret_n} acc={report['retention_taught']['acc']}",
        flush=True,
    )

    # secondary probe only
    gsm = None
    if args.probe_gsm8k and args.probe_gsm8k > 0:
        try:
            from fsot_nuron.math_rules import load_gsm8k_heldout

            items = load_gsm8k_heldout("test", args.probe_gsm8k)
            hit = 0
            for it in items:
                r = solve_multihop(it.question)
                if r.ok and r.answer is not None and exact_num(r.answer, it.answer):
                    hit += 1
            gsm = {
                "n": len(items),
                "hit": hit,
                "acc": round(hit / max(1, len(items)), 4),
                "note": "secondary probe only — not train target",
            }
            print(f"secondary GSM8K probe {hit}/{len(items)}", flush=True)
        except Exception as e:
            gsm = {"error": str(e)}

    report["gsm8k_probe"] = gsm
    report["trace_bank"] = str(TRACE_BANK_PATH)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== PROVE (novel numbers) ===", flush=True)
    print(json.dumps(report.get("prove"), indent=2), flush=True)
    print(
        f"traces={report.get('n_traces_final')} taught_ok={report.get('n_taught_ok')}/"
        f"{report.get('n_lessons')}",
        flush=True,
    )
    print(f"Wrote {OUT}", flush=True)

    prove = report.get("prove") or {}
    # pass if we taught something and prove is not total collapse
    ok = int(report.get("n_taught_ok") or 0) > 0 and float(prove.get("acc") or 0) >= 0.15
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
