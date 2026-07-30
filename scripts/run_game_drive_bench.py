#!/usr/bin/env python3
"""Catalog / convert / score game-drive training data; log emergent signals (observe only).

  python scripts/run_game_drive_bench.py --catalog
  python scripts/run_game_drive_bench.py --convert --bench --limit 60
  python scripts/run_game_drive_bench.py --emergent-summary
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
    p = argparse.ArgumentParser(description="FSOT game-drive capability apparatus")
    p.add_argument("--catalog", action="store_true", help="List datasets under game data + training pack")
    p.add_argument("--convert", action="store_true", help="Convert priority benches to bank.tsv")
    p.add_argument("--bench", action="store_true", help="Run capability scoreboard")
    p.add_argument("--limit", type=int, default=80, help="Max items per dataset")
    p.add_argument("--game-data", default=os.environ.get("FSOT_GAME_DATA", r"D:\training data"))
    p.add_argument("--training", default=os.environ.get("FSOT_TRAINING_ROOT", r"D:\fsot_training"))
    p.add_argument("--emergent-summary", action="store_true", help="Summarize emergent log")
    args = p.parse_args()

    from fsot_nuron.game_drive_bench import (
        DEFAULT_OUT,
        catalog,
        log_emergent,
        detect_emergent_from_board,
        run_capability_board,
        summarize_emergent,
    )
    from pathlib import Path as P

    game = P(args.game_data)
    train = P(args.training)
    did = False

    if args.catalog or (not args.bench and not args.convert and not args.emergent_summary):
        cat = catalog(game, train)
        out = train / "capability"
        out.mkdir(parents=True, exist_ok=True)
        (out / "CATALOG.json").write_text(json.dumps(cat, indent=2), encoding="utf-8")
        print(json.dumps({k: cat[k] for k in ("generated_at", "n_hits", "n_convertible", "priority_bench")}, indent=2))
        print(f"catalog hits={cat['n_hits']} convertible={cat['n_convertible']} → {out / 'CATALOG.json'}")
        # monorepo mirror
        mono = ROOT / "data" / "results"
        if mono.is_dir():
            (mono / "GAME_DRIVE_CATALOG.json").write_text(json.dumps(cat, indent=2), encoding="utf-8")
        did = True

    if args.bench or args.convert:
        board = run_capability_board(game, train, limit=args.limit)
        print("\n=== CAPABILITY SCOREBOARD ===")
        for s in board.get("scores") or []:
            flag = "↑" if s["above_chance"] else "·"
            print(
                f"  {flag} {s['dataset']:16s} n={s['n']:3d} acc={s['accuracy']:.3f} "
                f"chance={s['chance']:.3f} correct={s['correct']}"
            )
        sm = board.get("summary") or {}
        print(
            f"\nmean_acc={sm.get('mean_acc')} above_chance={sm.get('n_above_chance')}/{sm.get('n_scored')}"
        )
        print(f"bank={board.get('bank_path')}")
        print(f"report={train / 'capability' / 'CAPABILITY_SCOREBOARD.md'}")

        events = detect_emergent_from_board(board)
        log_emergent(
            source="game_drive_bench",
            signals={
                "events": events,
                "mean_acc": sm.get("mean_acc"),
                "n_above_chance": sm.get("n_above_chance"),
                "loaded_counts": board.get("loaded_counts"),
            },
            note="capability snapshot after convert+score; observe only",
        )
        if events:
            print(f"\nEMERGENT (observe only) n={len(events)}")
            for e in events[:12]:
                print(f"  • {e}")
        did = True

    if args.emergent_summary:
        summ = summarize_emergent()
        print(json.dumps(summ, indent=2)[:4000])
        did = True

    if not did:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
