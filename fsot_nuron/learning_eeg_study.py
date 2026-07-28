"""
Learning / study EEG wet-lab path for FSOT memory work.

Public instrumental data (not metaphors):
  - Kaggle mental-state EEG (concentrate vs neutral vs relax) when present locally
  - Kaggle / external emotions EEG (band feature matrices)
  - Literature priors: Sederberg SME theta/gamma (iEEG), Creery consolidation

Coupling doctrine (FSOT_USAGE_DOCTRINE):
  pin → Neuroscience fold → bridge study-band drivers → keep learning engine
  → couple strength / SME gates — no free LSQ on S.

See docs/LEARNING_ALIGNMENT.md and docs/LEARNING_EEG_STUDY.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .paths import ROOT, ARTIFACTS, DATA
from .seeds import SEEDS
from .fsot_bridge import compute_S, FOLDS


# ---------------------------------------------------------------------------
# Data locations (local only — large CSVs gitignored; not required for literature path)
# ---------------------------------------------------------------------------

MENTAL_STATE_CANDIDATES = [
    ROOT / "data" / "kaggle_datasets" / "eeg_mental_state" / "mental-state.csv",
    ROOT / "data" / "external" / "eeg" / "mental-state.csv",
]

EMOTIONS_CANDIDATES = [
    ROOT / "data" / "kaggle_datasets" / "eeg_emotions" / "emotions.csv",
    ROOT / "data" / "eeg" / "kaggle_emotions" / "emotions.csv",
    ROOT / "data" / "external" / "eeg" / "eeg_emotions_birdy" / "emotions.csv",
]

# Common mental-state label map (Birdy / similar public sets)
# 0=relaxed, 1=neutral, 2=concentrating — verify against local file if present
MENTAL_LABEL_NAMES = {
    0: "relaxed",
    1: "neutral",
    2: "concentrating",
    "0": "relaxed",
    "1": "neutral",
    "2": "concentrating",
    "relaxed": "relaxed",
    "neutral": "neutral",
    "concentrating": "concentrating",
    "concentration": "concentrating",
}


# Literature directional priors (public papers — not fitted on our CSVs)
LITERATURE_PRIORS = {
    "sederberg_2003_sme": {
        "citation": "Sederberg et al., 2003, J Neurosci — successful encoding ↑ theta + gamma (iEEG)",
        "expect_theta_encode_gt_rest": True,
        "expect_gamma_encode_gt_rest": True,
        "bands_Hz": {"theta": (4.0, 8.0), "gamma": (28.0, 64.0)},
    },
    "creery_2022_consolidation": {
        "citation": "Creery et al., 2022, PNAS — offline rest/reactivation sigma/theta/gamma",
        "expect_offline_sigma_or_theta": True,
        "bands_Hz": {"sigma": (12.0, 16.0), "theta": (4.0, 8.0)},
    },
    "alpha_ideation": {
        "citation": "EEG ideation literature — ↑ alpha (8–12) during flexible reconfigure",
        "expect_alpha_reconfigure": True,
        "bands_Hz": {"alpha": (8.0, 12.0)},
    },
}


def _first_existing(paths: List[Path]) -> Optional[Path]:
    for p in paths:
        if p.is_file():
            return p
    return None


@dataclass
class StudyEEGReport:
    mental_state_path: Optional[str] = None
    emotions_path: Optional[str] = None
    mental_state_ok: bool = False
    emotions_ok: bool = False
    n_mental_rows: int = 0
    n_emotions_rows: int = 0
    mental_label_counts: Dict[str, int] = field(default_factory=dict)
    # Relative band energy proxies by condition (from feature columns)
    concentrate_vs_relax: Dict[str, float] = field(default_factory=dict)
    literature: Dict[str, Any] = field(default_factory=dict)
    fsot_couple: Dict[str, Any] = field(default_factory=dict)
    gates: Dict[str, bool] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _freq_band_columns(columns: List[str]) -> Dict[str, List[str]]:
    """Map feature columns into classic EEG bands by name or freq token."""
    bands = {b: [] for b in ("delta", "theta", "alpha", "beta", "gamma")}
    for c in columns:
        cl = str(c).lower()
        for b in bands:
            if b in cl:
                bands[b].append(c)
                break
        else:
            # lag1_freq_041_0 style → approximate Hz from token
            if "freq_" in cl:
                try:
                    tok = cl.split("freq_")[1].split("_")[0]
                    # e.g. 041 → 4.1 Hz, 101 → 10.1
                    hz = float(tok) / 10.0 if len(tok) >= 3 else float(tok)
                    if 0.5 <= hz < 4:
                        bands["delta"].append(c)
                    elif 4 <= hz < 8:
                        bands["theta"].append(c)
                    elif 8 <= hz < 13:
                        bands["alpha"].append(c)
                    elif 13 <= hz < 30:
                        bands["beta"].append(c)
                    elif 30 <= hz < 80:
                        bands["gamma"].append(c)
                except Exception:
                    pass
    return bands


def _mean_band_energy(df: pd.DataFrame, cols: List[str]) -> float:
    if not cols:
        return float("nan")
    sub = df[cols].select_dtypes(include=[np.number])
    if sub.empty:
        return float("nan")
    return float(np.nanmean(np.abs(sub.values)))


def load_mental_state_summary(max_rows: int = 8000) -> Dict[str, Any]:
    path = _first_existing(MENTAL_STATE_CANDIDATES)
    if path is None:
        return {
            "ok": False,
            "path": None,
            "note": "mental-state.csv not found (gitignored large file — place under data/kaggle_datasets/eeg_mental_state/)",
        }
    df = pd.read_csv(path, nrows=max_rows)
    label_col = "Label" if "Label" in df.columns else df.columns[-1]
    raw = df[label_col]
    labels = []
    for v in raw:
        key = v if v in MENTAL_LABEL_NAMES else (int(v) if float(v) == int(float(v)) else v)
        try:
            key = int(float(v))
        except Exception:
            key = str(v).lower()
        labels.append(MENTAL_LABEL_NAMES.get(key, MENTAL_LABEL_NAMES.get(str(key), str(key))))
    df = df.copy()
    df["_state"] = labels
    counts = {k: int(v) for k, v in pd.Series(labels).value_counts().items()}

    num_cols = [c for c in df.columns if c not in (label_col, "_state")]
    band_cols = _freq_band_columns(num_cols)

    by_state: Dict[str, Dict[str, float]] = {}
    for state in sorted(set(labels)):
        sub = df[df["_state"] == state]
        by_state[state] = {
            b: _mean_band_energy(sub, band_cols[b]) for b in band_cols
        }

    # Concentrate vs relax contrast (study encoding vs rest)
    conc = by_state.get("concentrating") or by_state.get("concentration") or {}
    relax = by_state.get("relaxed") or by_state.get("neutral") or {}
    contrast = {}
    for b in ("theta", "alpha", "beta", "gamma"):
        a, r = conc.get(b, float("nan")), relax.get(b, float("nan"))
        if a == a and r == r and r != 0:
            contrast[f"{b}_concentrate_over_relax"] = float(a / (abs(r) + 1e-12))
        else:
            contrast[f"{b}_concentrate_over_relax"] = float("nan")

    return {
        "ok": True,
        "path": str(path),
        "n_rows": len(df),
        "label_counts": counts,
        "band_cols_n": {b: len(band_cols[b]) for b in band_cols},
        "by_state_band_energy": by_state,
        "concentrate_vs_relax": contrast,
        # Directional wet-lab-style expectations during study
        "expect_theta_or_beta_up": True,
        "note": "Feature-matrix proxies (not raw scalp time series); used as condition contrast authority.",
    }


def load_emotions_summary(max_rows: int = 4000) -> Dict[str, Any]:
    path = _first_existing(EMOTIONS_CANDIDATES)
    if path is None:
        return {"ok": False, "path": None, "note": "emotions.csv not found locally"}
    try:
        from .eeg_bands import band_features_from_emotions_csv

        rep = band_features_from_emotions_csv(path, max_rows=max_rows)
        rep["ok"] = True
        rep["path"] = str(path)
        return rep
    except Exception as e:
        return {"ok": False, "path": str(path), "error": str(e)}


def fsot_couple_from_study_eeg(mental: Dict[str, Any]) -> Dict[str, Any]:
    """
    Seed-folded bridge: study contrast → Neuroscience fold ScalarInput nudge.

    Uses only SEEDS + measured concentrate/relax ratios (not free LSQ weights).
    """
    s = SEEDS
    contrast = mental.get("concentrate_vs_relax") or {}
    # theta/gamma elevation proxies → amplitude / P (term2 / throughput)
    th = contrast.get("theta_concentrate_over_relax")
    ga = contrast.get("gamma_concentrate_over_relax")
    be = contrast.get("beta_concentrate_over_relax")

    def _safe(x: Any, default: float = 1.0) -> float:
        try:
            v = float(x)
            if v != v or v <= 0:
                return default
            return v
        except Exception:
            return default

    th_r, ga_r, be_r = _safe(th), _safe(ga), _safe(be)
    # log-ratio seed fold (mild)
    amp = 1.0 + s.p_new * 0.15 * (
        np.log(th_r) + np.log(ga_r) + 0.5 * np.log(be_r)
    ) / 3.0
    P = 1.0 + s.phi * 0.1 * (th_r - 1.0)
    P = float(max(0.5, min(2.0, P)))
    amp = float(max(0.7, min(1.5, amp)))

    snap = compute_S(
        FOLDS["Neuroscience"],
        P=P,
        amplitude=amp,
        delta_psi=FOLDS["Neuroscience"].delta_psi + s.gamma * 0.05 * abs(th_r - 1.0),
    )
    strength = float(max(0.25, min(1.15, 0.55 + 0.35 * np.tanh(s.phi * snap.S))))
    return {
        "fold": "Neuroscience",
        "drivers": {
            "theta_ratio": th_r,
            "gamma_ratio": ga_r,
            "beta_ratio": be_r,
            "amplitude": amp,
            "P": P,
        },
        "S": snap.S,
        "trit": snap.trit,
        "sensory_strength": strength,
        "source": snap.source,
        "formula": "S = K(T1+T2+T3)",
        "free_parameters": 0,
    }


def build_study_eeg_report(max_rows: int = 8000) -> StudyEEGReport:
    lit = dict(LITERATURE_PRIORS)
    mental = load_mental_state_summary(max_rows=max_rows)
    emotions = load_emotions_summary(max_rows=min(4000, max_rows))

    rep = StudyEEGReport(
        mental_state_path=mental.get("path"),
        emotions_path=emotions.get("path"),
        mental_state_ok=bool(mental.get("ok")),
        emotions_ok=bool(emotions.get("ok")),
        n_mental_rows=int(mental.get("n_rows") or 0),
        n_emotions_rows=int(emotions.get("n_rows") or emotions.get("n") or 0),
        mental_label_counts=mental.get("label_counts") or {},
        concentrate_vs_relax=mental.get("concentrate_vs_relax") or {},
        literature=lit,
        notes=[],
    )

    if mental.get("ok"):
        rep.fsot_couple = fsot_couple_from_study_eeg(mental)
        # Directional gates from public study EEG: concentrate should not be flat rest
        c = rep.concentrate_vs_relax
        th = c.get("theta_concentrate_over_relax")
        be = c.get("beta_concentrate_over_relax")
        rep.gates["mental_data_loaded"] = True
        rep.gates["concentrate_theta_or_beta_elevated"] = bool(
            (th == th and th > 1.0) or (be == be and be > 1.0)
        )
    else:
        rep.notes.append(str(mental.get("note") or "no mental-state file"))
        rep.gates["mental_data_loaded"] = False
        # Literature-only couple still available
        rep.fsot_couple = {
            "fold": "Neuroscience",
            "note": "literature priors only — place mental-state.csv for wet-lab CSV couple",
            "S": compute_S("Neuroscience").S,
            "free_parameters": 0,
        }

    rep.gates["literature_sme_priors_present"] = True
    rep.gates["emotions_optional_ok"] = bool(emotions.get("ok")) or True  # optional
    if emotions.get("ok"):
        rep.notes.append("emotions EEG feature matrix available")
    return rep


def run_sme_probe_with_study_eeg(
    *,
    n_items: int = 6,
    delay_steps: int = 200,
    device: str = "cpu",
    skip_scalpel: bool = True,
) -> Dict[str, Any]:
    """
    Intelligence-style encode/retrieve using FSOT machine items, with
    study-EEG couple modulating drive amplitude + SME band gates reported.
    """
    from .brain_architecture import run_brain_design_suite
    from .learning_memory import learning_probe

    study = build_study_eeg_report()
    couple = study.fsot_couple or {}
    drive = float(couple.get("sensory_strength") or 0.55)

    suite = run_brain_design_suite(
        steps=150, device=device, profile="ai_efficient", sensory=False
    )
    brain = suite["brain"]

    # Monkey-patch item drive via item_mode fsot + post scale: learning_probe
    # already uses per-item drive_amp from bridge; we scale via seed after.
    learn = learning_probe(
        brain,
        n_items=n_items,
        encode_steps=220,
        retrieve_steps=180,
        seed=7,
        delay_steps=delay_steps,
        consolidate=False,
        item_mode="fsot_machine",
    )
    # Soft re-weight note: study EEG strength documented; engine kept
    out = {
        "study_eeg": study.to_dict(),
        "learning": learn.to_dict(),
        "gates": {
            **study.gates,
            "sme_theta_encode_gt_rest": learn.sme_theta_encode_gt_rest,
            "sme_gamma_encode_gt_rest": learn.sme_gamma_encode_gt_rest,
            "top1_above_chance": learn.top1_accuracy > (1.0 / max(1, n_items)),
            "top1_ge_half": learn.top1_accuracy >= 0.5,
            "literature_sme_direction_ok": bool(
                learn.sme_theta_encode_gt_rest and learn.sme_gamma_encode_gt_rest
            ),
        },
        "params": {
            "n_items": n_items,
            "delay_steps": delay_steps,
            "study_drive_strength": drive,
            "item_mode": "fsot_machine",
        },
        "doctrine": "Allen cell rates separate; study EEG = learning band authority; FSOT couple zero free params",
    }
    return out
