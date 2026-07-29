#!/usr/bin/env python3
"""
Visual individual identity — look first, name second.

  python run_visual_individual.py
  python run_visual_individual.py --videos 6 --frames 28
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
    ap = argparse.ArgumentParser(description="VIU: visual individual identity probe")
    ap.add_argument("--videos", type=int, default=6)
    ap.add_argument("--frames", type=int, default=28)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    from fsot_nuron.knowledge.visual_individual import run_visual_individual_probe
    from fsot_nuron.capability_frontier import log_frontier, CLAIM_OPEN_WORLD

    print("=== FSOT VISUAL INDIVIDUAL IDENTITY ===")
    print("Stage 1: cluster looks into VIUs (no names required)")
    print("Stage 2: bind caption names onto the active VIU")
    print("Stage 3: pixels only → nearest VIU (tutor-ablated)")
    rep = run_visual_individual_probe(
        max_videos=args.videos,
        max_frames=args.frames,
        seed=args.seed,
    )
    print(f"ok={rep.ok}")
    print(
        f"VIU re-ID top1={rep.viu_reid_top1:.3f}  chance≈{rep.viu_reid_chance:.3f}  "
        f"heldout={rep.n_heldout}"
    )
    print(
        f"unique-name top1={rep.unique_name_top1:.3f}  "
        f"trials={rep.n_unique_name_trials}  n_viu={rep.n_viu} named={rep.n_named_viu}"
    )
    for n in rep.notes[-6:]:
        print(f"  · {n}")

    # Frontier: progress = VIU re-ID, not name-bag
    status = "unclaimed"
    if rep.n_heldout >= 8 and rep.viu_reid_top1 > rep.viu_reid_chance + 0.05:
        status = "probing"
    if (
        rep.n_heldout >= 12
        and rep.viu_reid_top1 >= 0.45
        and rep.n_viu >= 3
    ):
        status = "partial"
    if (
        rep.n_heldout >= 20
        and rep.viu_reid_top1 >= 0.70
        and rep.unique_name_top1 >= 0.50
        and rep.n_unique_name_trials >= 5
    ):
        status = "claimed"

    log_frontier(
        experiment="visual_individual_identity",
        related_metrics={
            "pixel_id_top1": rep.viu_reid_top1,
            "pixel_id_chance": rep.viu_reid_chance,
            "n_characters": rep.n_named_viu,
            "n_heldout_clips": rep.n_heldout,
            "tutor_ablated": True,
            "viu_reid_top1": rep.viu_reid_top1,
            "unique_name_top1": rep.unique_name_top1,
            "n_viu": rep.n_viu,
        },
        notes=(
            f"VIU-first identity status={status} re-id={rep.viu_reid_top1:.3f} "
            f"unique_name={rep.unique_name_top1:.3f} n_viu={rep.n_viu}"
        ),
        overrides={
            CLAIM_OPEN_WORLD: {
                "status": status,
                "status_note": (
                    f"VIU-first: look→individual then name bind; "
                    f"re-id={rep.viu_reid_top1:.3f} chance≈{rep.viu_reid_chance:.3f} "
                    f"unique_name={rep.unique_name_top1:.3f} "
                    f"(name-bag franchise protocol retired as primary)"
                ),
                "metrics": {
                    "pixel_id_top1": rep.viu_reid_top1,
                    "pixel_id_chance": rep.viu_reid_chance,
                    "n_characters": rep.n_named_viu,
                    "n_heldout_clips": rep.n_heldout,
                    "tutor_ablated": True,
                    "viu_reid_top1": rep.viu_reid_top1,
                    "unique_name_top1": rep.unique_name_top1,
                    "n_viu": rep.n_viu,
                },
            }
        },
    )
    print(f"frontier status → {status}")
    print("Wrote data/results/VISUAL_INDIVIDUAL.md")
    print("Doctrine: docs/VISUAL_INDIVIDUAL_IDENTITY.md")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
