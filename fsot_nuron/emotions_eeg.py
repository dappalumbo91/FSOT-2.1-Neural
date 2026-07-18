"""
Kaggle EEG Emotion dataset loader (emotions.csv).

Typical Kaggle pack: 2132 rows × 2548 numeric features + label
  labels: NEGATIVE | NEUTRAL | POSITIVE
  features: mean_*, fft_*, etc. (pre-engineered band/channel stats)

Used to:
  - derive emotion-conditioned irregularity / drive priors
  - modulate FSOT lesion / stim scales (research substrate, not clinical)
  - provide real multi-class EEG feature stats alongside Allen NWB
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .paths import ROOT, ARTIFACTS

CANDIDATES = [
    ROOT / "data" / "eeg" / "kaggle_emotions" / "emotions.csv",
    Path(r"D:\training data\archive\emotions.csv"),
]

STATS_OUT = ARTIFACTS / "eeg_cache" / "kaggle_emotions_stats.json"


def find_emotions_csv() -> Optional[Path]:
    for p in CANDIDATES:
        if p.is_file():
            return p
    return None


def load_emotions_frame(path: Optional[Path] = None, max_rows: Optional[int] = None):
    import pandas as pd

    path = path or find_emotions_csv()
    if path is None:
        raise FileNotFoundError("emotions.csv not found under data/eeg/kaggle_emotions or D:\\training data\\archive")
    df = pd.read_csv(path, nrows=max_rows)
    # normalize column names
    cols = list(df.columns)
    if cols[0].startswith("#"):
        cols[0] = cols[0].lstrip("#").strip()
        df.columns = cols
    label_col = "label" if "label" in df.columns else df.columns[-1]
    return df, label_col, path


def compute_emotions_stats(path: Optional[Path] = None) -> Dict[str, Any]:
    """Class-conditional means/stds and global irregularity proxies."""
    import numpy as np

    df, label_col, path = load_emotions_frame(path)
    y = df[label_col].astype(str).str.upper()
    X = df.drop(columns=[label_col]).select_dtypes(include="number")
    # drop all-nan cols
    X = X.dropna(axis=1, how="all")
    # sample subset of columns for speed if huge
    n_feat = X.shape[1]
    if n_feat > 256:
        # prefer mean_* and fft_* heads if present
        prefer = [c for c in X.columns if c.startswith("mean_") or c.startswith("fft_")]
        if len(prefer) >= 64:
            X = X[prefer[:256]]
        else:
            X = X.iloc[:, :256]

    global_std = float(X.std(axis=0, numeric_only=True).mean())
    global_mean_abs = float(X.abs().mean().mean())
    # row-wise energy CV as sample irregularity
    row_energy = X.abs().mean(axis=1)
    energy_cv = float(row_energy.std() / (row_energy.mean() + 1e-12))

    by_label: Dict[str, Any] = {}
    for lab in sorted(y.unique()):
        sub = X[y == lab]
        by_label[lab] = {
            "n": int(len(sub)),
            "mean_abs": float(sub.abs().mean().mean()),
            "std_mean": float(sub.std(axis=0).mean()),
            "energy_mean": float(sub.abs().mean(axis=1).mean()),
            "energy_std": float(sub.abs().mean(axis=1).std()),
        }

    # Emotion → FSOT drive / lesion-ish scales (research mapping)
    # POSITIVE: slightly higher drive, lower thr
    # NEGATIVE: higher irregularity / adapt, moderate thr up
    # NEUTRAL: baseline
    pos = by_label.get("POSITIVE", {})
    neg = by_label.get("NEGATIVE", {})
    neu = by_label.get("NEUTRAL", {})
    base_e = neu.get("energy_mean") or global_mean_abs or 1.0

    emotion_lesion_templates = {
        "POSITIVE": {
            "fi_stim_scale": float(min(1.4, 1.0 + 0.25 * ((pos.get("energy_mean") or base_e) / base_e - 1.0 + 0.2))),
            "fire_thr_delta": -0.06,
            "adapt_step_scale": 0.85,
            "isi_jitter": 0.15,
            "silence_fraction": 0.0,
        },
        "NEUTRAL": {
            "fi_stim_scale": 1.0,
            "fire_thr_delta": 0.0,
            "adapt_step_scale": 1.0,
            "isi_jitter": 0.10,
            "silence_fraction": 0.0,
        },
        "NEGATIVE": {
            "fi_stim_scale": float(min(1.2, 0.95 + 0.15 * ((neg.get("std_mean") or 1) / (neu.get("std_mean") or 1)))),
            "fire_thr_delta": 0.05,
            "adapt_step_scale": float(min(2.0, 1.2 + 0.5 * energy_cv)),
            "isi_jitter": float(min(0.6, 0.25 + 0.4 * energy_cv)),
            "silence_fraction": 0.05,
            "phase_lock_strength": 0.35,
        },
    }

    # Map into PD-style elevation priors for shared pipeline
    derived_priors = {
        "source": "kaggle_emotions_csv",
        "beta_power_elevation": float(min(2.0, 1.15 + energy_cv)),
        "isi_cv_elevation": float(min(2.2, 1.1 + 0.8 * energy_cv)),
        "sync_pressure": float(min(0.8, 0.3 + 0.4 * energy_cv)),
        "rate_irregularity": float(min(0.75, 0.25 + 0.5 * energy_cv)),
        "emotion_energy_cv": energy_cv,
    }

    report = {
        "ok": True,
        "path": str(path),
        "n_samples": int(df.shape[0]),
        "n_features_total": int(df.shape[1] - 1),
        "n_features_used": int(X.shape[1]),
        "labels": y.value_counts().to_dict(),
        "global": {
            "feature_std_mean": global_std,
            "feature_mean_abs": global_mean_abs,
            "sample_energy_cv": energy_cv,
        },
        "by_label": by_label,
        "emotion_lesion_templates": emotion_lesion_templates,
        "derived_priors": derived_priors,
        "kaggle_note": (
            "Dataset is third-party Kaggle EEG emotion features. "
            "Do not re-host the CSV without checking the original dataset license. "
            "Our loader/stats/code can be Apache-2.0."
        ),
    }
    STATS_OUT.parent.mkdir(parents=True, exist_ok=True)
    STATS_OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def emotion_conditioned_drive(
    label: str = "NEUTRAL",
    length: int = 256,
    seed: int = 0,
) -> "torch.Tensor":
    """
    Build a 1-D drive time series colored by emotion class stats
    (for reservoir / Morse hybrid experiments).
    """
    import torch
    import numpy as np

    stats = compute_emotions_stats()
    lab = label.upper()
    tmpl = stats["emotion_lesion_templates"].get(lab, stats["emotion_lesion_templates"]["NEUTRAL"])
    rng = np.random.default_rng(seed)
    # base oscillation + noise scaled by jitter / stim
    t = np.arange(length)
    jitter = float(tmpl.get("isi_jitter", 0.1))
    amp = float(tmpl.get("fi_stim_scale", 1.0))
    # 10 Hz-ish carrier + slower envelope
    sig = amp * (0.35 * np.sin(2 * np.pi * t / 25.0) + 0.2 * np.sin(2 * np.pi * t / 80.0))
    sig = sig + jitter * rng.standard_normal(length)
    thr = float(tmpl.get("fire_thr_delta", 0.0))
    # map to stim band [0.1, 1.0]
    sig = 0.45 + 0.35 * np.tanh(sig) - 0.1 * thr
    return torch.tensor(sig, dtype=torch.float32).clamp(0.05, 1.15)


def integrate_with_eeg_bundle() -> Dict[str, Any]:
    """Merge emotion EEG stats into the real_signal pipeline report."""
    from .eeg_loader import build_real_signal_bundle

    base = build_real_signal_bundle()
    try:
        emo = compute_emotions_stats()
    except Exception as e:
        emo = {"ok": False, "error": str(e)}
    base["kaggle_emotions"] = emo
    if emo.get("ok") and emo.get("derived_priors"):
        # blend priors (emotions irregularity + existing)
        d = dict(base.get("derived_priors") or {})
        e = emo["derived_priors"]
        for k in ("beta_power_elevation", "isi_cv_elevation", "sync_pressure", "rate_irregularity"):
            if k in e and k in d:
                d[k] = 0.5 * float(d[k]) + 0.5 * float(e[k])
            elif k in e:
                d[k] = float(e[k])
        d["from_kaggle_emotions"] = True
        base["derived_priors"] = d
    out = ARTIFACTS / "eeg_cache" / "real_signal_stats.json"
    out.write_text(json.dumps(base, indent=2, default=str), encoding="utf-8")
    return base
