#!/usr/bin/env python3
"""
Validate FSOT micro-neurons against Allen Cell Types ephys.

Default primary mode = bio_match (close ISI / adaptation gaps).
Also runs efficient mode for the dual-mode speed ledger.
"""

from __future__ import annotations

import argparse
import json

import torch

from fsot_nuron.validate import run_validation
from fsot_nuron.allen_data import data_status
from fsot_nuron.modes import OperatingMode


def main() -> None:
    p = argparse.ArgumentParser(description="FSOT bio validation vs Allen")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--units", type=int, default=64)
    p.add_argument("--steps", type=int, default=1000)
    p.add_argument(
        "--mode",
        default="bio_match",
        choices=["bio_match", "efficient", "bio", "fast"],
        help="primary mode (default bio_match)",
    )
    p.add_argument(
        "--primary-only",
        action="store_true",
        help="skip dual-mode efficient/bio comparison",
    )
    p.add_argument("--api", action="store_true", help="hit Allen/NeuroElectro APIs")
    p.add_argument("--no-calibrate", action="store_true", help="skip iterative ISI/adapt hone")
    p.add_argument("--status-only", action="store_true")
    args = p.parse_args()

    if args.status_only:
        print(json.dumps(data_status(), indent=2))
        return

    device = None if args.device == "auto" else args.device
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    mode = OperatingMode.parse(args.mode).value

    print("=" * 64)
    print("FSOT bio validation (Allen-mapped small population)")
    print(f"device={device} units={args.units} steps={args.steps} mode={mode} api={args.api}")
    print("=" * 64)

    report = run_validation(
        n_units=args.units,
        steps=args.steps,
        device=device,
        use_api=args.api,
        mode=mode,
        both_modes=not args.primary_only,
        calibrate=not args.no_calibrate,
    )

    print("\n--- data ---")
    ds = report["data_status"]
    print(f"  ephys_csv: {ds.get('ephys_csv')}")
    print(f"  n_cells:   {ds.get('n_ephys_rows')}")
    if ds.get("population"):
        pop = ds["population"]
        print(f"  Allen mean vrest: {pop.get('mean_vrest_mV'):.2f} mV")
        print(f"  Allen mean tau:   {pop.get('mean_tau_ms'):.2f} ms")
        print(f"  Allen mean Rin:   {pop.get('mean_rin_mohm'):.1f} MΩ")
        print(f"  Allen mean ISI:   {pop.get('mean_avg_isi_ms'):.1f} ms")
        print(f"  Allen mean adapt: {pop.get('mean_adaptation'):.4f}")

    print(f"\n--- primary mode: {report['primary_mode']} ---")
    ev = report["evoked"]["population"]
    print(f"  FI rate:         {ev['mean_firing_rate_Hz']:.2f} Hz")
    print(f"  FI adaptation:   {ev['mean_adaptation_index']:.4f}")
    print(f"  FI mean ISI:     {ev['mean_isi_ms']}")
    print(
        f"  evoked bands:    {report['evoked']['bands']['pass_rate']:.0%} "
        f"({report['evoked']['bands']['n_pass']}/{report['evoked']['bands']['n_total']})"
    )
    sp = report["spontaneous"]["population"]
    print(f"  sparse rate:     {sp['mean_firing_rate_Hz']:.2f} Hz "
          f"(band {report['spontaneous']['bands']['pass_rate']:.0%})")
    print(
        f"  rest Vrest:      {report['rest']['population'].get('configured_vrest_mV', float('nan')):.2f} mV "
        f"(band {report['rest']['bands']['pass_rate']:.0%})"
    )

    print("\n--- vs Allen sample ---")
    for k, v in report["comparison_to_allen_sample"].items():
        print(f"  {k}: {v}")

    cal = report.get("meta", {}).get("calibration", {})
    if cal.get("enabled"):
        print("\n--- calibration (FSOT-grade) ---")
        print(f"  converged: {cal.get('converged')}  iters: {len(cal.get('iters') or [])}")
        print(f"  grade: {cal.get('grade')}  isi_tol={cal.get('isi_tol')} adapt_tol={cal.get('adapt_tol')}")
        f = cal.get("final") or {}
        ie = f.get("isi_error") or {}
        ae = f.get("adapt_error") or {}
        if ie:
            print(
                f"  final ISI median_err={ie.get('median')}  mean={ie.get('mean')}  max={ie.get('max')}"
            )
        if ae:
            print(
                f"  final adapt median_err={ae.get('median')}  mean={ae.get('mean')}  max={ae.get('max')}"
            )

    print("\n--- gap ledger (FSOT-grade pop: ISI≤2%, adapt≤10%; 1ms grid floor) ---")
    pl = (report.get("meta") or {}).get("calibration", {}).get("precision_ledger")
    if pl:
        print(
            f"  precision_ledger ISI median={pl.get('isi_median_error_pct')}% "
            f"mean={pl.get('isi_mean_error_pct')}% max={pl.get('isi_max_error_pct')}%"
        )
        print(
            f"  precision_ledger adapt median={pl.get('adapt_median_error_pct')}% "
            f"mean={pl.get('adapt_mean_error_pct')}%"
        )
    gaps = report.get("gaps", {})
    print(f"  closed: {gaps.get('n_closed')}/{gaps.get('n_total')}  all={gaps.get('all_closed')}")
    for g in gaps.get("rows", []):
        mark = "OK" if g.get("closed") else "OPEN"
        err = g.get("rel_error")
        err_s = f"{err:.4f}" if isinstance(err, float) and err == err else str(err)
        print(
            f"  [{mark}] {g['gap']}: sim={g.get('sim')} target={g.get('target')} err={err_s}"
        )

    if report.get("efficiency"):
        print("\n--- dual-mode efficiency ---")
        for k, v in report["efficiency"].items():
            if k == "philosophy":
                print(f"  {k}: {v[:80]}...")
            else:
                print(f"  {k}: {v}")

    print(f"\nreport: {report['report_path']}")
    print(report["verdict"]["note"])


if __name__ == "__main__":
    main()
