"""
Neurological failure boundaries for the FSOT micro-neuron substrate.

Maps known neurodegenerative / neurological break modes onto FSOT knobs,
probes when the population leaves the healthy envelope, and records
wire-around strategies. Medical potential is a side-effect of boundary
knowledge — not the project goal.

Data: data/neuro_failure_boundaries.json + optional Allen envelope + OpenNeuro hooks.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch

from .allen_data import load_ephys_csv, population_stats
from .bio_metrics import population_profiles, summarize_profiles
from .neuron_batch import FSOTNeuronBatch
from .paths import ROOT, ARTIFACTS
from .validate import build_allen_tuned_batch

CATALOG_PATH = ROOT / "data" / "neuro_failure_boundaries.json"


def load_failure_catalog(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or CATALOG_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def allen_healthy_envelope() -> Dict[str, Any]:
    """Empirical envelope from local Allen ephys (p5–p95 style)."""
    rows = load_ephys_csv()
    if not rows:
        return {"ok": False, "reason": "no Allen CSV"}
    pop = population_stats(rows)
    isis = sorted(r.avg_isi_ms for r in rows if r.avg_isi_ms == r.avg_isi_ms and r.avg_isi_ms > 5)
    ads = sorted(r.adaptation for r in rows if r.adaptation == r.adaptation)
    vrests = sorted(r.vrest_mV for r in rows if r.vrest_mV == r.vrest_mV)

    def pct(a: List[float], p: float) -> float:
        if not a:
            return float("nan")
        return a[int(round((len(a) - 1) * p))]

    return {
        "ok": True,
        "n_cells": len(rows),
        "isi_ms_p05": pct(isis, 0.05),
        "isi_ms_p95": pct(isis, 0.95),
        "adapt_p05": pct(ads, 0.05),
        "adapt_p95": pct(ads, 0.95),
        "vrest_p05": pct(vrests, 0.05),
        "vrest_p95": pct(vrests, 0.95),
        "population_means": pop,
    }


@torch.no_grad()
def apply_lesion(
    net: FSOTNeuronBatch,
    mode_id: str,
    *,
    catalog: Optional[Dict[str, Any]] = None,
    seed: int = 0,
    lesion_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Apply a named failure mode's FSOT lesion to the batch in-place.
    lesion_override: replace catalog fsot_lesion (e.g. EEG-derived PD scales).
    """
    catalog = catalog or load_failure_catalog()
    modes = {m["id"]: m for m in catalog["failure_modes"]}
    if mode_id not in modes:
        raise KeyError(f"unknown failure mode {mode_id}; known={list(modes)}")

    mode = modes[mode_id]
    lesion = dict(mode["fsot_lesion"])
    if lesion_override:
        lesion.update(lesion_override)
    B = net.cfg.n_units
    g = torch.Generator(device="cpu")
    g.manual_seed(seed)

    meta: Dict[str, Any] = {
        "mode_id": mode_id,
        "label": mode["label"],
        "applied": {},
        "lesion_override": bool(lesion_override),
    }

    # Silence fraction = "dead" units (cannot fire)
    sil_f = float(lesion.get("silence_fraction", 0.0))
    n_sil = int(round(sil_f * B))
    perm = torch.randperm(B, generator=g)
    silenced = perm[:n_sil].tolist()
    alive = perm[n_sil:].tolist()
    meta["silenced_units"] = silenced
    meta["n_silenced"] = n_sil

    if not hasattr(net, "unit_alive"):
        net.unit_alive = torch.ones(B, device=net.device, dtype=torch.bool)
    net.unit_alive[:] = True
    if silenced:
        idx = torch.tensor(silenced, device=net.device, dtype=torch.long)
        net.unit_alive[idx] = False
        # Park silenced units at high threshold
        net.fire_thr[idx] = 9.0

    def scale_alive(tensor: torch.Tensor, key: str, default: float = 1.0) -> None:
        s = float(lesion.get(key, default))
        if abs(s - 1.0) < 1e-9 or not alive:
            return
        aidx = torch.tensor(alive, device=net.device, dtype=torch.long)
        tensor[aidx] = tensor[aidx] * s
        meta["applied"][key] = s

    scale_alive(net.adapt_step, "adapt_step_scale", 1.0)
    scale_alive(net.adapt_gain, "adapt_gain_scale", 1.0)
    scale_alive(net.fi_stim, "fi_stim_scale", 1.0)

    if "ref_steps_scale" in lesion and alive:
        s = float(lesion["ref_steps_scale"])
        aidx = torch.tensor(alive, device=net.device, dtype=torch.long)
        net.ref_steps[aidx] = (
            net.ref_steps[aidx].float() * s
        ).round().clamp(2, 250).to(torch.int32)
        meta["applied"]["ref_steps_scale"] = s

    if "fire_thr_delta" in lesion and alive:
        d = float(lesion["fire_thr_delta"])
        aidx = torch.tensor(alive, device=net.device, dtype=torch.long)
        net.fire_thr[aidx] = net.fire_thr[aidx] + d
        meta["applied"]["fire_thr_delta"] = d

    if "d_eff_delta" in lesion and alive:
        d = float(lesion["d_eff_delta"])
        aidx = torch.tensor(alive, device=net.device, dtype=torch.long)
        net.d_eff[aidx] = (net.d_eff[aidx] + d).clamp(4.0, 25.0)
        meta["applied"]["d_eff_delta"] = d

    # Optional ISI jitter stored for stimulus path
    net.lesion_isi_jitter = float(lesion.get("isi_jitter", 0.0))
    net.lesion_phase_lock = float(lesion.get("phase_lock_strength", 0.0))
    net.lesion_s_clamp = lesion.get("s_clamp")
    net.lesion_hard_kill_after = lesion.get("hard_kill_after_spikes")
    net.lesion_spread = float(lesion.get("spread_per_100_steps", 0.0))
    net.lesion_burst_force = float(lesion.get("burst_force", 0.0))
    net.lesion_mode_id = mode_id
    # consensus mask: True = participate (alive units)
    net.consensus_mask = net.unit_alive.clone()
    meta["wire_around"] = mode.get("wire_around", {})
    meta["break_signature"] = mode.get("break_signature", {})
    meta["fsot_lesion_final"] = lesion
    return meta


def _in_envelope(metrics: Dict[str, float], envelope: Dict[str, List[float]]) -> Dict[str, bool]:
    checks = {}
    mapping = {
        "firing_rate_Hz": "mean_firing_rate_Hz",
        "mean_isi_ms": "mean_isi_ms",
        "adaptation_index": "mean_adaptation_index",
        "isi_cv": "mean_isi_cv",
    }
    for ek, mk in mapping.items():
        band = envelope.get(ek)
        val = metrics.get(mk, float("nan"))
        if not band or val != val:
            checks[ek] = False
            continue
        checks[ek] = band[0] <= val <= band[1]
    checks["all_in"] = all(checks.values()) if checks else False
    return checks


@torch.no_grad()
def probe_failure_mode(
    mode_id: str,
    *,
    n_units: int = 64,
    steps: int = 1000,
    device: str = "cpu",
    seed: int = 42,
    use_eeg: bool = True,
    auto_wire: bool = True,
) -> Dict[str, Any]:
    """
    Healthy baseline vs lesioned population. Reports envelope breach + wire-around.
    PD mode can pull EEG-derived lesion scales; wire-around can be auto-selected.
    """
    from .wire_around_policy import select_wire_around

    catalog = load_failure_catalog()
    envelope = catalog["healthy_operating_envelope"]
    allen_env = allen_healthy_envelope()

    lesion_override = None
    eeg_ctx = None
    if use_eeg and mode_id == "PD_rate_irregularity":
        try:
            from .eeg_sources import gather_eeg_context, derive_pd_lesion_scales

            eeg_ctx = gather_eeg_context(fetch_live=True)
            lesion_override = eeg_ctx["pd_lesion_derived"]["fsot_lesion"]
        except Exception as e:
            eeg_ctx = {"ok": False, "error": str(e)}

    net_h, params, meta = build_allen_tuned_batch(
        n_units=n_units, device=device, seed=seed, mode="efficient", calibrate=False
    )
    net_h.reset()
    hist_h = net_h.run(steps, stimulus_pattern="fi_step", record=True)
    pop_h = summarize_profiles(population_profiles(hist_h["fired"], hist_h["S"]))
    env_h = _in_envelope(pop_h, envelope)

    net_l, _, _ = build_allen_tuned_batch(
        n_units=n_units, device=device, seed=seed, mode="efficient", calibrate=False
    )
    lesion_meta = apply_lesion(
        net_l, mode_id, catalog=catalog, seed=seed, lesion_override=lesion_override
    )
    # Gate firing on unit_alive
    _patch_alive_gate(net_l)
    net_l.reset()
    hist_l = net_l.run(steps, stimulus_pattern="fi_step", record=True)
    pop_l = summarize_profiles(population_profiles(hist_l["fired"], hist_l["S"]))
    env_l = _in_envelope(pop_l, envelope)

    # Precompute relative flags for auto wire-around (same logic as below, light)
    rh0 = pop_h.get("mean_firing_rate_Hz") or 0.0
    rl0 = pop_l.get("mean_firing_rate_Hz") or 0.0
    pre_flags = {
        "rate_drop": rh0 > 1e-6 and (rl0 / rh0) < 0.75,
        "rate_runaway": rh0 > 1e-6 and (rl0 / rh0) > 1.35,
        "global_silence": rl0 < 2.0,
        "population_sparsity": lesion_meta.get("n_silenced", 0) > 0.2 * n_units,
    }
    pre_hits = [k for k, v in pre_flags.items() if v]
    for k, want in (lesion_meta.get("break_signature") or {}).items():
        if want and k not in pre_hits:
            # light include catalog signatures as candidates for policy
            if k in ("isi_cv_high", "burst_clustering", "rate_drop", "progressive_sparsity"):
                pre_hits.append(k)

    catalog_wire = lesion_meta.get("wire_around") or {}
    if auto_wire:
        auto_policy = select_wire_around(
            pre_hits, relative_flags=pre_flags, catalog_default=catalog_wire
        )
    else:
        auto_policy = {**catalog_wire, "auto": False}

    # Wire-around demo with auto policy
    net_w, _, _ = build_allen_tuned_batch(
        n_units=n_units, device=device, seed=seed, mode="efficient", calibrate=False
    )
    apply_lesion(net_w, mode_id, catalog=catalog, seed=seed, lesion_override=lesion_override)
    _patch_alive_gate(net_w)
    _apply_wire_around(net_w, auto_policy)
    net_w.reset()
    hist_w = net_w.run(steps, stimulus_pattern="fi_step", record=True)
    pop_w = summarize_profiles(population_profiles(hist_w["fired"], hist_w["S"]))
    env_w = _in_envelope(pop_w, envelope)

    # Relative breach vs healthy (envelope alone is too soft for efficient-mode rates)
    sig = lesion_meta.get("break_signature") or {}
    rh = pop_h.get("mean_firing_rate_Hz") or 0.0
    rl = pop_l.get("mean_firing_rate_Hz") or 0.0
    rw = pop_w.get("mean_firing_rate_Hz") or 0.0
    ih = pop_h.get("mean_isi_ms") or float("nan")
    il = pop_l.get("mean_isi_ms") or float("nan")
    ah = pop_h.get("mean_adaptation_index") or 0.0
    al = pop_l.get("mean_adaptation_index") or 0.0

    rel_flags = {
        "rate_drop": rh > 1e-6 and (rl / rh) < 0.75,
        "rate_runaway": rh > 1e-6 and (rl / rh) > 1.35,
        "isi_prolonged": ih == ih and il == il and il > ih * 1.25,
        "adaptation_runaway": abs(al) > abs(ah) * 1.4 + 0.02,
        "global_silence": rl < 2.0,
        "population_sparsity": lesion_meta.get("n_silenced", 0) > 0.2 * n_units,
    }
    # Mode-specific signature hits
    sig_hits = []
    for k, want in sig.items():
        if not want:
            continue
        if k in rel_flags and rel_flags[k]:
            sig_hits.append(k)
        elif k == "survivor_hyperexcitability" and rel_flags["rate_runaway"]:
            sig_hits.append(k)
        elif k == "late_silence" and rel_flags["rate_drop"]:
            sig_hits.append(k)
        elif k == "progressive_sparsity" and lesion_meta.get("n_silenced", 0) > 0:
            sig_hits.append(k)
        elif k == "s_collapse" and rel_flags["global_silence"]:
            sig_hits.append(k)
        elif k == "burst_clustering" and rel_flags.get("rate_runaway"):
            sig_hits.append(k)
        elif k == "isi_cv_high":
            cvl = pop_l.get("mean_isi_cv") or 0
            cvh = pop_h.get("mean_isi_cv") or 0
            if cvl > cvh * 1.2 + 0.05:
                sig_hits.append(k)
        elif k == "adaptation_collapse" and abs(al) < abs(ah) * 0.5:
            sig_hits.append(k)
        elif k == "emergent_fraction_drop":
            # proxy: rate drop
            if rel_flags["rate_drop"]:
                sig_hits.append(k)

    breached = (not env_l.get("all_in", True)) or any(rel_flags.values()) or len(sig_hits) > 0
    # Recovery: move rate back toward healthy or re-enter envelope
    recovered = env_w.get("all_in", False) or (
        abs(rw - rh) < abs(rl - rh) * 0.85 if rh > 1e-6 else env_w.get("all_in", False)
    )

    report = {
        "mode_id": mode_id,
        "label": lesion_meta.get("label"),
        "lesion": lesion_meta,
        "healthy": {"population": pop_h, "envelope": env_h},
        "lesioned": {
            "population": pop_l,
            "envelope": env_l,
            "breached": breached,
            "relative_flags": rel_flags,
            "signature_hits": sig_hits,
            "rate_ratio_vs_healthy": (rl / rh) if rh > 1e-6 else float("nan"),
        },
        "wire_around": {
            "strategy": auto_policy.get("strategy"),
            "actions": auto_policy.get("actions"),
            "auto": auto_policy.get("auto", False),
            "from_signatures": auto_policy.get("from_signatures"),
            "catalog_default": catalog_wire,
            "population": pop_w,
            "envelope": env_w,
            "recovered_envelope": recovered,
            "rate_ratio_vs_healthy": (rw / rh) if rh > 1e-6 else float("nan"),
        },
        "eeg_context": {
            "used": bool(lesion_override),
            "n_local_eeg": (eeg_ctx or {}).get("n_local_eeg"),
            "openneuro_pd_ok": (eeg_ctx or {}).get("openneuro_pd", {}).get("ok")
            if eeg_ctx
            else None,
            "pd_lesion": (eeg_ctx or {}).get("pd_lesion_derived") if eeg_ctx else None,
        },
        "allen_envelope": allen_env,
        "catalog_source": str(CATALOG_PATH),
        "project_note": (
            "Boundaries show how the substrate breaks; wire-around preserves compute "
            "capability. Not a medical device or treatment claim."
        ),
    }
    return report


def _patch_alive_gate(net: FSOTNeuronBatch) -> None:
    """Monkey-patch step to respect unit_alive (minimal invasive)."""
    if getattr(net, "_alive_patched", False):
        return
    orig_step = net.step

    def gated_step(stimulus):
        S, fired, phase, tern = orig_step(stimulus)
        if hasattr(net, "unit_alive"):
            fired = fired & net.unit_alive
            # zero spikes attributed to dead units already counted — correct count
            # (best-effort: dead units forced high thr so rarely fire)
        # progressive spread lesion
        spread = float(getattr(net, "lesion_spread", 0.0) or 0.0)
        if spread > 0 and hasattr(net, "unit_alive") and net.steps_run % 100 == 0:
            alive_idx = torch.nonzero(net.unit_alive, as_tuple=False).flatten()
            if alive_idx.numel() > 1:
                n_kill = max(1, int(round(spread * alive_idx.numel())))
                n_kill = min(n_kill, int(alive_idx.numel()) - 1)
                choice = alive_idx[torch.randperm(alive_idx.numel(), device=net.device)[:n_kill]]
                net.unit_alive[choice] = False
                net.fire_thr[choice] = 9.0
        # hard kill after N spikes
        hk = getattr(net, "lesion_hard_kill_after", None)
        if hk is not None and hasattr(net, "unit_alive"):
            kill = net.spike_count >= int(hk)
            if kill.any():
                net.unit_alive = net.unit_alive & (~kill)
                net.fire_thr = torch.where(kill, torch.full_like(net.fire_thr, 9.0), net.fire_thr)
        # S clamp (energy collapse)
        sc = getattr(net, "lesion_s_clamp", None)
        if sc is not None:
            net.S = net.S.clamp(max=float(sc))
            S = net.S
        # PD-like burst force: periodically amplify surviving units' effective fire
        bf = float(getattr(net, "lesion_burst_force", 0.0) or 0.0)
        if bf > 0 and hasattr(net, "unit_alive") and net.steps_run % 40 < int(8 + 20 * bf):
            # mark forced high-S on alive for clustering
            net.S = torch.where(net.unit_alive, net.S + 0.35 * bf, net.S)
            S = net.S
        return S, fired, phase, tern

    net.step = gated_step  # type: ignore
    net._alive_patched = True


def _apply_wire_around(net: FSOTNeuronBatch, wire: Dict[str, Any]) -> None:
    """Heuristic wire-around on survivors — keep system usable past lesion."""
    actions = set(wire.get("actions") or [])
    alive = getattr(net, "unit_alive", None)
    if alive is None:
        net.unit_alive = torch.ones(net.cfg.n_units, device=net.device, dtype=torch.bool)
        alive = net.unit_alive
    aidx = torch.nonzero(alive, as_tuple=False).flatten()
    if aidx.numel() == 0:
        # revive a minimal reserve pool
        if "recruit_reserve_units" in actions or "checkpoint_restore_revive" in actions:
            n_rev = max(1, net.cfg.n_units // 4)
            alive[:n_rev] = True
            net.fire_thr[:n_rev] = 1.05
            aidx = torch.nonzero(alive, as_tuple=False).flatten()
        else:
            return
    if "boost_fi_stim_on_survivors" in actions:
        net.fi_stim[aidx] = (net.fi_stim[aidx] * 1.35).clamp(max=1.2)
    if "lower_adapt_step" in actions:
        net.adapt_step[aidx] = net.adapt_step[aidx] * 0.55
    if "raise_fire_thr" in actions:
        net.fire_thr[aidx] = net.fire_thr[aidx] + 0.15
    if "lower_fire_thr" in actions:
        net.fire_thr[aidx] = (net.fire_thr[aidx] - 0.08).clamp(min=0.6)
    if "increase_adapt_step" in actions:
        net.adapt_step[aidx] = (net.adapt_step[aidx] * 1.8).clamp(max=6.0)
    if "shorten_ref_on_healthy" in actions or "subms_timing_compensate" in actions:
        net.ref_steps[aidx] = (
            net.ref_steps[aidx].float() * 0.7
        ).round().clamp(4, 200).to(torch.int32)
        if hasattr(net, "subms_enabled"):
            net.subms_enabled = True
    if "cap_survivor_rate" in actions:
        net.adapt_step[aidx] = (net.adapt_step[aidx] * 1.4).clamp(max=6.0)
        net.fire_thr[aidx] = net.fire_thr[aidx] + 0.05
    if "clamp_isi_cv" in actions or "inject_phase_noise" in actions:
        net.lesion_isi_jitter = 0.0
        net.lesion_phase_lock = 0.0
    if "recruit_reserve_units" in actions or "checkpoint_restore_revive" in actions:
        dead = torch.nonzero(~alive, as_tuple=False).flatten()
        if dead.numel() > 0:
            n_rev = max(1, min(int(dead.numel()), max(2, net.cfg.n_units // 5)))
            revive = dead[:n_rev]
            net.unit_alive[revive] = True
            net.fire_thr[revive] = 1.05
            net.fi_stim[revive] = 0.55
            net.adapt_step[revive] = 0.5
    if "consensus_quarantine_failed" in actions or "isolate_hot_units" in actions:
        # Mark dead units for consensus mask
        net.consensus_mask = net.unit_alive.clone()
    if "consensus_sparse_gate" in actions or "consensus_collapse_gate" in actions:
        net.consensus_gate_mode = (
            "sparse" if "consensus_sparse_gate" in actions else "collapse"
        )
    if "load_balance_consensus" in actions:
        net.consensus_load_balance = True
    if "lower_metabolic_load" in actions:
        net.fi_stim[aidx] = (net.fi_stim[aidx] * 0.85).clamp(min=0.2)
        net.adapt_step[aidx] = net.adapt_step[aidx] * 0.8


def probe_all_modes(
    n_units: int = 48,
    steps: int = 800,
    device: str = "cpu",
) -> Dict[str, Any]:
    catalog = load_failure_catalog()
    results = []
    for m in catalog["failure_modes"]:
        mid = m["id"]
        try:
            r = probe_failure_mode(mid, n_units=n_units, steps=steps, device=device)
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
                }
            )
        except Exception as e:
            results.append({"id": mid, "error": str(e)})
    out = {
        "n_modes": len(results),
        "modes": results,
        "allen_envelope": allen_healthy_envelope(),
        "catalog": str(CATALOG_PATH),
    }
    path = ARTIFACTS / "failure_boundary_report.json"
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    out["report_path"] = str(path)
    return out
