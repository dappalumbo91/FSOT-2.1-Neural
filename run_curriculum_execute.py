#!/usr/bin/env python3
"""
Execute gap curriculum as chained short-horizon learning units.

  python run_curriculum_execute.py
  python run_curriculum_execute.py --steps 3 --videos 2 --docs 2
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="FSOT curriculum = chain of short-horizon units")
    ap.add_argument("--steps", type=int, default=3)
    ap.add_argument("--docs", type=int, default=2)
    ap.add_argument("--videos", type=int, default=2)
    ap.add_argument("--frames", type=int, default=8)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    from fsot_nuron.learn.curriculum_execute import execute_curriculum

    print("=== FSOT CURRICULUM EXECUTE ===")
    print("unit = short_horizon · chain = gap plan steps")
    rep = execute_curriculum(
        max_steps=args.steps,
        docs_per_step=args.docs,
        videos_per_step=args.videos,
        frames_per_step=args.frames,
        seed=args.seed,
    )
    print(f"ok={rep.ok} steps={rep.n_steps}")
    print(
        f"recall {rep.before_recall:.3f} → {rep.after_recall:.3f} "
        f"(Δ={rep.metric_delta_recall:+.3f})"
    )
    print(
        f"pixel  {rep.before_pixel:.3f} → {rep.after_pixel:.3f} "
        f"(Δ={rep.metric_delta_pixel:+.3f})"
    )
    print(
        f"caption→name {rep.before_caption:.3f} → {rep.after_caption:.3f}"
    )
    for s in rep.step_results:
        print(
            f"  step {s.step} {s.target_symbol}: recall={s.recall_top1:.3f} "
            f"pixel={s.pixel_id_top1:.3f} cap={s.caption_bind_top1:.3f}"
        )
    print("Wrote artifacts/curriculum_execute_last.json")
    print("Wrote data/results/CURRICULUM_EXECUTE.md")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
