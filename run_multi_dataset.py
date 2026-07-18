#!/usr/bin/env python3
"""Run FSOT multi-dataset scoreboard on downloaded Kaggle sets."""

from __future__ import annotations

import argparse
import json

from fsot_nuron.multi_dataset import run_scoreboard, DATA_ROOT, SCOREBOARD_PATH


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(DATA_ROOT))
    p.add_argument("--max-files", type=int, default=15)
    args = p.parse_args()

    print("=" * 64)
    print("FSOT-2.1-Neural multi-dataset scoreboard")
    print(f"root={args.root}")
    print("=" * 64)

    board = run_scoreboard(root=__import__("pathlib").Path(args.root), max_files=args.max_files)
    print(f"\nDatasets evaluated: {board['n_datasets']}")
    print("\nRank by FSOT fit score:")
    for row in board["rank_by_fsot_fit"]:
        print(
            f"  #{row['rank']:2d}  fit={row['fit']:.3f}  [{row['kind']}]  {row['name']}"
            f"  rows={row['n_rows']}  metrics={ {k:row['metrics'][k] for k in row['metrics'] if k not in ('by_label',)} }"
        )
    print(f"\nScoreboard: {SCOREBOARD_PATH}")


if __name__ == "__main__":
    main()
