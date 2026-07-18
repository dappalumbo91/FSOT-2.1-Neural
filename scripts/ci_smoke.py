#!/usr/bin/env python3
"""Lightweight CI smoke for FSOT-2.1-Neural (no GPU, no large third-party CSVs)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    errors: list[str] = []
    print("=== FSOT-2.1-Neural CI smoke ===")

    # 1) Seeds match archive closed-form
    from fsot_nuron.archive_pin import check_local_seeds, pin_archive

    ok, max_err, bad = check_local_seeds()
    print(f"seeds_match: {ok} max_rel_err={max_err:.3e}")
    if not ok:
        errors.append(f"seed mismatch: {bad}")

    # 2) Pin (uses snapshot if archive absent)
    pin = pin_archive(write_snapshot=False)
    print(f"seed_match_ok: {pin.seed_match_ok}")
    print(f"snapshot_authority: {(pin.cert_authority_sha256 or '')[:16]}")
    if not pin.seed_match_ok:
        errors.append("pin seed_match_ok false")

    snap = ROOT / "data" / "archive_snapshot" / "fsot_compute_AUTHORITY_PIN.json"
    if snap.is_file():
        d = json.loads(snap.read_text(encoding="utf-8"))
        auth = (d.get("authority_sha256") or "").upper()
        print(f"shipped_authority_pin: {auth[:16]}…")
        if not auth.startswith("D1D38A"):
            errors.append(f"unexpected authority pin {auth[:16]}")
    else:
        errors.append("missing data/archive_snapshot/fsot_compute_AUTHORITY_PIN.json")

    # 3) Morse + codon gates
    from fsot_nuron.morse_itu import verify_morse_tables
    from fsot_nuron.chemical_codon import codon_path_verify

    mv = verify_morse_tables()
    cv = codon_path_verify()
    print(f"morse_ok: {mv.get('letter_digit_ok')} phrase={mv.get('phrase_test', {}).get('exact_morse_path')}")
    print(f"codon_ok: {cv.get('perfect')} {cv.get('roundtrip_ok')}/{cv.get('n_codons')}")
    if not mv.get("letter_digit_ok"):
        errors.append("morse table fail")
    if not cv.get("perfect"):
        errors.append("codon map fail")

    # 4) Tiny CPU neuron step (no CUDA required)
    import torch
    from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig

    cfg = NeuronConfig(n_units=8)
    net = FSOTNeuronBatch(cfg, device="cpu")
    S, fired, phase, ternary = net.step(torch.ones(8) * 0.5)
    print(f"neuron_step_ok: fired={int(fired.sum())} S_mean={float(S.mean()):.4f}")
    if S.shape[0] != 8:
        errors.append(f"unexpected S shape {tuple(S.shape)}")

    # 5) Failure catalog loads
    from fsot_nuron.failure_boundaries import load_failure_catalog

    cat = load_failure_catalog()
    modes = cat.get("failure_modes") or cat.get("modes") or cat.get("boundaries") or []
    n = len(modes)
    print(f"failure_boundaries: {n}")
    if n < 5:
        errors.append(f"too few failure modes: {n}")

    if errors:
        print("FAIL:")
        for e in errors:
            print(" -", e)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
