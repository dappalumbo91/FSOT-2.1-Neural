#!/usr/bin/env python3
"""Distill definition + usage for lexicon words via local Ollama teacher.

Examples:
  python run_lexicon_distill.py --report
  python run_lexicon_distill.py --limit 20 --model gemma:7b
  python run_lexicon_distill.py --limit 100 --model fsot-gemma:latest
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
    p = argparse.ArgumentParser(description="FSOT lexicon distill (Ollama teacher)")
    p.add_argument("--limit", type=int, default=30, help="Max new words to distill this run")
    p.add_argument("--model", default=None, help="Ollama model (default: auto gemma/…)")
    p.add_argument("--all", action="store_true", help="Re-distill even if already present")
    p.add_argument("--report", action="store_true", help="Coverage report only")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    from fsot_nuron.lexicon_distill import coverage_report, distill_batch

    if args.report:
        rep = coverage_report()
        if args.json:
            print(json.dumps(rep, indent=2))
        else:
            print("=== LEXICON COVERAGE ===")
            print(f"role_words={rep['n_role_words']} distilled={rep['n_distilled']} "
                  f"({rep['pct_distilled']}%) missing={rep['n_missing_distill']}")
            print("targets:", rep["targets"])
            print("by_role:", rep["by_role"])
            print("FSOT_LEXICON_COVERAGE_OK")
        return 0

    rep = distill_batch(
        limit=args.limit,
        model=args.model,
        only_missing=not args.all,
    )
    cov = coverage_report()
    rep["coverage"] = {
        "n_role_words": cov["n_role_words"],
        "n_distilled": cov["n_distilled"],
        "pct_distilled": cov["pct_distilled"],
    }
    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        print("=== FSOT LEXICON DISTILL ===")
        print(f"teacher={rep.get('teacher')} added={rep['batch_added']}/{rep['batch_todo']} "
              f"errors={rep['batch_errors']}")
        print(f"path={rep['path']}")
        print(f"total_distilled={rep['n_distill']} / roles={rep['n_roles']} "
              f"({rep['coverage']['pct_distilled']}%)")
        print(rep["doctrine"])
        print("FSOT_LEXICON_DISTILL_OK" if rep["batch_errors"] == 0 or rep["batch_added"] > 0
              else "FSOT_LEXICON_DISTILL_PARTIAL")
    return 0 if rep["batch_added"] > 0 or rep["batch_todo"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
