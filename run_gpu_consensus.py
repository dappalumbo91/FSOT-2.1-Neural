#!/usr/bin/env python3
"""FSOT-GPU consensus under Morse + chemical readout."""

from __future__ import annotations

import argparse
import json

from fsot_nuron.gpu_consensus import consensus_morse_chem_loop


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--text", default="TO BE OR NOT TO BE")
    p.add_argument("--units", type=int, default=24)
    p.add_argument("--device", default="auto")
    p.add_argument(
        "--failure-mode",
        default=None,
        help="optional lesion id (e.g. PD_rate_irregularity, AD_synaptic_fatigue)",
    )
    p.add_argument("--no-auto-wire", action="store_true")
    args = p.parse_args()
    device = None if args.device == "auto" else args.device
    print("=" * 64)
    print("FSOT-GPU consensus → Morse / chemical readout")
    print("=" * 64)
    rep = consensus_morse_chem_loop(
        args.text,
        n_units=args.units,
        device=device,
        failure_mode=args.failure_mode,
        auto_wire=not args.no_auto_wire,
    )
    print(f"backend: {rep['backend']}  device: {rep['device']}")
    if rep.get("lesion", {}).get("applied"):
        print(f"lesion: {rep['lesion'].get('mode')}  silenced={rep['lesion'].get('n_silenced')}")
        print(f"quarantine: {rep.get('quarantine')}")
        if rep["lesion"].get("wire_policy"):
            print(f"auto-wire: {rep['lesion']['wire_policy'].get('strategy')} {rep['lesion']['wire_policy'].get('actions')}")
    print(f"consensus emergent_frac: {rep['consensus']['emergent_frac']:.3f}")
    print(f"morse text: {rep['morse_readout']['text'][:120]}")
    print(f"chem (consensus): {rep['chemical_readout']['from_consensus']['utterance'][:160]}")
    print(f"chem (clean Morse): {rep['chemical_readout']['from_clean_morse']['utterance'][:160]}")
    print(f"report: {rep['report_path']}")


if __name__ == "__main__":
    main()
