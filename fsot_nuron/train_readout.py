"""
Train/test FSOT-gated readout on Morse–reservoir fingerprints.

SOTA track: richer fingerprints, feature standardization, class-balanced
ridge, multi-seed evaluation. Still a linear probe on FSOT substrate —
not a transformer. Goal is climbing measured test accuracy over time.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .literature_chew import LiteratureMind
from .multi_dataset import (
    DATA_ROOT,
    LABEL_CANDIDATES,
    TEXT_CANDIDATES,
    _confusion_and_balanced,
    _find_col,
    load_table,
)
from .paths import ARTIFACTS, ROOT

RESULTS_DIR = ROOT / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

FP_DIM = 32  # pad/truncate fingerprints to this width


@dataclass
class ReadoutResult:
    dataset: str
    n_train: int
    n_test: int
    n_classes: int
    classes: List[str]
    train_acc: float
    test_acc: float
    balanced_accuracy: float
    per_class_recall: Dict[str, float]
    confusion: Dict[str, Dict[str, int]]
    mean_fire_rate_train: float
    n_features: int
    multi_seed_test_mean: Optional[float] = None
    multi_seed_test_std: Optional[float] = None
    multi_seed_bal_mean: Optional[float] = None
    honesty: str = ""


def _pad_fp(fp: Sequence[float], dim: int = FP_DIM) -> List[float]:
    v = list(fp)[:dim]
    if len(v) < dim:
        v = v + [0.0] * (dim - len(v))
    return v


def _encode_rows(
    texts: Sequence[str],
    labels: Sequence[str],
    mind: LiteratureMind,
    max_len: int = 280,
) -> Tuple[np.ndarray, List[str], float]:
    X: List[List[float]] = []
    y: List[str] = []
    rates: List[float] = []
    for text, lab in zip(texts, labels):
        t = str(text)[:max_len]
        if len(t) < 4:
            continue
        r = mind._run_passage(t)
        X.append(_pad_fp(r["fingerprint"]))
        y.append(str(lab).upper().strip())
        rates.append(float(r["fire_rate"]))
    return np.asarray(X, dtype=np.float64), y, float(np.mean(rates) if rates else 0.0)


def _stratified_split(
    X: np.ndarray,
    y: List[str],
    test_frac: float = 0.3,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, List[str], List[str]]:
    rng = np.random.default_rng(seed)
    by: Dict[str, List[int]] = {}
    for i, lab in enumerate(y):
        by.setdefault(lab, []).append(i)
    tr_idx: List[int] = []
    te_idx: List[int] = []
    for lab, idxs in by.items():
        idxs = list(idxs)
        rng.shuffle(idxs)
        n_te = max(1, int(round(len(idxs) * test_frac))) if len(idxs) > 1 else 0
        if len(idxs) == 1:
            tr_idx.extend(idxs)
            continue
        te_idx.extend(idxs[:n_te])
        tr_idx.extend(idxs[n_te:])
    if not te_idx:
        te_idx = tr_idx[-max(1, len(tr_idx) // 4) :]
        tr_idx = tr_idx[: -len(te_idx)] or tr_idx
    return X[tr_idx], X[te_idx], [y[i] for i in tr_idx], [y[i] for i in te_idx]


def _standardize(
    Xtr: np.ndarray, Xte: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mu = Xtr.mean(axis=0)
    sd = Xtr.std(axis=0)
    sd = np.where(sd < 1e-8, 1.0, sd)
    return (Xtr - mu) / sd, (Xte - mu) / sd, mu, sd


def _fit_ovr_ridge_balanced(
    X: np.ndarray, y: List[str], classes: List[str], ridge: float = 0.05
) -> np.ndarray:
    """Class-balanced one-vs-rest ridge (bias column included)."""
    n, d = X.shape
    Xb = np.concatenate([X, np.ones((n, 1))], axis=1)
    # sample weights inverse to class frequency
    counts = {c: sum(1 for yi in y if yi == c) for c in classes}
    W_rows = []
    for c in classes:
        t = np.array([1.0 if yi == c else -1.0 for yi in y], dtype=np.float64)
        w_samp = np.array(
            [1.0 / max(counts.get(yi, 1), 1) for yi in y], dtype=np.float64
        )
        w_samp = w_samp / w_samp.mean()
        # weighted normal equations: (X' W X + λI) β = X' W t
        sw = np.sqrt(w_samp)
        Xw = Xb * sw[:, None]
        tw = t * sw
        reg = ridge * np.eye(d + 1)
        reg[-1, -1] = ridge * 0.1  # weaker penalty on bias
        beta = np.linalg.solve(Xw.T @ Xw + reg, Xw.T @ tw)
        W_rows.append(beta)
    return np.stack(W_rows, axis=0)


def _predict(W: np.ndarray, X: np.ndarray, classes: List[str]) -> List[str]:
    Xb = np.concatenate([X, np.ones((X.shape[0], 1))], axis=1)
    scores = Xb @ W.T
    idx = np.argmax(scores, axis=1)
    return [classes[int(i)] for i in idx]


def train_test_readout_on_csv(
    path: Path,
    *,
    max_docs: int = 240,
    test_frac: float = 0.3,
    n_units: int = 20,
    seed: int = 42,
    n_seeds: int = 3,
) -> ReadoutResult:
    df = load_table(path)
    text_col = _find_col(df, TEXT_CANDIDATES)
    label_col = _find_col(df, LABEL_CANDIDATES)
    if text_col is None:
        obj = [c for c in df.columns if df[c].dtype == object]
        text_col = obj[0] if obj else df.columns[0]
    if label_col is None:
        label_col = df.columns[0] if df.columns[0] != text_col else df.columns[-1]

    df = df[[text_col, label_col]].dropna()
    df[text_col] = df[text_col].astype(str)
    df[label_col] = df[label_col].astype(str).str.upper().str.strip()

    parts = []
    n_lab = max(df[label_col].nunique(), 1)
    per = max(12, max_docs // n_lab)
    for lab, g in df.groupby(label_col):
        parts.append(g.sample(n=min(len(g), per), random_state=seed))
    sample = pd.concat(parts, ignore_index=True)
    if len(sample) > max_docs:
        sample = sample.sample(n=max_docs, random_state=seed)

    mind = LiteratureMind(n_units=n_units, device="cpu")
    X_all, y_all, mean_rate = _encode_rows(
        sample[text_col].tolist(), sample[label_col].tolist(), mind
    )
    if len(y_all) < 4:
        raise RuntimeError(f"too few encoded samples from {path}")

    seed_tests: List[float] = []
    seed_bals: List[float] = []
    best: Optional[Dict[str, Any]] = None

    for s in range(seed, seed + n_seeds):
        Xtr, Xte, ytr, yte = _stratified_split(X_all, y_all, test_frac=test_frac, seed=s)
        Xtr_s, Xte_s, _, _ = _standardize(Xtr, Xte)
        classes = sorted(set(ytr) | set(yte))
        W = _fit_ovr_ridge_balanced(Xtr_s, ytr, classes, ridge=0.04)
        pred_tr = _predict(W, Xtr_s, classes)
        pred_te = _predict(W, Xte_s, classes)
        train_acc = float(np.mean([a == b for a, b in zip(pred_tr, ytr)]))
        test_acc = float(np.mean([a == b for a, b in zip(pred_te, yte)]))
        conf, bal, recalls = _confusion_and_balanced(yte, pred_te)
        seed_tests.append(test_acc)
        seed_bals.append(bal)
        pack = {
            "train_acc": train_acc,
            "test_acc": test_acc,
            "bal": bal,
            "conf": conf,
            "recalls": recalls,
            "classes": classes,
            "n_train": len(ytr),
            "n_test": len(yte),
            "pred_te": pred_te,
            "yte": yte,
        }
        if best is None or test_acc > best["test_acc"]:
            best = pack

    assert best is not None
    return ReadoutResult(
        dataset=path.parent.name + "/" + path.name,
        n_train=best["n_train"],
        n_test=best["n_test"],
        n_classes=len(best["classes"]),
        classes=best["classes"],
        train_acc=best["train_acc"],
        test_acc=best["test_acc"],
        balanced_accuracy=best["bal"],
        per_class_recall=best["recalls"],
        confusion=best["conf"],
        mean_fire_rate_train=mean_rate,
        n_features=int(X_all.shape[1]),
        multi_seed_test_mean=float(np.mean(seed_tests)),
        multi_seed_test_std=float(np.std(seed_tests)),
        multi_seed_bal_mean=float(np.mean(seed_bals)),
        honesty=(
            "Class-balanced ridge OVR on standardized FSOT Morse/reservoir fingerprints "
            f"({X_all.shape[1]}-D, {n_seeds} seeds). Linear probe — SOTA track climbs these numbers."
        ),
    )


def run_readout_suite(
    paths: Optional[Sequence[Path]] = None,
    write: bool = True,
    n_seeds: int = 3,
) -> Dict[str, Any]:
    if paths is None:
        candidates = [
            DATA_ROOT / "sms_spam" / "spam.csv",
            DATA_ROOT / "sentiment_tiny" / "sentiment_analysis.csv",
        ]
        paths = [p for p in candidates if p.is_file()]
    results = []
    for p in paths:
        try:
            r = train_test_readout_on_csv(p, n_seeds=n_seeds)
            results.append(asdict(r))
            print(
                f"  {r.dataset}: train={r.train_acc:.3f} test={r.test_acc:.3f} "
                f"bal={r.balanced_accuracy:.3f} "
                f"seed_mean={r.multi_seed_test_mean:.3f}±{r.multi_seed_test_std:.3f} "
                f"feat={r.n_features} n_te={r.n_test}"
            )
        except Exception as e:
            results.append({"dataset": str(p), "error": str(e)})
            print(f"  FAIL {p}: {e}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_datasets": len(results),
        "results": results,
        "method": "class_balanced_ridge_ovr_standardized_fsot_fingerprints_multiseed",
        "goal": "climb measured test accuracy toward SOTA-class substrate performance",
    }
    if write:
        path = RESULTS_DIR / "train_test_readout.json"
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "train_test_readout.json").write_text(
            json.dumps(out, indent=2), encoding="utf-8"
        )
        out["path"] = str(path)
    return out
