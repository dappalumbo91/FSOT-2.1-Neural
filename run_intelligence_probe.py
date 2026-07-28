#!/usr/bin/env python3
"""
Intelligence probe on wet-lab-accurate FSOT neurons.

1) Multi-region brain
2) Scalpel lock class rates to Allen (≤2% default)
3) Encode → retrieve item memory (fingerprint)
4) Learning-band SME-style proxies

North star: accurate neurons → intelligence dynamics (not NLP scoreboard).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="FSOT intelligence probe")
    ap.add_argument("--profile", default="ai_efficient", choices=["ai_efficient", "wetware_ref"])
    ap.add_argument("--tol", type=float, default=0.02, help="scalpel rate tol")
    ap.add_argument("--items", type=int, default=6)
    ap.add_argument("--encode-steps", type=int, default=400)
    ap.add_argument("--retrieve-steps", type=int, default=300)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--skip-scalpel", action="store_true")
    args = ap.parse_args()

    from fsot_nuron.scalpel_brain import build_scalpel_brain, scalpel_lock_brain
    from fsot_nuron.brain_architecture import run_brain_design_suite
    from fsot_nuron.learning_memory import learning_probe
    from fsot_nuron.thesis_ledger import record_run
    from fsot_nuron.paths import ARTIFACTS, DATA
    from fsot_nuron.archive_pin import pin_archive

    print("=== FSOT intelligence probe ===")
    print("accurate neurons → multi-region brain → encode/retrieve memory")
    print(f"profile={args.profile} scalpel_tol={args.tol:.0%} items={args.items}")

    pin = pin_archive(write_snapshot=False)
    print(f"archive pin seed_ok: {pin.seed_match_ok}")

    if args.skip_scalpel:
        suite = run_brain_design_suite(
            steps=400, device=args.device, profile=args.profile, sensory=False
        )
        brain = suite["brain"]
        scalpel_meta = {"scalpel_ok": False, "skipped": True}
        report = None
    else:
        brain, report, scalpel_meta = build_scalpel_brain(
            profile=args.profile, device=args.device, tol=args.tol
        )

    print("\n--- Scalpel (Allen class rates on brain units) ---")
    if report is not None:
        for lab, st in sorted(report.classes.items()):
            print(
                f"  {lab:4} target={st.target_Hz:6.2f} measured={st.measured_Hz:6.2f} "
                f"err={st.rel_err:5.1%}"
            )
        print(f"  scalpel_ok: {report.ok}")
    else:
        print("  skipped")

    print("\n--- Encode / retrieve ---")
    learn = learning_probe(
        brain,
        n_items=args.items,
        encode_steps=args.encode_steps,
        retrieve_steps=args.retrieve_steps,
        seed=7,
    )
    print(f"  top1_accuracy:     {learn.top1_accuracy:.3f}")
    print(f"  mean_correct_sim:  {learn.mean_correct_sim:.3f}")
    print(f"  mean_incorrect_sim:{learn.mean_incorrect_sim:.3f}")
    print(f"  SME theta enc>rest:{learn.sme_theta_encode_gt_rest}")
    print(f"  SME gamma enc>rest:{learn.sme_gamma_encode_gt_rest}")

    # Gates: bio foundation + intelligence primitive above chance
    chance = 1.0 / max(1, args.items)
    gates = {
        "pin_seed_ok": bool(pin.seed_match_ok),
        "scalpel_ok": bool(scalpel_meta.get("scalpel_ok", args.skip_scalpel)),
        "retrieve_above_chance": learn.top1_accuracy > chance + 1e-9,
        "retrieve_ge_half": learn.top1_accuracy >= 0.5,
        "correct_sim_gt_incorrect": learn.mean_correct_sim > learn.mean_incorrect_sim,
        "sme_theta_direction": learn.sme_theta_encode_gt_rest,
        "sme_gamma_direction": learn.sme_gamma_encode_gt_rest,
    }
    print("\n--- Gates ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mission": "accurate FSOT neurons → multi-region intelligence probe",
        "accuracy_standard": "docs/ACCURACY_STANDARD.md",
        "learning_alignment": "docs/LEARNING_ALIGNMENT.md",
        "scalpel": scalpel_meta,
        "scalpel_detail": report.to_dict() if report is not None else None,
        "learning": learn.to_dict(),
        "gates": gates,
        "chance_accuracy": chance,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "intelligence_probe.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    res = DATA / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "intelligence_probe.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    md = [
        "# FSOT intelligence probe",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        "## Foundation",
        "",
        f"- Archive pin: **{gates['pin_seed_ok']}**",
        f"- Scalpel Allen class rates (tol {args.tol:.0%}): **{gates['scalpel_ok']}**",
        "",
        "## Memory (encode → retrieve)",
        "",
        f"- Items: {learn.n_items} (chance {chance:.2f})",
        f"- Top-1 accuracy: **{learn.top1_accuracy:.3f}**",
        f"- Mean sim correct / incorrect: **{learn.mean_correct_sim:.3f}** / **{learn.mean_incorrect_sim:.3f}**",
        "",
        "## Learning bands (SME-style direction)",
        "",
        f"- Theta encode > rest: **{learn.sme_theta_encode_gt_rest}**",
        f"- Gamma encode > rest: **{learn.sme_gamma_encode_gt_rest}**",
        "",
        "## Gates",
        "",
        *[f"- `{k}`: **{v}**" for k, v in gates.items()],
        "",
        "Neuron accuracy first; intelligence is dynamics on that substrate.",
        "",
    ]
    (res / "INTELLIGENCE_PROBE.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {res / 'INTELLIGENCE_PROBE.md'}")

    record_run(
        "intelligence_probe",
        profile=args.profile,
        gates=gates,
        metrics={
            "top1": learn.top1_accuracy,
            "correct_sim": learn.mean_correct_sim,
            "incorrect_sim": learn.mean_incorrect_sim,
            "scalpel": scalpel_meta.get("class_rel_err"),
        },
        notes="scalpel brain + encode/retrieve fingerprint memory",
    )

    # Must have bio lock (unless skipped) and above-chance structured retrieval
    ok = gates["pin_seed_ok"] and (
        gates["scalpel_ok"] or args.skip_scalpel
    ) and gates["retrieve_above_chance"] and gates["correct_sim_gt_incorrect"]
    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
