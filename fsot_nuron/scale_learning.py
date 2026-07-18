"""
Scale benchmarks under *learning load*: encode + probe train at growing N.

Complements step-only throughput in scale_sweep.py.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import torch

from .deep_readout import DeepEncodeConfig, DeepFSOTEncoder, train_deep_probe
from .paths import ARTIFACTS, ROOT

RESULTS_DIR = ROOT / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def scale_learning_benchmark(
    unit_sizes: Optional[List[int]] = None,
    n_docs: int = 40,
    device_probe: Optional[str] = None,
) -> Dict[str, Any]:
    unit_sizes = unit_sizes or [8, 16, 32, 64]
    device_probe = device_probe or ("cuda" if torch.cuda.is_available() else "cpu")
    # synthetic short texts (domain-mixed labels)
    texts = [
        "great product love it excellent quality",
        "terrible waste of money never again",
        "okay average fine nothing special",
        "FSOT scalar S equals K times T1 T2 T3",
        "buy now free shipping limited offer",
        "the movie was boring and slow",
        "absolutely fantastic experience overall",
        "neutral statement about the weather today",
    ] * (n_docs // 8 + 1)
    labels = (["POS", "NEG", "NEU", "NEU", "POS", "NEG", "POS", "NEU"] * (n_docs // 8 + 1))[
        :n_docs
    ]
    texts = texts[:n_docs]

    rows = []
    for n_units in unit_sizes:
        # encode always on CPU reservoir (launch stability); measure that cost
        enc = DeepFSOTEncoder(
            DeepEncodeConfig(n_units=n_units, max_steps=160, device="cpu")
        )
        t0 = time.perf_counter()
        X = np.stack([enc.encode_numpy(t) for t in texts], axis=0)
        enc_s = time.perf_counter() - t0
        # train probe on selected device
        t1 = time.perf_counter()
        model, classes, meta = train_deep_probe(
            X, labels, epochs=40, device=device_probe, lr=0.08
        )
        if device_probe == "cuda":
            torch.cuda.synchronize()
        train_s = time.perf_counter() - t1
        rows.append(
            {
                "n_units": n_units,
                "n_docs": n_docs,
                "encode_seconds": enc_s,
                "encode_docs_per_s": n_docs / max(enc_s, 1e-9),
                "probe_train_seconds": train_s,
                "probe_device": device_probe,
                "train_acc": meta["train_acc"],
                "unit_encode_throughput": (n_units * n_docs) / max(enc_s, 1e-9),
            }
        )
        print(
            f"  n_units={n_units:3d} encode={enc_s:.2f}s ({rows[-1]['encode_docs_per_s']:.1f} docs/s) "
            f"probe={train_s:.3f}s acc={meta['train_acc']:.3f} dev={device_probe}"
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "note": "Learning-load scale: reservoir encode (CPU) + FSOT-gated probe train.",
    }


def run_scale_learning(write: bool = True) -> Dict[str, Any]:
    out = {"cpu_probe": scale_learning_benchmark(device_probe="cpu")}
    if torch.cuda.is_available():
        out["cuda_probe"] = scale_learning_benchmark(device_probe="cuda")
    if write:
        path = RESULTS_DIR / "scale_learning.json"
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "scale_learning.json").write_text(
            json.dumps(out, indent=2), encoding="utf-8"
        )
        out["path"] = str(path)
    return out
