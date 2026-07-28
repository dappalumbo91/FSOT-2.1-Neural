#!/usr/bin/env python3
"""
Fix timing resolution *before* chasing more accuracy.

Compares Allen class-rate lock at dt_ms ∈ {1.0, 0.5, 0.25, 0.1}
with continuous-ms refractory (not integer 1 ms lattice only).

  python run_timing_resolution.py
  python run_timing_resolution.py --dts 1.0,0.25,0.1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def run_at_dt(dt_ms: float, tol: float, sim_ms: float, device: str) -> Dict:
    import torch
    from fsot_nuron.class_ephys import build_class_targets
    from fsot_nuron.cell_types import build_typed_population
    from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
    from fsot_nuron.scalpel_rate import scalpel_calibrate

    steps = max(200, int(round(sim_ms / dt_ms)))
    targets = build_class_targets(min_cells=15, mouse_only=True)
    genotypes = build_typed_population(64, seed=42, diversity=True)
    labels = [getattr(g, "cell_type", "Pyr") for g in genotypes]
    phenotypes = [dict(g.phenotype) for g in genotypes]
    cfg = NeuronConfig(n_units=64, dt_ms=dt_ms)
    net = FSOTNeuronBatch(cfg, device=device)
    d_eff = torch.tensor([p["d_eff"] for p in phenotypes], dtype=net.dtype)
    thr = torch.tensor([p["fire_threshold"] for p in phenotypes], dtype=net.dtype)
    vrest = torch.tensor([p.get("vrest_mV", -70.0) for p in phenotypes], dtype=net.dtype)
    net.apply_bio_params(d_eff=d_eff, fire_threshold=thr, vrest_mV=vrest, mode_name="timing")
    focus = [c for c in ("Pyr", "PV", "SST", "VIP") if c in labels and c in targets]
    report = scalpel_calibrate(
        net,
        labels,
        phenotypes,
        targets,
        focus_order=focus,
        tol=tol,
        max_iters=28,
        steps=steps,
        require_classes=focus,
    )
    classes = {}
    for lab, st in report.classes.items():
        classes[lab] = {
            "target_Hz": st.target_Hz,
            "measured_Hz": st.measured_Hz,
            "rel_err": st.rel_err,
            "within_1pct": st.rel_err == st.rel_err and st.rel_err <= 0.01,
            "within_2pct": st.rel_err == st.rel_err and st.rel_err <= 0.02,
            "R_ms": st.refractory_steps,
            "fi": st.fi_stim,
        }
    n1 = sum(1 for c in classes.values() if c["within_1pct"])
    n2 = sum(1 for c in classes.values() if c["within_2pct"])
    return {
        "dt_ms": dt_ms,
        "steps": steps,
        "sim_ms": steps * dt_ms,
        "scalpel_ok_2pct": report.ok if tol <= 0.02 else n2 == len(classes),
        "n_within_1pct": n1,
        "n_within_2pct": n2,
        "classes": classes,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dts", default="1.0,0.5,0.25")
    ap.add_argument("--tol", type=float, default=0.02, help="scalpel lock tol")
    # Long enough FI window for 1% with integer spikes (see TIMING_RESOLUTION.md)
    ap.add_argument("--sim-ms", type=float, default=4200.0)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    from fsot_nuron.archive_pin import pin_archive

    print("=== Timing resolution study (before more accuracy pushes) ===")
    print("Continuous-ms refractory; compare dt grids vs Allen rates")
    pin = pin_archive(write_snapshot=False)
    print(f"pin seed_ok={pin.seed_match_ok}")

    dts = [float(x) for x in args.dts.split(",") if x.strip()]
    rows = []
    for dt in dts:
        print(f"\n--- dt_ms={dt} ---")
        row = run_at_dt(dt, args.tol, args.sim_ms, args.device)
        rows.append(row)
        for lab, st in sorted(row["classes"].items()):
            mark = "OK1" if st["within_1pct"] else ("OK2" if st["within_2pct"] else "HIGH")
            print(
                f"  {lab:4} err={st['rel_err']:6.2%} measured={st['measured_Hz']:7.2f} "
                f"target={st['target_Hz']:7.2f} [{mark}]"
            )
        print(f"  within 1%: {row['n_within_1pct']}/4  within 2%: {row['n_within_2pct']}/4")

    # Recommend finest that maximized 1% hits without losing 2% floor
    best = max(rows, key=lambda r: (r["n_within_2pct"], r["n_within_1pct"], -r["dt_ms"]))
    rec = {
        "recommended_dt_ms": best["dt_ms"],
        "reason": "maximize classes within 2% then 1%; prefer coarser dt if tied",
        "best_n_1pct": best["n_within_1pct"],
        "best_n_2pct": best["n_within_2pct"],
    }
    print("\n=== Recommendation ===")
    print(json.dumps(rec, indent=2))

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "doctrine": "resolve continuous-ms timing before free-parameter accuracy pushes",
        "rows": rows,
        "recommendation": rec,
        "note": "ref_timer_ms continuous; FI onset scales with dt; steps = sim_ms/dt",
    }
    res = ROOT / "data" / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "timing_resolution.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    md = [
        "# Timing resolution study",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        "Continuous-ms refractory (`ref_timer_ms`) vs Allen rates at several `dt_ms`.",
        "",
        f"**Recommended dt_ms: {rec['recommended_dt_ms']}** "
        f"(1% hits={rec['best_n_1pct']}/4, 2% hits={rec['best_n_2pct']}/4)",
        "",
        "| dt_ms | steps | ≤1% | ≤2% | Pyr err | PV err | SST err | VIP err |",
        "|------:|------:|----:|----:|--------:|-------:|--------:|--------:|",
    ]
    for r in rows:
        c = r["classes"]
        md.append(
            f"| {r['dt_ms']} | {r['steps']} | {r['n_within_1pct']} | {r['n_within_2pct']} | "
            f"{c.get('Pyr',{}).get('rel_err', float('nan')):.2%} | "
            f"{c.get('PV',{}).get('rel_err', float('nan')):.2%} | "
            f"{c.get('SST',{}).get('rel_err', float('nan')):.2%} | "
            f"{c.get('VIP',{}).get('rel_err', float('nan')):.2%} |"
        )
    md += [
        "",
        "Policy: **fix time resolution before pushing accuracy further.**",
        "",
    ]
    (res / "TIMING_RESOLUTION.md").write_text("\n".join(md), encoding="utf-8")
    (ROOT / "docs" / "TIMING_RESOLUTION.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {res / 'TIMING_RESOLUTION.md'}")

    # Success if any dt keeps 2% floor on all four
    floor = any(r["n_within_2pct"] >= 4 for r in rows)
    return 0 if floor else 1


if __name__ == "__main__":
    raise SystemExit(main())
