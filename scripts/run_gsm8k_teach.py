#!/usr/bin/env python3
"""Teach GSM8K pathways into FSOT bank (first high-impact external benchmark).

  python scripts/run_gsm8k_teach.py
  python scripts/run_gsm8k_teach.py --limit-train 800 --limit-test 200
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
    p = argparse.ArgumentParser(description="FSOT GSM8K teach pack + pathway score")
    p.add_argument("--gsm8k", default=r"D:\training data\gsm8k")
    p.add_argument("--limit-train", type=int, default=500)
    p.add_argument("--limit-test", type=int, default=150)
    args = p.parse_args()

    from fsot_nuron.curriculum_gsm8k import build_pack

    man = build_pack(
        gsm8k_root=Path(args.gsm8k),
        limit_train=args.limit_train,
        limit_test=args.limit_test,
    )
    print(json.dumps({
        "benchmark": man["benchmark"],
        "n_train": man["n_train_problems"],
        "n_test": man["n_test_problems"],
        "n_bank_rows": man["n_bank_rows"],
        "n_calc_atoms": man["n_unique_calc_atoms"],
        "cold_final": man["cold"]["final"]["accuracy"],
        "after_final": man["after_teach"]["final"]["accuracy"],
        "cold_hop": man["cold"]["pathways"]["hop_accuracy"],
        "after_hop": man["after_teach"]["pathways"]["hop_accuracy"],
        "after_pathway_full": man["after_teach"]["pathways"]["full_pathway_accuracy"],
        "lift": man["lift"],
        "written": man["written_dirs"],
    }, indent=2))
    print("\n" + man.get("why_first", ""))
    print(f"\nREPORT → data/results/GSM8K_TEACH.md")
    print(f"BANK   → data/curriculum/gsm8k/bank.tsv (+ game drive mirror)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
