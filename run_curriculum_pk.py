#!/usr/bin/env python3
"""PK/K/G1 curriculum: ensure lexicon, expand facts (Ollama), report coverage.

Examples:
  python run_curriculum_pk.py --ensure-lexicon --target 2000
  python run_curriculum_pk.py --expand-facts 15 --model gemma:7b
  python run_curriculum_pk.py --report
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
    p = argparse.ArgumentParser(description="FSOT preschool–G1 curriculum teacher")
    p.add_argument("--ensure-lexicon", action="store_true", help="Grow en_roles to cover curriculum + target")
    p.add_argument("--target", type=int, default=2000, help="Lexicon size target")
    p.add_argument("--expand-facts", type=int, default=0, help="Ollama-add N new facts")
    p.add_argument("--grade", default="kindergarten", help="Grade for new facts")
    p.add_argument("--model", default=None, help="Ollama model")
    p.add_argument("--report", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    from fsot_nuron.curriculum_pk import ensure_lexicon_for_curriculum, expand_facts_ollama, report
    from fsot_nuron.lexicon_teacher import teach

    out: dict = {}

    if args.ensure_lexicon:
        # offline bulk first toward target
        out["lexicon_offline"] = teach(offline=True, llm=False, target=args.target)
        out["lexicon_curriculum"] = ensure_lexicon_for_curriculum(target_lex=args.target)

    if args.expand_facts > 0:
        out["facts"] = expand_facts_ollama(n=args.expand_facts, grade=args.grade, model=args.model)

    if args.report or not out:
        out["report"] = report()

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print("=== FSOT PK/K/G1 CURRICULUM ===")
        if "lexicon_offline" in out:
            lo = out["lexicon_offline"]
            print(f"lexicon offline {lo['before']} → {lo['after']} (+{lo['added']})")
        if "lexicon_curriculum" in out:
            lc = out["lexicon_curriculum"]
            print(f"curriculum keywords missing={lc['n_missing']} lex={lc['lexicon_after']}")
        if "facts" in out:
            print(f"facts added={out['facts']['added_facts']} total={out['facts']['total_facts']}")
        if "report" in out:
            r = out["report"]
            print(f"facts={r['n_facts']} problems={r['n_problems']} "
                  f"keyword_cov={r['keyword_coverage_pct']}% lex={r['lexicon_size']}")
            print("targets:", r["targets"])
            print(r["doctrine"])
        print("FSOT_CURRICULUM_PK_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
