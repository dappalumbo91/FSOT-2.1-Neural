"""
FSOT language loop — ITU Morse interpretation + chemical codon generation.

Layers:
  1) Symbolic Morse (ITU) — lossless round-trip (precision path)
  2) Reservoir fluid dynamics — efficient/bio-matched substrate
  3) Chemical generative — trinary → 64-codon → AA/process (FSOT-verified map)
  4) Reconstruction head — emergent zones → source text windows

Morse is not the physics; it is the *readout alphabet*. Chemistry is the
generative meaning layer, cross-checked against codon map + SMILES Lab precision.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import torch

from .chemical_codon import generative_chemical_report, codon_path_verify, smiles_lab_precision_ref
from .morse_itu import ITUMorseCodec, verify_morse_tables
from .paths import ARTIFACTS
from .reservoir import FluidReservoir, ReservoirConfig
from .validate import build_allen_tuned_batch


def drive_from_morse_units(units: List[int], device: str) -> torch.Tensor:
    """OOK Morse units → stim in (0.1, 0.9) for reservoir."""
    t = torch.tensor(units, dtype=torch.float32, device=device)
    return 0.12 + 0.78 * t


def reconstruct_phrases(
    fired: torch.Tensor,
    S: torch.Tensor,
    original: str,
    top_k: int = 10,
) -> List[str]:
    T = fired.shape[0]
    fire_u = fired.float().mean(dim=1) if fired.ndim == 2 else fired.float()
    S_u = S.mean(dim=1) if S.ndim == 2 else S
    score = fire_u * (S_u > 0.35).float() + 0.4 * (S_u > 0.65).float()
    idx = torch.nonzero(score > 0.12, as_tuple=False).flatten().tolist()
    phrases: List[str] = []
    seen = set()
    orig = original.upper()
    for i in idx:
        char_idx = min(int(i * len(orig) / max(T, 1)), max(0, len(orig) - 1))
        start = max(0, char_idx - 3)
        end = min(len(orig), char_idx + 6)
        phrase = orig[start:end].strip()
        if len(phrase) > 2 and phrase not in seen:
            seen.add(phrase)
            phrases.append(phrase)
        if len(phrases) >= top_k:
            break
    return phrases


@torch.no_grad()
def run_language_loop(
    text: str,
    *,
    n_units: int = 32,
    device: Optional[str] = None,
    mode: str = "efficient",
    seed: int = 42,
    pad_units: int = 8,
) -> Dict[str, Any]:
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    codec = ITUMorseCodec()
    morse_verify = verify_morse_tables()
    symbolic = codec.roundtrip_accuracy(text)

    # --- symbolic path (must be near-perfect for mapped charset) ---
    cleaned = symbolic["input_normalized"]
    units = codec.text_to_units(cleaned)
    # pad silence
    units = [0] * pad_units + units + [0] * pad_units
    tern_clean = codec.units_to_ternary(units)
    text_from_units, morse_from_units = codec.ternary_to_text(
        # rebuild ternary from units properly for clean path
        codec.units_to_ternary(units)
    )
    # Prefer exact decode from morse string
    morse_str = codec.encode_text(cleaned)
    text_exact = codec.decode_morse_string(morse_str)

    # --- reservoir path ---
    net, params, meta = build_allen_tuned_batch(
        n_units=n_units,
        device=device,
        seed=seed,
        mode=mode,
        calibrate=(mode == "bio_match"),
        calibrate_steps=500 if mode == "bio_match" else 0,
    )
    res = FluidReservoir(
        ReservoirConfig(
            n_units=n_units,
            device=device,
            fire_threshold=float(net.fire_thr.mean().item()),
        )
    )
    res.enc.apply_bio_params(
        d_eff=net.d_eff,
        fire_threshold=net.fire_thr,
        vrest_mV=net.vrest,
        adapt_gain=net.adapt_gain,
        adapt_decay=net.adapt_decay,
        refractory_steps=net.ref_steps,
        fi_stim=net.fi_stim,
        mode_name=mode,
    )

    stim = drive_from_morse_units(units, device)
    out = res.run_sequence(stim, record=True)
    S = out["S_dec"]
    fired = out["fired_dec"]
    S_mean = S.mean(dim=1)

    # Reservoir trinary from S (emergent +1, damped -1)
    res_tern = torch.zeros_like(S_mean, dtype=torch.int8)
    res_tern = torch.where(S_mean > 0.45, torch.full_like(res_tern, 1), res_tern)
    res_tern = torch.where(S_mean < -0.05, torch.full_like(res_tern, -1), res_tern)
    # also force fire moments to +1
    fire_any = fired.any(dim=1) if fired.ndim == 2 else fired
    res_tern = torch.where(fire_any, torch.full_like(res_tern, 1), res_tern)

    res_text, res_morse = codec.ternary_to_text(res_tern.tolist())
    phrases = reconstruct_phrases(fired, S, cleaned)

    # --- chemical generative path (codon / AA / process) ---
    # Use clean Morse ternary for chemical authority path + reservoir ternary for live path
    chem_clean = generative_chemical_report(tern_clean)
    chem_live = generative_chemical_report(res_tern.tolist())
    codon_verify = codon_path_verify()
    smiles_ref = smiles_lab_precision_ref()

    if phrases:
        utterance = " | ".join(phrases[:8])
        if text_exact and symbolic.get("exact_morse_path"):
            utterance = f"{text_exact} || RECONSTRUCTED: {utterance}"
        elif res_text and set(res_text) - {"?", " "}:
            utterance = f"{res_text} || RECONSTRUCTED: {utterance}"
    else:
        utterance = text_exact if symbolic.get("exact_morse_path") else (res_text or "fluid lock only")

    chem_utt = chem_live.get("chemical_utterance") or chem_clean.get("chemical_utterance")

    report = {
        "input_text": text,
        "normalized": cleaned,
        "mode": mode,
        "device": device,
        "n_units": n_units,
        "layers": {
            "1_symbolic_morse": {
                "standard": morse_verify.get("standard"),
                "table_ok": morse_verify.get("letter_digit_ok"),
                "roundtrip": symbolic,
                "morse": morse_str,
                "decoded_exact": text_exact,
            },
            "2_reservoir_fluid": {
                "stats": {
                    "mean_decoder_rate_Hz": float(out["firing_rate_Hz"].mean().item()),
                    "mean_S": float(S.mean().item()),
                    "max_S": float(S.max().item()),
                    "spike_count_mean": float(out["spike_count"].float().mean().item()),
                    "T": int(S.shape[0]),
                },
                "morse_from_reservoir": res_morse[:400],
                "text_from_reservoir": res_text,
                "reconstructed_phrases": phrases,
            },
            "3_chemical_generative": {
                "codon_map_verify": codon_verify,
                "smiles_lab_precision": smiles_ref,
                "from_clean_morse_trinary": {
                    "aa_sequence": chem_clean.get("aa_sequence"),
                    "n_codons": chem_clean.get("n_codons"),
                    "chemical_utterance": chem_clean.get("chemical_utterance"),
                },
                "from_reservoir_trinary": {
                    "aa_sequence": chem_live.get("aa_sequence"),
                    "n_codons": chem_live.get("n_codons"),
                    "chemical_utterance": chem_live.get("chemical_utterance"),
                    "process_stream_head": (chem_live.get("process_stream") or [])[:12],
                },
            },
        },
        "utterance": utterance,
        "chemical_utterance": chem_utt,
        "precision_gates": {
            "morse_symbolic_exact": bool(symbolic.get("exact_morse_path")),
            "morse_char_accuracy": symbolic.get("char_accuracy_morse"),
            "codon_map_perfect": bool(codon_verify.get("perfect")),
            "smiles_median_error_pct": smiles_ref.get("median_error_pct"),
            "smiles_hit_rate": smiles_ref.get("hit_rate"),
            "note": (
                "Symbolic Morse and codon map must be perfect. "
                "Reservoir is fluid dynamics; chemical path interprets trinary as codon chemistry. "
                "SMILES Lab median_error_pct is the chemical precision bar for FSOT (~0.058%)."
            ),
        },
        "meta": {
            "allen_source": meta.get("source"),
            "sample_n": len(params),
            "calibration": meta.get("calibration", {}).get("precision_ledger"),
        },
    }

    path = ARTIFACTS / "language_loop_report.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    report["report_path"] = str(path)
    return report
