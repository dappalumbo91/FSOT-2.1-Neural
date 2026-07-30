#!/usr/bin/env python3
"""Teach all rulebooks currently wired: math generator import + math apply + linguistics.

  python scripts/run_rules_teach_all.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    from fsot_nuron.math_rulebook_import import DEFAULT_SOURCE, import_all
    from fsot_nuron.math_rules import build_pack as math_pack
    from fsot_nuron.linguistics_rules import build_pack as ling_pack

    print("=== 1) Import Math generator rulebook ===")
    if DEFAULT_SOURCE.is_dir():
        imp = import_all(DEFAULT_SOURCE)
        print(f"  imported rules={imp['n_rules']} docs={imp['n_documents']}")
    else:
        print(f"  skip import (missing {DEFAULT_SOURCE})")
        imp = {"n_rules": 0}

    print("=== 2) Math rules apply + drills ===")
    math = math_pack(gsm8k_practice_limit=400, gsm8k_test_limit=200)
    print(
        f"  drills={math['scores']['drills_rule_application']['accuracy']} "
        f"imported={math.get('n_imported_math_generator_rules')} "
        f"straight_a={math['gates']['straight_a_rules']}"
    )

    print("=== 3) Linguistics reading/writing rules ===")
    ling = ling_pack()
    print(
        f"  drills={ling['scores']['drills']['accuracy']} "
        f"n_rules={ling['n_rules']} "
        f"straight_a={ling['gates']['straight_a_drills']}"
    )

    summary = {
        "math_generator_rules": imp.get("n_rules", 0),
        "math_drills_acc": math["scores"]["drills_rule_application"]["accuracy"],
        "math_straight_a": math["gates"]["straight_a_rules"],
        "ling_rules": ling["n_rules"],
        "ling_drills_acc": ling["scores"]["drills"]["accuracy"],
        "ling_straight_a": ling["gates"]["straight_a_drills"],
        "doctrine": "rules + why + how; not stuffing",
    }
    print("\n" + json.dumps(summary, indent=2))
    ok = summary["math_straight_a"] and summary["ling_straight_a"]
    print("\nFSOT_RULES_TEACH_ALL " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
