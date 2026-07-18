"""
EEG / clinical-signal sources for failure-boundary calibration.

Priority:
  1) Local EEG files (user machine)
  2) Cached OpenNeuro metadata (ds002778 PD)
  3) Live OpenNeuro GraphQL API
  4) Literature priors (always available)

Derives PD lesion strength scales from beta-sync / irregularity priors.
"""

from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .paths import ROOT, ARTIFACTS

EEG_CACHE = ARTIFACTS / "eeg_cache"
EEG_CACHE.mkdir(parents=True, exist_ok=True)

LOCAL_EEG_ROOTS = [
    ROOT / "data" / "eeg",
    ROOT / "data" / "eeg" / "allen_ephys",
    ROOT / "data" / "eeg" / "openneuro_pd",
    Path(r"C:\Users\damia\Desktop\Brain"),
    Path(r"C:\Users\damia\Desktop\FSOT NeuroLab"),
    Path(r"C:\Users\damia\Desktop\nuron"),
    Path(r"I:\FSOT-Physical-Archive\03_FSOT-PublicData\consciousness"),
]

OPENNEURO_INDEX_CANDIDATES = [
    Path(r"I:\FSOT-Physical-Archive\03_FSOT-PublicData\consciousness\openneuro\openneuro_index.json"),
    Path(r"I:\FSOT-Physical-Archive\03_FSOT-PublicData\anomaly_observables\consciousness\openneuro\openneuro_index.json"),
]

# Literature-grounded PD resting EEG priors (used when raw EEG not yet loaded)
PD_LITERATURE_PRIORS = {
    "beta_band_Hz": [13.0, 30.0],
    "beta_power_elevation": 1.45,  # relative to healthy baseline (typical reports)
    "isi_cv_elevation": 1.55,
    "sync_pressure": 0.55,
    "rate_irregularity": 0.42,
    "burst_index": 0.35,
    "source": "PD resting-state EEG literature + OpenNeuro ds002778 target",
}


def discover_local_eeg(max_files: int = 50) -> List[Dict[str, Any]]:
    """Find candidate EEG/signal files on known roots."""
    exts = {".edf", ".bdf", ".fif", ".set", ".vhdr", ".eeg", ".csv", ".mat", ".npy", ".txt"}
    found: List[Dict[str, Any]] = []
    for root in LOCAL_EEG_ROOTS:
        if not root.exists():
            continue
        try:
            for p in root.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in exts:
                    continue
                # skip huge unrelated
                try:
                    sz = p.stat().st_size
                except OSError:
                    continue
                if sz < 100 or sz > 2_000_000_000:
                    continue
                name_l = p.name.lower()
                score = 0
                for kw in ("eeg", "park", "pd", "neuro", "brain", "rest", "channel"):
                    if kw in name_l or kw in str(p).lower():
                        score += 1
                found.append(
                    {
                        "path": str(p),
                        "size": sz,
                        "suffix": p.suffix.lower(),
                        "relevance_score": score,
                    }
                )
                if len(found) >= max_files:
                    break
        except OSError:
            continue
        if len(found) >= max_files:
            break
    found.sort(key=lambda x: (-x["relevance_score"], -x["size"]))
    return found


def load_openneuro_index() -> Dict[str, Any]:
    for p in OPENNEURO_INDEX_CANDIDATES:
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                # find PD dataset
                pd_hits = []
                for d in data.get("datasets") or []:
                    name = str(d.get("name", "")).lower()
                    if "parkinson" in name or "pd " in name or d.get("id") == "ds002778":
                        pd_hits.append(d)
                return {
                    "ok": True,
                    "path": str(p),
                    "dataset_count": data.get("dataset_count"),
                    "pd_datasets": pd_hits,
                    "source": data.get("source"),
                }
            except Exception as e:
                return {"ok": False, "path": str(p), "error": str(e)}
    return {"ok": False, "reason": "no openneuro index on disk"}


def fetch_openneuro_pd_metadata(timeout: float = 45.0) -> Dict[str, Any]:
    """Live GraphQL pull for ds002778; caches to artifacts/eeg_cache."""
    import urllib.request

    cache_path = EEG_CACHE / "openneuro_ds002778.json"
    # OpenNeuro GraphQL (public); schema may evolve — fall back to cache/priors
    query = {
        "query": 'query { dataset(id: "ds002778") { id name } }',
    }
    req = urllib.request.Request(
        "https://openneuro.org/crn/graphql",
        data=json.dumps(query).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "FSOT-2.1-Neural/0.3"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        out = {"ok": True, "live": True, "data": data, "dataset_id": "ds002778"}
        cache_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        return out
    except Exception as e:
        if cache_path.is_file():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            cached["live"] = False
            cached["cache_fallback"] = True
            cached["error_ignored"] = str(e)
            return cached
        return {
            "ok": False,
            "live": False,
            "error": str(e),
            "offline_priors": PD_LITERATURE_PRIORS,
        }


def estimate_signal_stats_from_csv(path: Path, max_rows: int = 5000) -> Optional[Dict[str, float]]:
    """Best-effort numeric column variance as irregularity proxy."""
    try:
        import csv

        vals: List[float] = []
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                for cell in row:
                    try:
                        vals.append(float(cell))
                    except ValueError:
                        continue
        if len(vals) < 20:
            return None
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = math.sqrt(var)
        # crude peak rate proxy via zero crossings
        zc = 0
        for a, b in zip(vals, vals[1:]):
            if (a - mean) * (b - mean) < 0:
                zc += 1
        return {
            "n": float(len(vals)),
            "std": std,
            "cv": abs(std / mean) if abs(mean) > 1e-9 else float("nan"),
            "zero_cross_rate": zc / max(len(vals) - 1, 1),
        }
    except Exception:
        return None


def derive_pd_lesion_scales(eeg_bundle: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Map PD EEG irregularity / sync priors → stronger FSOT lesion knobs.
    """
    priors = dict(PD_LITERATURE_PRIORS)
    if eeg_bundle and eeg_bundle.get("derived_priors"):
        priors.update(eeg_bundle["derived_priors"])

    beta_el = float(priors.get("beta_power_elevation", 1.45))
    cv_el = float(priors.get("isi_cv_elevation", 1.55))
    sync = float(priors.get("sync_pressure", 0.55))
    irreg = float(priors.get("rate_irregularity", 0.42))

    # Stronger than v1 PD lesion
    lesion = {
        "adapt_step_scale": round(1.2 + 0.9 * irreg, 3),
        "isi_jitter": round(0.25 + 0.55 * (cv_el - 1.0), 3),
        "fire_thr_delta": round(-0.06 - 0.08 * sync, 3),
        "phase_lock_strength": round(min(0.85, 0.35 + 0.5 * sync), 3),
        "silence_fraction": round(0.08 + 0.12 * max(0.0, beta_el - 1.2), 3),
        "fi_stim_scale": round(0.85 + 0.2 * irreg, 3),
        "ref_steps_scale": round(0.9 + 0.25 * irreg, 3),
        "burst_force": round(0.2 + 0.4 * sync, 3),
    }
    return {
        "priors": priors,
        "fsot_lesion": lesion,
        "break_signature": {
            "isi_cv_high": True,
            "burst_clustering": True,
            "rate_drop": True,
        },
        "wire_around": {
            "strategy": "desync_and_regularize",
            "actions": [
                "inject_phase_noise",
                "clamp_isi_cv",
                "consensus_sparse_gate",
                "consensus_quarantine_failed",
                "raise_fire_thr",
            ],
        },
    }


def gather_eeg_context(fetch_live: bool = True) -> Dict[str, Any]:
    """Full EEG/PD context bundle for failure probe + reports."""
    local = discover_local_eeg()
    index = load_openneuro_index()
    live = fetch_openneuro_pd_metadata() if fetch_live else {"ok": False, "skipped": True}

    # Prefer staged real-signal bundle (Allen NWB + PD priors)
    derived = None
    real_bundle = None
    try:
        from .eeg_loader import build_real_signal_bundle

        real_bundle = build_real_signal_bundle()
        if real_bundle.get("ok") and real_bundle.get("derived_priors"):
            derived = dict(real_bundle["derived_priors"])
    except Exception as e:
        real_bundle = {"ok": False, "error": str(e)}

    if derived is None:
        for f in local[:15]:
            if f["suffix"] == ".csv" and f["relevance_score"] > 0:
                st = estimate_signal_stats_from_csv(Path(f["path"]))
                if st:
                    derived = {
                        "isi_cv_elevation": min(2.5, 1.2 + float(st.get("cv") or 0.3)),
                        "rate_irregularity": min(0.8, 0.3 + float(st.get("zero_cross_rate") or 0.2)),
                        "beta_power_elevation": 1.4,
                        "sync_pressure": 0.5,
                        "from_file": f["path"],
                    }
                    break

    pd_lesion = derive_pd_lesion_scales({"derived_priors": derived} if derived else None)
    bundle = {
        "local_eeg_files": local[:20],
        "n_local_eeg": len(local),
        "openneuro_index": index,
        "openneuro_pd": live,
        "real_signal_bundle": {
            "ok": (real_bundle or {}).get("ok"),
            "nwb_ok": (real_bundle or {}).get("allen_nwb", {}).get("ok"),
            "aggregate": (real_bundle or {}).get("allen_nwb", {}).get("aggregate"),
            "paths": (real_bundle or {}).get("paths"),
        },
        "pd_lesion_derived": pd_lesion,
        "note": (
            "Staged under data/eeg/: Allen NWB ephys + OpenNeuro PD priors. "
            "Drop raw .edf for further override. ds002778 is the PD target dataset."
        ),
    }
    (EEG_CACHE / "eeg_context.json").write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    return bundle
