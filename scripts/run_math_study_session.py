#!/usr/bin/env python3
"""Long bio-style study session: epochs of encode → practice → sleep, then exam.

People need time to retain. The organism uses the same idea, compressed:

  for epoch in 1..N:
      ENCODE curriculum (teach bank)
      PRACTICE spaced retrieval (hit → strengthen, miss → restudy)
      REST (weak decay)
      SLEEP (replay densify)
  FINAL SLEEP
  EXAM (only after study — drills + binding + optional GSM8K)

Local only. No cloud API.

  # default: 8 epochs on unified public curriculum bank
  python scripts/run_math_study_session.py

  # longer study
  python scripts/run_math_study_session.py --epochs 20 --practice-frac 0.4

  # study then full GSM8K exam
  python scripts/run_math_study_session.py --epochs 12 --exam-gsm8k 500

  # ensure curriculum imported first
  python scripts/import_public_math_curricula.py
  python scripts/run_math_study_session.py --epochs 10
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))

BANK = ROOT / "data" / "curriculum" / "public_math" / "UNIFIED_TEACH_BANK.tsv"
OUT = ROOT / "data" / "results" / "MATH_STUDY_SESSION_REPORT.json"


def load_curriculum(limit: int | None = None) -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    if BANK.is_file():
        for line in BANK.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            # source, question, answer, meta
            q, a = parts[1].strip(), parts[2].strip()
            if q and a and any(c.isdigit() for c in a):
                items.append((q, a))
            if limit and len(items) >= limit:
                break
    if not items:
        # fallback drills
        from fsot_nuron.math_rules import build_rule_drills
        from fsot_nuron.math_binding import binding_drills

        for it in build_rule_drills():
            items.append((it.question, it.answer))
        for q, a, _ in binding_drills():
            items.append((q, a))
    return items


def exam(org, exam_gsm8k: int) -> dict:
    from fsot_nuron.math_rules import apply_rules, exact_num, build_rule_drills, score_items, PASS
    from fsot_nuron.math_binding import binding_drills
    from fsot_nuron.math_multihop_organism import solve_multihop

    drills = score_items(build_rule_drills())
    bd = binding_drills()
    bd_ok = 0
    for q, a, _ in bd:
        r = apply_rules(q)
        if r.ok and r.answer and exact_num(r.answer, a):
            bd_ok += 1

    # organism-only probe on a practice slice of curriculum
    org_hit = org_n = 0
    # sample last 100 binding+drills
    probe = [(it.question, it.answer) for it in build_rule_drills()[:40]]
    probe += [(q, a) for q, a, _ in bd]
    for q, a in probe:
        org_n += 1
        r = solve_multihop(q)
        if r.ok and r.answer and exact_num(r.answer, a):
            org_hit += 1

    gsm = None
    if exam_gsm8k and exam_gsm8k > 0:
        from fsot_nuron.math_rules import load_gsm8k_heldout

        items = load_gsm8k_heldout("test", exam_gsm8k)
        c = wf = no = 0
        for it in items:
            r = apply_rules(it.question)
            if not r.ok or r.answer is None:
                no += 1
                continue
            if exact_num(r.answer, it.answer):
                c += 1
            else:
                wf += 1
        fire = c + wf
        gsm = {
            "n": len(items),
            "correct": c,
            "wrong_fire": wf,
            "no_fire": no,
            "overall": round(c / max(1, len(items)), 4),
            "fire_precision": round(c / max(1, fire), 4),
        }

    return {
        "drills_acc": drills["accuracy"],
        "drills_pass": drills["accuracy"] >= PASS,
        "binding": f"{bd_ok}/{len(bd)}",
        "organism_probe_acc": round(org_hit / max(1, org_n), 4),
        "organism_probe_n": org_n,
        "gsm8k": gsm,
        "n_episodes": len(org.episodes),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Multi-epoch bio math study session")
    ap.add_argument("--epochs", type=int, default=8, help="Study epochs (default 8)")
    ap.add_argument("--practice-frac", type=float, default=0.35, help="Fraction practiced each epoch")
    ap.add_argument("--sleep-rounds", type=int, default=4, help="Replay rounds per sleep")
    ap.add_argument("--curriculum-limit", type=int, default=None, help="Cap curriculum items")
    ap.add_argument("--exam-gsm8k", type=int, default=0, help="If >0, held-out GSM8K after study")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--import-first", action="store_true", help="Run public curriculum import first")
    args = ap.parse_args()

    if args.import_first or not BANK.is_file():
        print("=== Ensuring public curriculum bank exists ===", flush=True)
        import subprocess

        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "import_public_math_curricula.py")],
            cwd=str(ROOT),
            check=False,
        )

    items = load_curriculum(args.curriculum_limit)
    print(
        f"=== STUDY SESSION start epochs={args.epochs} curriculum={len(items)} "
        f"practice_frac={args.practice_frac} ===",
        flush=True,
    )
    print(
        "schedule: each epoch = ENCODE → PRACTICE (spaced) → REST → SLEEP; "
        "then FINAL SLEEP; then EXAM",
        flush=True,
    )

    from fsot_nuron.math_multihop_organism import get_organism

    org = get_organism()
    # baseline seed atomics always present
    study = org.study_session(
        items,
        epochs=args.epochs,
        practice_frac=args.practice_frac,
        sleep_rounds=args.sleep_rounds,
        seed=args.seed,
    )

    print("=== EXAM (after study + consolidation) ===", flush=True)
    ex = exam(org, args.exam_gsm8k)
    report = {
        "doctrine": (
            "Long study before test — encode/practice/sleep epochs "
            "(bio intel-loop schedule, not one-shot cram)"
        ),
        "study": study,
        "exam": ex,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:4000], flush=True)
    print(f"\nWrote {OUT}", flush=True)
    print(
        f"\nGATES drills={ex['drills_acc']} binding={ex['binding']} "
        f"org_probe={ex['organism_probe_acc']} episodes={ex['n_episodes']}",
        flush=True,
    )
    return 0 if ex.get("drills_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
