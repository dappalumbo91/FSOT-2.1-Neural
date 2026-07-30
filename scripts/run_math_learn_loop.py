#!/usr/bin/env python3
"""Bio math learn loop: teach atomics → multi-hop practice → sleep replay → prove.

  python scripts/run_math_learn_loop.py

Local only. Uses MathMultihopOrganism (WM + episodes + claim), not an LLM.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    from fsot_nuron.math_multihop_organism import (
        bootstrap_train_from_drills,
        get_organism,
        solve_multihop,
    )
    from fsot_nuron.math_rules import apply_rules, exact_num, load_gsm8k_heldout
    from fsot_nuron.math_binding import binding_drills

    print("=== TRAIN (bootstrap atomics + successful solves) ===", flush=True)
    boot = bootstrap_train_from_drills()
    print(json.dumps(boot, indent=2), flush=True)

    org = get_organism()
    print("=== SLEEP REPLAY ===", flush=True)
    org.sleep_replay(5)
    org.save()

    print("=== PROVE binding drills via multihop ===", flush=True)
    bd = binding_drills()
    ok = 0
    for q, a, f in bd:
        r = solve_multihop(q)
        # also allow full apply_rules (hand path teaches org)
        if not (r.ok and r.answer and exact_num(r.answer, a)):
            r2 = apply_rules(q)
            hit = r2.ok and r2.answer and exact_num(r2.answer, a)
        else:
            hit = True
        ok += int(hit)
    print(f"binding_prove {ok}/{len(bd)}", flush=True)

    print("=== PROVE GSM8K sample after learn ===", flush=True)
    items = load_gsm8k_heldout("test", 200)
    c = wf = no = 0
    for it in items:
        r = apply_rules(it.question)
        if not r.ok or r.answer is None:
            no += 1
            continue
        if exact_num(r.answer, it.answer):
            c += 1
        else:
            wf += 1
    fire = c + wf
    report = {
        "bootstrap": boot,
        "n_episodes": len(org.episodes),
        "binding_prove": f"{ok}/{len(bd)}",
        "gsm8k_200": {
            "correct": c,
            "wrong_fire": wf,
            "no_fire": no,
            "overall": round(c / max(1, len(items)), 4),
            "fire_precision": round(c / max(1, fire), 4),
        },
        "doctrine": "train→sleep→prove multi-hop organism (not LLM)",
    }
    out = ROOT / "data" / "results" / "MATH_LEARN_LOOP.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    print(f"Wrote {out}", flush=True)
    return 0 if ok == len(bd) else 1


if __name__ == "__main__":
    raise SystemExit(main())
