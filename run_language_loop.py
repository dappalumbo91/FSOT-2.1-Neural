#!/usr/bin/env python3
"""
FSOT language loop — ITU Morse + chemical codon generative path.

Precision gates:
  - Symbolic Morse round-trip must be exact (ITU table)
  - 64-codon trinary map must round-trip 64/64
  - SMILES Lab chemical precision referenced (~0.058% median when present)
"""

from __future__ import annotations

import argparse
import json

import torch

from fsot_nuron.language_loop import run_language_loop
from fsot_nuron.morse_itu import verify_morse_tables
from fsot_nuron.chemical_codon import codon_path_verify, smiles_lab_precision_ref


DEFAULT_TEXT = (
    "To be or not to be that is the question whether tis nobler in the mind "
    "to suffer the slings and arrows of outrageous fortune"
)


def main() -> None:
    p = argparse.ArgumentParser(description="FSOT Morse + chemical language loop")
    p.add_argument("--text", default=DEFAULT_TEXT)
    p.add_argument("--units", type=int, default=32)
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--mode", default="efficient", choices=["efficient", "bio_match"])
    p.add_argument("--verify-only", action="store_true", help="Morse+codon+SMILES gates only")
    args = p.parse_args()

    print("=" * 64)
    print("FSOT language loop — Morse (ITU) + chemical codon generative")
    print("=" * 64)

    mv = verify_morse_tables()
    cv = codon_path_verify()
    sm = smiles_lab_precision_ref()
    print("\n--- precision gates (authority) ---")
    print(f"  Morse letter/digit table OK: {mv.get('letter_digit_ok')}  entries={mv.get('table_entries')}")
    print(f"  Morse phrase exact:          {mv.get('phrase_test', {}).get('exact_morse_path')}")
    print(f"  Codon map 64-roundtrip:      {cv.get('perfect')}  ({cv.get('roundtrip_ok')}/{cv.get('n_codons')})")
    print(f"  Codon map path:              {cv.get('map_path')}")
    if sm.get("ok"):
        print(f"  SMILES Lab hit_rate:         {sm.get('hit_rate')}")
        print(f"  SMILES median_error_pct:     {sm.get('median_error_pct')}")
        print(f"  SMILES free_parameters:      {sm.get('free_parameters')}")
    else:
        print(f"  SMILES Lab:                  {sm}")

    if args.verify_only:
        return

    device = None if args.device == "auto" else args.device
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"\ndevice={device} units={args.units} mode={args.mode}")
    print(f"input: {args.text[:100]}{'...' if len(args.text) > 100 else ''}")

    rep = run_language_loop(
        args.text,
        n_units=args.units,
        device=device,
        mode=args.mode,
    )

    g = rep["precision_gates"]
    print("\n--- run gates ---")
    print(f"  symbolic Morse exact: {g.get('morse_symbolic_exact')}  acc={g.get('morse_char_accuracy')}")
    print(f"  codon map perfect:    {g.get('codon_map_perfect')}")
    print(f"  SMILES median err %:  {g.get('smiles_median_error_pct')}")

    print("\n--- symbolic decode ---")
    print(rep["layers"]["1_symbolic_morse"]["decoded_exact"])
    print("\n--- reconstructed phrases (reservoir) ---")
    for ph in rep["layers"]["2_reservoir_fluid"]["reconstructed_phrases"]:
        print(f"  · {ph}")
    print("\n--- chemical generative (reservoir trinary → codon/AA) ---")
    ch = rep["layers"]["3_chemical_generative"]["from_reservoir_trinary"]
    print(f"  n_codons: {ch.get('n_codons')}")
    print(f"  AA seq:   {ch.get('aa_sequence')}")
    print(f"  process:  {ch.get('chemical_utterance')}")
    print("\n--- utterance ---")
    print(rep["utterance"])
    print(f"\nreport: {rep['report_path']}")


if __name__ == "__main__":
    main()
