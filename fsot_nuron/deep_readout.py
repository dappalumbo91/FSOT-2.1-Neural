"""
Deep FSOT-gated readout for SOTA track.

Pipeline:
  text → Morse units → long FluidReservoir → Morse-time attention pool
  → multi-layer FSOT-gated MLP probe → class logits

Still seed/structure-first (no giant free-param transformer). Designed to
climb multi-class sentiment and held-out domain NLP accuracy.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

from .literature_chew import LiteratureMind
from .morse_itu import ITUMorseCodec
from .multi_dataset import (
    LABEL_CANDIDATES,
    TEXT_CANDIDATES,
    _confusion_and_balanced,
    _find_col,
    load_table,
)
from .paths import ARTIFACTS, ROOT
from .reservoir import FluidReservoir, ReservoirConfig
from .seeds import SEEDS

RESULTS_DIR = ROOT / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
EXTERNAL = ROOT / "data" / "external"


def discover_nlp_csvs() -> List[Path]:
    """Local + external NLP tables (I: downloads preferred)."""
    roots = [
        ROOT / "data" / "kaggle_datasets",
        EXTERNAL / "nlp",
        Path(r"I:\FSOT-Physical-Archive\03_FSOT-PublicData\kaggle_downloads"),
    ]
    out: List[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*.csv"):
            try:
                if p.stat().st_size > 400_000_000:
                    continue
            except OSError:
                continue
            out.append(p)
    # de-dupe by name preference: external first
    seen = set()
    uniq = []
    for p in sorted(out, key=lambda x: (0 if "external" in str(x) else 1, str(x))):
        key = p.name.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


class MorseAttentionPool(nn.Module):
    """Single-head attention over Morse/reservoir time (no softmax free-for-all theater — scaled)."""

    def __init__(self, dim: int):
        super().__init__()
        self.q = nn.Linear(dim, dim, bias=False)
        self.k = nn.Linear(dim, dim, bias=False)
        self.v = nn.Linear(dim, dim, bias=False)
        # FSOT seed-derived scale (not learned temperature free param)
        self.scale = float(SEEDS.k) * 0.5 + 0.25

    def forward(self, H: torch.Tensor) -> torch.Tensor:
        # H: [T, D]
        q = self.q(H.mean(dim=0, keepdim=True))  # [1, D]
        k = self.k(H)
        v = self.v(H)
        scores = (q @ k.T) * self.scale / math.sqrt(H.shape[-1])
        w = torch.softmax(scores, dim=-1)  # attention weights over time
        return (w @ v).squeeze(0)  # [D]


class FSOTGatedMLP(nn.Module):
    """Multi-layer probe with FSOT-style multiplicative gates from seeds."""

    def __init__(self, in_dim: int, n_classes: int, hidden: int = 64):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.fc3 = nn.Linear(hidden, n_classes)
        # fixed gates from seeds (buffers, not free params we claim as theory)
        g1 = float(SEEDS.c_eff)
        g2 = float(SEEDS.p_var)
        self.register_buffer("gate1", torch.tensor(g1))
        self.register_buffer("gate2", torch.tensor(g2))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = F.relu(self.fc1(x)) * self.gate1
        h = F.relu(self.fc2(h)) * self.gate2
        return self.fc3(h)


@dataclass
class DeepEncodeConfig:
    n_units: int = 32
    max_steps: int = 320
    feat_dim: int = 48
    device: str = "cpu"


class DeepFSOTEncoder:
    """Encode text → reservoir trajectory → attention pool + stats fingerprint."""

    def __init__(self, cfg: Optional[DeepEncodeConfig] = None):
        self.cfg = cfg or DeepEncodeConfig()
        self.device = self.cfg.device
        self.codec = ITUMorseCodec()
        self.res = FluidReservoir(
            ReservoirConfig(n_units=self.cfg.n_units, device=self.device)
        )
        self.pool = MorseAttentionPool(dim=8).to(self.device)
        # small learnable attention lives with probe training

    def _stim(self, text: str) -> torch.Tensor:
        cleaned = self.codec.roundtrip_accuracy(text)["input_normalized"] or "EMPTY"
        units = [0] * 3 + self.codec.text_to_units(cleaned) + [0] * 3
        if len(units) > self.cfg.max_steps:
            units = units[: self.cfg.max_steps]
        return torch.tensor(
            [0.12 + 0.78 * u for u in units], device=self.device, dtype=torch.float32
        )

    @torch.no_grad()
    def encode_numpy(self, text: str) -> np.ndarray:
        stim = self._stim(text)
        self.res.reset()
        out = self.res.run_sequence(stim, record=True)
        S = out["S_dec"]  # [T, B]
        fired = out["fired_dec"].float()
        T, B = S.shape
        # base sequence features [T, 8]
        run = torch.cumsum(S.mean(dim=1), dim=0) / torch.arange(
            1, T + 1, device=S.device, dtype=S.dtype
        )
        lag = torch.roll(S.mean(dim=1), 1)
        lag[0] = 0
        base = torch.stack(
            [
                S.mean(dim=1),
                S.std(dim=1, unbiased=False),
                fired.mean(dim=1),
                S.max(dim=1).values,
                S.min(dim=1).values,
                run,
                lag,
                (S > 0.4).float().mean(dim=1),
            ],
            dim=-1,
        )
        # deterministic pool if attention untrained: energy-weighted mean
        energy = base.abs().mean(dim=-1)
        w = energy / (energy.sum() + 1e-9)
        pooled = (w.unsqueeze(-1) * base).sum(dim=0)  # [8]

        s_mean = S.mean(dim=1)
        thirds = []
        for a, b in ((0, T // 3), (T // 3, 2 * T // 3), (2 * T // 3, T)):
            seg = s_mean[a:b]
            thirds.extend(
                [
                    float(seg.mean()) if seg.numel() else 0.0,
                    float(seg.std(unbiased=False)) if seg.numel() else 0.0,
                ]
            )
        raw = text.upper()
        ln = max(len(raw), 1)
        surface = [
            sum(c.isalpha() for c in raw) / ln,
            sum(c.isdigit() for c in raw) / ln,
            sum(c in "!?$%&@#*" for c in raw) / ln,
            raw.count(" ") / ln,
            min(len(raw) / 280.0, 1.5),
            min(T / float(self.cfg.max_steps), 1.0),
            float(out["firing_rate_Hz"].mean().cpu()),
            float((fired.mean()).cpu()),
        ]
        fp = (
            pooled.detach().cpu().tolist()
            + thirds
            + surface
            + [
                float(S.mean().cpu()),
                float(S.std(unbiased=False).cpu()),
                float(S.max().cpu()),
                float(S.min().cpu()),
            ]
        )
        # pad
        if len(fp) < self.cfg.feat_dim:
            fp = fp + [0.0] * (self.cfg.feat_dim - len(fp))
        return np.asarray(fp[: self.cfg.feat_dim], dtype=np.float64)


def _load_text_label_frame(path: Path, max_rows: int = 80_000) -> Optional[pd.DataFrame]:
    name = path.name.lower()
    # Twitter entity sentiment: no header → id, entity, sentiment, text
    if "twitter" in name or "twitter" in str(path.parent).lower():
        try:
            df = pd.read_csv(
                path,
                header=None,
                names=["id", "entity", "label", "text"],
                nrows=max_rows,
                encoding="utf-8",
                encoding_errors="replace",
            )
            out = df[["text", "label"]].dropna()
            out["text"] = out["text"].astype(str)
            out["label"] = out["label"].astype(str).str.upper().str.strip()
            # map irrelevant to drop or keep as 4th class
            vc = out["label"].value_counts()
            keep = vc[vc >= 8].index
            out = out[out["label"].isin(keep)]
            return out if len(out) >= 40 else None
        except Exception:
            pass
    # FinancialPhraseBank all-data.csv: no header → label, text
    if name in {"all-data.csv", "data.csv"} or "financial" in str(path.parent).lower():
        try:
            df = pd.read_csv(
                path,
                header=None if name == "all-data.csv" else "infer",
                nrows=max_rows,
                encoding="latin-1",
                encoding_errors="replace",
            )
            if name == "all-data.csv" or df.shape[1] == 2 and not any(
                str(c).lower() in ("sentence", "text", "sentiment", "label") for c in df.columns
            ):
                df.columns = ["label", "text"][: df.shape[1]]
                if df.shape[1] == 2 and "text" not in df.columns:
                    df.columns = ["label", "text"]
            text_col = _find_col(df, TEXT_CANDIDATES + ["Sentence", "sentence", "text", "Text"])
            label_col = _find_col(df, LABEL_CANDIDATES + ["Sentiment", "sentiment", "label"])
            if text_col and label_col:
                out = df[[text_col, label_col]].dropna()
                out.columns = ["text", "label"]
                out["text"] = out["text"].astype(str)
                out["label"] = out["label"].astype(str).str.upper().str.strip()
                vc = out["label"].value_counts()
                keep = vc[vc >= 8].index
                out = out[out["label"].isin(keep)]
                return out if len(out) >= 40 else None
        except Exception:
            pass
    try:
        df = load_table(path, max_rows=max_rows)
    except Exception:
        return None
    text_col = _find_col(df, TEXT_CANDIDATES + ["Text", "Sentence", "review", "Content"])
    label_col = _find_col(df, LABEL_CANDIDATES + ["Sentiment", "sentiment", "emotion"])
    if text_col is None:
        for c in df.columns:
            if df[c].dtype == object and df[c].astype(str).str.len().mean() > 8:
                text_col = str(c)
                break
    if label_col is None:
        for c in df.columns:
            cl = str(c).lower()
            if any(k in cl for k in ("sent", "label", "class", "target", "polarity", "emotion")):
                label_col = str(c)
                break
    if text_col is None or label_col is None:
        cols = {str(c).lower(): c for c in df.columns}
        if "review" in cols and "sentiment" in cols:
            text_col, label_col = cols["review"], cols["sentiment"]
        else:
            return None
    out = df[[text_col, label_col]].dropna()
    out.columns = ["text", "label"]
    out["text"] = out["text"].astype(str)
    out["label"] = out["label"].astype(str).str.upper().str.strip()
    vc = out["label"].value_counts()
    keep = vc[vc >= 8].index
    out = out[out["label"].isin(keep)]
    return out if len(out) >= 40 else None


def _stratified_indices(y: List[str], test_frac: float, seed: int) -> Tuple[List[int], List[int]]:
    rng = np.random.default_rng(seed)
    by: Dict[str, List[int]] = {}
    for i, lab in enumerate(y):
        by.setdefault(lab, []).append(i)
    tr, te = [], []
    for idxs in by.values():
        idxs = list(idxs)
        rng.shuffle(idxs)
        n_te = max(1, int(round(len(idxs) * test_frac))) if len(idxs) > 3 else max(1, len(idxs) // 5)
        te.extend(idxs[:n_te])
        tr.extend(idxs[n_te:] or idxs[:1])
    return tr, te


def train_deep_probe(
    X: np.ndarray,
    y: List[str],
    *,
    epochs: int = 80,
    lr: float = 0.05,
    seed: int = 0,
    device: str = "cpu",
) -> Tuple[FSOTGatedMLP, List[str], Dict[str, float]]:
    classes = sorted(set(y))
    cls_to_i = {c: i for i, c in enumerate(classes)}
    y_idx = np.array([cls_to_i[c] for c in y], dtype=np.int64)
    # standardize
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd < 1e-8, 1.0, sd)
    Xs = (X - mu) / sd
    xt = torch.tensor(Xs, dtype=torch.float32, device=device)
    yt = torch.tensor(y_idx, dtype=torch.long, device=device)
    hidden = 128 if len(classes) >= 3 else 96
    model = FSOTGatedMLP(X.shape[1], len(classes), hidden=hidden).to(device)
    # Full-batch more stable on small FSOT-fingerprint sets; mini-batch for larger n
    use_mb = xt.shape[0] >= 400
    opt = torch.optim.Adam(
        model.parameters(),
        lr=(lr * 0.4 if use_mb else lr),
        weight_decay=1e-4,
    )
    counts = np.bincount(y_idx, minlength=len(classes)).astype(np.float64)
    w = 1.0 / np.maximum(counts, 1.0)
    w = w / w.mean()
    weight = torch.tensor(w, dtype=torch.float32, device=device)
    model.train()
    n = xt.shape[0]
    for ep in range(epochs):
        if use_mb:
            perm = torch.randperm(n, device=device)
            for i in range(0, n, 64):
                idx = perm[i : i + 64]
                opt.zero_grad()
                logits = model(xt[idx])
                loss = F.cross_entropy(logits, yt[idx], weight=weight)
                loss.backward()
                opt.step()
        else:
            opt.zero_grad()
            logits = model(xt)
            loss = F.cross_entropy(logits, yt, weight=weight)
            loss.backward()
            opt.step()
    model.eval()
    with torch.no_grad():
        pred = model(xt).argmax(dim=-1).cpu().numpy()
    train_acc = float((pred == y_idx).mean())
    meta = {"train_acc": train_acc, "mu": mu.tolist(), "sd": sd.tolist()}
    # stash norm on module
    model.register_buffer("_mu", torch.tensor(mu, dtype=torch.float32))
    model.register_buffer("_sd", torch.tensor(sd, dtype=torch.float32))
    return model, classes, meta


@torch.no_grad()
def predict_deep(model: FSOTGatedMLP, X: np.ndarray, classes: List[str], device: str) -> List[str]:
    mu = model._mu.cpu().numpy()
    sd = model._sd.cpu().numpy()
    Xs = (X - mu) / sd
    xt = torch.tensor(Xs, dtype=torch.float32, device=device)
    pred = model(xt).argmax(dim=-1).cpu().numpy()
    return [classes[int(i)] for i in pred]


def eval_dataset_deep(
    path: Path,
    *,
    max_docs: int = 400,
    n_units: int = 28,
    device: Optional[str] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    df = _load_text_label_frame(path)
    if df is None:
        return {"dataset": str(path), "error": "could not parse text/label"}

    # balance sample
    parts = []
    n_lab = df["label"].nunique()
    per = max(20, max_docs // max(n_lab, 1))
    for lab, g in df.groupby("label"):
        parts.append(g.sample(n=min(len(g), per), random_state=seed))
    sample = pd.concat(parts, ignore_index=True)
    if len(sample) > max_docs:
        sample = sample.sample(n=max_docs, random_state=seed)

    enc = DeepFSOTEncoder(DeepEncodeConfig(n_units=n_units, device=device if device == "cpu" else "cpu"))
    # encode on CPU reservoir for stability; probe can be cuda
    t0 = time.perf_counter()
    X_list = []
    y_list = []
    for text, lab in zip(sample["text"].tolist(), sample["label"].tolist()):
        if len(str(text)) < 4:
            continue
        X_list.append(enc.encode_numpy(str(text)[:400]))
        y_list.append(str(lab))
    encode_s = time.perf_counter() - t0
    X = np.stack(X_list, axis=0)
    tr_idx, te_idx = _stratified_indices(y_list, 0.3, seed)
    Xtr, Xte = X[tr_idx], X[te_idx]
    ytr = [y_list[i] for i in tr_idx]
    yte = [y_list[i] for i in te_idx]

    model, classes, meta = train_deep_probe(Xtr, ytr, epochs=100, device=device)
    pred_tr = predict_deep(model, Xtr, classes, device)
    pred_te = predict_deep(model, Xte, classes, device)
    train_acc = float(np.mean([a == b for a, b in zip(pred_tr, ytr)]))
    test_acc = float(np.mean([a == b for a, b in zip(pred_te, yte)]))
    conf, bal, recalls = _confusion_and_balanced(yte, pred_te)
    return {
        "dataset": path.parent.name + "/" + path.name,
        "path": str(path),
        "n_train": len(ytr),
        "n_test": len(yte),
        "n_classes": len(classes),
        "classes": classes,
        "train_acc": train_acc,
        "test_acc": test_acc,
        "balanced_accuracy": bal,
        "per_class_recall": recalls,
        "confusion": conf,
        "encode_seconds": encode_s,
        "n_features": int(X.shape[1]),
        "n_units": n_units,
        "device_probe": device,
        "method": "deep_fsot_gated_mlp_morse_attention_pool",
    }


def run_deep_nlp_suite(
    paths: Optional[Sequence[Path]] = None,
    max_docs: int = 360,
    write: bool = True,
) -> Dict[str, Any]:
    if paths is None:
        # prioritize sentiment-ish and known good files
        prefer = []
        all_csvs = discover_nlp_csvs()
        for p in all_csvs:
            name = p.name.lower()
            parent = p.parent.name.lower()
            score = 0
            for kw in ("sentiment", "imdb", "twitter", "spam", "financial", "review", "social"):
                if kw in name or kw in parent:
                    score += 1
            if score:
                prefer.append((score, p))
        prefer.sort(key=lambda x: -x[0])
        paths = [p for _, p in prefer[:8]]
        # always include local tiny if present
        local = [
            ROOT / "data" / "kaggle_datasets" / "sentiment_tiny" / "sentiment_analysis.csv",
            ROOT / "data" / "kaggle_datasets" / "sms_spam" / "spam.csv",
        ]
        for p in local:
            if p.is_file() and p not in paths:
                paths.insert(0, p)

    results = []
    for p in paths:
        print(f"  deep-eval {p} ...")
        try:
            r = eval_dataset_deep(p, max_docs=max_docs)
            results.append(r)
            if "error" in r:
                print(f"    ERR {r['error']}")
            else:
                print(
                    f"    test={r['test_acc']:.3f} bal={r['balanced_accuracy']:.3f} "
                    f"classes={r['n_classes']} n_te={r['n_test']}"
                )
        except Exception as e:
            results.append({"dataset": str(p), "error": str(e)})
            print(f"    FAIL {e}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_datasets": len(results),
        "results": results,
        "external_root": str(EXTERNAL),
        "goal": "SOTA-track multi-domain NLP on FSOT deep readout",
    }
    if write:
        path = RESULTS_DIR / "deep_nlp_suite.json"
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "deep_nlp_suite.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        out["path"] = str(path)
    return out
