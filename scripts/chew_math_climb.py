#!/usr/bin/env python3
"""Local math climb — score GSM8K + drills offline. No cloud APIs.

  python scripts/chew_math_climb.py
  python scripts/chew_math_climb.py --test 1319

Budget: run this yourself between chat sessions; only open chat when
cluster report shows a new family to wire.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", type=int, default=1319)
    args = ap.parse_args()

    from fsot_nuron.math_rules import (
        PASS,
        apply_rules,
        build_rule_drills,
        exact_num,
        load_gsm8k_heldout,
        score_items,
    )
    from fsot_nuron.math_binding import binding_drills
    from fsot_nuron.math_sense_interlingua import MathSenseInterlingua

    drills = score_items(build_rule_drills())
    bd = binding_drills()
    bd_ok = sum(
        1
        for q, a, _ in bd
        if (r := apply_rules(q)).ok and r.answer and exact_num(r.answer, a)
    )

    items = load_gsm8k_heldout("test", args.test)
    ix = MathSenseInterlingua()
    c = wf = no = 0
    sense_ready = 0
    tags = Counter()
    for it in items:
        r = apply_rules(it.question)
        if r.ok and r.answer and exact_num(r.answer, it.answer):
            c += 1
            continue
        if r.ok and r.answer:
            wf += 1
            continue
        no += 1
        cue = ix.translate_cues(it.question)
        if cue.strategies:
            sense_ready += 1
        ql = it.question.lower()
        for name, pat in [
            ("money", r"\$"),
            ("percent", r"%|percent"),
            ("each", r"\beach\b"),
            ("week", r"week"),
            ("times", r"times as"),
            ("left", r"left|remain"),
            ("rate", r"per hour|per day"),
            ("ratio", r"ratio"),
        ]:
            if re.search(pat, ql):
                tags[name] += 1

    fire = c + wf
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "drills_acc": drills["accuracy"],
        "drills_n": drills["n"],
        "drills_pass": drills["accuracy"] >= PASS,
        "binding_drills": f"{bd_ok}/{len(bd)}",
        "gsm8k": {
            "n": len(items),
            "correct": c,
            "wrong_fire": wf,
            "no_fire": no,
            "fire": fire,
            "precision": round(c / max(1, fire), 4),
            "recall": round(c / max(1, len(items)), 4),
        },
        "nofire_sense_ready": sense_ready,
        "nofire_tags": dict(tags.most_common()),
        "note": (
            "Local only. Sense-ready no-fires need executors, not more chat. "
            "Wire largest tag families in one batch."
        ),
    }
    out = ROOT / "data" / "results" / "MATH_CHEW_CLIMB.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {out}")
    return 0 if report["drills_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
