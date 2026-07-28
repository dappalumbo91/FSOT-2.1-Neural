#!/usr/bin/env python3
"""
Short-horizon learning accuracy + real-media pixel-ID.

  python run_short_horizon_learn.py
  python run_short_horizon_learn.py --videos 4 --docs 3
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
    ap = argparse.ArgumentParser(description="FSOT short-horizon learn + media pixel-ID")
    ap.add_argument("--docs", type=int, default=4)
    ap.add_argument("--videos", type=int, default=5)
    ap.add_argument("--frames", type=int, default=12)
    ap.add_argument("--no-pixel-id", action="store_true")
    ap.add_argument("--no-learning-probe", action="store_true")
    ap.add_argument("--no-caption-bind", action="store_true")
    args = ap.parse_args()

    from fsot_nuron.learn.short_horizon import run_short_horizon_learn

    print("=== FSOT SHORT-HORIZON LEARN ===")
    rep = run_short_horizon_learn(
        max_docs=args.docs,
        max_videos=args.videos,
        media_frames=args.frames,
        run_pixel_id=not args.no_pixel_id,
        run_learning_probe=not args.no_learning_probe,
        run_caption_bind=not args.no_caption_bind,
    )
    print(f"ok={rep.ok}  elapsed_min={rep.encode_minutes_est:.2f}")
    print(f"recall top1={rep.recall_top1:.3f}  @3={rep.recall_at_k:.3f}")
    print(
        f"pixel_id top1={rep.pixel_id_top1:.3f}  synthetic={rep.pixel_id_synthetic}"
    )
    print(
        f"caption_bind pairs={rep.caption_bind_pairs} names={rep.caption_bind_names} "
        f"pixel→name top1={rep.caption_bind_top1:.3f}"
    )
    print(
        f"learning_probe top1={rep.learning_probe_top1:.3f}  "
        f"margin={rep.learning_probe_margin:.3f}  SME={rep.sme_theta}/{rep.sme_gamma}"
    )
    for n in rep.notes[:12]:
        print(f"  · {n}")
    print("Wrote artifacts/short_horizon_last.json")
    print("Wrote data/results/SHORT_HORIZON_LEARN.md")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
