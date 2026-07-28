#!/usr/bin/env python3
"""
Bio-fidelity refine cycle: score layers → pick highest below threshold → fix → retest → log.

  python run_refine_cycle.py
  python run_refine_cycle.py --threshold 70
  python run_refine_cycle.py --layer retina_like_decode
  python run_refine_cycle.py --score-only
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
    ap = argparse.ArgumentParser(description="FSOT bio refine cycle (test→log→fix→retest)")
    ap.add_argument("--threshold", type=float, default=70.0)
    ap.add_argument("--layer", default="", help="force layer_id")
    ap.add_argument(
        "--domain",
        default="all",
        choices=["all", "bio", "capability"],
        help="bio=wet-lab/sensory/learning accuracy; capability=frontier gaps",
    )
    ap.add_argument("--score-only", action="store_true")
    args = ap.parse_args()

    from fsot_nuron.refine.layers import score_all_layers, select_refine_target
    from fsot_nuron.refine.cycle import run_refine_cycle
    from fsot_nuron.paths import ARTIFACTS, DATA

    print("=== FSOT REFINE CYCLE ===")
    print(
        f"threshold={args.threshold}  domain={args.domain}  "
        f"rule=highest score still below threshold"
    )
    layers = score_all_layers(threshold=args.threshold, domain=args.domain)
    print("\n--- layer scores ---")
    for L in sorted(layers, key=lambda x: -x.score):
        mark = "BELOW" if L.below_threshold else "ok   "
        print(f"  [{mark}] {L.score:5.1f}%  {L.layer_id:28}  {L.title}")

    target = select_refine_target(
        layers, threshold=args.threshold, domain=args.domain
    )
    if target:
        print(f"\n>>> NEXT TARGET: {target.layer_id} @ {target.score:.1f}%")
    else:
        print("\n>>> all layers >= threshold")

    if args.score_only:
        return 0

    rep = run_refine_cycle(
        threshold=args.threshold,
        layer_id=args.layer or None,
        apply_fix=True,
        domain=args.domain,
    )
    print("\n--- cycle result ---")
    print(f"target: {rep.target_layer}")
    print(f"score:  {rep.before_score} → {rep.after_score}")
    for n in rep.notes:
        print(f"  {n}")

    md = DATA / "results" / "REFINE_CYCLE.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Refine cycle",
        "",
        f"Threshold: **{rep.threshold}%**  ",
        f"Target: `{rep.target_layer}`  ",
        f"Score: **{rep.before_score}** → **{rep.after_score}**",
        "",
        "## Rule",
        "",
        "Among layers **below** threshold, refine the **highest** score first.",
        "",
        "## Notes",
        "",
    ]
    for n in rep.notes:
        lines.append(f"- {n}")
    lines += ["", "## All layers (after)", ""]
    for L in rep.all_layers_after:
        flag = "below" if L.get("below_threshold") else "ok"
        lines.append(f"- [{flag}] {L['score']:.1f}% `{L['layer_id']}`")
    lines += ["", f"JSON: `{ARTIFACTS / 'refine_cycle_last.json'}`", ""]
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {md}")
    print(f"Wrote {ARTIFACTS / 'refine_cycle_last.json'}")
    print(f"Ledger: {DATA / 'refine_cycles' / 'cycles.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
