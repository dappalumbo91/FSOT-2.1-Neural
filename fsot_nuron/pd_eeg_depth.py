"""
Deeper PD EEG integration: local signal stats → lesion scales → failure probe.

Uses whatever is already staged under data/eeg (Allen features, OpenNeuro index,
Kaggle emotions energy proxies, optional EDF if present). Does not re-upload data.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .paths import ARTIFACTS, ROOT
from .eeg_sources import (
    PD_LITERATURE_PRIORS,
    discover_local_eeg,
    gather_eeg_context,
    derive_pd_lesion_scales,
)
from .failure_boundaries import probe_failure_mode

RESULTS_DIR = ROOT / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _try_signal_stats(path: Path, max_samples: int = 50_000) -> Optional[Dict[str, Any]]:
    """Lightweight numeric channel stats from csv/npy/txt; skip if unreadable."""
    try:
        suf = path.suffix.lower()
        if suf == ".npy":
            arr = np.load(path, mmap_mode="r")
            flat = np.asarray(arr).reshape(-1)[:max_samples].astype(np.float64)
        elif suf in {".csv", ".txt"}:
            # sample first columns
            data = np.genfromtxt(path, delimiter=",", max_rows=2000)
            if data.ndim == 1:
                flat = data[:max_samples]
            else:
                flat = data[:, 0][:max_samples]
            flat = flat[np.isfinite(flat)].astype(np.float64)
        else:
            return None
        if flat.size < 32:
            return None
        # crude band proxies via successive diffs (not clinical PSD)
        d1 = np.diff(flat)
        energy = float(np.mean(flat**2))
        high = float(np.mean(d1**2))
        irreg = float(np.std(d1) / (np.std(flat) + 1e-9))
        return {
            "path": str(path),
            "n": int(flat.size),
            "energy": energy,
            "diff_energy": high,
            "irregularity": irreg,
            "beta_proxy": high / (energy + 1e-9),
        }
    except Exception as e:
        return {"path": str(path), "error": str(e)}


def build_pd_eeg_depth_report(
    *,
    run_probe: bool = True,
    n_units: int = 48,
    steps: int = 600,
    write: bool = True,
) -> Dict[str, Any]:
    local = discover_local_eeg(max_files=40)
    signal_stats: List[Dict[str, Any]] = []
    for item in local[:12]:
        p = Path(item["path"])
        if p.suffix.lower() in {".csv", ".txt", ".npy"}:
            st = _try_signal_stats(p)
            if st:
                signal_stats.append(st)

    ctx = gather_eeg_context(fetch_live=False)
    # blend literature + measured irregularity if any
    irreg_vals = [s["irregularity"] for s in signal_stats if "irregularity" in s]
    beta_vals = [s["beta_proxy"] for s in signal_stats if "beta_proxy" in s]
    measured = {
        "n_signal_files_scored": len(signal_stats),
        "mean_irregularity": float(np.mean(irreg_vals)) if irreg_vals else None,
        "mean_beta_proxy": float(np.mean(beta_vals)) if beta_vals else None,
        "literature": PD_LITERATURE_PRIORS,
    }
    lesion = ctx.get("pd_lesion_derived") or derive_pd_lesion_scales({})
    if measured["mean_irregularity"] is not None:
        # strengthen lesion with measured irregularity (clamped)
        irr = float(measured["mean_irregularity"])
        scale = float(np.clip(0.8 + 0.4 * irr, 0.7, 2.2))
        base = dict(lesion.get("fsot_lesion") or lesion)
        for k in ("adapt_step_scale", "isi_cv_scale", "fi_stim_scale"):
            if k in base and isinstance(base[k], (int, float)):
                if "fi_stim" in k:
                    base[k] = float(base[k]) * (2.0 - 0.3 * scale)  # lower drive
                else:
                    base[k] = float(base[k]) * scale
        lesion = {**lesion, "fsot_lesion": base, "measured_scale": scale}

    probe = None
    if run_probe:
        probe = probe_failure_mode(
            "PD_rate_irregularity",
            n_units=n_units,
            steps=steps,
            device="cpu",
            use_eeg=True,
            auto_wire=True,
        )

    def _pop_rate(block: Any, key: str = "population") -> Any:
        if not isinstance(block, dict):
            return None
        pop = block.get(key) if key in block else block
        if isinstance(pop, dict):
            return pop.get("mean_firing_rate_Hz")
        return None

    probe_summary = None
    if probe:
        les = probe.get("lesioned") or {}
        wire = probe.get("wire_around") or {}
        healthy = probe.get("healthy") or {}
        eeg = probe.get("eeg_context") or {}
        probe_summary = {
            "mode_id": probe.get("mode_id"),
            "label": probe.get("label"),
            "breached": les.get("breached"),
            "signature_hits": les.get("signature_hits"),
            "relative_flags": les.get("relative_flags"),
            "rate_healthy": _pop_rate(healthy),
            "rate_lesion": _pop_rate(les),
            "rate_wire": _pop_rate(wire),
            "rate_ratio_lesion": les.get("rate_ratio_vs_healthy"),
            "rate_ratio_wire": wire.get("rate_ratio_vs_healthy"),
            "recovered": wire.get("recovered_envelope"),
            "wire_strategy": wire.get("strategy"),
            "wire_actions": wire.get("actions"),
            "eeg_used": eeg.get("used"),
            "n_local_eeg": eeg.get("n_local_eeg"),
            "openneuro_pd_ok": eeg.get("openneuro_pd_ok"),
        }

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "local_eeg_candidates": len(local),
        "signal_stats_head": signal_stats[:6],
        "measured": measured,
        "eeg_context_ok": bool(ctx.get("ok", True) if isinstance(ctx, dict) else False),
        "openneuro": (ctx.get("openneuro_pd") if isinstance(ctx, dict) else None),
        "pd_lesion": lesion,
        "probe": probe_summary,
        "honesty": (
            "Signal stats are lightweight local proxies (not clinical PSD diagnosis). "
            "OpenNeuro ds002778 metadata/priors used when full EDF absent. "
            "Failure probe is substrate lesion engineering."
        ),
    }

    if write:
        p = RESULTS_DIR / "pd_eeg_depth.json"
        p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "pd_eeg_depth.json").write_text(
            json.dumps(out, indent=2, default=str), encoding="utf-8"
        )
        out["path"] = str(p)
    return out
