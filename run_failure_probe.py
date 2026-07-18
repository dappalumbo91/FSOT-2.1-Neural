#!/usr/bin/env python3
"""
Probe neurological failure boundaries on the FSOT micro-neuron substrate.

Maps neurodegenerative / neurological break modes → FSOT lesions,
measures healthy envelope breach, and demos wire-around strategies.

Not a medical device. Boundaries inform substrate design.
"""

from __future__ import annotations

import argparse
import json

from fsot_nuron.failure_boundaries import (
    load_failure_catalog,
    probe_all_modes,
    probe_failure_mode,
    allen_healthy_envelope,
)


def main() -> None:
    p = argparse.ArgumentParser(description="FSOT neuro failure boundary probe")
    p.add_argument("--mode", default="all", help="failure mode id or 'all'")
    p.add_argument("--units", type=int, default=48)
    p.add_argument("--steps", type=int, default=800)
    p.add_argument("--device", default="cpu")
    p.add_argument("--list", action="store_true")
    p.add_argument("--no-eeg", action="store_true", help="skip OpenNeuro/local EEG for PD")
    p.add_argument("--no-auto-wire", action="store_true", help="use catalog wire-around only")
    args = p.parse_args()

    cat = load_failure_catalog()
    if args.list:
        print(json.dumps([{"id": m["id"], "label": m["label"]} for m in cat["failure_modes"]], indent=2))
        return

    print("=" * 64)
    print("FSOT neurological failure boundaries")
    print("Purpose: substrate break modes + wire-around (not clinical treatment)")
    print("=" * 64)
    env = allen_healthy_envelope()
    if env.get("ok"):
        print(f"Allen envelope n={env['n_cells']}  ISI p05–p95: {env['isi_ms_p05']:.1f}–{env['isi_ms_p95']:.1f} ms")

    if args.mode == "all":
        from fsot_nuron.paths import ARTIFACTS

        results = []
        for m in cat["failure_modes"]:
            mid = m["id"]
            try:
                r = probe_failure_mode(
                    mid,
                    n_units=args.units,
                    steps=args.steps,
                    device=args.device,
                    use_eeg=not args.no_eeg,
                    auto_wire=not args.no_auto_wire,
                )
                results.append(
                    {
                        "id": mid,
                        "label": r["label"],
                        "breached": r["lesioned"]["breached"],
                        "recovered": r["wire_around"]["recovered_envelope"],
                        "signature_hits": r["lesioned"].get("signature_hits"),
                        "rate_ratio_lesion": r["lesioned"].get("rate_ratio_vs_healthy"),
                        "rate_ratio_wire": r["wire_around"].get("rate_ratio_vs_healthy"),
                        "healthy_rate": r["healthy"]["population"].get("mean_firing_rate_Hz"),
                        "lesion_rate": r["lesioned"]["population"].get("mean_firing_rate_Hz"),
                        "wire_rate": r["wire_around"]["population"].get("mean_firing_rate_Hz"),
                        "strategy": r["wire_around"]["strategy"],
                        "auto_wire": r["wire_around"].get("auto"),
                        "actions": r["wire_around"].get("actions"),
                        "eeg_used": r.get("eeg_context", {}).get("used"),
                    }
                )
            except Exception as e:
                results.append({"id": mid, "error": str(e)})
        rep = {"n_modes": len(results), "modes": results}
        path = ARTIFACTS / "failure_boundary_report.json"
        path.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        print(f"\nprobed {rep['n_modes']} modes → {path}\n")
        for m in rep["modes"]:
            if "error" in m:
                print(f"  [ERR] {m['id']}: {m['error']}")
                continue
            print(
                f"  {m['id']}: breach={m['breached']} recovered={m['recovered']} "
                f"rate H/L/W={m['healthy_rate']:.1f}/{m['lesion_rate']:.1f}/{m['wire_rate']:.1f} "
                f"ratio L/W={m.get('rate_ratio_lesion')}/{m.get('rate_ratio_wire')} "
                f"sig={m.get('signature_hits')} auto={m.get('auto_wire')} [{m['strategy']}]"
            )
    else:
        r = probe_failure_mode(
            args.mode,
            n_units=args.units,
            steps=args.steps,
            device=args.device,
            use_eeg=not args.no_eeg,
            auto_wire=not args.no_auto_wire,
        )
        print(json.dumps({
            "mode": r["mode_id"],
            "label": r["label"],
            "breached": r["lesioned"]["breached"],
            "recovered": r["wire_around"]["recovered_envelope"],
            "signature_hits": r["lesioned"].get("signature_hits"),
            "healthy": r["healthy"]["population"],
            "lesioned": r["lesioned"]["population"],
            "wire_around": r["wire_around"],
            "eeg_context": r.get("eeg_context"),
        }, indent=2, default=str))


if __name__ == "__main__":
    main()
