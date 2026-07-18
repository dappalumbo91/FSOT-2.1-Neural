"""
Load real neural signals staged under data/eeg/

Primary: Allen NWB voltage sweeps (h5py)
Secondary: OpenNeuro PD feature priors JSON
Optional: raw .edf if user stages them
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .paths import ROOT, ARTIFACTS

EEG_ROOT = ROOT / "data" / "eeg"
ALLEN_DIR = EEG_ROOT / "allen_ephys"
PD_DIR = EEG_ROOT / "openneuro_pd"
STATS_PATH = ARTIFACTS / "eeg_cache" / "real_signal_stats.json"


def _stats_1d(x: List[float]) -> Dict[str, float]:
    n = len(x)
    if n < 10:
        return {"n": float(n)}
    mean = sum(x) / n
    var = sum((v - mean) ** 2 for v in x) / n
    std = math.sqrt(var)
    # spike-like events: threshold crossings of mean+2std
    thr = mean + 2.0 * std
    events = [i for i, v in enumerate(x) if v > thr]
    isis = []
    for a, b in zip(events, events[1:]):
        isis.append(float(b - a))
    isi_mean = sum(isis) / len(isis) if isis else float("nan")
    isi_std = math.sqrt(sum((v - isi_mean) ** 2 for v in isis) / len(isis)) if len(isis) > 2 else float("nan")
    isi_cv = (isi_std / isi_mean) if isi_mean == isi_mean and isi_mean > 0 else float("nan")
    # zero-cross rate as irregularity
    zc = sum(1 for a, b in zip(x, x[1:]) if (a - mean) * (b - mean) < 0)
    return {
        "n": float(n),
        "mean": mean,
        "std": std,
        "cv": abs(std / mean) if abs(mean) > 1e-12 else float("nan"),
        "n_events": float(len(events)),
        "isi_samples_mean": isi_mean,
        "isi_cv": isi_cv,
        "zero_cross_rate": zc / max(n - 1, 1),
        "range": max(x) - min(x),
    }


def load_allen_nwb_stats(
    nwb_path: Optional[Path] = None,
    max_sweeps: int = 8,
    max_samples: int = 50_000,
) -> Dict[str, Any]:
    """Extract per-sweep stats from real Allen ephys NWB."""
    import h5py

    nwb_path = nwb_path or (ALLEN_DIR / "ephys.nwb")
    if not nwb_path.is_file():
        return {"ok": False, "reason": f"missing {nwb_path}"}

    sweeps = []
    with h5py.File(nwb_path, "r") as f:
        base = "acquisition/timeseries"
        if base not in f:
            return {"ok": False, "reason": "no acquisition/timeseries"}
        names = sorted([k for k in f[base].keys() if k.startswith("Sweep_")])
        for name in names[:max_sweeps]:
            ds = f[f"{base}/{name}/data"]
            n = min(int(ds.shape[0]), max_samples)
            # subsample evenly for speed
            step = max(1, n // 20000)
            raw = ds[0:n:step]
            x = [float(v) for v in raw]
            st = _stats_1d(x)
            st["sweep"] = name
            st["raw_len"] = int(ds.shape[0])
            sweeps.append(st)

    if not sweeps:
        return {"ok": False, "reason": "no sweeps"}

    def mean_key(k: str) -> float:
        vals = [s[k] for s in sweeps if s.get(k) == s.get(k)]
        return sum(vals) / len(vals) if vals else float("nan")

    return {
        "ok": True,
        "source": str(nwb_path),
        "specimen_hint": "allen_cell_types specimen NWB",
        "n_sweeps_analyzed": len(sweeps),
        "sweeps": sweeps,
        "aggregate": {
            "mean_cv": mean_key("cv"),
            "mean_isi_cv": mean_key("isi_cv"),
            "mean_zero_cross_rate": mean_key("zero_cross_rate"),
            "mean_std": mean_key("std"),
        },
    }


def load_pd_priors() -> Dict[str, Any]:
    p = PD_DIR / "pd_eeg_feature_priors.json"
    if p.is_file():
        return {"ok": True, **json.loads(p.read_text(encoding="utf-8"))}
    return {"ok": False, "reason": "no PD priors yet — run scripts/fetch_openneuro_pd_files.py"}


def load_allen_feature_envelope() -> Dict[str, Any]:
    csv_path = ALLEN_DIR / "ephys_features.csv"
    if not csv_path.is_file():
        return {"ok": False}
    import csv

    isis, ads, vrests = [], [], []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                if row.get("avg_isi"):
                    isis.append(float(row["avg_isi"]))
                if row.get("adaptation"):
                    ads.append(float(row["adaptation"]))
                if row.get("vrest"):
                    vrests.append(float(row["vrest"]))
            except ValueError:
                continue

    def mean(a: List[float]) -> float:
        return sum(a) / len(a) if a else float("nan")

    return {
        "ok": True,
        "path": str(csv_path),
        "n": len(isis),
        "mean_avg_isi_ms": mean(isis),
        "mean_adaptation": mean(ads),
        "mean_vrest": mean(vrests),
    }


def build_real_signal_bundle() -> Dict[str, Any]:
    """Combine Allen NWB + features + PD priors → lesion-usable stats."""
    nwb = load_allen_nwb_stats()
    feat = load_allen_feature_envelope()
    pd = load_pd_priors()

    # Map real signal irregularity into PD-like elevation ratios
    derived_priors = {
        "source": "allen_nwb+features+pd_priors",
        "beta_power_elevation": 1.45,
        "isi_cv_elevation": 1.55,
        "sync_pressure": 0.55,
        "rate_irregularity": 0.42,
    }
    if nwb.get("ok"):
        agg = nwb["aggregate"]
        isi_cv = agg.get("mean_isi_cv") or 0.3
        zc = agg.get("mean_zero_cross_rate") or 0.2
        # normalize roughly into elevation factors
        derived_priors["isi_cv_elevation"] = float(min(2.5, max(1.1, 1.0 + isi_cv)))
        derived_priors["rate_irregularity"] = float(min(0.85, max(0.2, zc * 1.2)))
        derived_priors["beta_power_elevation"] = float(min(2.0, 1.2 + abs(agg.get("mean_cv") or 0.3)))
        derived_priors["sync_pressure"] = float(min(0.9, 0.35 + zc))
        derived_priors["from_nwb"] = True

    if pd.get("ok") and "pd_vs_control" in pd:
        pvc = pd["pd_vs_control"]
        derived_priors["beta_power_elevation"] = float(pvc.get("beta_power_ratio", 1.45))
        derived_priors["isi_cv_elevation"] = float(pvc.get("signal_cv_ratio", 1.55))
        derived_priors["from_pd_priors"] = True

    bundle = {
        "ok": bool(nwb.get("ok") or feat.get("ok")),
        "allen_nwb": nwb,
        "allen_features": feat,
        "pd_openneuro": pd,
        "derived_priors": derived_priors,
        "paths": {
            "eeg_root": str(EEG_ROOT),
            "allen_dir": str(ALLEN_DIR),
            "pd_dir": str(PD_DIR),
        },
    }
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    return bundle
