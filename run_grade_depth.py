"""Build held-out paraphrase exam for grade-school depth claim."""
from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--max-per-domain", type=int, default=150)
    args = p.parse_args()
    from fsot_nuron.grade_depth import build_exam

    man = build_exam(max_per_domain=args.max_per_domain)
    print(json.dumps(man, indent=2))
    print(f"\nDEPTH_EXAM n={man['n_exam']} by_domain={man.get('by_domain')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
