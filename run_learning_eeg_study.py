#!/usr/bin/env python3
"""
Study / learning EEG wet-lab path → FSOT memory probe.

Uses local public EEG CSVs when present (mental-state concentrate vs relax)
plus literature SME priors, then runs FSOT-bridged encode/retrieve.

  python run_learning_eeg_study.py
  python run_learning_eeg_study.py --items 8 --delay-steps 300
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
    ap = argparse.ArgumentParser(description="FSOT learning EEG study path")
    ap.add_argument("--items", type=int, default=6)
    ap.add_argument("--delay-steps", type=int, default=200)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    from fsot_nuron.archive_pin import pin_archive
    from fsot_nuron.fsot_bridge import fold_diagnostics
    from fsot_nuron.learning_eeg_study import (
        build_study_eeg_report,
        run_sme_probe_with_study_eeg,
    )
    from fsot_nuron.paths import ARTIFACTS, DATA
    from fsot_nuron.thesis_ledger import record_run

    print("=== FSOT learning / study EEG path ===")
    print("Wet-lab public EEG + literature SME → memory probe (FSOT couple)")

    pin = pin_archive(write_snapshot=False)
    folds = fold_diagnostics()
    print(f"pin seed_ok={pin.seed_match_ok}  S_neuro={folds.get('S_Neuroscience'):+.4f}")

    study = build_study_eeg_report()
    print("\n--- Study EEG inventory ---")
    print(f"  mental-state: {study.mental_state_ok}  path={study.mental_state_path}")
    print(f"  labels: {study.mental_label_counts}")
    print(f"  concentrate_vs_relax: {study.concentrate_vs_relax}")
    print(f"  emotions: {study.emotions_ok}")
    print(f"  literature priors: {list(study.literature.keys())}")

    print("\n--- SME memory probe (FSOT machine items) ---")
    out = run_sme_probe_with_study_eeg(
        n_items=args.items,
        delay_steps=args.delay_steps,
        device=args.device,
    )
    learn = out["learning"]
    gates = out["gates"]
    print(f"  top1={learn.get('top1_accuracy'):.3f}")
    print(f"  SME theta_enc>rest={learn.get('sme_theta_encode_gt_rest')}  gamma={learn.get('sme_gamma_encode_gt_rest')}")
    print("\n--- Gates ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pin_seed_ok": pin.seed_match_ok,
        "fsot_folds": folds,
        **out,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "learning_eeg_study.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    res = DATA / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "learning_eeg_study.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    md = [
        "# Learning EEG study path",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        f"- Mental-state EEG loaded: **{study.mental_state_ok}**",
        f"- Top-1: **{learn.get('top1_accuracy'):.3f}**",
        f"- SME theta↑: **{learn.get('sme_theta_encode_gt_rest')}** gamma↑: **{learn.get('sme_gamma_encode_gt_rest')}**",
        "",
        "## Gates",
        "",
        *[f"- `{k}`: **{v}**" for k, v in gates.items()],
        "",
        "See `docs/LEARNING_EEG_STUDY.md`, `docs/LEARNING_ALIGNMENT.md`.",
        "",
    ]
    (res / "LEARNING_EEG_STUDY.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {res / 'LEARNING_EEG_STUDY.md'}")

    record_run(
        "learning_eeg_study",
        profile="ai_efficient",
        gates=gates,
        metrics={
            "top1": learn.get("top1_accuracy"),
            "mental_ok": study.mental_state_ok,
            "items": args.items,
        },
        notes="study EEG wet-lab path + SME probe",
    )

    ok = (
        pin.seed_match_ok
        and gates.get("literature_sme_direction_ok")
        and gates.get("top1_above_chance")
    )
    # mental CSV optional for PASS if literature SME direction holds
    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
