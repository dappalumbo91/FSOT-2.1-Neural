#!/usr/bin/env python3
"""
Scalpel rate targeting: close Allen class rate errors in priority order.

Default: fix Pyr (large error) first, then PV (smaller error), then SST/VIP.
Hard gate: rel_err ≤ 5% (0.05) on focused classes.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import torch

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="Scalpel class-rate lock to Allen wet-lab")
    ap.add_argument("--units", type=int, default=64)
    ap.add_argument("--steps", type=int, default=1400)
    ap.add_argument("--tol", type=float, default=0.05, help="max relative rate error")
    ap.add_argument("--max-iters", type=int, default=28)
    ap.add_argument(
        "--focus",
        type=str,
        default="Pyr,PV",
        help="comma order: large errors first (default Pyr then PV)",
    )
    ap.add_argument("--device", type=str, default="cpu")
    args = ap.parse_args()

    from fsot_nuron.class_ephys import build_class_targets
    from fsot_nuron.cell_types import build_typed_population
    from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
    from fsot_nuron.scalpel_rate import scalpel_calibrate
    from fsot_nuron.thesis_ledger import record_run
    from fsot_nuron.paths import ARTIFACTS, DATA

    print("=== FSOT SCALPEL rate targeting ===")
    print("Policy: biological accuracy first — close large rel_err, then tight.")
    print(f"tol={args.tol:.0%}  focus={args.focus}  steps={args.steps}")

    targets = build_class_targets(min_cells=15, mouse_only=True)
    if "Pyr" not in targets or "PV" not in targets:
        print("FAIL: need Pyr and PV Allen targets")
        return 1

    print("\n--- Allen wet-lab targets ---")
    for k, t in sorted(targets.items()):
        print(f"  {k:4} n={t.n_cells:4}  rate={t.mean_rate_Hz:7.2f} Hz  ISI={t.mean_isi_ms:6.2f} ms")

    genotypes = build_typed_population(args.units, seed=42, diversity=True)
    labels = [getattr(g, "cell_type", "Pyr") for g in genotypes]
    phenotypes = [dict(g.phenotype) for g in genotypes]

    net = FSOTNeuronBatch(NeuronConfig(n_units=args.units), device=args.device)
    # seed d_eff etc from genotypes
    d_eff = torch.tensor([p["d_eff"] for p in phenotypes], dtype=net.dtype)
    thr = torch.tensor([p["fire_threshold"] for p in phenotypes], dtype=net.dtype)
    vrest = torch.tensor([p.get("vrest_mV", -70.0) for p in phenotypes], dtype=net.dtype)
    net.apply_bio_params(
        d_eff=d_eff,
        fire_threshold=thr,
        vrest_mV=vrest,
        mode_name="pre_scalpel",
    )

    focus = [x.strip() for x in args.focus.split(",") if x.strip()]
    # Only focus classes that exist in population + targets
    present = set(labels)
    focus = [c for c in focus if c in present and c in targets]
    # append remaining targeted classes by error later inside calibrator if empty
    if not focus:
        focus = None

    report = scalpel_calibrate(
        net,
        labels,
        phenotypes,
        targets,
        focus_order=focus,
        tol=args.tol,
        max_iters=args.max_iters,
        steps=args.steps,
        require_classes=focus,  # PASS = focused classes only (Pyr then PV)
    )

    print("\n--- Scalpel results ---")
    for lab, st in sorted(report.classes.items()):
        status = "OK" if (st.rel_err == st.rel_err and st.rel_err <= args.tol) else "HIGH"
        print(
            f"  {lab:4} target={st.target_Hz:7.2f}  measured={st.measured_Hz:7.2f}  "
            f"rel_err={st.rel_err:6.1%}  R={st.refractory_steps:3d}  fi={st.fi_stim:.3f}  "
            f"iters={st.iters}  [{status}]"
        )

    print(f"\nhistory_points: {len(report.history)}")
    print(f"scalpel_ok (all targeted ≤ {args.tol:.0%}): {report.ok}")

    # Priority gates
    pyr = report.classes.get("Pyr")
    pv = report.classes.get("PV")
    gates = {
        "pyr_within_tol": bool(pyr and pyr.rel_err == pyr.rel_err and pyr.rel_err <= args.tol),
        "pv_within_tol": bool(pv and pv.rel_err == pv.rel_err and pv.rel_err <= args.tol),
        "pv_faster_than_pyr": bool(
            pv and pyr and pv.measured_Hz > pyr.measured_Hz
        ),
        "scalpel_ok": report.ok,
    }
    print("\n--- Gates ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tol": args.tol,
        "focus": focus,
        "report": report.to_dict(),
        "gates": gates,
        "authority": "Allen Cell Types Cre-line wet-lab rates",
        "policy": "scalpel: large error first (Pyr), then PV; bio before performance",
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "scalpel_rates.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    res = DATA / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "scalpel_rates.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    md = [
        "# Scalpel class-rate targeting",
        "",
        f"Generated: `{out['generated_at']}`  ",
        f"Tolerance: **{args.tol:.0%}** relative rate error vs Allen wet-lab means.",
        "",
        "## Focus order",
        "",
        f"`{focus}` — close large margin first, then tight.",
        "",
        "## Results",
        "",
        "| Class | Target Hz | Measured Hz | Rel err | R (ms) | fi |",
        "|-------|-----------|-------------|---------|--------|-----|",
    ]
    for lab, st in sorted(report.classes.items()):
        md.append(
            f"| {lab} | {st.target_Hz:.2f} | {st.measured_Hz:.2f} | "
            f"{st.rel_err:.1%} | {st.refractory_steps} | {st.fi_stim:.3f} |"
        )
    md += [
        "",
        "## Gates",
        "",
        *[f"- `{k}`: **{v}**" for k, v in gates.items()],
        "",
        "Biological model-Hz only; silicon wall-clock is separate.",
        "",
    ]
    (res / "SCALPEL_RATES.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {res / 'SCALPEL_RATES.md'}")

    record_run(
        "scalpel_class_rates",
        profile=f"tol_{args.tol}",
        gates=gates,
        metrics={
            lab: {"target": st.target_Hz, "measured": st.measured_Hz, "rel_err": st.rel_err}
            for lab, st in report.classes.items()
        },
        notes="Scalpel rate lock Pyr then PV to Allen wet-lab",
    )

    # Require Pyr and PV within tol (the two margins user named)
    ok = gates["pyr_within_tol"] and gates["pv_within_tol"] and gates["pv_faster_than_pyr"]
    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
