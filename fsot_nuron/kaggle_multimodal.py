"""
Kaggle → multimodal machine-language inject for FSOT Zig mind.

Doctrine:
  - Mind thinks in machine language (features + tokens + frames).
  - Kaggle is a *lab supply closet* of images/labels (STEM first).
  - No history curriculum. Math / science / literacy vision only here.
  - LLM not required. kaggle CLI must already be authenticated.

Output formats Zig already understands:
  - inject feature text:  vision <strength> f0..f7
  - optional text line with label binding
  - JSONL lesson cards for curriculum merge
"""

from __future__ import annotations

import csv
import json
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .paths import ROOT, DATA

KAGGLE_ROOT = DATA / "kaggle_datasets"
OUT_ROOT = DATA / "multimodal" / "inject"


# STEM-oriented catalog (no history / politics / news)
CATALOG: Dict[str, Dict[str, Any]] = {
    "mnist_csv": {
        "kaggle": "oddrationale/mnist-in-csv",
        "domain": "math",
        "grade_band": "k-g3",
        "desc": "Handwritten digits 0-9 — number identity / visual math",
        "train": "mnist_train.csv",
        "label_col": "label",
        "kind": "mnist_row",
    },
    # Placeholders for later pulls (user already has CLI):
    "fashion_mnist": {
        "kaggle": "zalando-research/fashionmnist",
        "domain": "science",
        "grade_band": "g3-g6",
        "desc": "Clothing object classes — visual category ID",
        "kind": "skip_until_downloaded",
    },
}


@dataclass
class InjectFrame:
    label: str
    domain: str
    vision: List[float]  # 8 dims in [-1,1]
    text_feats: List[float]
    strength: float = 0.9

    def to_inject_lines(self) -> List[str]:
        def fmt(xs: Sequence[float]) -> str:
            return " ".join(f"{x:.6f}" for x in xs)

        return [
            f"vision {self.strength:.3f} {fmt(self.vision)}",
            f"text 0.75 {fmt(self.text_feats)}",
        ]


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _to_signed(x: float) -> float:
    """Map 0..1 → -1..1 for Fixed inject."""
    return max(-1.0, min(1.0, x * 2.0 - 1.0))


def pixels_to_vision8(pixels: Sequence[float]) -> List[float]:
    """
    Compress image pixels (0..255 or 0..1) into 8 Fixed-friendly features.
    Quads mean/std style — machine-language visual code, not CNN.
    """
    vals = [float(p) for p in pixels]
    if not vals:
        return [0.0] * 8
    # normalize to 0..1
    mx = max(vals) if max(vals) > 1.5 else 1.0
    if mx <= 0:
        mx = 1.0
    norm = [v / mx for v in vals]
    n = len(norm)
    # 4 quadrant means + global mean + contrast + edge-ish + sparsity
    if n >= 4:
        q = n // 4
        qmeans = [
            sum(norm[i * q : (i + 1) * q]) / max(1, q) for i in range(4)
        ]
    else:
        qmeans = [sum(norm) / n] * 4
    gmean = sum(norm) / n
    var = sum((x - gmean) ** 2 for x in norm) / n
    contrast = _clamp01(var ** 0.5 * 2.0)
    # simple horizontal gradient energy
    grad = 0.0
    step = max(1, n // 64)
    c = 0
    for i in range(0, n - step, step):
        grad += abs(norm[i] - norm[i + step])
        c += 1
    edge = _clamp01(grad / max(1, c))
    sparse = _clamp01(sum(1 for x in norm if x > 0.15) / n)

    feats01 = qmeans + [gmean, contrast, edge, sparse]
    return [_to_signed(x) for x in feats01[:8]]


def label_to_text8(label: str) -> List[float]:
    """Stable pseudo-features from label string (bind vision↔symbol)."""
    h = 2166136261
    for c in label.encode("utf-8"):
        h ^= c
        h = (h * 16777619) & 0xFFFFFFFF
    out = []
    x = h
    for i in range(8):
        x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        out.append(_to_signed((x % 1000) / 999.0))
    return out


def ensure_dataset(key: str = "mnist_csv") -> Path:
    meta = CATALOG[key]
    dest = KAGGLE_ROOT / key
    dest.mkdir(parents=True, exist_ok=True)
    train_name = meta.get("train")
    if train_name and (dest / train_name).is_file():
        return dest
    ref = meta["kaggle"]
    cmd = [
        "kaggle",
        "datasets",
        "download",
        "-d",
        ref,
        "-p",
        str(dest),
        "--unzip",
    ]
    subprocess.run(cmd, check=True)
    return dest


def load_mnist_frames(path: Path, limit: int = 64, split: str = "train") -> List[InjectFrame]:
    name = "mnist_train.csv" if split == "train" else "mnist_test.csv"
    fpath = path / name
    if not fpath.is_file():
        # alternate names
        cands = list(path.glob("*.csv"))
        if not cands:
            raise FileNotFoundError(f"no csv in {path}")
        fpath = cands[0]
    frames: List[InjectFrame] = []
    with fpath.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            label = str(row.get("label") or row.get("Label") or "0")
            pix = []
            for k, v in row.items():
                if k.lower() == "label":
                    continue
                try:
                    pix.append(float(v))
                except ValueError:
                    pass
            if len(pix) < 16:
                continue
            frames.append(
                InjectFrame(
                    label=label,
                    domain="math",
                    vision=pixels_to_vision8(pix),
                    text_feats=label_to_text8(label),
                )
            )
    return frames


def write_inject_bundle(
    frames: List[InjectFrame],
    out_dir: Path,
    stem: str = "mnist_stem",
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    inject_path = out_dir / f"{stem}_inject.txt"
    jsonl_path = out_dir / f"{stem}_lessons.jsonl"
    lines = [
        "# FSOT multimodal inject — Kaggle STEM vision → Fixed features",
        "# modality strength f0..f7",
        "metric 0.20 0.25 0.10 0.05 0.15",
    ]
    lessons = []
    for i, fr in enumerate(frames):
        lines.append(f"# sample {i} label={fr.label} domain={fr.domain}")
        lines.extend(fr.to_inject_lines())
        lessons.append(
            {
                "id": f"{stem}-{i}-digit-{fr.label}",
                "domain": fr.domain,
                "grade": "k-g3",
                "fact": f"This image shows the digit {fr.label}.",
                "question": "what digit",
                "answer": fr.label,
                "keywords": ["digit", "number", fr.label, "image", "see"],
                "vision_index": i,
            }
        )
    inject_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in lessons:
            f.write(json.dumps(row) + "\n")
    return {
        "inject_path": str(inject_path),
        "lessons_path": str(jsonl_path),
        "n_frames": len(frames),
        "domains": sorted({fr.domain for fr in frames}),
        "doctrine": "Kaggle STEM images → vision/text Fixed features → Zig machine language",
    }


def build_mnist(limit: int = 48, split: str = "train") -> Dict[str, Any]:
    path = ensure_dataset("mnist_csv")
    frames = load_mnist_frames(path, limit=limit, split=split)
    return write_inject_bundle(frames, OUT_ROOT, stem="mnist_digits")


def catalog_report() -> Dict[str, Any]:
    rows = []
    for key, meta in CATALOG.items():
        dest = KAGGLE_ROOT / key
        present = dest.is_dir() and any(dest.iterdir()) if dest.exists() else False
        rows.append(
            {
                "key": key,
                "kaggle": meta["kaggle"],
                "domain": meta["domain"],
                "grade_band": meta.get("grade_band"),
                "desc": meta.get("desc"),
                "local": present,
                "path": str(dest),
            }
        )
    return {
        "n": len(rows),
        "datasets": rows,
        "out_root": str(OUT_ROOT),
        "exclude": "history, news, politics — STEM + literacy vision only",
    }
