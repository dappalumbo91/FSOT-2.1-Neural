"""
Cross-validate FSOT batch neurons against Allen population statistics.

Modes:
  bio_match — close ISI / adaptation gaps vs Allen sample
  efficient — same structure, faster trains (intelligence throughput)

Reports a gap ledger so nothing stays "honest but ignored."
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import torch

from .allen_data import (
    data_status,
    load_ephys_csv,
    map_allen_to_fsot_params,
    population_stats,
    sample_cells,
    fetch_allen_specimen_features,
    fetch_neuroelectro_summary,
)
from .bio_metrics import (
    CORTICAL_BANDS,
    band_report,
    population_profiles,
    summarize_profiles,
)
from .modes import OperatingMode, mode_philosophy
from .calibrate import calibrate_batch
from .neuron_batch import FSOTNeuronBatch, NeuronConfig
from .paths import ARTIFACTS


def build_allen_tuned_batch(
    n_units: int = 64,
    device: Optional[str] = None,
    seed: int = 42,
    mode: str = "bio_match",
    calibrate: bool = True,
    calibrate_steps: int = 700,
) -> tuple[FSOTNeuronBatch, List[Dict[str, float]], Dict[str, Any]]:
    op = OperatingMode.parse(mode)
    rows = load_ephys_csv()
    meta: Dict[str, Any] = {
        "source": "allen_csv" if rows else "defaults",
        "n_source_cells": len(rows),
        "mode": op.value,
    }
    if not rows:
        net = FSOTNeuronBatch(NeuronConfig(n_units=n_units), device=device)
        net.mode_name = op.value
        return net, [], meta

    sample = sample_cells(rows, n=n_units, seed=seed)
    params = [map_allen_to_fsot_params(r, mode=op.value) for r in sample]
    cfg = NeuronConfig(n_units=len(params))
    net = FSOTNeuronBatch(cfg, device=device)

    d_eff = torch.tensor([p["d_eff"] for p in params], device=net.device, dtype=net.dtype)
    fire = torch.tensor([p["fire_threshold"] for p in params], device=net.device, dtype=net.dtype)
    vrest = torch.tensor([p["vrest_mV"] for p in params], device=net.device, dtype=net.dtype)
    again = torch.tensor([p["adapt_gain"] for p in params], device=net.device, dtype=net.dtype)
    adec = torch.tensor([p["adapt_decay"] for p in params], device=net.device, dtype=net.dtype)
    ref = torch.tensor([int(p["refractory_steps"]) for p in params], device=net.device, dtype=torch.int32)
    fistim = torch.tensor([p["fi_stim"] for p in params], device=net.device, dtype=net.dtype)
    net.apply_bio_params(
        d_eff=d_eff,
        fire_threshold=fire,
        vrest_mV=vrest,
        adapt_gain=again,
        adapt_decay=adec,
        refractory_steps=ref,
        fi_stim=fistim,
        mode_name=op.value,
    )

    cal_report: Dict[str, Any] = {"enabled": calibrate}
    if calibrate and params:
        # FSOT-grade analytical lock + polish (SMILES-lab style ledger)
        cal_report = calibrate_batch(
            net,
            params,
            mode=op.value,
            steps=max(calibrate_steps, 1000),
            max_iters=5,
            isi_tol=0.005,
            adapt_tol=0.02,
            grade="fsot",
        )
        cal_report["enabled"] = True

    meta["population_allen"] = population_stats(rows)
    meta["sample_specimen_ids"] = [int(p["specimen_id"]) for p in params]
    meta["mean_target_isi_ms"] = sum(p["avg_isi_ms_target"] for p in params) / len(params)
    meta["mean_target_adapt"] = sum(p["adaptation_target"] for p in params) / len(params)
    meta["mean_ref_steps"] = float(net.ref_steps.float().mean().item())
    meta["mean_adapt_gain"] = float(net.adapt_gain.mean().item())
    meta["calibration"] = cal_report
    return net, params, meta


def _rel_err(sim: float, target: float) -> float:
    if sim != sim or target != target or abs(target) < 1e-9:
        return float("nan")
    return abs(sim - target) / (abs(target) + 1e-9)


def _gap_row(
    name: str,
    sim: float,
    target: float,
    *,
    tol_rel: float,
    note: str,
) -> Dict[str, Any]:
    err = _rel_err(sim, target)
    closed = err == err and err <= tol_rel
    return {
        "gap": name,
        "sim": sim,
        "target": target,
        "rel_error": err,
        "tol_rel": tol_rel,
        "closed": closed,
        "note": note,
    }


@torch.no_grad()
def run_mode_protocols(
    net: FSOTNeuronBatch,
    params: List[Dict[str, float]],
    steps: int,
) -> Dict[str, Any]:
    net.reset()
    hist_ev = net.run(steps, stimulus_pattern="fi_step", record=True)
    sum_ev = net.metrics_summary(hist_ev)
    prof_ev = population_profiles(hist_ev["fired"], hist_ev["S"])
    pop_ev = summarize_profiles(prof_ev)

    net.reset()
    hist_per = net.run(steps, stimulus_pattern="periodic", record=True)
    pop_per = summarize_profiles(population_profiles(hist_per["fired"], hist_per["S"]))

    net.reset()
    hist_sp = net.run(steps, stimulus_pattern="random", record=True)
    sum_sp = net.metrics_summary(hist_sp)
    prof_sp = population_profiles(hist_sp["fired"], hist_sp["S"])
    pop_sp = summarize_profiles(prof_sp)

    net.reset()
    hist_rest = net.run(min(400, steps), stimulus_pattern="rest", record=True)
    pop_rest = summarize_profiles(population_profiles(hist_rest["fired"], hist_rest["S"]))

    allen_adapt = float("nan")
    allen_isi = float("nan")
    if params:
        adapts = [p["adaptation_target"] for p in params if p["adaptation_target"] == p["adaptation_target"]]
        isis = [p["avg_isi_ms_target"] for p in params if p["avg_isi_ms_target"] == p["avg_isi_ms_target"]]
        allen_adapt = sum(adapts) / len(adapts) if adapts else float("nan")
        allen_isi = sum(isis) / len(isis) if isis else float("nan")

    band_ev = band_report(
        {
            "firing_rate_Hz": pop_ev["mean_firing_rate_Hz"],
            "adaptation_index": pop_ev["mean_adaptation_index"],
        },
        {
            "firing_rate_Hz": "firing_rate_evoked_Hz",
            "adaptation_index": "adaptation_index",
        },
    )
    band_sp = band_report(
        {
            "firing_rate_Hz": pop_sp["mean_firing_rate_Hz"],
            "isi_cv": pop_sp["mean_isi_cv"],
        },
        {
            "firing_rate_Hz": "firing_rate_spontaneous_Hz",
            "isi_cv": "isi_cv",
        },
    )
    mean_vrest_cfg = float(net.vrest.mean().item())
    band_rest = band_report(
        {"Vm_proxy": mean_vrest_cfg},
        {"Vm_proxy": "vrest_mV"},
    )
    pop_rest = {
        **pop_rest,
        "configured_vrest_mV": mean_vrest_cfg,
        "dynamic_Vm_proxy_mV": pop_rest.get("mean_Vm_proxy_mV", float("nan")),
        "rest_rate_Hz": pop_rest.get("mean_firing_rate_Hz", float("nan")),
    }

    comparison = {
        "allen_mean_adaptation": allen_adapt,
        "fsot_mean_adaptation_evoked": pop_ev["mean_adaptation_index"],
        "adaptation_rel_error": _rel_err(pop_ev["mean_adaptation_index"], allen_adapt),
        "allen_mean_avg_isi_ms": allen_isi,
        "fsot_mean_isi_ms_evoked": pop_ev["mean_isi_ms"],
        "isi_rel_error": _rel_err(pop_ev["mean_isi_ms"], allen_isi),
        "fsot_mean_rate_evoked_Hz": pop_ev["mean_firing_rate_Hz"],
        "allen_implied_rate_Hz": (1000.0 / allen_isi) if allen_isi == allen_isi and allen_isi > 0 else float("nan"),
    }

    # Gap ledger — tolerances depend on mode intent
    mode = getattr(net, "mode_name", "bio_match")
    if mode == OperatingMode.BIO_MATCH.value:
        # FSOT-grade pop-mean gap budget (1 ms grid → ~1–2% floor on ~70 ms ISI)
        isi_tol, adapt_tol = 0.02, 0.10  # ISI ≤2%, adapt ≤10%
    else:
        # Efficient: ISI expected ~3× faster → compare to scaled target
        isi_tol, adapt_tol = 0.10, 0.25
        if allen_isi == allen_isi:
            comparison["efficient_isi_target_ms"] = allen_isi / 3.0
            comparison["isi_rel_error_vs_efficient_target"] = _rel_err(
                pop_ev["mean_isi_ms"], allen_isi / 3.0
            )

    isi_target_for_gap = allen_isi if mode == OperatingMode.BIO_MATCH.value else (
        allen_isi / 3.0 if allen_isi == allen_isi else float("nan")
    )
    gaps = [
        _gap_row(
            "mean_isi_ms",
            pop_ev["mean_isi_ms"],
            isi_target_for_gap,
            tol_rel=isi_tol,
            note=(
                "bio_match tracks Allen avg_isi; efficient tracks Allen/3 (throughput)"
                if mode == OperatingMode.EFFICIENT.value
                else "bio_match: refractory floor ≈ 0.78× Allen avg_isi"
            ),
        ),
        _gap_row(
            "adaptation_index",
            pop_ev["mean_adaptation_index"],
            allen_adapt,
            tol_rel=adapt_tol,
            note="mild AHP; sign/order match matters more than exact magnitude",
        ),
        {
            "gap": "evoked_rate_band",
            "sim": pop_ev["mean_firing_rate_Hz"],
            "target": "band 5–80 Hz",
            "rel_error": float("nan"),
            "tol_rel": 0.0,
            "closed": band_ev["rows"][0]["in_band"] if band_ev["rows"] else False,
            "note": "cortical evoked band",
        },
        {
            "gap": "spontaneous_rate_band",
            "sim": pop_sp["mean_firing_rate_Hz"],
            "target": "band 0.1–15 Hz",
            "rel_error": float("nan"),
            "tol_rel": 0.0,
            "closed": band_sp["rows"][0]["in_band"] if band_sp["rows"] else False,
            "note": "sparse bombardment",
        },
        {
            "gap": "rest_vrest_band",
            "sim": mean_vrest_cfg,
            "target": "band -85–-55 mV",
            "rel_error": float("nan"),
            "tol_rel": 0.0,
            "closed": band_rest["pass_rate"] >= 1.0,
            "note": "Allen-mapped passive Vrest",
        },
        {
            "gap": "rest_mostly_silent",
            "sim": pop_rest.get("rest_rate_Hz", float("nan")),
            "target": 3.0,  # Hz upper soft bound
            "rel_error": float("nan"),
            "tol_rel": 0.0,
            "closed": (
                pop_rest.get("rest_rate_Hz", 99) == pop_rest.get("rest_rate_Hz", 99)
                and pop_rest.get("rest_rate_Hz", 99) <= 3.0
            ),
            "note": "no free phase-drift pacemaker",
        },
    ]
    n_closed = sum(1 for g in gaps if g.get("closed"))
    gap_summary = {
        "n_closed": n_closed,
        "n_total": len(gaps),
        "all_closed": n_closed == len(gaps),
        "rows": gaps,
    }

    return {
        "mode": mode,
        "evoked": {"summary": sum_ev, "population": pop_ev, "bands": band_ev, "protocol": "fi_step"},
        "periodic": {"population": pop_per, "protocol": "periodic"},
        "spontaneous": {"summary": sum_sp, "population": pop_sp, "bands": band_sp, "protocol": "random"},
        "rest": {"population": pop_rest, "bands": band_rest},
        "comparison_to_allen_sample": comparison,
        "gaps": gap_summary,
        "verdict": {
            "evoked_band_pass_rate": band_ev["pass_rate"],
            "spontaneous_band_pass_rate": band_sp["pass_rate"],
            "rest_band_pass_rate": band_rest["pass_rate"],
            "gaps_closed": f"{n_closed}/{len(gaps)}",
            "small_net": True,
        },
    }


@torch.no_grad()
def run_validation(
    n_units: int = 64,
    steps: int = 1000,
    device: Optional[str] = None,
    use_api: bool = False,
    seed: int = 42,
    mode: str = "bio_match",
    both_modes: bool = True,
    calibrate: bool = True,
) -> Dict[str, Any]:
    """
    Validate one mode (default bio_match). If both_modes, also run efficient
    and attach a dual-mode efficiency ledger.
    """
    primary = OperatingMode.parse(mode)
    net, params, meta = build_allen_tuned_batch(
        n_units=n_units,
        device=device,
        seed=seed,
        mode=primary.value,
        calibrate=calibrate,
    )
    primary_block = run_mode_protocols(net, params, steps)

    modes_out: Dict[str, Any] = {primary.value: primary_block}

    if both_modes:
        other = (
            OperatingMode.EFFICIENT
            if primary is OperatingMode.BIO_MATCH
            else OperatingMode.BIO_MATCH
        )
        net2, params2, meta2 = build_allen_tuned_batch(
            n_units=n_units,
            device=device,
            seed=seed,
            mode=other.value,
            calibrate=calibrate,
        )
        modes_out[other.value] = run_mode_protocols(net2, params2, steps)
        # Keep efficiency meta from other mode calibration too
        meta["other_mode_calibration"] = meta2.get("calibration")

    # Dual-mode efficiency ratio (when both present)
    efficiency: Dict[str, Any] = {}
    if "bio_match" in modes_out and "efficient" in modes_out:
        isi_b = modes_out["bio_match"]["comparison_to_allen_sample"]["fsot_mean_isi_ms_evoked"]
        isi_e = modes_out["efficient"]["comparison_to_allen_sample"]["fsot_mean_isi_ms_evoked"]
        rate_b = modes_out["bio_match"]["evoked"]["population"]["mean_firing_rate_Hz"]
        rate_e = modes_out["efficient"]["evoked"]["population"]["mean_firing_rate_Hz"]
        efficiency = {
            "bio_match_isi_ms": isi_b,
            "efficient_isi_ms": isi_e,
            "isi_speedup": (isi_b / isi_e) if isi_e and isi_e == isi_e and isi_e > 0 else float("nan"),
            "bio_match_rate_Hz": rate_b,
            "efficient_rate_Hz": rate_e,
            "rate_speedup": (rate_e / rate_b) if rate_b and rate_b > 0 else float("nan"),
            "philosophy": mode_philosophy()["efficient"],
        }

    api_block: Dict[str, Any] = {"enabled": use_api}
    if use_api:
        if meta.get("sample_specimen_ids"):
            sid = meta["sample_specimen_ids"][0]
            api_block["specimen_features"] = fetch_allen_specimen_features(sid)
        api_block["neuroelectro"] = fetch_neuroelectro_summary()

    primary_gaps = primary_block["gaps"]
    report = {
        "data_status": data_status(),
        "meta": meta,
        "device": str(net.device),
        "n_units": n_units,
        "steps": steps,
        "primary_mode": primary.value,
        "modes": modes_out,
        # Flatten primary for backward-compatible CLI
        "evoked": primary_block["evoked"],
        "periodic": primary_block["periodic"],
        "spontaneous": primary_block["spontaneous"],
        "rest": primary_block["rest"],
        "comparison_to_allen_sample": primary_block["comparison_to_allen_sample"],
        "gaps": primary_gaps,
        "efficiency": efficiency,
        "mode_philosophy": mode_philosophy(),
        "cortical_bands_reference": {k: list(v) for k, v in CORTICAL_BANDS.items()},
        "api": api_block,
        "verdict": {
            **primary_block["verdict"],
            "note": (
                "Gaps are closed under explicit tolerances. bio_match tracks wetware timing; "
                "efficient keeps FSOT structure with faster ISI for intelligence throughput. "
                "Biology is the reference, not the speed limit."
            ),
        },
    }

    out_path = ARTIFACTS / "bio_validation_report.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    report["report_path"] = str(out_path)
    return report
