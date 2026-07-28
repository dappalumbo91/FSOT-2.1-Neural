#!/usr/bin/env python3
"""
Consolidation ladder with study-EEG couple.

Target: keep top-1 ≥ 0.5 after delay + offline consolidate on FSOT machine items,
using study EEG wet-lab couple when available.

  python run_consolidate_study.py
  python run_consolidate_study.py --items 12 --delay-steps 400
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", type=int, default=8)
    ap.add_argument("--delay-steps", type=int, default=300)
    ap.add_argument("--encode-steps", type=int, default=250)
    ap.add_argument("--retrieve-steps", type=int, default=200)
    ap.add_argument("--replay-rounds", type=int, default=2)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    from fsot_nuron.archive_pin import pin_archive
    from fsot_nuron.fsot_bridge import fold_diagnostics
    from fsot_nuron.learning_eeg_study import build_study_eeg_report
    from fsot_nuron.brain_architecture import run_brain_design_suite
    from fsot_nuron.learning_memory import learning_probe
    from fsot_nuron.paths import ARTIFACTS, DATA
    from fsot_nuron.thesis_ledger import record_run

    print("=== FSOT consolidate + study EEG ===")
    pin = pin_archive(write_snapshot=False)
    folds = fold_diagnostics()
    study = build_study_eeg_report()
    print(f"pin_ok={pin.seed_match_ok}  mental_eeg={study.mental_state_ok}")
    print(f"S_neuro={folds.get('S_Neuroscience'):+.4f}")
    if study.concentrate_vs_relax:
        print(f"study contrast: {study.concentrate_vs_relax}")

    suite = run_brain_design_suite(
        steps=150, device=args.device, profile="ai_efficient", sensory=False
    )
    brain = suite["brain"]

    print("\n--- A Immediate ---")
    imm = learning_probe(
        brain,
        n_items=args.items,
        encode_steps=args.encode_steps,
        retrieve_steps=args.retrieve_steps,
        seed=7,
        delay_steps=0,
        consolidate=False,
        item_mode="fsot_machine",
    )
    print(f"  top1={imm.top1_accuracy:.3f}")

    print(f"\n--- B Delay {args.delay_steps} ---")
    delayed = learning_probe(
        brain,
        n_items=args.items,
        encode_steps=args.encode_steps,
        retrieve_steps=args.retrieve_steps,
        seed=7,
        delay_steps=args.delay_steps,
        consolidate=False,
        item_mode="fsot_machine",
    )
    print(f"  top1={delayed.top1_accuracy:.3f}  imm_was={delayed.top1_immediate:.3f}")

    print("\n--- C Delay + offline consolidate ---")
    cons = learning_probe(
        brain,
        n_items=args.items,
        encode_steps=args.encode_steps,
        retrieve_steps=args.retrieve_steps,
        seed=7,
        delay_steps=max(50, args.delay_steps // 2),
        consolidate=True,
        consolidate_rest_steps=350,
        replay_rounds=args.replay_rounds,
        replay_steps=100,
        item_mode="fsot_machine",
    )
    print(
        f"  top1={cons.top1_accuracy:.3f}  "
        f"imm={cons.top1_immediate:.3f}  after_delay={cons.top1_after_delay:.3f}"
    )

    chance = 1.0 / max(1, args.items)
    gates = {
        "pin_seed_ok": pin.seed_match_ok,
        "mental_eeg_loaded": study.mental_state_ok,
        "study_theta_or_beta_up": study.gates.get("concentrate_theta_or_beta_elevated", False),
        "immediate_ge_half": imm.top1_accuracy >= 0.5,
        "delay_ge_half": delayed.top1_accuracy >= 0.5,
        "consolidate_ge_half": cons.top1_accuracy >= 0.5,
        "consolidate_above_chance": cons.top1_accuracy > chance,
        "sme_theta": cons.sme_theta_encode_gt_rest,
        "sme_gamma": cons.sme_gamma_encode_gt_rest,
        "delay_not_worse_than_chance": delayed.top1_accuracy > chance,
    }
    print("\n--- Gates ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": vars(args),
        "study_eeg": {
            "mental_ok": study.mental_state_ok,
            "contrast": study.concentrate_vs_relax,
            "couple": study.fsot_couple,
        },
        "fsot_folds": folds,
        "results": {
            "immediate": imm.to_dict(),
            "delay": delayed.to_dict(),
            "consolidate": cons.to_dict(),
        },
        "gates": gates,
        "chance": chance,
        "target": "top-1 ≥ 0.5 after consolidate; study EEG wet-lab couple",
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "consolidate_study.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    res = DATA / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "consolidate_study.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    md = [
        "# Consolidate + study EEG",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        f"| Condition | Top-1 |",
        f"|-----------|------:|",
        f"| Immediate | {imm.top1_accuracy:.3f} |",
        f"| After delay | {delayed.top1_accuracy:.3f} |",
        f"| After consolidate | {cons.top1_accuracy:.3f} |",
        "",
        f"Chance: {chance:.3f} · items={args.items}",
        "",
        "## Gates",
        "",
        *[f"- `{k}`: **{v}**" for k, v in gates.items()],
        "",
    ]
    (res / "CONSOLIDATE_STUDY.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {res / 'CONSOLIDATE_STUDY.md'}")

    record_run(
        "consolidate_study_eeg",
        profile="ai_efficient",
        gates=gates,
        metrics={
            "imm": imm.top1_accuracy,
            "delay": delayed.top1_accuracy,
            "cons": cons.top1_accuracy,
            "items": args.items,
        },
        notes="consolidate ladder + study EEG",
    )

    ok = (
        gates["pin_seed_ok"]
        and gates["consolidate_above_chance"]
        and gates["consolidate_ge_half"]
        and gates["sme_theta"]
        and gates["sme_gamma"]
    )
    print("\nPASS" if ok else "\nFAIL (frontier — see gates)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
