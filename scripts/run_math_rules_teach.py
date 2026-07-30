#!/usr/bin/env python3
"""Teach math RULES + apply them (not GSM8K Q/A stuffing).

  python scripts/run_math_rules_teach.py
  python scripts/run_math_rules_teach.py --gsm8k-practice 500 --test 500
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    p = argparse.ArgumentParser(description="FSOT rule-first math teaching")
    p.add_argument("--gsm8k-practice", type=int, default=500)
    p.add_argument("--test", type=int, default=500)
    args = p.parse_args()

    from fsot_nuron.math_rules import PASS, build_pack

    man = build_pack(
        gsm8k_practice_limit=args.gsm8k_practice,
        gsm8k_test_limit=args.test,
    )
    s = man["scores"]
    g = man["gates"]
    print(
        json.dumps(
            {
                "doctrine": "rules_not_stuffing",
                "pass_threshold": PASS,
                "n_runtime_apply_rules": man.get("n_arith_rules_runtime"),
                "n_imported_math_generator_rules": man.get("n_imported_math_generator_rules"),
                "n_imported_bank_rows": man.get("n_imported_bank_rows"),
                "n_lang_maps": man["n_language_maps"],
                "drills_acc": s["drills_rule_application"]["accuracy"],
                "drills_n": s["drills_rule_application"]["n"],
                "gsm8k_rule_covered_train_acc": s["gsm8k_train_rule_covered"].get("accuracy"),
                "gsm8k_test_all_acc": s["gsm8k_test_all"]["accuracy"],
                "gsm8k_test_all_n": s["gsm8k_test_all"]["n"],
                "gsm8k_test_covered_acc": s["gsm8k_test_where_rules_fire"].get("accuracy"),
                "gsm8k_test_covered_n": s["gsm8k_test_where_rules_fire"].get("n"),
                "straight_a_drills": g["straight_a_rules"],
                "rulebook_imported": g.get("rulebook_imported"),
                "coverage_note": man["coverage_note"],
            },
            indent=2,
        )
    )
    if g["straight_a_rules"]:
        print(f"\nFSOT_MATH_RULES_DRILLS PASS (≥{PASS})")
    else:
        print(f"\nFSOT_MATH_RULES_DRILLS FAIL")
    print("REPORT data/results/MATH_RULES_TEACH.md")
    print("RULES  data/curriculum/math_rules/RULES.md")
    return 0 if g["straight_a_rules"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
