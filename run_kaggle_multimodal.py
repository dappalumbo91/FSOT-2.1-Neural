#!/usr/bin/env python3
"""Kaggle STEM multimodal → Zig inject frames (machine language).

Requires: kaggle CLI authenticated (you already have this).

Examples:
  python run_kaggle_multimodal.py --catalog
  python run_kaggle_multimodal.py --mnist --limit 32
  # then:
  #   fsot_mind vision  OR  inject-file path\to\mnist_digits_inject.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    p = argparse.ArgumentParser(description="FSOT Kaggle multimodal STEM ingest")
    p.add_argument("--catalog", action="store_true", help="List STEM Kaggle targets")
    p.add_argument("--mnist", action="store_true", help="Build MNIST digit inject bundle")
    p.add_argument("--limit", type=int, default=32, help="Max samples")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    from fsot_nuron.kaggle_multimodal import build_mnist, catalog_report

    if args.catalog or (not args.mnist):
        rep = catalog_report()
        if args.json:
            print(json.dumps(rep, indent=2))
        else:
            print("=== FSOT KAGGLE MULTIMODAL CATALOG (STEM only) ===")
            print("exclude:", rep["exclude"])
            for d in rep["datasets"]:
                print(f"  [{d['key']}] {d['kaggle']} domain={d['domain']} local={d['local']}")
                print(f"      {d['desc']}")
            if not args.mnist:
                print("FSOT_KAGGLE_CATALOG_OK")
                return 0

    if args.mnist:
        rep = build_mnist(limit=args.limit)
        if args.json:
            print(json.dumps(rep, indent=2))
        else:
            print("=== FSOT KAGGLE MNIST → INJECT ===")
            print(f"frames={rep['n_frames']}")
            print(f"inject={rep['inject_path']}")
            print(f"lessons={rep['lessons_path']}")
            print(rep["doctrine"])
            print("Next: fsot_mind inject-file <inject path>  OR vision demo")
            print("FSOT_KAGGLE_MULTIMODAL_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
