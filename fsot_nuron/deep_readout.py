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
    """Single-head attention over Morse/reservoir time (FSOT seed-scaled)."""

    def __init__(self, dim: int):
        super().__init__()
        self.q = nn.Linear(dim, dim, bias=False)
        self.k = nn.Linear(dim, dim, bias=False)
        self.v = nn.Linear(dim, dim, bias=False)
        self.scale = float(SEEDS.k) * 0.5 + 0.25

    def forward(self, H: torch.Tensor) -> torch.Tensor:
        """
        H: [T, D] or [B, T, D] → [D] or [B, D]
        Residual mean pool for stability on small datasets.
        """
        if H.dim() == 2:
            H = H.unsqueeze(0)
            squeeze = True
        else:
            squeeze = False
        # H: [B, T, D]
        mean_pool = H.mean(dim=1)
        q = self.q(mean_pool).unsqueeze(1)  # [B, 1, D]
        k = self.k(H)
        v = self.v(H)
        scores = torch.bmm(q, k.transpose(1, 2)) * self.scale / math.sqrt(H.shape[-1])
        w = torch.softmax(scores, dim=-1)
        attn = torch.bmm(w, v).squeeze(1)  # [B, D]
        out = 0.55 * attn + 0.45 * mean_pool
        return out.squeeze(0) if squeeze else out


class FSOTGatedMLP(nn.Module):
    """Multi-layer probe with FSOT-style multiplicative gates from seeds."""

    def __init__(self, in_dim: int, n_classes: int, hidden: int = 64, depth: int = 2):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.fc3 = nn.Linear(hidden, hidden if depth >= 3 else n_classes)
        self.fc4 = nn.Linear(hidden, n_classes) if depth >= 3 else None
        self.depth = depth
        g1 = float(SEEDS.c_eff)
        g2 = float(SEEDS.p_var)
        g3 = float(SEEDS.p_new)
        self.register_buffer("gate1", torch.tensor(g1))
        self.register_buffer("gate2", torch.tensor(g2))
        self.register_buffer("gate3", torch.tensor(g3))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = F.relu(self.fc1(x)) * self.gate1
        h = F.relu(self.fc2(h)) * self.gate2
        if self.fc4 is not None:
            h = F.relu(self.fc3(h)) * self.gate3
            return self.fc4(h)
        return self.fc3(h)


@dataclass
class DeepEncodeConfig:
    n_units: int = 32
    max_steps: int = 320
    feat_dim: int = 48
    device: str = "cpu"
    # Long-context / capacity
    long_context: bool = False
    chunk_chars: int = 220
    chunk_overlap: int = 40
    max_chunks: int = 6  # hierarchical windows over document
    max_doc_chars: int = 2400
    long_max_steps: int = 640  # per-chunk Morse/reservoir length
    long_n_units: int = 48
    long_feat_dim: int = 160
    chunk_feat_dim: int = 40  # fixed per-chunk vector before hierarchy


def long_context_config(device: str = "cpu") -> DeepEncodeConfig:
    """Higher capacity encoder for IMDB-style long documents."""
    return DeepEncodeConfig(
        n_units=48,
        max_steps=640,
        feat_dim=160,
        device=device,
        long_context=True,
        chunk_chars=240,
        chunk_overlap=48,
        max_chunks=6,
        max_doc_chars=2800,
        long_max_steps=560,
        long_n_units=48,
        long_feat_dim=160,
        chunk_feat_dim=40,
    )


def _chunk_text(text: str, chunk_chars: int, overlap: int, max_chunks: int) -> List[str]:
    text = " ".join(text.split())
    if not text:
        return ["EMPTY"]
    if len(text) <= chunk_chars:
        return [text]
    chunks: List[str] = []
    step = max(1, chunk_chars - overlap)
    i = 0
    while i < len(text) and len(chunks) < max_chunks:
        piece = text[i : i + chunk_chars]
        # prefer break at space
        if i + chunk_chars < len(text):
            cut = piece.rfind(" ")
            if cut > chunk_chars // 3:
                piece = piece[:cut]
        piece = piece.strip()
        if len(piece) >= 12:
            chunks.append(piece)
        i += max(step, len(piece) - overlap if piece else step)
    # always include document tail (often holds verdict sentences)
    if len(text) > chunk_chars and len(chunks) < max_chunks:
        tail = text[-chunk_chars:].strip()
        if tail and (not chunks or tail != chunks[-1]):
            chunks.append(tail)
    return chunks or [text[:chunk_chars]]


class DeepFSOTEncoder:
    """Encode text → reservoir trajectory → attention pool + stats fingerprint.

    long_context=True: hierarchical chunk encode over the full document so
    capacity is not limited to a single short Morse window.
    """

    def __init__(self, cfg: Optional[DeepEncodeConfig] = None):
        self.cfg = cfg or DeepEncodeConfig()
        self.device = self.cfg.device
        self.codec = ITUMorseCodec()
        n_units = self.cfg.long_n_units if self.cfg.long_context else self.cfg.n_units
        self.res = FluidReservoir(
            ReservoirConfig(n_units=n_units, device=self.device)
        )
        self.pool = MorseAttentionPool(dim=8).to(self.device)
        self._max_steps = (
            self.cfg.long_max_steps if self.cfg.long_context else self.cfg.max_steps
        )
        self._feat_dim = (
            self.cfg.long_feat_dim if self.cfg.long_context else self.cfg.feat_dim
        )

    def _stim(self, text: str, max_steps: Optional[int] = None) -> torch.Tensor:
        cleaned = self.codec.roundtrip_accuracy(text)["input_normalized"] or "EMPTY"
        units = [0] * 3 + self.codec.text_to_units(cleaned) + [0] * 3
        cap = max_steps or self._max_steps
        if len(units) > cap:
            # head + tail sample so long reviews keep ending verdict
            head = int(cap * 0.65)
            tail = cap - head
            units = units[:head] + units[-tail:]
        return torch.tensor(
            [0.12 + 0.78 * u for u in units], device=self.device, dtype=torch.float32
        )

    def _trajectory_fingerprint(
        self, S: torch.Tensor, fired: torch.Tensor, fire_rate: torch.Tensor, text: str
    ) -> np.ndarray:
        T, B = S.shape
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
        # quarters for longer windows
        quarters = []
        for q in range(4):
            a, b = q * T // 4, (q + 1) * T // 4
            seg = s_mean[a:b]
            quarters.append(float(seg.mean()) if seg.numel() else 0.0)
            quarters.append(float(fired[a:b].mean()) if b > a else 0.0)

        raw = text.upper()
        ln = max(len(raw), 1)
        surface = [
            sum(c.isalpha() for c in raw) / ln,
            sum(c.isdigit() for c in raw) / ln,
            sum(c in "!?$%&@#*" for c in raw) / ln,
            raw.count(" ") / ln,
            min(len(raw) / 500.0, 2.5),
            min(T / float(self._max_steps), 1.5),
            float(fire_rate.mean().cpu()) if fire_rate.numel() else 0.0,
            float(fired.mean().cpu()),
        ]
        # cheap polarity lexemes (surface cue only; reservoir still carries structure)
        pos = sum(1 for w in ("GOOD", "GREAT", "LOVE", "EXCELLENT", "BEST", "AMAZING") if w in raw)
        neg = sum(1 for w in ("BAD", "TERRIBLE", "WORST", "HATE", "AWFUL", "BORING") if w in raw)
        surface.extend([pos / 6.0, neg / 6.0, (pos - neg) / 6.0])

        fp = (
            pooled.detach().cpu().tolist()
            + thirds
            + quarters
            + surface
            + [
                float(S.mean().cpu()),
                float(S.std(unbiased=False).cpu()),
                float(S.max().cpu()),
                float(S.min().cpu()),
                float((S.mean(dim=1)[: max(1, T // 5)].mean()).cpu()),  # lead
                float((S.mean(dim=1)[-max(1, T // 5) :].mean()).cpu()),  # tail
            ]
        )
        return np.asarray(fp, dtype=np.float64)

    @torch.no_grad()
    def encode_chunk(self, text: str) -> np.ndarray:
        stim = self._stim(text, max_steps=self._max_steps)
        self.res.reset()
        out = self.res.run_sequence(stim, record=True)
        return self._trajectory_fingerprint(
            out["S_dec"], out["fired_dec"].float(), out["firing_rate_Hz"], text
        )

    @torch.no_grad()
    def encode_numpy(self, text: str) -> np.ndarray:
        text = str(text)
        if not self.cfg.long_context:
            fp = self.encode_chunk(text[:800])
            return self._pad(fp)

        doc = text[: self.cfg.max_doc_chars]
        chunks = _chunk_text(
            doc, self.cfg.chunk_chars, self.cfg.chunk_overlap, self.cfg.max_chunks
        )
        # Always process first + last chunk explicitly for long reviews
        if len(doc) > self.cfg.chunk_chars * 2:
            head = doc[: self.cfg.chunk_chars]
            tail = doc[-self.cfg.chunk_chars :]
            if head not in chunks:
                chunks = [head] + chunks
            if tail not in chunks:
                chunks = chunks + [tail]
            chunks = chunks[: self.cfg.max_chunks]

        cd = int(self.cfg.chunk_feat_dim)
        chunk_fps = [self._pad(self.encode_chunk(ch))[:cd] for ch in chunks]
        M = np.stack(chunk_fps, axis=0)  # [C, cd]
        # hierarchical document pool (fixed-width)
        doc_fp = np.concatenate(
            [
                M.mean(axis=0),
                M.max(axis=0),
                M.std(axis=0),
                M[0],  # first window
                M[-1],  # last window
                np.array(
                    [
                        float(len(chunks)),
                        min(len(doc) / float(self.cfg.max_doc_chars), 1.5),
                        float(np.mean([len(c) for c in chunks])),
                        float(np.max([len(c) for c in chunks])),
                    ],
                    dtype=np.float64,
                ),
            ]
        )
        return self._pad(doc_fp)

    def _pad(self, fp: np.ndarray) -> np.ndarray:
        fp = np.asarray(fp, dtype=np.float64).ravel()
        d = self._feat_dim
        if fp.size < d:
            fp = np.concatenate([fp, np.zeros(d - fp.size)])
        return fp[:d]

    @torch.no_grad()
    def encode_trajectory(
        self, text: str, t_pool: int = 64
    ) -> np.ndarray:
        """
        Return fixed [t_pool, 8] Morse/reservoir time features for learned attention.
        Long docs: concatenate chunk trajectories then resample to t_pool.
        """
        text = str(text)

        def traj_from_text(piece: str) -> np.ndarray:
            stim = self._stim(piece, max_steps=self._max_steps)
            self.res.reset()
            out = self.res.run_sequence(stim, record=True)
            S = out["S_dec"]
            fired = out["fired_dec"].float()
            T = S.shape[0]
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
            )  # [T, 8]
            return base.detach().cpu().numpy().astype(np.float64)

        if self.cfg.long_context:
            doc = text[: self.cfg.max_doc_chars]
            chunks = _chunk_text(
                doc, self.cfg.chunk_chars, self.cfg.chunk_overlap, self.cfg.max_chunks
            )
            if len(doc) > self.cfg.chunk_chars * 2:
                head, tail = doc[: self.cfg.chunk_chars], doc[-self.cfg.chunk_chars :]
                if head not in chunks:
                    chunks = [head] + chunks
                if tail not in chunks:
                    chunks = chunks + [tail]
                chunks = chunks[: self.cfg.max_chunks]
            parts = [traj_from_text(ch) for ch in chunks]
            H = np.concatenate(parts, axis=0) if parts else traj_from_text(doc[:400])
        else:
            H = traj_from_text(text[:1000])

        # resample to fixed t_pool
        T = H.shape[0]
        if T == t_pool:
            return H
        idx = np.linspace(0, T - 1, t_pool)
        i0 = np.floor(idx).astype(int)
        i1 = np.minimum(i0 + 1, T - 1)
        a = (idx - i0).reshape(-1, 1)
        return (1 - a) * H[i0] + a * H[i1]


class AttentionProbe(nn.Module):
    """Learned Morse-time attention + FSOT-gated MLP (end-to-end)."""

    def __init__(self, n_classes: int, hidden: int = 160, depth: int = 3):
        super().__init__()
        self.attn = MorseAttentionPool(dim=8)
        self.mlp = FSOTGatedMLP(in_dim=8, n_classes=n_classes, hidden=hidden, depth=depth)

    def forward(self, H: torch.Tensor) -> torch.Tensor:
        # H: [B, T, 8] or [T, 8]
        pooled = self.attn(H)
        if pooled.dim() == 1:
            return self.mlp(pooled.unsqueeze(0)).squeeze(0)
        return self.mlp(pooled)


def train_attention_probe(
    H: np.ndarray,
    y: List[str],
    *,
    epochs: int = 150,
    lr: float = 0.03,
    device: str = "cpu",
) -> Tuple[AttentionProbe, List[str], Dict[str, float]]:
    """
    H: [N, T, 8] trajectories. Trains learned attention + gated MLP jointly.
    """
    classes = sorted(set(y))
    cls_to_i = {c: i for i, c in enumerate(classes)}
    y_idx = np.array([cls_to_i[c] for c in y], dtype=np.int64)
    # normalize features over train set
    mu = H.reshape(-1, H.shape[-1]).mean(0)
    sd = H.reshape(-1, H.shape[-1]).std(0)
    sd = np.where(sd < 1e-8, 1.0, sd)
    Hs = (H - mu) / sd
    ht = torch.tensor(Hs, dtype=torch.float32, device=device)
    yt = torch.tensor(y_idx, dtype=torch.long, device=device)
    model = AttentionProbe(n_classes=len(classes), hidden=192, depth=3).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=2e-4)
    counts = np.bincount(y_idx, minlength=len(classes)).astype(np.float64)
    w = 1.0 / np.maximum(counts, 1.0)
    w = w / w.mean()
    weight = torch.tensor(w, dtype=torch.float32, device=device)
    n = ht.shape[0]
    model.train()
    for ep in range(epochs):
        perm = torch.randperm(n, device=device)
        for i in range(0, n, 32):
            idx = perm[i : i + 32]
            opt.zero_grad()
            logits = model(ht[idx])
            loss = F.cross_entropy(logits, yt[idx], weight=weight)
            loss.backward()
            opt.step()
    model.eval()
    with torch.no_grad():
        pred = model(ht).argmax(-1).cpu().numpy()
    train_acc = float((pred == y_idx).mean())
    model.register_buffer("_mu", torch.tensor(mu, dtype=torch.float32))
    model.register_buffer("_sd", torch.tensor(sd, dtype=torch.float32))
    return model, classes, {"train_acc": train_acc, "mu": mu.tolist(), "sd": sd.tolist()}


@torch.no_grad()
def predict_attention(
    model: AttentionProbe, H: np.ndarray, classes: List[str], device: str
) -> List[str]:
    mu = model._mu.cpu().numpy()
    sd = model._sd.cpu().numpy()
    Hs = (H - mu) / sd
    ht = torch.tensor(Hs, dtype=torch.float32, device=device)
    pred = model(ht).argmax(-1).cpu().numpy()
    return [classes[int(i)] for i in pred]


def eval_dataset_attention(
    path: Path,
    *,
    max_docs: int = 360,
    long_context: bool = True,
    t_pool: int = 64,
    device: Optional[str] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """Long-context encode trajectories + learned Morse-time attention probe."""
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    df = _load_text_label_frame(path)
    if df is None:
        return {"dataset": str(path), "error": "could not parse text/label"}
    parts = []
    n_lab = df["label"].nunique()
    per = max(24, max_docs // max(n_lab, 1))
    for lab, g in df.groupby("label"):
        parts.append(g.sample(n=min(len(g), per), random_state=seed))
    sample = pd.concat(parts, ignore_index=True)
    if len(sample) > max_docs:
        sample = sample.sample(n=max_docs, random_state=seed)

    mean_len = float(sample["text"].astype(str).str.len().mean())
    if long_context:
        # Faster long path for attention climb: fewer steps/chunks, more docs
        enc_cfg = DeepEncodeConfig(
            n_units=40,
            max_steps=360,
            feat_dim=96,
            device="cpu",
            long_context=True,
            chunk_chars=220,
            chunk_overlap=40,
            max_chunks=4,
            max_doc_chars=2400,
            long_max_steps=360,
            long_n_units=40,
            long_feat_dim=96,
            chunk_feat_dim=40,
        )
    else:
        enc_cfg = DeepEncodeConfig(
            n_units=36, max_steps=420, feat_dim=64, device="cpu", long_context=False
        )
    enc = DeepFSOTEncoder(enc_cfg)
    t0 = time.perf_counter()
    H_list, y_list = [], []
    for text, lab in zip(sample["text"].tolist(), sample["label"].tolist()):
        if len(str(text)) < 4:
            continue
        H_list.append(enc.encode_trajectory(str(text), t_pool=t_pool))
        y_list.append(str(lab))
    encode_s = time.perf_counter() - t0
    H = np.stack(H_list, axis=0)  # [N, T, 8]
    tr_idx, te_idx = _stratified_indices(y_list, 0.3, seed)
    Htr, Hte = H[tr_idx], H[te_idx]
    ytr = [y_list[i] for i in tr_idx]
    yte = [y_list[i] for i in te_idx]
    model, classes, meta = train_attention_probe(
        Htr, ytr, epochs=160, lr=0.025, device=device
    )
    pred_tr = predict_attention(model, Htr, classes, device)
    pred_te = predict_attention(model, Hte, classes, device)
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
        "t_pool": t_pool,
        "long_context": long_context,
        "mean_doc_chars": mean_len,
        "max_chunks": enc_cfg.max_chunks if long_context else 1,
        "max_steps_per_chunk": enc_cfg.long_max_steps if long_context else enc_cfg.max_steps,
        "n_units": enc_cfg.long_n_units if long_context else enc_cfg.n_units,
        "device_probe": device,
        "method": "learned_morse_time_attention_fsot_gated_mlp",
    }


def eval_multitask_domains(
    paths: Sequence[Path],
    *,
    max_docs_each: int = 200,
    device: Optional[str] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Shared encoder fingerprints + domain-tagged multi-class head.
    Labels become DOMAIN::CLASS so the probe learns multi-domain structure.
    """
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    enc = DeepFSOTEncoder(
        DeepEncodeConfig(n_units=32, max_steps=400, feat_dim=64, device="cpu")
    )
    X_list, y_list, domain_list = [], [], []
    t0 = time.perf_counter()
    for path in paths:
        if not path.is_file():
            continue
        df = _load_text_label_frame(path)
        if df is None:
            continue
        domain = path.parent.name
        parts = []
        n_lab = df["label"].nunique()
        per = max(16, max_docs_each // max(n_lab, 1))
        for lab, g in df.groupby("label"):
            parts.append(g.sample(n=min(len(g), per), random_state=seed))
        sample = pd.concat(parts, ignore_index=True)
        if len(sample) > max_docs_each:
            sample = sample.sample(n=max_docs_each, random_state=seed)
        for text, lab in zip(sample["text"].tolist(), sample["label"].tolist()):
            if len(str(text)) < 4:
                continue
            X_list.append(enc.encode_numpy(str(text)[:900]))
            y_list.append(f"{domain}::{lab}")
            domain_list.append(domain)
    encode_s = time.perf_counter() - t0
    if len(y_list) < 40:
        return {"error": "too few multitask samples", "n": len(y_list)}
    X = np.stack(X_list, axis=0)
    tr_idx, te_idx = _stratified_indices(y_list, 0.3, seed)
    Xtr, Xte = X[tr_idx], X[te_idx]
    ytr = [y_list[i] for i in tr_idx]
    yte = [y_list[i] for i in te_idx]
    model, classes, meta = train_deep_probe(
        Xtr, ytr, epochs=140, device=device, capacity="long"
    )
    pred_te = predict_deep(model, Xte, classes, device)
    # overall + per-domain accuracy (strip domain::)
    test_acc = float(np.mean([a == b for a, b in zip(pred_te, yte)]))
    conf, bal, recalls = _confusion_and_balanced(yte, pred_te)
    per_domain: Dict[str, float] = {}
    for d in sorted(set(domain_list)):
        idx = [i for i, lab in enumerate(yte) if lab.startswith(d + "::")]
        if not idx:
            continue
        per_domain[d] = float(
            np.mean([pred_te[i] == yte[i] for i in idx])
        )
    return {
        "method": "multitask_domain_tagged_fsot_probe",
        "n_train": len(ytr),
        "n_test": len(yte),
        "n_classes": len(classes),
        "test_acc": test_acc,
        "balanced_accuracy": bal,
        "per_domain_test_acc": per_domain,
        "encode_seconds": encode_s,
        "device_probe": device,
        "train_acc": meta.get("train_acc"),
    }


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
    capacity: str = "standard",
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
    if capacity == "long":
        hidden, depth, epochs = 192, 3, max(epochs, 120)
    else:
        hidden = 128 if len(classes) >= 3 else 96
        depth = 2
    model = FSOTGatedMLP(X.shape[1], len(classes), hidden=hidden, depth=depth).to(device)
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


def _wants_long_context(path: Path, mean_len: float) -> bool:
    blob = (str(path) + " " + path.name).lower()
    if any(k in blob for k in ("imdb", "review", "movie")):
        return True
    return mean_len >= 180.0


def eval_dataset_deep(
    path: Path,
    *,
    max_docs: int = 400,
    n_units: int = 28,
    device: Optional[str] = None,
    seed: int = 42,
    long_context: Optional[bool] = None,
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

    mean_len = float(sample["text"].astype(str).str.len().mean())
    use_long = long_context if long_context is not None else _wants_long_context(path, mean_len)
    if use_long:
        enc_cfg = long_context_config(device="cpu")
        capacity = "long"
        # slightly fewer docs if each doc is multi-chunk (runtime)
        if len(sample) > 280:
            sample = sample.sample(n=280, random_state=seed)
    else:
        enc_cfg = DeepEncodeConfig(n_units=n_units, max_steps=400, feat_dim=64, device="cpu")
        capacity = "standard"

    enc = DeepFSOTEncoder(enc_cfg)
    t0 = time.perf_counter()
    X_list = []
    y_list = []
    for text, lab in zip(sample["text"].tolist(), sample["label"].tolist()):
        if len(str(text)) < 4:
            continue
        X_list.append(enc.encode_numpy(str(text)))
        y_list.append(str(lab))
    encode_s = time.perf_counter() - t0
    X = np.stack(X_list, axis=0)
    tr_idx, te_idx = _stratified_indices(y_list, 0.3, seed)
    Xtr, Xte = X[tr_idx], X[te_idx]
    ytr = [y_list[i] for i in tr_idx]
    yte = [y_list[i] for i in te_idx]

    model, classes, meta = train_deep_probe(
        Xtr, ytr, epochs=120 if use_long else 100, device=device, capacity=capacity
    )
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
        "n_units": enc_cfg.long_n_units if use_long else n_units,
        "device_probe": device,
        "long_context": use_long,
        "mean_doc_chars": mean_len,
        "max_doc_chars": enc_cfg.max_doc_chars if use_long else 800,
        "max_chunks": enc_cfg.max_chunks if use_long else 1,
        "max_steps_per_chunk": enc_cfg.long_max_steps if use_long else enc_cfg.max_steps,
        "method": (
            "hierarchical_chunk_fsot_reservoir_long_context"
            if use_long
            else "deep_fsot_gated_mlp_morse_attention_pool"
        ),
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
