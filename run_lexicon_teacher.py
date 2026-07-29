#!/usr/bin/env python3
"""Grow en_roles.tsv for the Zig English codec (teacher → student).

Examples:
  python run_lexicon_teacher.py --offline --target 500
  python run_lexicon_teacher.py --llm --target 800   # needs XAI_API_KEY
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
    p = argparse.ArgumentParser(description="FSOT lexicon teacher (not the mind)")
    p.add_argument("--offline", action="store_true", help="Free offline expansion only")
    p.add_argument("--llm", action="store_true", help="Use xAI teacher after offline seed")
    p.add_argument("--target", type=int, default=500, help="Target vocabulary size")
    p.add_argument("--json", action="store_true", help="Print JSON report")
    args = p.parse_args()

    if not args.offline and not args.llm:
        args.offline = True  # default free path

    from fsot_nuron.lexicon_teacher import teach

    rep = teach(offline=args.offline or not args.llm, llm=args.llm, target=args.target)
    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        print("=== FSOT LEXICON TEACHER ===")
        print(f"mode={rep['mode']} target={rep['target']}")
        print(f"path={rep['path']}")
        print(f"size {rep['before']} → {rep['after']} (+{rep['added']})")
        print("by_role:", rep["by_role"])
        print(rep["doctrine"])
        print("FSOT_LEXICON_TEACHER_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
