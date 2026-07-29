"""Build open PK→K→G1 curriculum bank from public knowledge (no proprietary books).

  python run_curriculum_open.py
  python run_curriculum_open.py --report
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    p = argparse.ArgumentParser(description="FSOT open curriculum packer (math/Dolch/phonics/science)")
    p.add_argument("--report", action="store_true", help="Print MANIFEST only (build if missing)")
    p.add_argument("--no-merge", action="store_true", help="Do not merge prior facts.jsonl rows")
    args = p.parse_args()

    from fsot_nuron.curriculum_open import build_all, report

    if args.report:
        man = report()
    else:
        man = build_all(merge_existing=not args.no_merge)

    print(json.dumps(man, indent=2))
    print(
        f"\nOPEN_CURRICULUM bank_rows={man.get('n_bank_rows')} "
        f"facts={man.get('n_facts_jsonl')} problems={man.get('n_problems_jsonl')}"
    )
    if man.get("by_domain"):
        print("domains:", man["by_domain"])
    if man.get("by_grade"):
        print("grades:", man["by_grade"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
