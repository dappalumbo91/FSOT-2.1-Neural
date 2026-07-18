"""
Multi-dataset Kaggle evaluation harness for FSOT-2.1-Neural.

Supports:
  - Tabular EEG / signal feature CSVs with a label column
  - Text classification (text + label columns)
  - Free-text corpora (chew + retrieval Q&A)

Produces a scoreboard so diverse industry datasets can be compared fairly.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .paths import ROOT, ARTIFACTS

DATA_ROOT = ROOT / "data" / "kaggle_datasets"
SCOREBOARD_PATH = ARTIFACTS / "multi_dataset_scoreboard.json"

# Common label / text column names
LABEL_CANDIDATES = [
    "label", "Label", "LABEL", "class", "Class", "target", "Target",
    "sentiment", "Sentiment", "emotion", "Emotion", "category", "Category",
    "Label", "mental_state", "state", "Condition",
    "v1",  # SMS spam classic
]
TEXT_CANDIDATES = [
    "text", "Text", "TEXT", "sentence", "Sentence", "review", "Review",
    "content", "Content", "message", "Message", "tweet", "Tweet",
    "v2",  # SMS spam classic
    "news", "headline", "title", "Title", "body", "Body",
]


@dataclass
class DatasetScore:
    name: str
    kind: str
    path: str
    n_rows: int
    n_features_or_docs: int
    labels: Dict[str, int]
    metrics: Dict[str, Any]
    notes: str = ""


def discover_datasets(root: Optional[Path] = None) -> List[Path]:
    root = root or DATA_ROOT
    if not root.is_dir():
        return []
    files: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() in {".csv", ".tsv", ".txt"}:
            # skip huge binaries-ish
            try:
                if p.stat().st_size > 200_000_000:
                    continue
            except OSError:
                continue
            files.append(p)
    return sorted(files, key=lambda x: x.stat().st_size)


def _guess_kind(df: pd.DataFrame, path: Path) -> str:
    cols = [str(c) for c in df.columns]
    low = " ".join(cols).lower()
    name = path.name.lower()
    # EEG-ish feature names
    if any(c.startswith("mean_") or c.startswith("fft_") or "eeg" in c.lower() for c in cols):
        return "tabular_signal"
    if "emotion" in name or "eeg" in name or "brainwave" in name:
        return "tabular_signal"
    # text + label
    has_text = any(c in df.columns for c in TEXT_CANDIDATES) or any(
        df[c].dtype == object for c in df.columns if c not in LABEL_CANDIDATES
    )
    has_label = any(c in df.columns for c in LABEL_CANDIDATES)
    if has_text and has_label:
        return "text_classification"
    if path.suffix.lower() == ".txt" or (df.shape[1] <= 2 and has_text):
        return "text_corpus"
    if has_label and df.select_dtypes(include=[np.number]).shape[1] > 5:
        return "tabular_signal"
    if has_text:
        return "text_corpus"
    return "tabular_generic"


def _find_col(df: pd.DataFrame, cands: Sequence[str]) -> Optional[str]:
    for c in cands:
        if c in df.columns:
            return c
    # fuzzy
    for c in df.columns:
        cl = str(c).lower()
        for cand in cands:
            if cand.lower() in cl:
                return str(c)
    return None


def load_table(path: Path, max_rows: int = 50_000) -> pd.DataFrame:
    encodings = ("utf-8", "latin-1", "cp1252")
    df = None
    last_err = None
    if path.suffix.lower() == ".tsv":
        for enc in encodings:
            try:
                df = pd.read_csv(path, sep="\t", nrows=max_rows, encoding=enc)
                break
            except Exception as e:
                last_err = e
    elif path.suffix.lower() == ".txt":
        # try SMS spam style: label\ttext or just lines
        try:
            df = pd.read_csv(
                path, sep="\t", header=None, names=["label", "text"],
                nrows=max_rows, encoding="utf-8", encoding_errors="replace",
            )
            if df["text"].isna().mean() > 0.5:
                raise ValueError("bad tsv")
        except Exception:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:max_rows]
            labels, texts = [], []
            for ln in lines:
                if "\t" in ln:
                    a, b = ln.split("\t", 1)
                    labels.append(a)
                    texts.append(b)
                elif ln.lower().startswith("ham ") or ln.lower().startswith("spam "):
                    a, b = ln.split(" ", 1)
                    labels.append(a)
                    texts.append(b)
                else:
                    labels.append("doc")
                    texts.append(ln)
            df = pd.DataFrame({"label": labels, "text": texts})
    else:
        for enc in encodings:
            try:
                df = pd.read_csv(path, nrows=max_rows, encoding=enc)
                break
            except Exception as e:
                last_err = e
                try:
                    df = pd.read_csv(path, nrows=max_rows, encoding=enc, encoding_errors="replace")
                    break
                except Exception as e2:
                    last_err = e2
    if df is None:
        raise RuntimeError(f"could not load {path}: {last_err}")
    # clean first col hash
    cols = list(df.columns)
    if cols and str(cols[0]).startswith("#"):
        cols[0] = str(cols[0]).lstrip("#").strip()
        df.columns = cols
    # drop fully empty unnamed cols (SMS spam export)
    drop = [c for c in df.columns if str(c).startswith("Unnamed") and df[c].isna().all()]
    if drop:
        df = df.drop(columns=drop)
    return df


def eval_tabular_signal(df: pd.DataFrame, path: Path) -> DatasetScore:
    label_col = _find_col(df, LABEL_CANDIDATES) or df.columns[-1]
    y = df[label_col].astype(str).str.upper()
    X = df.drop(columns=[label_col], errors="ignore").select_dtypes(include=[np.number]).dropna(axis=1, how="all")
    if X.shape[1] > 256:
        prefer = [c for c in X.columns if str(c).startswith("mean_") or str(c).startswith("fft_")]
        X = X[prefer[:256]] if len(prefer) >= 32 else X.iloc[:, :256]

    row_e = X.abs().mean(axis=1)
    energy_cv = float(row_e.std() / (row_e.mean() + 1e-12))
    labels = y.value_counts().to_dict()

    by = {}
    for lab in sorted(y.unique()):
        sub = X[y == lab]
        if len(sub) == 0:
            continue
        by[str(lab)] = {
            "n": int(len(sub)),
            "energy_mean": float(sub.abs().mean().mean()),
            "std_mean": float(sub.std(axis=0).mean()),
        }

    # Separability: pairwise energy mean distance / pooled std
    energies = {k: v["energy_mean"] for k, v in by.items()}
    if len(energies) >= 2:
        vals = list(energies.values())
        sep = float((max(vals) - min(vals)) / (np.std(vals) + 1e-9))
    else:
        sep = 0.0

    # FSOT template diversity score
    template_spread = 0.0
    if len(by) >= 2:
        stims = []
        base = list(by.values())[0]["energy_mean"] or 1.0
        for lab, v in by.items():
            stims.append(1.0 + 0.3 * ((v["energy_mean"] / base) - 1.0))
        template_spread = float(np.std(stims))

    metrics = {
        "energy_cv": energy_cv,
        "class_separability": sep,
        "template_spread": template_spread,
        "n_classes": len(by),
        "by_label": by,
        "fsot_fit_score": float(min(1.0, 0.35 * min(energy_cv, 2.0) + 0.35 * min(sep / 5.0, 1.0) + 0.3 * min(template_spread * 5, 1.0))),
    }
    return DatasetScore(
        name=path.parent.name + "/" + path.name,
        kind="tabular_signal",
        path=str(path),
        n_rows=int(len(df)),
        n_features_or_docs=int(X.shape[1]),
        labels={str(k): int(v) for k, v in labels.items()},
        metrics=metrics,
        notes="EEG/signal features → emotion-style FSOT drive priors",
    )


def eval_text_classification(df: pd.DataFrame, path: Path, max_docs: int = 120) -> DatasetScore:
    """Chew labeled texts; measure retrieval of correct label via keyword+fluid match proxy."""
    from .literature_chew import LiteratureMind, chunk_text

    text_col = _find_col(df, TEXT_CANDIDATES)
    label_col = _find_col(df, LABEL_CANDIDATES)
    if text_col is None:
        # pick first object column
        obj = [c for c in df.columns if df[c].dtype == object]
        text_col = obj[0] if obj else df.columns[0]
    if label_col is None:
        label_col = df.columns[0] if df.columns[0] != text_col else df.columns[-1]

    df = df[[text_col, label_col]].dropna()
    df[text_col] = df[text_col].astype(str)
    df[label_col] = df[label_col].astype(str).str.upper().str.strip()
    # balance subsample
    parts = []
    for lab, g in df.groupby(label_col):
        parts.append(g.sample(n=min(len(g), max_docs // max(df[label_col].nunique(), 1)), random_state=42))
    sample = pd.concat(parts, ignore_index=True)
    if len(sample) > max_docs:
        sample = sample.sample(n=max_docs, random_state=42)

    mind = LiteratureMind(n_units=12, device="cpu")
    mind.memory = []
    # Chew each doc as its own memory with label tagged in text for retrieval test
    # For fair test: store text WITHOUT label; query uses "which class is this text?"
    from .literature_chew import MemoryEntry

    n_chewed = 0
    for i, row in sample.iterrows():
        text = str(row[text_col])[:400]
        if len(text) < 8:
            continue
        lab = str(row[label_col])
        r = mind._run_passage(text)
        mind.memory.append(
            MemoryEntry(
                id=len(mind.memory),
                source=lab,  # label as source for scoring
                text=text,
                morse=r["morse"][:120],
                ternary_hist=r["fingerprint"],
                s_mean=r["s_mean"],
                s_std=r["s_std"],
                fire_rate=r["fire_rate"],
                reconstructed=r["reconstructed"],
                chemical_utterance=r["chemical_utterance"] or "",
                aa_head=r["aa_head"],
            )
        )
        n_chewed += 1
        if n_chewed >= max_docs:
            break

    # Leave-one-out style: for each memory, query with the text and see if top source label matches
    correct = 0
    total = 0
    # subsample eval for speed
    eval_idx = list(range(len(mind.memory)))
    if len(eval_idx) > 40:
        rng = np.random.default_rng(0)
        eval_idx = list(rng.choice(eval_idx, size=40, replace=False))

    for i in eval_idx:
        m = mind.memory[i]
        # temporary remove self
        hold = mind.memory.pop(i)
        res = mind.query(hold.text[:200], top_k=3)
        mind.memory.insert(i, hold)
        if not res.get("ok"):
            continue
        top_sources = [t["source"] for t in res.get("top", [])]
        total += 1
        if top_sources and top_sources[0] == hold.source:
            correct += 1
        elif hold.source in top_sources[:2]:
            correct += 0.5  # partial credit top-2

    acc = float(correct / total) if total else 0.0
    labels = sample[label_col].value_counts().to_dict()
    metrics = {
        "retrieval_top1_acc": acc,
        "n_chewed": n_chewed,
        "n_eval": total,
        "mean_fire_rate": float(np.mean([m.fire_rate for m in mind.memory])) if mind.memory else 0.0,
        "fsot_fit_score": float(min(1.0, acc)),  # for text, retrieval accuracy is the fit
    }
    return DatasetScore(
        name=path.parent.name + "/" + path.name,
        kind="text_classification",
        path=str(path),
        n_rows=int(len(df)),
        n_features_or_docs=n_chewed,
        labels={str(k): int(v) for k, v in labels.items()},
        metrics=metrics,
        notes="Labeled text chewed into Morse/reservoir memory; retrieval accuracy = label recovery",
    )


def eval_text_corpus(df: pd.DataFrame, path: Path, max_docs: int = 60) -> DatasetScore:
    from .literature_chew import LiteratureMind, MemoryEntry

    text_col = _find_col(df, TEXT_CANDIDATES)
    if text_col is None:
        obj = [c for c in df.columns if df[c].dtype == object]
        text_col = obj[0] if obj else df.columns[0]
    texts = [str(t)[:400] for t in df[text_col].dropna().tolist() if len(str(t)) > 20][:max_docs]

    mind = LiteratureMind(n_units=12, device="cpu")
    mind.memory = []
    for i, text in enumerate(texts):
        r = mind._run_passage(text)
        mind.memory.append(
            MemoryEntry(
                id=i,
                source=path.name,
                text=text,
                morse=r["morse"][:120],
                ternary_hist=r["fingerprint"],
                s_mean=r["s_mean"],
                s_std=r["s_std"],
                fire_rate=r["fire_rate"],
                reconstructed=r["reconstructed"],
                chemical_utterance=r["chemical_utterance"] or "",
                aa_head=r["aa_head"],
            )
        )

    # Self-retrieval: query first 40 chars should retrieve same chunk often
    hits = 0
    n_eval = min(20, len(mind.memory))
    for i in range(n_eval):
        m = mind.memory[i]
        hold = mind.memory.pop(i)
        res = mind.query(hold.text[:120], top_k=1)
        mind.memory.insert(i, hold)
        if res.get("ok") and res.get("top") and res["top"][0]["text"][:40] == hold.text[:40]:
            hits += 1
    acc = hits / max(n_eval, 1)
    metrics = {
        "self_retrieval_acc": float(acc),
        "n_chewed": len(mind.memory),
        "mean_fire_rate": float(np.mean([m.fire_rate for m in mind.memory])) if mind.memory else 0.0,
        "fsot_fit_score": float(acc),
    }
    return DatasetScore(
        name=path.parent.name + "/" + path.name,
        kind="text_corpus",
        path=str(path),
        n_rows=len(texts),
        n_features_or_docs=len(mind.memory),
        labels={},
        metrics=metrics,
        notes="Unlabeled corpus self-retrieval via Morse/fluid memory",
    )


def evaluate_file(path: Path) -> DatasetScore:
    try:
        df = load_table(path)
    except Exception as e:
        return DatasetScore(
            name=str(path),
            kind="error",
            path=str(path),
            n_rows=0,
            n_features_or_docs=0,
            labels={},
            metrics={"error": str(e)},
            notes="load failed",
        )
    if df is None or len(df) == 0:
        return DatasetScore(str(path), "empty", str(path), 0, 0, {}, {}, "empty")

    kind = _guess_kind(df, path)
    try:
        if kind == "tabular_signal":
            return eval_tabular_signal(df, path)
        if kind == "text_classification":
            return eval_text_classification(df, path, max_docs=200)
        if kind == "text_corpus":
            return eval_text_corpus(df, path)
        # generic: try signal if many numeric else text
        if df.select_dtypes(include=[np.number]).shape[1] > 5:
            return eval_tabular_signal(df, path)
        return eval_text_classification(df, path, max_docs=150)
    except Exception as e:
        return DatasetScore(
            name=path.parent.name + "/" + path.name,
            kind=kind,
            path=str(path),
            n_rows=int(len(df)),
            n_features_or_docs=0,
            labels={},
            metrics={"error": str(e)},
            notes="eval failed",
        )


def run_scoreboard(
    root: Optional[Path] = None,
    max_files: int = 12,
) -> Dict[str, Any]:
    root = root or DATA_ROOT
    files = discover_datasets(root)[:max_files]
    # always include staged emotions if present
    emo = ROOT / "data" / "eeg" / "kaggle_emotions" / "emotions.csv"
    if emo.is_file() and emo not in files:
        files = [emo] + files

    scores: List[DatasetScore] = []
    seen = set()
    seen_sig = set()
    for f in files:
        key = str(f.resolve())
        if key in seen:
            continue
        seen.add(key)
        # dedupe identical files staged twice (same size+name)
        try:
            sig = (f.name.lower(), f.stat().st_size)
        except OSError:
            sig = (f.name.lower(), 0)
        if sig in seen_sig:
            continue
        seen_sig.add(sig)
        print(f"Evaluating {f} ...")
        scores.append(evaluate_file(f))

    # rank by fsot_fit_score when present
    def fit(s: DatasetScore) -> float:
        m = s.metrics or {}
        if "error" in m:
            return -1.0
        return float(m.get("fsot_fit_score", 0.0))

    ranked = sorted(scores, key=fit, reverse=True)
    board = {
        "n_datasets": len(scores),
        "rank_by_fsot_fit": [
            {
                "rank": i + 1,
                "name": s.name,
                "kind": s.kind,
                "fit": fit(s),
                "n_rows": s.n_rows,
                "metrics": {k: v for k, v in s.metrics.items() if k != "by_label"},
            }
            for i, s in enumerate(ranked)
        ],
        "datasets": [asdict(s) for s in scores],
    }
    SCOREBOARD_PATH.write_text(json.dumps(board, indent=2, default=str), encoding="utf-8")
    return board
