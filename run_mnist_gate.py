"""
Real MNIST accuracy gate — straight-A bar for vision domain.

Uses local MNIST CSV (repo or D:/fsot_training). Features = 14x14 spatial pool
(L2-normalized). Classifier = k-NN (default k=3). Target top1 ≥ 0.95.

Writes:
  - binary feature pack for Zig (mnist_pack.bin)
  - JSON gate report (mnist_gate.json)
  - mirrors to D:/fsot_training/datasets when present

Usage:
  python run_mnist_gate.py
  python run_mnist_gate.py --train-per-class 1500 --test-per-class 100 --k 3
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from fsot_nuron.paths import DATA

PASS_THRESHOLD = 0.95
SIDE = 14
DIM = SIDE * SIDE  # 196

CANDIDATE_ROOTS = [
    Path(r"D:/fsot_training/datasets/mnist_csv"),
    DATA / "kaggle_datasets" / "mnist_csv",
]
OUT_DIR = DATA / "multimodal" / "mnist_gate"
GAME_OUT = Path(r"D:/fsot_training/datasets/mnist_gate")


def find_mnist() -> Path:
    for root in CANDIDATE_ROOTS:
        if (root / "mnist_train.csv").is_file() and (root / "mnist_test.csv").is_file():
            return root
    raise FileNotFoundError(
        "MNIST CSV not found. Expected mnist_train.csv + mnist_test.csv under "
        + " or ".join(str(p) for p in CANDIDATE_ROOTS)
    )


def load_csv(path: Path, limit: int | None = None) -> Tuple[np.ndarray, np.ndarray]:
    data = np.loadtxt(path, delimiter=",", skiprows=1, max_rows=limit)
    y = data[:, 0].astype(np.int32)
    x = data[:, 1:].astype(np.float32)
    if float(x.max()) > 1.5:
        x = x / 255.0
    return x, y


def pool14(x: np.ndarray, side: int = SIDE) -> np.ndarray:
    """(n,784) → (n, side*side) L2-normalized block means."""
    n = x.shape[0]
    img = x.reshape(n, 28, 28)
    step = 28 // side
    out = np.zeros((n, side, side), dtype=np.float32)
    for y in range(side):
        for xx in range(side):
            out[:, y, xx] = img[:, y * step : (y + 1) * step, xx * step : (xx + 1) * step].mean(axis=(1, 2))
    f = out.reshape(n, -1)
    nrm = np.linalg.norm(f, axis=1, keepdims=True) + 1e-9
    return (f / nrm).astype(np.float32)


def balanced_indices(y: np.ndarray, per_class: int) -> np.ndarray:
    idxs: List[np.ndarray] = []
    for d in range(10):
        ii = np.where(y == d)[0][:per_class]
        if len(ii) < per_class:
            raise RuntimeError(f"digit {d}: need {per_class} samples, have {len(ii)}")
        idxs.append(ii)
    return np.concatenate(idxs)


def knn_predict(A: np.ndarray, ya: np.ndarray, B: np.ndarray, k: int) -> np.ndarray:
    """A (n_train,d), B (n_test,d) → pred labels for B."""
    a2 = (A * A).sum(1)[:, None]
    b2 = (B * B).sum(1)[None, :]
    d2 = a2 + b2 - 2.0 * (A @ B.T)
    if k <= 1:
        return ya[d2.argmin(axis=0)]
    nn = np.argpartition(d2, kth=k - 1, axis=0)[:k, :]
    votes = ya[nn]
    pred = np.zeros(votes.shape[1], dtype=np.int32)
    for i in range(votes.shape[1]):
        pred[i] = int(np.bincount(votes[:, i], minlength=10).argmax())
    return pred


def write_pack(
    path: Path,
    A: np.ndarray,
    ya: np.ndarray,
    B: np.ndarray,
    yb: np.ndarray,
    k: int,
) -> None:
    """
    Binary pack for Zig:
      magic 8s = b'FSOTMN14'
      u32 dim, n_train, n_test, k
      n_train * u8 labels
      n_train * dim * f32 features
      n_test * u8 labels
      n_test * dim * f32 features
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    dim = A.shape[1]
    n_train = A.shape[0]
    n_test = B.shape[0]
    with path.open("wb") as f:
        f.write(b"FSOTMN14")
        f.write(struct.pack("<IIII", dim, n_train, n_test, k))
        f.write(ya.astype(np.uint8).tobytes())
        f.write(np.ascontiguousarray(A, dtype=np.float32).tobytes())
        f.write(yb.astype(np.uint8).tobytes())
        f.write(np.ascontiguousarray(B, dtype=np.float32).tobytes())


def run_gate(
    train_per_class: int = 1500,
    test_per_class: int = 100,
    k: int = 3,
) -> Dict[str, Any]:
    root = find_mnist()
    Xtr, ytr = load_csv(root / "mnist_train.csv")
    Xte, yte = load_csv(root / "mnist_test.csv")
    Ftr = pool14(Xtr)
    Fte = pool14(Xte)

    tr_i = balanced_indices(ytr, train_per_class)
    te_i = balanced_indices(yte, test_per_class)
    A, ya = Ftr[tr_i], ytr[tr_i]
    B, yb = Fte[te_i], yte[te_i]

    pred = knn_predict(A, ya, B, k=k)
    ok = int((pred == yb).sum())
    n = int(len(yb))
    top1 = ok / n if n else 0.0
    passed = top1 + 1e-12 >= PASS_THRESHOLD

    per_digit = {}
    for d in range(10):
        m = yb == d
        if m.any():
            per_digit[str(d)] = float((pred[m] == yb[m]).mean())

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pack_path = OUT_DIR / "mnist_pack.bin"
    write_pack(pack_path, A, ya, B, yb, k)

    report: Dict[str, Any] = {
        "gate": "mnist_accuracy",
        "threshold": PASS_THRESHOLD,
        "top1": round(top1, 6),
        "correct": ok,
        "n_test": n,
        "n_train": int(len(ya)),
        "pass": passed,
        "method": f"knn_k{k}_pool{SIDE}x{SIDE}_l2",
        "dim": DIM,
        "train_per_class": train_per_class,
        "test_per_class": test_per_class,
        "k": k,
        "per_digit": per_digit,
        "mnist_root": str(root),
        "pack_path": str(pack_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "doctrine": "real MNIST held-out accuracy ≥95% (not synthetic digit prototypes)",
    }
    json_path = OUT_DIR / "mnist_gate.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["json_path"] = str(json_path)

    # game drive mirror
    try:
        if Path("D:/").exists():
            GAME_OUT.mkdir(parents=True, exist_ok=True)
            (GAME_OUT / "mnist_gate.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            write_pack(GAME_OUT / "mnist_pack.bin", A, ya, B, yb, k)
            report["game_mirror"] = str(GAME_OUT)
    except OSError as e:
        report["game_mirror_error"] = str(e)

    return report


def main() -> int:
    p = argparse.ArgumentParser(description="MNIST ≥95% accuracy gate")
    p.add_argument("--train-per-class", type=int, default=2000)
    p.add_argument("--test-per-class", type=int, default=150)
    p.add_argument("--k", type=int, default=3)
    args = p.parse_args()

    rep = run_gate(args.train_per_class, args.test_per_class, args.k)
    print(json.dumps(rep, indent=2))
    print(
        f"\nMNIST_GATE top1={rep['top1']:.4f} thr={PASS_THRESHOLD} "
        f"pass={rep['pass']} {rep['correct']}/{rep['n_test']}"
    )
    if rep["pass"]:
        print("FSOT_MNIST_GATE PASS")
        print("FSOT_MNIST_ACCURACY_OK")
        return 0
    print("FSOT_MNIST_GATE FAIL (need ≥95% held-out top1)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
