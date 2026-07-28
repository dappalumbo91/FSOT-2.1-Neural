#!/usr/bin/env python3
"""
Intelligence probe on wet-lab-accurate FSOT neurons.

Climbs:
  - more items + retention delay
  - offline consolidation (sleep-like rest + replay)
  - (Zig fingerprints via embodiment/zig QEMU — separate)

Default: scalpel ≤1% when stable else 2%.
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
    ap.add_argument("--tol", type=float, default=0.01, help="scalpel rate tol (try 1%)")
    ap.add_argument("--items", type=int, default=12, help="memory list length")
    ap.add_argument("--encode-steps", type=int, default=350)
    ap.add_argument("--retrieve-steps", type=int, default=280)
    ap.add_argument("--delay-steps", type=int, default=500, help="retention delay (model-ms)")
    ap.add_argument("--consolidate", action="store_true", help="offline rest+replay")
    ap.add_argument("--no-consolidate", action="store_true", help="disable consolidate")
    ap.add_argument("--replay-rounds", type=int, default=2)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--skip-scalpel", action="store_true")
    ap.add_argument("--suite", action="store_true", help="run delay + consolidate suite")
    ap.add_argument(
        "--item-mode",
        default="fsot_machine",
        choices=["fsot_machine", "random"],
        help="fsot_machine (default): labels via machine encode + FSOT bridge; random=legacy",
    )
    args = ap.parse_args()

    consolidate = args.consolidate or (args.suite and not args.no_consolidate)
    if args.suite and not args.consolidate and not args.no_consolidate:
        consolidate = True

    from fsot_nuron.scalpel_brain import build_scalpel_brain
    from fsot_nuron.brain_architecture import run_brain_design_suite
    from fsot_nuron.learning_memory import learning_probe
    from fsot_nuron.thesis_ledger import record_run
    from fsot_nuron.paths import ARTIFACTS, DATA
    from fsot_nuron.archive_pin import pin_archive
    from fsot_nuron.fsot_bridge import fold_diagnostics
    from fsot_nuron.scalpel_rate import scalpel_calibrate
    from fsot_nuron.class_ephys import build_class_targets
    from fsot_nuron.cell_types import build_typed_population
    from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
    import torch

    print("=== FSOT intelligence probe ===")
    print("accurate neurons → multi-region brain → encode/delay/consolidate/retrieve")
    print(
        f"profile={args.profile} scalpel_tol={args.tol:.0%} items={args.items} "
        f"delay={args.delay_steps} consolidate={consolidate} item_mode={args.item_mode}"
    )

    pin = pin_archive(write_snapshot=False)
    print(f"archive pin seed_ok: {pin.seed_match_ok}")
    folds = fold_diagnostics()
    print(
        f"FSOT folds  S_bio={folds.get('S_Biology'):+.4f}  "
        f"S_neuro={folds.get('S_Neuroscience'):+.4f}  "
        f"S_body={folds.get('S_Computer_Body'):+.4f}  pin_ok={folds.get('pin_ok')}"
    )

    # --- Scalpel 1% with fallback to 2% ---
    scalpel_tol_used = args.tol
    report = None
    scalpel_meta = {"scalpel_ok": False}

    if not args.skip_scalpel:
        brain, report, scalpel_meta = build_scalpel_brain(
            profile=args.profile, device=args.device, tol=args.tol
        )
        if not report.ok and args.tol <= 0.01:
            print("scalpel 1% not stable — falling back to 2%")
            scalpel_tol_used = 0.02
            brain, report, scalpel_meta = build_scalpel_brain(
                profile=args.profile, device=args.device, tol=0.02
            )
        scalpel_meta["tol_used"] = scalpel_tol_used
    else:
        suite = run_brain_design_suite(
            steps=400, device=args.device, profile=args.profile, sensory=False
        )
        brain = suite["brain"]
        scalpel_meta = {"scalpel_ok": False, "skipped": True, "tol_used": None}

    print("\n--- Scalpel (Allen class rates on brain units) ---")
    if report is not None:
        for lab, st in sorted(report.classes.items()):
            print(
                f"  {lab:4} target={st.target_Hz:6.2f} measured={st.measured_Hz:6.2f} "
                f"err={st.rel_err:5.1%}"
            )
        print(f"  scalpel_ok: {report.ok}  tol_used={scalpel_tol_used:.0%}")
    else:
        print("  skipped")

    def run_probe(**kw):
        return learning_probe(
            brain,
            n_items=args.items,
            encode_steps=args.encode_steps,
            retrieve_steps=args.retrieve_steps,
            seed=7,
            item_mode=args.item_mode,
            **kw,
        )

    results = {}

    # A) Immediate (baseline)
    print("\n--- A) Immediate encode/retrieve ---")
    learn_imm = run_probe(delay_steps=0, consolidate=False)
    print(f"  top1={learn_imm.top1_accuracy:.3f}  sim+={learn_imm.mean_correct_sim:.3f}")
    results["immediate"] = learn_imm.to_dict()

    # B) Retention delay
    print(f"\n--- B) Retention delay ({args.delay_steps} model-ms) ---")
    learn_del = run_probe(delay_steps=args.delay_steps, consolidate=False)
    print(
        f"  top1={learn_del.top1_accuracy:.3f}  "
        f"immediate_was={learn_del.top1_immediate:.3f}"
    )
    results["delay"] = learn_del.to_dict()

    # C) Offline consolidation
    if consolidate or args.suite:
        print("\n--- C) Offline consolidation (rest + replay) ---")
        learn_con = run_probe(
            delay_steps=args.delay_steps // 2,
            consolidate=True,
            consolidate_rest_steps=400,
            replay_rounds=args.replay_rounds,
            replay_steps=120,
        )
        print(
            f"  top1={learn_con.top1_accuracy:.3f}  "
            f"imm={learn_con.top1_immediate:.3f}  "
            f"after_delay={learn_con.top1_after_delay:.3f}  "
            f"sigma_rel_replay={learn_con.consolidate_sigma_rel}"
        )
        results["consolidate"] = learn_con.to_dict()
        learn_final = learn_con
    else:
        learn_final = learn_del

    chance = 1.0 / max(1, args.items)
    gates = {
        "pin_seed_ok": bool(pin.seed_ok if hasattr(pin, "seed_ok") else pin.seed_match_ok),
        "scalpel_ok": bool(scalpel_meta.get("scalpel_ok", args.skip_scalpel)),
        "scalpel_tol_1pct_or_fallback": bool(
            scalpel_meta.get("tol_used") is None
            or scalpel_meta.get("tol_used", 1) <= 0.02
        ),
        "immediate_above_chance": learn_imm.top1_accuracy > chance,
        "delay_above_chance": learn_del.top1_accuracy > chance,
        "delay_ge_half": learn_del.top1_accuracy >= 0.5,
        "correct_sim_gt_incorrect": learn_final.mean_correct_sim
        > learn_final.mean_incorrect_sim,
        "sme_theta_direction": learn_final.sme_theta_encode_gt_rest,
        "sme_gamma_direction": learn_final.sme_gamma_encode_gt_rest,
    }
    if "consolidate" in results:
        gates["consolidate_above_chance"] = learn_final.top1_accuracy > chance
        gates["consolidate_ge_half"] = learn_final.top1_accuracy >= 0.5

    print("\n--- Gates ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mission": "retention + consolidation on scalpel-accurate FSOT brain",
        "doctrine": "pin→fold→bridge→couple; item_mode=" + args.item_mode,
        "fsot_folds": folds,
        "scalpel": scalpel_meta,
        "scalpel_detail": report.to_dict() if report is not None else None,
        "results": results,
        "gates": gates,
        "chance_accuracy": chance,
        "params": {
            "items": args.items,
            "delay_steps": args.delay_steps,
            "consolidate": consolidate,
            "tol": scalpel_meta.get("tol_used"),
            "item_mode": args.item_mode,
        },
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "intelligence_probe.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    res = DATA / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "intelligence_probe.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )

    md = [
        "# FSOT intelligence probe — retention & consolidation",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        f"- Items: **{args.items}** (chance {chance:.3f})",
        f"- Delay: **{args.delay_steps}** model-ms",
        f"- Consolidate: **{consolidate}**",
        f"- Scalpel tol used: **{scalpel_meta.get('tol_used')}** ok={scalpel_meta.get('scalpel_ok')}",
        f"- Item mode: **{args.item_mode}**",
        f"- S_Biology: **{folds.get('S_Biology')}** · S_Neuroscience: **{folds.get('S_Neuroscience')}**",
        "",
        "## Accuracy ladder",
        "",
        f"| Condition | Top-1 |",
        f"|-----------|------:|",
        f"| Immediate | {learn_imm.top1_accuracy:.3f} |",
        f"| After delay | {learn_del.top1_accuracy:.3f} |",
    ]
    if "consolidate" in results:
        md.append(f"| After consolidate | {learn_final.top1_accuracy:.3f} |")
    md += [
        "",
        "## Gates",
        "",
        *[f"- `{k}`: **{v}**" for k, v in gates.items()],
        "",
        "See `docs/STAGE_INTELLIGENCE_PROBE.md`, `docs/LEARNING_ALIGNMENT.md`.",
        "",
    ]
    (res / "INTELLIGENCE_PROBE.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {res / 'INTELLIGENCE_PROBE.md'}")

    record_run(
        "intelligence_probe_retention",
        profile=args.profile,
        gates=gates,
        metrics={
            "immediate": learn_imm.top1_accuracy,
            "delay": learn_del.top1_accuracy,
            "final": learn_final.top1_accuracy,
            "items": args.items,
            "delay_steps": args.delay_steps,
            "scalpel_tol": scalpel_meta.get("tol_used"),
        },
        notes="more items, retention delay, optional offline consolidate",
    )

    ok = (
        gates["pin_seed_ok"]
        and (gates["scalpel_ok"] or args.skip_scalpel)
        and gates["immediate_above_chance"]
        and gates["delay_above_chance"]
        and gates["correct_sim_gt_incorrect"]
    )
    if "consolidate" in results:
        ok = ok and gates.get("consolidate_above_chance", False)
    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
