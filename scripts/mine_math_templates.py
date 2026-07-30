#!/usr/bin/env python3
"""Mine GSM8K train → executable templates (curriculum bulk). Local, no API.

  python scripts/mine_math_templates.py
  python scripts/mine_math_templates.py --limit 2000
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--min-support", type=int, default=1)
    args = ap.parse_args()
    from fsot_nuron.math_auto_templates import mine_train

    pack = mine_train(limit=args.limit, min_support=args.min_support)
    print(
        json.dumps(
            {
                "n_templates": pack.get("n_templates"),
                "n_abstracted_ok": pack.get("n_abstracted_ok"),
                "n_train_rows_scanned": pack.get("n_train_rows_scanned"),
                "path": "data/math_templates/TRAIN_TEMPLATES.json",
            },
            indent=2,
        )
    )
    return 0 if pack.get("n_templates", 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
