#!/usr/bin/env python3
"""Teach reading/writing RULES with why + how (not passage stuffing).

  python scripts/run_linguistics_rules_teach.py
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
    argparse.ArgumentParser(description="FSOT linguistics rules teach").parse_args()
    from fsot_nuron.linguistics_rules import PASS, build_pack

    man = build_pack()
    s = man["scores"]["drills"]
    print(
        json.dumps(
            {
                "doctrine": "rules_why_how_not_stuffing",
                "pass_threshold": PASS,
                "n_rules": man["n_rules"],
                "by_domain": man["by_domain"],
                "drills_acc": s["accuracy"],
                "drills_n": s["n"],
                "by_kind": s.get("by_kind"),
                "straight_a": man["gates"]["straight_a_drills"],
                "sample_fails": s.get("sample_fails", [])[:6],
            },
            indent=2,
        )
    )
    if man["gates"]["straight_a_drills"]:
        print(f"\nFSOT_LINGUISTICS_RULES PASS (≥{PASS})")
    else:
        print(f"\nFSOT_LINGUISTICS_RULES FAIL")
    print("RULES data/curriculum/linguistics_rules/RULES.md")
    print("REPORT data/results/LINGUISTICS_RULES_TEACH.md")
    return 0 if man["gates"]["straight_a_drills"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
