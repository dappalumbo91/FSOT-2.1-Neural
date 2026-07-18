"""
Allen Cell Types data loader — offline CSV first, optional live API.

Local: Desktop nuron ephys_features.csv (2333 cells).
API: Allen Brain Atlas REST (no allensdk required).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .paths import ARTIFACTS, find_allen_ephys, find_allen_cells_json

# Public Allen API (Cell Types ephys features via data API)
ALLEN_API_BASE = "http://api.brain-map.org/api/v2/data"
# Cached optional download path
CACHE_DIR = ARTIFACTS / "allen_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class AllenCellRow:
    specimen_id: int
    vrest_mV: float
    tau_ms: float
    input_resistance_mohm: float
    threshold_v_mV: float
    peak_v_mV: float
    f_i_slope: float
    adaptation: float
    avg_isi_ms: float
    rheobase_i_pA: float
    upstroke_downstroke: float

    @property
    def rheobase_nA(self) -> float:
        return self.rheobase_i_pA / 1000.0


def _safe_float(x: Any, default: float = float("nan")) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def load_ephys_csv(path: Optional[Path] = None) -> List[AllenCellRow]:
    """Load Allen ephys feature table from CSV."""
    path = path or find_allen_ephys()
    if path is None:
        return []

    import csv

    rows: List[AllenCellRow] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                AllenCellRow(
                    specimen_id=int(float(r.get("specimen_id") or 0)),
                    vrest_mV=_safe_float(r.get("vrest")),
                    tau_ms=_safe_float(r.get("tau")),
                    input_resistance_mohm=_safe_float(r.get("input_resistance_mohm")),
                    threshold_v_mV=_safe_float(r.get("threshold_v_long_square")),
                    peak_v_mV=_safe_float(r.get("peak_v_long_square")),
                    f_i_slope=_safe_float(r.get("f_i_curve_slope")),
                    adaptation=_safe_float(r.get("adaptation"), 0.0),
                    avg_isi_ms=_safe_float(r.get("avg_isi")),
                    rheobase_i_pA=_safe_float(r.get("threshold_i_long_square")),
                    upstroke_downstroke=_safe_float(r.get("upstroke_downstroke_ratio_long_square")),
                )
            )
    return rows


def population_stats(rows: List[AllenCellRow]) -> Dict[str, float]:
    def mean(vals: List[float]) -> float:
        good = [v for v in vals if v == v]
        return sum(good) / len(good) if good else float("nan")

    def percentile(vals: List[float], p: float) -> float:
        good = sorted(v for v in vals if v == v)
        if not good:
            return float("nan")
        k = int(round((len(good) - 1) * p))
        return good[k]

    return {
        "n_cells": float(len(rows)),
        "mean_vrest_mV": mean([r.vrest_mV for r in rows]),
        "mean_tau_ms": mean([r.tau_ms for r in rows]),
        "mean_rin_mohm": mean([r.input_resistance_mohm for r in rows]),
        "mean_threshold_v_mV": mean([r.threshold_v_mV for r in rows]),
        "mean_adaptation": mean([r.adaptation for r in rows]),
        "mean_avg_isi_ms": mean([r.avg_isi_ms for r in rows]),
        "mean_fi_slope": mean([r.f_i_slope for r in rows]),
        "mean_rheobase_pA": mean([r.rheobase_i_pA for r in rows]),
        "p25_vrest": percentile([r.vrest_mV for r in rows], 0.25),
        "p75_vrest": percentile([r.vrest_mV for r in rows], 0.75),
        "p25_tau": percentile([r.tau_ms for r in rows], 0.25),
        "p75_tau": percentile([r.tau_ms for r in rows], 0.75),
    }


def map_allen_to_fsot_params(row: AllenCellRow, mode: str = "bio_match") -> Dict[str, float]:
    """
    Map one Allen cell → FSOT neuron knobs (scalar remains zero free params;
    these set domain priors, timing, and bio readout scale).

    mode:
      bio_match — refractory/AHP/FI sized so ISI & adaptation track Allen
      efficient — shorter refractory (faster trains) for intelligence throughput
    """
    from .modes import OperatingMode

    op = OperatingMode.parse(mode)

    tau = row.tau_ms if row.tau_ms == row.tau_ms else 20.0
    rin = row.input_resistance_mohm if row.input_resistance_mohm == row.input_resistance_mohm else 150.0
    d_eff = 12.0 + max(-2.0, min(3.0, (25.0 - tau) / 15.0)) + max(-1.0, min(1.0, (150.0 - rin) / 200.0))

    vrest = row.vrest_mV if row.vrest_mV == row.vrest_mV else -70.0
    thr_v = row.threshold_v_mV if row.threshold_v_mV == row.threshold_v_mV else -40.0
    fire_thr = 1.05 + max(-0.08, min(0.15, (-65.0 - vrest) / 80.0))
    fire_thr = max(0.95, min(1.25, fire_thr))

    rh = row.rheobase_i_pA if row.rheobase_i_pA == row.rheobase_i_pA else 200.0
    stim_gain = max(0.4, min(2.0, 200.0 / max(50.0, rh)))

    ad = row.adaptation if row.adaptation == row.adaptation else 0.05
    isi = row.avg_isi_ms if row.avg_isi_ms == row.avg_isi_ms and row.avg_isi_ms > 5.0 else 70.0
    isi = float(max(15.0, min(200.0, isi)))
    ad = float(max(-0.15, min(0.6, ad)))

    if op is OperatingMode.BIO_MATCH:
        # Primary ISI control = refractory floor near Allen avg_isi.
        # Progressive relative refractory (adapt * 55 ms) yields mild +adaptation.
        refractory_steps = int(max(12, min(150, round(isi * 0.72))))
        # Map Allen adapt index → AHP deposit (scaled so late ISI > early ISI ~5%)
        adapt_gain = max(0.015, min(0.08, 0.025 + 0.55 * max(0.0, ad)))
        adapt_decay = 0.991
        fi_stim = max(0.38, min(0.70, 0.42 * stim_gain))
        isi_scale = 1.0
    else:
        # Efficient: same shape, ~3× faster trains for intelligence throughput
        isi_scale = 1.0 / 3.0
        refractory_steps = int(max(6, min(40, round(isi * 0.72 * isi_scale))))
        adapt_gain = max(0.015, min(0.07, 0.025 + 0.40 * max(0.0, ad)))
        adapt_decay = 0.990
        fi_stim = max(0.40, min(0.75, 0.48 * stim_gain))

    return {
        "d_eff": float(d_eff),
        "fire_threshold": float(fire_thr),
        "vrest_mV": float(vrest),
        "threshold_v_mV": float(thr_v),
        "stim_gain": float(stim_gain),
        "adapt_gain": float(adapt_gain),
        "adapt_decay": float(adapt_decay),
        "refractory_steps": float(refractory_steps),
        "fi_stim": float(fi_stim),
        "isi_scale": float(isi_scale),
        "adaptation_target": float(ad),
        "avg_isi_ms_target": float(isi),
        "target_rate_Hz": float(1000.0 / isi),
        "mode": op.value,
        "specimen_id": float(row.specimen_id),
    }


def sample_cells(rows: List[AllenCellRow], n: int = 64, seed: int = 42) -> List[AllenCellRow]:
    import random

    rng = random.Random(seed)
    if len(rows) <= n:
        return list(rows)
    return rng.sample(rows, n)


# ---------------------------------------------------------------------------
# Optional live API
# ---------------------------------------------------------------------------

def api_get_json(url: str, timeout: float = 30.0) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "FSOT-Nuron/0.2"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_allen_specimen_features(specimen_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch one specimen's ephys features from Allen REST API.
    Offline-safe: returns None on network failure.
    """
    # Rma query for Cell ephys features by specimen
    criteria = urllib.parse.quote(f"[specimen_id$eq{specimen_id}]")
    url = (
        f"{ALLEN_API_BASE}/query.json?"
        f"criteria=model::EphysFeature,rma::criteria,{criteria}"
        f"&include=specimen"
        f"&num_rows=50"
    )
    cache_path = CACHE_DIR / f"specimen_{specimen_id}_features.json"
    try:
        data = api_get_json(url)
        cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        if cache_path.is_file():
            return json.loads(cache_path.read_text(encoding="utf-8"))
        return {"ok": False, "error": str(e), "specimen_id": specimen_id}


def fetch_neuroelectro_summary(timeout: float = 20.0) -> Optional[Dict[str, Any]]:
    """
    NeuroElectro neuron property summary (species-spanning).
    Best-effort; never required for offline validation.
    """
    # Public NeuroElectro API (historical); may be flaky
    url = "https://neuroelectro.org/api/1/nedm/?limit=5&format=json"
    cache_path = CACHE_DIR / "neuroelectro_sample.json"
    try:
        data = api_get_json(url, timeout=timeout)
        cache_path.write_text(json.dumps(data, indent=2)[:500_000], encoding="utf-8")
        return {"ok": True, "source": "neuroelectro", "n_keys": len(data) if isinstance(data, dict) else 0}
    except Exception as e:
        if cache_path.is_file():
            return {"ok": True, "source": "neuroelectro_cache", "error_ignored": str(e)}
        return {"ok": False, "source": "neuroelectro", "error": str(e)}


def data_status() -> Dict[str, Any]:
    ephys = find_allen_ephys()
    cells = find_allen_cells_json()
    rows = load_ephys_csv(ephys) if ephys else []
    return {
        "ephys_csv": str(ephys) if ephys else None,
        "cells_json": str(cells) if cells else None,
        "n_ephys_rows": len(rows),
        "population": population_stats(rows) if rows else {},
        "cache_dir": str(CACHE_DIR),
    }
