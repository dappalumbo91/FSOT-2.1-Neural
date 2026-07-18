"""
Train/test FSOT-gated linear readout on Morse–reservoir fingerprints.

Honest protocol:
  - Stratified train/test split (not leave-one-out memory match)
  - Fingerprints from LiteratureMind._run_passage (FSOT substrate)
  - Linear multi-class probe (one-vs-rest least squares) — no transformer
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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
    honesty: str


def _encode_rows(
    texts: Sequence[str],
    labels: Sequence[str],
    mind: LiteratureMind,
    max_len: int = 200,
) -> Tuple[np.ndarray, List[str], float]:
    X: List[List[float]] = []
    y: List[str] = []
    rates: List[float] = []
    for text, lab in zip(texts, labels):
        t = str(text)[:max_len]
        if len(t) < 4:
            continue
        r = mind._run_passage(t)
        fp = list(r["fingerprint"])
        # pad/truncate to fixed
        if len(fp) < 16:
            fp = fp + [0.0] * (16 - len(fp))
        X.append(fp[:16])
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
    if not te_idx:  # tiny data fallback
        te_idx = tr_idx[-max(1, len(tr_idx) // 4) :]
        tr_idx = tr_idx[: -len(te_idx)] or tr_idx
    return X[tr_idx], X[te_idx], [y[i] for i in tr_idx], [y[i] for i in te_idx]


def _fit_ovr_least_squares(X: np.ndarray, y: List[str], classes: List[str]) -> np.ndarray:
    """Return weight matrix W shape [n_classes, n_feat+1] including bias."""
    n, d = X.shape
    Xb = np.concatenate([X, np.ones((n, 1))], axis=1)
    # ridge for stability
    reg = 1e-2 * np.eye(d + 1)
    XtX = Xb.T @ Xb + reg
    W = []
    for c in classes:
        t = np.array([1.0 if yi == c else -1.0 for yi in y], dtype=np.float64)
        w = np.linalg.solve(XtX, Xb.T @ t)
        W.append(w)
    return np.stack(W, axis=0)


def _predict(W: np.ndarray, X: np.ndarray, classes: List[str]) -> List[str]:
    Xb = np.concatenate([X, np.ones((X.shape[0], 1))], axis=1)
    scores = Xb @ W.T  # [n, C]
    idx = np.argmax(scores, axis=1)
    return [classes[int(i)] for i in idx]


def train_test_readout_on_csv(
    path: Path,
    *,
    max_docs: int = 160,
    test_frac: float = 0.3,
    n_units: int = 12,
    seed: int = 42,
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

    # balance subsample before split
    parts = []
    n_lab = max(df[label_col].nunique(), 1)
    per = max(8, max_docs // n_lab)
    for lab, g in df.groupby(label_col):
        parts.append(g.sample(n=min(len(g), per), random_state=seed))
    sample = pd.concat(parts, ignore_index=True)
    if len(sample) > max_docs:
        sample = sample.sample(n=max_docs, random_state=seed)

    mind = LiteratureMind(n_units=n_units, device="cpu")
    X, y, mean_rate = _encode_rows(
        sample[text_col].tolist(), sample[label_col].tolist(), mind
    )
    if len(y) < 4:
        raise RuntimeError(f"too few encoded samples from {path}")

    Xtr, Xte, ytr, yte = _stratified_split(X, y, test_frac=test_frac, seed=seed)
    classes = sorted(set(ytr) | set(yte))
    W = _fit_ovr_least_squares(Xtr, ytr, classes)
    pred_tr = _predict(W, Xtr, classes)
    pred_te = _predict(W, Xte, classes)
    train_acc = float(np.mean([a == b for a, b in zip(pred_tr, ytr)]))
    test_acc = float(np.mean([a == b for a, b in zip(pred_te, yte)]))
    conf, bal, recalls = _confusion_and_balanced(yte, pred_te)

    return ReadoutResult(
        dataset=path.parent.name + "/" + path.name,
        n_train=len(ytr),
        n_test=len(yte),
        n_classes=len(classes),
        classes=classes,
        train_acc=train_acc,
        test_acc=test_acc,
        balanced_accuracy=bal,
        per_class_recall=recalls,
        confusion=conf,
        mean_fire_rate_train=mean_rate,
        honesty=(
            "Supervised linear readout on FSOT Morse/reservoir fingerprints; "
            "stratified train/test split. Not LOO memory retrieval; not clinical diagnosis."
        ),
    )


def run_readout_suite(
    paths: Optional[Sequence[Path]] = None,
    write: bool = True,
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
            r = train_test_readout_on_csv(p)
            results.append(asdict(r))
            print(
                f"  {r.dataset}: train={r.train_acc:.3f} test={r.test_acc:.3f} "
                f"bal={r.balanced_accuracy:.3f} n_te={r.n_test}"
            )
        except Exception as e:
            results.append({"dataset": str(p), "error": str(e)})
            print(f"  FAIL {p}: {e}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_datasets": len(results),
        "results": results,
        "method": "ridge_ovr_least_squares_on_fsot_fingerprints",
    }
    if write:
        path = RESULTS_DIR / "train_test_readout.json"
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "train_test_readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        out["path"] = str(path)
    return out
