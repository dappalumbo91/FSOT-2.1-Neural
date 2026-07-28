#!/usr/bin/env python3
"""
FSOT-native precision climb: push Allen class rates toward ≤1% without free S params.

  python run_precision_climb.py
  python run_precision_climb.py --tol 0.01 --rounds 50
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
    ap.add_argument("--tol", type=float, default=0.01)
    ap.add_argument("--rounds", type=int, default=48)
    ap.add_argument("--steps", type=int, default=0, help="0 = auto from sim-ms / dt")
    # FI window must be long enough that integer spike counts can hit 1%:
    # |n/T - f| / f ≤ 0.01 ⇒ T ≳ 0.5/(0.01 f) ≈ 3 s for f≈16 Hz Pyr.
    ap.add_argument("--sim-ms", type=float, default=4200.0)
    ap.add_argument("--dt-ms", type=float, default=0.5, help="model-ms step; continuous R_ms")
    ap.add_argument("--units", type=int, default=64)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    import torch
    from fsot_nuron.archive_pin import pin_archive
    from fsot_nuron.class_ephys import build_class_targets
    from fsot_nuron.cell_types import build_typed_population
    from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
    from fsot_nuron.precision_climb import precision_micro_climb, climb_summary
    from fsot_nuron.paths import ARTIFACTS, DATA
    from fsot_nuron.thesis_ledger import record_run

    print("=== FSOT precision climb (seed-scaled timing; S law fixed) ===")
    print(f"dt_ms={args.dt_ms} (continuous refractory timer; fix time before more accuracy)")
    pin = pin_archive(write_snapshot=False)
    print(f"pin seed_ok={pin.seed_match_ok}")

    if args.steps <= 0:
        args.steps = max(200, int(round(args.sim_ms / max(args.dt_ms, 1e-9))))

    targets = build_class_targets(min_cells=15, mouse_only=True)
    genotypes = build_typed_population(args.units, seed=42, diversity=True)
    labels = [getattr(g, "cell_type", "Pyr") for g in genotypes]
    phenotypes = [dict(g.phenotype) for g in genotypes]
    net = FSOTNeuronBatch(
        NeuronConfig(n_units=args.units, dt_ms=args.dt_ms), device=args.device
    )
    d_eff = torch.tensor([p["d_eff"] for p in phenotypes], dtype=net.dtype)
    thr = torch.tensor([p["fire_threshold"] for p in phenotypes], dtype=net.dtype)
    vrest = torch.tensor([p.get("vrest_mV", -70.0) for p in phenotypes], dtype=net.dtype)
    net.apply_bio_params(
        d_eff=d_eff, fire_threshold=thr, vrest_mV=vrest, mode_name="precision_pre"
    )

    focus = [c for c in ("Pyr", "PV", "SST", "VIP") if c in labels and c in targets]
    print(f"focus={focus} tol={args.tol:.0%} rounds≤{args.rounds}")

    report = precision_micro_climb(
        net,
        labels,
        phenotypes,
        targets,
        tol=args.tol,
        max_rounds=args.rounds,
        steps=args.steps,
        seed_order=focus,
    )
    summary = climb_summary(report)

    print("\n--- Class results ---")
    for lab, st in sorted(summary["classes"].items()):
        mark = "OK" if st["within_tol"] else "HIGH"
        print(
            f"  {lab:4} target={st['target_Hz']:7.2f} measured={st['measured_Hz']:7.2f} "
            f"err={st['rel_err']:6.2%} R={st['R']} fi={st['fi']:.3f} [{mark}]"
        )
    print(f"\nprecision_ok (all ≤ {args.tol:.0%}): {report.ok}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pin_seed_ok": pin.seed_match_ok,
        "params": vars(args),
        "summary": summary,
        "report": report.to_dict(),
        "doctrine": "seed-scaled R/FI/thr only; free_parameters on S = 0",
        "alphafold_class_note": (
            "T3 discipline: ≤1% on primary ephys locks without free scalar fit"
        ),
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "precision_climb.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    res = DATA / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "precision_climb.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    md = [
        "# Precision climb (FSOT-native)",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        f"Tolerance: **{args.tol:.0%}** · ok=**{report.ok}**",
        "",
        "| Class | Target Hz | Measured | Rel err | Within |",
        "|-------|-----------|----------|---------|:------:|",
    ]
    for lab, st in sorted(summary["classes"].items()):
        md.append(
            f"| {lab} | {st['target_Hz']:.2f} | {st['measured_Hz']:.2f} | "
            f"{st['rel_err']:.2%} | {'Y' if st['within_tol'] else 'N'} |"
        )
    md += [
        "",
        "Method: seed-scaled refractory/FI/threshold micro-steps after 2% scalpel.",
        "FSOT seeds and \(S=K(T_1+T_2+T_3)\) **not** fitted.",
        "",
        "See `docs/thesis/FSOT_NEURAL_STAGE_VERIFICATION.tex` §Precision climb.",
        "",
    ]
    (res / "PRECISION_CLIMB.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {res / 'PRECISION_CLIMB.md'}")

    record_run(
        "precision_climb",
        profile="bio_match",
        gates={"precision_ok": report.ok, "pin_ok": pin.seed_match_ok},
        metrics={k: v["rel_err"] for k, v in summary["classes"].items()},
        notes="FSOT-native 1% climb",
    )

    # Soft exit: report always useful; fail only if worse than 2% floor
    floor_ok = all(
        st["rel_err"] == st["rel_err"] and st["rel_err"] <= 0.02
        for st in summary["classes"].values()
        if st["target_Hz"] > 1
    )
    print("\nPASS (1%)" if report.ok else ("\nFLOOR_OK (2%)" if floor_ok else "\nFAIL"))
    return 0 if floor_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
