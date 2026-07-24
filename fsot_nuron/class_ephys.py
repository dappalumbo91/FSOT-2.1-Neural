"""
Cell-class ephys targets from Allen wet-lab metadata (Cre lines + features).

Public wet-lab authority: Allen Cell Types cells.json + ephys_features.csv.
Maps Pvalb/Sst/Vip/excitatory Cre lines → FSOT Pyr/PV/SST/VIP targets.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .allen_data import AllenCellRow, load_ephys_csv
from .paths import DATA, ROOT

CELLS_JSON = DATA / "eeg" / "allen_ephys" / "cells.json"
EPHYS_CSV = DATA / "eeg" / "allen_ephys" / "ephys_features.csv"

# Wet-lab Cre / line → FSOT class
LINE_TO_CLASS = {
    "Pvalb-IRES-Cre": "PV",
    "Sst-IRES-Cre": "SST",
    "Vip-IRES-Cre": "VIP",
    # common excitatory / pyramidal-associated lines
    "Rorb-IRES2-Cre": "Pyr",
    "Scnn1a-Tg3-Cre": "Pyr",
    "Scnn1a-Tg2-Cre": "Pyr",
    "Cux2-CreERT2": "Pyr",
    "Rbp4-Cre_KL100": "Pyr",
    "Nr5a1-Cre": "Pyr",
    "Tlx3-Cre_PL56": "Pyr",
    "Ntsr1-Cre_GN220": "Pyr",
    "Ctgf-T2A-dgCre": "Pyr",
}


@dataclass
class ClassEphysTarget:
    cell_type: str
    n_cells: int
    mean_isi_ms: float
    mean_adapt: float
    mean_rate_Hz: float
    mean_vrest_mV: float
    mean_tau_ms: float
    mean_rin_mohm: float
    source: str = "Allen Cell Types (public wet-lab)"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe(x: Any, default: float = float("nan")) -> float:
    try:
        if x is None or x == "":
            return default
        v = float(x)
        if v != v:
            return default
        return v
    except (TypeError, ValueError):
        return default


def _mean(xs: List[float]) -> float:
    good = [x for x in xs if x == x]
    return sum(good) / len(good) if good else float("nan")


def load_allen_cells_meta(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = path or CELLS_JSON
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def classify_line(line_name: str) -> Optional[str]:
    if not line_name:
        return None
    if line_name in LINE_TO_CLASS:
        return LINE_TO_CLASS[line_name]
    # substring fallbacks
    ln = line_name.lower()
    if "pvalb" in ln or "pv-" in ln:
        return "PV"
    if ln.startswith("sst") or "sst-" in ln:
        return "SST"
    if "vip" in ln:
        return "VIP"
    return None


def build_class_targets(
    min_cells: int = 15,
    mouse_only: bool = True,
) -> Dict[str, ClassEphysTarget]:
    """
    Aggregate wet-lab ephys by Cre class from cells.json.

    Uses ef__* fields embedded in cells.json (same Allen release as CSV).
    """
    cells = load_allen_cells_meta()
    buckets: Dict[str, Dict[str, List[float]]] = defaultdict(
        lambda: {
            "isi": [],
            "adapt": [],
            "rate": [],
            "vrest": [],
            "tau": [],
            "rin": [],
        }
    )

    for c in cells:
        if mouse_only and c.get("donor__species") != "Mus musculus":
            continue
        cls = classify_line(c.get("line_name") or "")
        if cls is None:
            # dendrite heuristic for unlabeled: spiny ~ Pyr, aspiny skip without line
            continue
        isi = _safe(c.get("ef__avg_isi"))
        rate = _safe(c.get("ef__avg_firing_rate"))
        if rate != rate and isi == isi and isi > 1:
            rate = 1000.0 / isi
        buckets[cls]["isi"].append(isi)
        buckets[cls]["adapt"].append(_safe(c.get("ef__adaptation")))
        buckets[cls]["rate"].append(rate)
        buckets[cls]["vrest"].append(_safe(c.get("ef__vrest")))
        buckets[cls]["tau"].append(_safe(c.get("ef__tau")))
        buckets[cls]["rin"].append(_safe(c.get("ef__ri")))

    out: Dict[str, ClassEphysTarget] = {}
    for cls, b in buckets.items():
        n = len([x for x in b["isi"] if x == x])
        if n < min_cells:
            continue
        out[cls] = ClassEphysTarget(
            cell_type=cls,
            n_cells=n,
            mean_isi_ms=_mean(b["isi"]),
            mean_adapt=_mean(b["adapt"]),
            mean_rate_Hz=_mean(b["rate"]),
            mean_vrest_mV=_mean(b["vrest"]),
            mean_tau_ms=_mean(b["tau"]),
            mean_rin_mohm=_mean(b["rin"]),
        )
    return out


def class_order_gates(targets: Dict[str, ClassEphysTarget]) -> Dict[str, Any]:
    """Biological order: PV faster (higher rate / shorter ISI) than Pyr."""
    gates = {}
    if "PV" in targets and "Pyr" in targets:
        gates["pv_rate_gt_pyr"] = targets["PV"].mean_rate_Hz > targets["Pyr"].mean_rate_Hz
        gates["pv_isi_lt_pyr"] = targets["PV"].mean_isi_ms < targets["Pyr"].mean_isi_ms
        gates["pv_n"] = targets["PV"].n_cells
        gates["pyr_n"] = targets["Pyr"].n_cells
    if "SST" in targets and "Pyr" in targets:
        gates["sst_adapt_ge_pyr"] = (
            targets["SST"].mean_adapt >= targets["Pyr"].mean_adapt - 0.02
        )
    return gates


def apply_class_targets_to_genotype_phenotype(
    cell_type: str,
    phenotype: Dict[str, float],
    targets: Dict[str, ClassEphysTarget],
    mode: str = "bio_match",
) -> Dict[str, float]:
    """
    Snap refractory / adapt_step / fi toward wet-lab class means.

    Primary lock for FI rate match uses Allen mean_rate_Hz → ISI_eff = 1000/rate
    (Allen avg_isi and avg_firing_rate can disagree across protocols; rate is
    the operational FI target). Scalar law unchanged.
    """
    ph = dict(phenotype)
    t = targets.get(cell_type)
    if t is None:
        return ph
    rate = t.mean_rate_Hz if t.mean_rate_Hz == t.mean_rate_Hz and t.mean_rate_Hz > 1 else 15.0
    # Primary: rate → ISI (FI sustained-drive operational definition)
    isi_from_rate = 1000.0 / rate
    isi_table = t.mean_isi_ms if t.mean_isi_ms == t.mean_isi_ms and t.mean_isi_ms > 5 else isi_from_rate
    # Fast-spiking: almost pure rate lock; regular-spiking: blend with table ISI
    if rate >= 40.0:
        isi = isi_from_rate
    else:
        isi = 0.65 * isi_from_rate + 0.35 * isi_table
    isi = max(5.0, min(200.0, isi))

    ad = max(0.0, min(0.55, t.mean_adapt if t.mean_adapt == t.mean_adapt else 0.05))
    scale = 1.0 if mode == "bio_match" else 1.0 / 3.0
    # Refractory floor = operational ISI (train adapt separate)
    R = isi * scale
    # PV: prevent train_count*adapt_step from killing high rate
    if cell_type == "PV" or rate >= 40.0:
        R = max(4.0, min(40.0, isi_from_rate * 0.92 * scale))
        d = 0.0
        ph["adapt_gain"] = 0.01
        ph["adapt_decay"] = 0.995
        ph["fire_threshold"] = float(max(0.84, ph.get("fire_threshold", 1.05) - 0.10))
        ph["fi_stim"] = float(min(1.4, 0.55 + 0.012 * rate))
    else:
        R = max(5.0, min(180.0, isi * (1.0 - 0.35 * ad)))
        n1 = 9.0
        d = 0.0 if ad < 1e-6 else (2.0 * ad * R) / (n1 * (1.0 - ad) + 1e-9) * 1.12
        ph["adapt_gain"] = float(max(0.01, min(0.09, 0.02 + 0.5 * ad)))
        ph["fi_stim"] = float(max(0.35, min(1.1, 0.32 + 0.012 * rate)))
    ph["refractory_steps"] = float(int(round(R)))
    ph["adapt_step"] = float(max(0.0, min(10.0, d)))
    if t.mean_vrest_mV == t.mean_vrest_mV:
        ph["vrest_mV"] = float(t.mean_vrest_mV)
    ph["avg_isi_ms_target"] = float((1000.0 / rate) * scale)
    ph["adaptation_target"] = float(ad)
    ph["class_rate_target_Hz"] = float(rate)
    return ph
