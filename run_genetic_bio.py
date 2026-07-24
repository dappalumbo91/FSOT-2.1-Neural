#!/usr/bin/env python3
"""
Primary mission runner: FSOT genetic-codon neural network.

Biologically structured network:
  64-codon trinary map → ion-channel gene programs (SCN/KCN/CACNA/LEAK)
  → neuron phenotypes → FSOT trinary synaptic matrix → dynamics
  → Allen ephys lock (optional) + hard bio metrics

Not an NLP scoreboard. Language/Morse demos are secondary.

Usage:
  cd "I:\\fsot nuron"
  $env:PYTHONPATH = "I:\\fsot nuron"
  $env:FSOT_PHYSICAL_ARCHIVE = "I:\\FSOT-Physical-Archive"
  python run_genetic_bio.py
  python run_genetic_bio.py --units 64 --steps 1200 --connectivity genetic_sparse
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
    ap = argparse.ArgumentParser(description="FSOT genetic-codon neural network (primary mission)")
    ap.add_argument("--units", type=int, default=64)
    ap.add_argument("--steps", type=int, default=1200)
    ap.add_argument("--device", type=str, default="auto", help="auto|cpu|cuda")
    ap.add_argument("--mode", type=str, default="bio_match", help="bio_match|efficient")
    ap.add_argument(
        "--connectivity",
        type=str,
        default="genetic_dense",
        choices=["genetic_dense", "genetic_sparse", "local"],
    )
    ap.add_argument("--no-allen-lock", action="store_true")
    ap.add_argument("--pin-only", action="store_true")
    ap.add_argument("--status-only", action="store_true")
    args = ap.parse_args()

    from fsot_nuron.archive_pin import pin_archive
    from fsot_nuron.genetic_genotype import genetic_authority_report
    from fsot_nuron.genetic_network import run_genetic_network_suite
    from fsot_nuron.paths import ARTIFACTS
    from fsot_nuron.thesis_ledger import record_run

    print("=== FSOT-2.1-Neural — Genetic Codon Network (primary mission) ===")
    pin = pin_archive(write_snapshot=True)
    print(f"archive connected: {pin.connected}")
    print(f"seed_match_ok:     {pin.seed_match_ok}")
    print(f"compute_match:     {pin.compute_matches_certificate}")
    print(f"authority:         {(pin.compute_sha256 or pin.cert_authority_sha256 or '')[:16]}…")

    auth = genetic_authority_report()
    cv = auth["codon_map"]
    print(f"codon_map:         {cv.get('roundtrip_ok')}/{cv.get('n_codons')} perfect={cv.get('perfect')}")
    print("channel genes:")
    for name, g in auth["channel_genes"].items():
        print(f"  {name:6} spin={g['spin']:+.3f} expr={g['expression']:.3f} aa={g['aa']}")

    if args.pin_only or args.status_only:
        ok = bool(pin.seed_match_ok and cv.get("perfect"))
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1

    device = None if args.device == "auto" else args.device
    report = run_genetic_network_suite(
        n_units=args.units,
        steps=args.steps,
        device=device,
        mode=args.mode,
        allen_lock=not args.no_allen_lock,
        connectivity=args.connectivity,
    )

    st = report["structure"]
    dyn = report["dynamics"]
    gates = report["gates"]
    pop = dyn.get("population") or {}

    print("\n--- Network structure (genetic) ---")
    print(f"units:           {st['n_units']}")
    print(f"connectivity:    {st['connectivity']}")
    print(f"synapses:        {st['n_synapses']}  density={st['synapse_density']:.3f}")
    print(f"mean d_eff:      {st['mean_d_eff']:.3f}")
    print(
        f"expr SCN/KCN/Ca/Leak: "
        f"{st['mean_scn']:.3f} / {st['mean_kcn']:.3f} / {st['mean_cacna']:.3f} / {st['mean_leak']:.3f}"
    )

    print("\n--- Dynamics (FI step) ---")
    print(f"mean rate Hz:    {dyn.get('mean_rate_Hz')}")
    print(f"coactive frac:   {dyn.get('coactive_fraction')}")
    print(f"emergent frac:   {dyn.get('emergent_fraction')}")
    if isinstance(pop, dict):
        print(f"mean ISI ms:     {pop.get('mean_isi_ms')}")
        print(f"mean adapt:      {pop.get('mean_adaptation_index')}")

    allen = report.get("allen") or {}
    if allen.get("ok"):
        print("\n--- Allen lock ---")
        print(f"mode:            {allen.get('mode')}")
        print(f"target ISI:      {allen.get('mean_target_isi')}")
        print(f"target adapt:    {allen.get('mean_target_adapt')}")
    elif allen.get("locked") is False:
        print("\n--- Allen lock --- skipped or no CSV")

    print("\n--- Genetics coupling ---")
    print(f"rate↔SCN corr:   {report['genetics'].get('rate_vs_scn_corr')}")

    print("\n--- Mission gates ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mission": report["mission"],
        "pin": {
            "connected": pin.connected,
            "seed_match_ok": pin.seed_match_ok,
            "compute_matches_certificate": pin.compute_matches_certificate,
            "authority_prefix": (pin.compute_sha256 or "")[:16],
        },
        "report": report,
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    art_path = ARTIFACTS / "genetic_network_report.json"
    art_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    results_dir = ROOT / "data" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    res_path = results_dir / "genetic_network_report.json"
    res_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    # Markdown card
    md = [
        "# FSOT genetic-codon neural network — report card",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        "## Mission",
        "",
        report["mission"],
        "",
        "## Gates",
        "",
        f"- Codon map perfect: **{gates['codon_map_perfect']}**",
        f"- Channel genes ok: **{gates['channel_genes_ok']}**",
        f"- Has synapses: **{gates['has_synapses']}**",
        f"- Archive seed match: **{pin.seed_match_ok}**",
        "",
        "## Structure",
        "",
        f"- Units: {st['n_units']} · connectivity `{st['connectivity']}`",
        f"- Synapses: {st['n_synapses']} (density {st['synapse_density']:.3f})",
        f"- Mean d_eff: {st['mean_d_eff']:.3f}",
        f"- Channel expression SCN/KCN/CACNA/LEAK: "
        f"{st['mean_scn']:.3f} / {st['mean_kcn']:.3f} / {st['mean_cacna']:.3f} / {st['mean_leak']:.3f}",
        "",
        "## Dynamics",
        "",
        f"- Mean rate: {dyn.get('mean_rate_Hz')} Hz",
        f"- Mean ISI: {pop.get('mean_isi_ms') if isinstance(pop, dict) else 'n/a'} ms",
        f"- Mean adaptation: {pop.get('mean_adaptation_index') if isinstance(pop, dict) else 'n/a'}",
        f"- Rate↔SCN expression correlation: {report['genetics'].get('rate_vs_scn_corr')}",
        "",
        "## Honesty",
        "",
        "- Genetic structure sets channel balance and synaptic topology from codon trinary.",
        "- Allen lock (when available) snaps timing to ephys targets without free scalar params.",
        "- Not a medical device; not a transformer NLP benchmark.",
        "",
    ]
    md_path = results_dir / "GENETIC_NETWORK.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {art_path}")
    print(f"Wrote {res_path}")
    print(f"Wrote {md_path}")

    ok = all(gates.values()) and bool(pin.seed_match_ok)
    record_run(
        "genetic_bio",
        profile="genetic_population",
        gates=gates,
        metrics={
            "n_units": st.get("n_units"),
            "n_synapses": st.get("n_synapses"),
            "mean_rate_Hz": dyn.get("mean_rate_Hz"),
            "mean_isi_ms": (pop or {}).get("mean_isi_ms") if isinstance(pop, dict) else None,
        },
        notes="genetic codon network population run",
    )
    print("\nPASS" if ok else "\nFAIL (see gates / pin)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
