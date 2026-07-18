"""
FSOT-GPU consensus bridge under Morse / chemical readout.

Imports owned consensus_aggregate (no softmax) from the Desktop FSOT-GPU
stack when present; otherwise uses a local twin. Reservoir S / trinary
feeds Q,K,V; output is re-read as Morse + chemical codon stream.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch

from .chemical_codon import generative_chemical_report
from .morse_itu import ITUMorseCodec
from .paths import ARTIFACTS, ROOT
from .reservoir import FluidReservoir, ReservoirConfig

FSOT_GPU_LIB = Path(
    r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star"
)


def _load_consensus_fn():
    """Prefer Desktop FSOT-GPU consensus; fallback local twin."""
    if FSOT_GPU_LIB.is_dir():
        p = str(FSOT_GPU_LIB)
        if p not in sys.path:
            sys.path.insert(0, p)
        try:
            from fsot_lib.consensus import consensus_aggregate, apply_phase_rotation  # type: ignore

            return consensus_aggregate, apply_phase_rotation, "desktop_fsot_gpu"
        except Exception as e:
            pass

    # Local twin (same structure as fsot_lib.consensus)
    def apply_phase_rotation(h, positions=None):
        out = h.clone()
        seq, dim = h.shape
        if positions is None:
            positions = torch.arange(seq, device=h.device, dtype=h.dtype)
        theta = 2.0 * positions
        cs, sn = torch.cos(theta), torch.sin(theta)
        pairs = dim // 2
        for k in range(pairs):
            a, b = out[:, 2 * k], out[:, 2 * k + 1]
            out[:, 2 * k] = cs * a - sn * b
            out[:, 2 * k + 1] = sn * a + cs * b
        return out

    def trit_sim(q, k):
        # sign agreement proxy
        qs = torch.sign(q)
        ks = torch.sign(k)
        return (qs @ ks.T) / max(q.shape[-1], 1)

    def consensus_aggregate(q, k, v):
        seq = q.shape[0]
        sim = trit_sim(q, k)
        # coherence proxy: column energy
        k_coh = (k.abs().mean(dim=-1) > 0.05).float()
        idx = torch.arange(seq, device=q.device)
        causal = idx.unsqueeze(1) >= idx.unsqueeze(0)
        gate = (k_coh > 0.5).unsqueeze(0) & causal
        w = torch.where(gate, sim, torch.zeros_like(sim))
        active = (w != 0).to(torch.float64).sum(dim=-1, keepdim=True).clamp_min(1.0)
        out = (w.to(torch.float64) @ v.to(torch.float64)) / active
        return out.to(v.dtype)

    return consensus_aggregate, apply_phase_rotation, "local_twin"


@torch.no_grad()
def reservoir_to_qkv(
    S_dec: torch.Tensor,
    fired: torch.Tensor,
    head_dim: int = 32,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Map [T, B] reservoir decoder state → [T, head_dim] Q,K,V for consensus.
    """
    T, B = S_dec.shape
    # Features: S, fire, running mean, phase-like lag
    fire_f = fired.float()
    run_mean = torch.cumsum(S_dec, dim=0) / torch.arange(
        1, T + 1, device=S_dec.device, dtype=S_dec.dtype
    ).unsqueeze(1)
    lag = torch.roll(S_dec, 1, dims=0)
    lag[0] = 0
    # Pool across units → sequence embedding
    base = torch.stack(
        [
            S_dec.mean(dim=1),
            S_dec.std(dim=1, unbiased=False),
            fire_f.mean(dim=1),
            run_mean.mean(dim=1),
            lag.mean(dim=1),
            S_dec.max(dim=1).values,
            S_dec.min(dim=1).values,
            (S_dec > 0.4).float().mean(dim=1),
        ],
        dim=-1,
    )  # [T, 8]
    # Expand to head_dim with deterministic Fourier features
    t = torch.arange(T, device=S_dec.device, dtype=S_dec.dtype).unsqueeze(1)
    freqs = torch.arange(1, head_dim // 2 + 1, device=S_dec.device, dtype=S_dec.dtype)
    ang = t * freqs * 0.07
    fourier = torch.cat([torch.sin(ang), torch.cos(ang)], dim=-1)[:, : head_dim - 8]
    h = torch.cat([base, fourier], dim=-1)
    if h.shape[-1] < head_dim:
        h = torch.nn.functional.pad(h, (0, head_dim - h.shape[-1]))
    h = h[:, :head_dim]
    # Q=h, K=phase-rotated, V=h * (1+fire)
    q = h
    k = h
    v = h * (1.0 + 0.5 * fire_f.mean(dim=1, keepdim=True))
    return q, k, v


@torch.no_grad()
def apply_unit_mask_to_state(
    S: torch.Tensor,
    fired: torch.Tensor,
    unit_mask: Optional[torch.Tensor],
) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, Any]]:
    """
    Quarantine failed units: zero their contribution in [T, B] tensors.
    unit_mask: [B] bool, True = keep.
    """
    if unit_mask is None:
        return S, fired, {"quarantined": 0, "kept": int(S.shape[1])}
    m = unit_mask.to(device=S.device).bool()
    if m.numel() != S.shape[1]:
        return S, fired, {"quarantined": 0, "kept": int(S.shape[1]), "warn": "mask size mismatch"}
    S2 = S * m.float().unsqueeze(0)
    f2 = fired & m.unsqueeze(0)
    return S2, f2, {
        "quarantined": int((~m).sum().item()),
        "kept": int(m.sum().item()),
        "mask_frac_alive": float(m.float().mean().item()),
    }


@torch.no_grad()
def consensus_morse_chem_loop(
    text: str,
    *,
    n_units: int = 24,
    device: Optional[str] = None,
    head_dim: int = 32,
    failure_mode: Optional[str] = None,
    auto_wire: bool = True,
) -> Dict[str, Any]:
    """
    Full path: text → Morse drive → reservoir → (optional lesion + quarantine)
    → FSOT consensus → Morse/chem readout.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    consensus_aggregate, apply_phase_rotation, backend = _load_consensus_fn()
    codec = ITUMorseCodec()
    cleaned = codec.roundtrip_accuracy(text)["input_normalized"]
    units = codec.text_to_units(cleaned)
    units = [0] * 4 + units + [0] * 4
    stim = torch.tensor([0.12 + 0.78 * u for u in units], device=device, dtype=torch.float32)

    res = FluidReservoir(ReservoirConfig(n_units=n_units, device=device))
    lesion_info: Dict[str, Any] = {"applied": False}
    unit_mask = None

    if failure_mode:
        from .failure_boundaries import apply_lesion, _patch_alive_gate, _apply_wire_around, load_failure_catalog
        from .wire_around_policy import select_wire_around
        from .validate import build_allen_tuned_batch

        net, _, _ = build_allen_tuned_batch(
            n_units=n_units, device=device, seed=7, mode="efficient", calibrate=False
        )
        lesion_override = None
        if failure_mode == "PD_rate_irregularity":
            try:
                from .eeg_sources import gather_eeg_context

                eeg = gather_eeg_context(fetch_live=True)
                lesion_override = eeg["pd_lesion_derived"]["fsot_lesion"]
                lesion_info["eeg"] = {"n_local": eeg.get("n_local_eeg"), "openneuro": eeg.get("openneuro_pd", {}).get("ok")}
            except Exception as e:
                lesion_info["eeg_error"] = str(e)
        lmeta = apply_lesion(net, failure_mode, seed=7, lesion_override=lesion_override)
        _patch_alive_gate(net)
        if auto_wire:
            policy = select_wire_around(
                list((lmeta.get("break_signature") or {}).keys()),
                catalog_default=lmeta.get("wire_around"),
            )
            # force quarantine action for consensus path
            acts = list(policy.get("actions") or [])
            if "consensus_quarantine_failed" not in acts:
                acts.insert(0, "consensus_quarantine_failed")
            policy["actions"] = acts
            _apply_wire_around(net, policy)
            lesion_info["wire_policy"] = policy
        # copy timing + mask into reservoir encoder
        res.enc.apply_bio_params(
            d_eff=net.d_eff,
            fire_threshold=net.fire_thr,
            vrest_mV=net.vrest,
            adapt_gain=net.adapt_gain,
            adapt_decay=net.adapt_decay,
            refractory_steps=net.ref_steps,
            fi_stim=net.fi_stim,
            adapt_step=net.adapt_step,
            mode_name="lesion_" + failure_mode,
        )
        res.enc.unit_alive = net.unit_alive.clone()
        unit_mask = net.unit_alive.clone()
        lesion_info.update(
            {
                "applied": True,
                "mode": failure_mode,
                "n_silenced": lmeta.get("n_silenced"),
                "label": lmeta.get("label"),
            }
        )

    out = res.run_sequence(stim, record=True)
    S = out["S_dec"]
    fired = out["fired_dec"]

    # Quarantine dead units before consensus
    S_q, fired_q, qmeta = apply_unit_mask_to_state(S, fired, unit_mask)

    q, k, v = reservoir_to_qkv(S_q, fired_q, head_dim=head_dim)
    k = apply_phase_rotation(k)
    q, k, v = q.to(device), k.to(device), v.to(device)
    try:
        y = consensus_aggregate(q, k, v)
    except Exception:
        y = consensus_aggregate(q.cpu(), k.cpu(), v.cpu()).to(device)

    # Readout: mean projection → trinary
    y_score = y.mean(dim=-1) if y.ndim == 2 else y
    y_score = y_score - y_score.mean()
    tern = torch.zeros(y_score.shape[0], dtype=torch.int8, device=device)
    thr = y_score.std().clamp(min=1e-4) * 0.5
    tern = torch.where(y_score > thr, torch.full_like(tern, 1), tern)
    tern = torch.where(y_score < -thr, torch.full_like(tern, -1), tern)

    text_c, morse_c = codec.ternary_to_text(tern.tolist())
    chem = generative_chemical_report(tern.tolist())
    tern_clean = codec.units_to_ternary(units)
    chem_clean = generative_chemical_report(tern_clean)

    report = {
        "backend": backend,
        "device": device,
        "input": text,
        "normalized": cleaned,
        "lesion": lesion_info,
        "quarantine": qmeta,
        "consensus": {
            "seq_len": int(q.shape[0]),
            "head_dim": head_dim,
            "y_mean": float(y_score.mean().item()),
            "y_std": float(y_score.std().item()),
            "emergent_frac": float((tern == 1).float().mean().item()),
        },
        "morse_readout": {
            "text": text_c,
            "morse_head": morse_c[:300],
            "symbolic_exact": codec.decode_morse_string(codec.encode_text(cleaned)) == cleaned,
        },
        "chemical_readout": {
            "from_consensus": {
                "aa_sequence": chem.get("aa_sequence"),
                "n_codons": chem.get("n_codons"),
                "utterance": chem.get("enriched_utterance") or chem.get("chemical_utterance"),
            },
            "from_clean_morse": {
                "aa_sequence": chem_clean.get("aa_sequence"),
                "n_codons": chem_clean.get("n_codons"),
                "utterance": chem_clean.get("enriched_utterance") or chem_clean.get("chemical_utterance"),
            },
        },
        "reservoir_stats": {
            "mean_rate_Hz": float(out["firing_rate_Hz"].mean().item()),
            "mean_S": float(S.mean().item()),
            "mean_S_quarantined": float(S_q.mean().item()),
        },
    }
    path = ARTIFACTS / "gpu_consensus_morse_chem_report.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    report["report_path"] = str(path)
    return report
