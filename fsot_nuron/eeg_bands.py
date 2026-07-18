"""
EEG band models from CSV feature matrices and optional EDF (if available).

Does not require clinical tooling for the CSV path (Kaggle emotions / mental state).
EDF path uses pure-Python / numpy if mne is absent; skips gracefully.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .paths import ARTIFACTS, ROOT

RESULTS_DIR = ROOT / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
EXTERNAL_EEG = ROOT / "data" / "external" / "eeg"

BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 45.0),
}


def _bandpower_welch(x: np.ndarray, fs: float, fmin: float, fmax: float) -> float:
    """Simple periodogram band power (no scipy required)."""
    x = np.asarray(x, dtype=np.float64)
    x = x - np.mean(x)
    n = len(x)
    if n < 16 or fs <= 0:
        return 0.0
    # Hann window
    w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / max(n - 1, 1))
    xw = x * w
    spec = np.fft.rfft(xw)
    psd = (np.abs(spec) ** 2) / (np.sum(w**2) * fs + 1e-12)
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    mask = (freqs >= fmin) & (freqs < fmax)
    if not np.any(mask):
        return 0.0
    # integrate
    try:
        return float(np.trapezoid(psd[mask], freqs[mask]))
    except AttributeError:
        return float(np.trapz(psd[mask], freqs[mask]))


def extract_bands_from_1d(x: np.ndarray, fs: float = 128.0) -> Dict[str, float]:
    out = {}
    total = 0.0
    for name, (lo, hi) in BANDS.items():
        p = _bandpower_welch(x, fs, lo, hi)
        out[f"bp_{name}"] = p
        total += p
    for name in BANDS:
        out[f"rel_{name}"] = out[f"bp_{name}"] / (total + 1e-12)
    out["bp_total"] = total
    out["fs"] = fs
    return out


def try_read_edf_basic(path: Path, max_seconds: float = 30.0) -> Optional[Dict[str, Any]]:
    """
    Minimal EDF reader (16-bit digital). Returns channel means of band powers.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if len(raw) < 256 or raw[1:4] != b"DF ":
        # some files start with '0       ' header
        if not raw.startswith(b"0") and b"EDF" not in raw[:256]:
            return None
    try:
        header = raw[:256].decode("ascii", errors="replace")
        n_bytes_header = int(header[184:192].strip() or "0")
        n_records = int(header[236:244].strip() or "0")
        rec_dur = float(header[244:252].strip() or "1")
        n_signals = int(header[252:256].strip() or "0")
        if n_signals <= 0 or n_records <= 0:
            return None
        # label section
        h2 = raw[256:n_bytes_header]
        # n_samples per record per signal at offset 216*n after labels etc. — simplified parse
        # EDF layout: each field is n_signals * fixed width
        def field(start_chars: int, width: int) -> List[str]:
            # start_chars is cumulative from after main header in chars
            chunk = h2[start_chars : start_chars + width * n_signals]
            return [
                chunk[i * width : (i + 1) * width].decode("ascii", errors="replace").strip()
                for i in range(n_signals)
            ]

        # After 256-byte header: labels 16*ns, transducer 80*ns, dim 8*ns, physmin 8*ns, physmax 8*ns,
        # digmin 8*ns, digmax 8*ns, prefilt 80*ns, n_samples 8*ns
        off = 0
        labels = field(off, 16)
        off += 16 * n_signals
        off += 80 * n_signals  # transducer
        off += 8 * n_signals  # dim
        phys_min = field(off, 8)
        off += 8 * n_signals
        phys_max = field(off, 8)
        off += 8 * n_signals
        dig_min = field(off, 8)
        off += 8 * n_signals
        dig_max = field(off, 8)
        off += 8 * n_signals
        off += 80 * n_signals  # prefilter
        n_samp = field(off, 8)
        ns = [max(1, int(float(x))) for x in n_samp]
        samples_per_record = sum(ns)
        # data
        data_start = n_bytes_header
        max_recs = min(n_records, int(max_seconds / max(rec_dur, 1e-6)))
        ch_bands: List[Dict[str, float]] = []
        # reconstruct first few channels fully
        for ci in range(min(n_signals, 8)):
            # gather samples for channel ci across records
            buf = []
            ptr = data_start
            for rec in range(max_recs):
                # skip earlier channels in record
                skip = sum(ns[:ci]) * 2
                take = ns[ci] * 2
                base = ptr + skip
                chunk = raw[base : base + take]
                if len(chunk) < take:
                    break
                vals = np.frombuffer(chunk, dtype="<i2").astype(np.float64)
                # scale
                try:
                    d0, d1 = float(dig_min[ci]), float(dig_max[ci])
                    p0, p1 = float(phys_min[ci]), float(phys_max[ci])
                    if d1 != d0:
                        vals = (vals - d0) / (d1 - d0) * (p1 - p0) + p0
                except Exception:
                    pass
                buf.append(vals)
                ptr += samples_per_record * 2
            if not buf:
                continue
            sig = np.concatenate(buf)
            fs = ns[ci] / max(rec_dur, 1e-6)
            bands = extract_bands_from_1d(sig[: int(fs * max_seconds)], fs=fs)
            bands["label"] = labels[ci] if ci < len(labels) else f"ch{ci}"
            ch_bands.append(bands)
        if not ch_bands:
            return None
        # mean relative beta etc.
        rel_beta = float(np.mean([c["rel_beta"] for c in ch_bands]))
        rel_alpha = float(np.mean([c["rel_alpha"] for c in ch_bands]))
        return {
            "path": str(path),
            "n_channels_scored": len(ch_bands),
            "mean_rel_beta": rel_beta,
            "mean_rel_alpha": rel_alpha,
            "beta_alpha_ratio": rel_beta / (rel_alpha + 1e-9),
            "channels_head": ch_bands[:3],
            "format": "edf_basic",
        }
    except Exception as e:
        return {"path": str(path), "error": str(e)}


def band_features_from_emotions_csv(path: Path, max_rows: int = 4000) -> Dict[str, Any]:
    """
    Kaggle emotions CSV already has fft_* style features — group into band proxies.
    """
    df = pd.read_csv(path, nrows=max_rows)
    label_col = None
    for c in df.columns:
        if str(c).lower() in ("label", "emotion", "class", "sentiment"):
            label_col = c
            break
    if label_col is None:
        label_col = df.columns[-1]
    y = df[label_col].astype(str)
    num = df.select_dtypes(include=[np.number])
    # map columns containing band-ish tokens
    band_cols = {b: [] for b in BANDS}
    for c in num.columns:
        cl = str(c).lower()
        for b in BANDS:
            if b in cl or f"fft_{b}" in cl:
                band_cols[b].append(c)
        # birdy dataset uses mean_* and fft_* without names — use spectral thirds
    feats = {}
    if any(band_cols.values()):
        for b, cols in band_cols.items():
            if cols:
                feats[f"mean_{b}"] = float(num[cols].mean().mean())
    else:
        # frequency-ordered columns: split into 5 bands by column index
        cols = list(num.columns)
        n = len(cols)
        if n >= 10:
            edges = np.linspace(0, n, 6, dtype=int)
            for i, b in enumerate(BANDS):
                sl = cols[edges[i] : edges[i + 1]]
                feats[f"mean_{b}"] = float(num[sl].mean().mean()) if sl else 0.0
    # class separability on beta proxy if present
    beta_col = None
    for c in num.columns:
        if "beta" in str(c).lower():
            beta_col = c
            break
    sep = 0.0
    if beta_col is not None:
        means = y.to_frame().join(num[beta_col]).groupby(label_col)[beta_col].mean()
        if len(means) >= 2:
            sep = float((means.max() - means.min()) / (means.std() + 1e-9))
    return {
        "path": str(path),
        "n_rows": int(len(df)),
        "label_col": str(label_col),
        "n_classes": int(y.nunique()),
        "band_feature_means": feats,
        "beta_class_separability": sep,
        "labels": y.value_counts().to_dict(),
    }


def run_eeg_band_suite(write: bool = True) -> Dict[str, Any]:
    reports = []
    # CSV paths
    csv_candidates = [
        ROOT / "data" / "eeg" / "kaggle_emotions" / "emotions.csv",
        ROOT / "data" / "kaggle_datasets" / "eeg_emotions" / "emotions.csv",
        ROOT / "data" / "kaggle_datasets" / "eeg_mental_state" / "mental-state.csv",
    ]
    if EXTERNAL_EEG.is_dir():
        csv_candidates.extend(EXTERNAL_EEG.rglob("*.csv"))
    seen = set()
    for p in csv_candidates:
        p = Path(p)
        if not p.is_file() or str(p) in seen:
            continue
        seen.add(str(p))
        try:
            reports.append({"kind": "csv_bands", **band_features_from_emotions_csv(p)})
            print(f"  csv bands ok {p.name}")
        except Exception as e:
            reports.append({"kind": "csv_bands", "path": str(p), "error": str(e)})

    # EDF search on external + project
    edf_roots = [
        ROOT / "data" / "eeg",
        EXTERNAL_EEG,
        Path(r"I:\FSOT-Physical-Archive\03_FSOT-PublicData"),
        Path(r"D:\training data"),
    ]
    edf_files = []
    for root in edf_roots:
        if not root.exists():
            continue
        try:
            for p in root.rglob("*"):
                if p.suffix.lower() in {".edf", ".bdf"} and p.is_file():
                    edf_files.append(p)
                    if len(edf_files) >= 15:
                        break
        except OSError:
            continue
        if len(edf_files) >= 15:
            break

    for p in edf_files[:10]:
        r = try_read_edf_basic(p)
        if r:
            reports.append({"kind": "edf_bands", **r})
            print(f"  edf bands {p.name}: beta/alpha={r.get('beta_alpha_ratio')}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_reports": len(reports),
        "n_edf_found": len(edf_files),
        "reports": reports,
        "honesty": (
            "CSV band proxies from feature matrices; EDF uses lightweight pure-Python reader. "
            "Not a clinical EEG report."
        ),
    }
    if write:
        path = RESULTS_DIR / "eeg_bands_suite.json"
        path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "eeg_bands_suite.json").write_text(
            json.dumps(out, indent=2, default=str), encoding="utf-8"
        )
        out["path"] = str(path)
    return out
