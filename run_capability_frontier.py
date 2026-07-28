#!/usr/bin/env python3
"""
Log / display capability frontier (claims we do not yet make).

  python run_capability_frontier.py
  python run_capability_frontier.py --history 15
  python run_capability_frontier.py --bootstrap
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="FSOT capability frontier tracker")
    ap.add_argument("--history", type=int, default=0, help="show last N ledger rows")
    ap.add_argument("--bootstrap", action="store_true", help="force baseline snapshot + docs")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    from fsot_nuron.capability_frontier import (
        log_frontier,
        read_latest,
        read_history,
        write_capability_frontier_doc,
        CLAIM_DEFS,
        FRONTIER_DIR,
    )

    if args.bootstrap or read_latest() is None:
        row = log_frontier(
            experiment="frontier_baseline",
            notes=args.notes or "Baseline: three unclaimed/partial gaps tracked going forward.",
        )
    else:
        row = log_frontier(
            experiment="frontier_snapshot",
            notes=args.notes or "Periodic frontier snapshot.",
        )

    print("=== CAPABILITY FRONTIER ===")
    print(f"ts={row.get('ts_utc')}  git={row.get('git_sha')}")
    print(f"ledger: {FRONTIER_DIR / 'frontier_runs.jsonl'}")
    print(f"status: {FRONTIER_DIR / 'STATUS.md'}")
    print(f"docs:   docs/CAPABILITY_FRONTIER.md")
    print()
    claims = row.get("claims") or {}
    for cid, meta in CLAIM_DEFS.items():
        c = claims.get(cid) or {}
        print(f"[{c.get('status', '?'):10}] {meta['title']}")
        print(f"             {meta['short']}")
        print(f"             note: {c.get('status_note', '')}")
        print(f"             metrics: {json.dumps(c.get('metrics') or {})}")
        print()

    if args.history > 0:
        hist = read_history(limit=args.history)
        print(f"--- history ({len(hist)}) ---")
        for h in hist:
            cl = h.get("claims") or {}
            sts = {k: (cl.get(k) or {}).get("status") for k in CLAIM_DEFS}
            print(f"  {h.get('ts_utc')}  {h.get('experiment')}  {sts}")

    write_capability_frontier_doc(row)
    print("OK — frontier logged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
