"""
Real-media pixel identity probe (tutor-ablated).

Train prototypes from early frames of N distinct videos using **only**
retina features (no path / title / subtitle / lexicon in the feature vector).
Test on later frames — progress toward open-world pixel-ID claim gate.

Does **not** claim open-world identity until held-out silent clips of named
characters clear the CAPABILITY_FRONTIER gate. This is a media-entity
discrimination probe on real pixels.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..seeds import SEEDS
from ..sensory.media_stream import (
    discover_media_files,
    media_roots_from_env,
    iter_video_frames,
    _rgb_to_features,
)


@dataclass
class MediaPixelIdReport:
    ok: bool
    pixel_id_top1: float
    pixel_id_chance: float
    n_characters: int  # media entities (videos)
    n_heldout_clips: int
    tutor_ablated: bool
    synthetic: bool
    feature_mode: str
    above_chance: bool
    names: List[str] = field(default_factory=list)
    paths: List[str] = field(default_factory=list)
    per_class_top1: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v) + 1e-12)
    return (v / n).astype(np.float32)


def _frame_feats(rgb: np.ndarray, prev: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
    feats, gray, _st = _rgb_to_features(rgb, prev)
    return _l2_normalize(np.asarray(feats, dtype=np.float32)), gray


def sample_video_feature_bank(
    path: Path,
    *,
    n_train: int = 6,
    n_test: int = 4,
    max_side: int = 72,
    train_stride: int = 12,
    test_stride: int = 25,
) -> Tuple[List[np.ndarray], List[np.ndarray], List[str]]:
    """
    Early frames → train bank; later frames → test bank.
    Temporal split reduces trivial same-frame leakage.
    """
    notes: List[str] = []
    train: List[np.ndarray] = []
    test: List[np.ndarray] = []
    # Collect a longer span so train/test are visually distinct
    need = max(n_train + n_test + 4, 20)
    frames: List[np.ndarray] = []
    try:
        # Larger stride skips title cards / similar consecutive frames
        for img, _t in iter_video_frames(
            path,
            max_frames=need * 4,
            stride=max(8, train_stride),
            max_side=max_side,
        ):
            frames.append(img)
            if len(frames) >= need * 2:
                break
    except Exception as e:
        notes.append(f"decode fail {path.name}: {e}")
        return [], [], notes

    if len(frames) < n_train + 1:
        notes.append(f"too few frames {path.name}: {len(frames)}")
        return [], [], notes

    # Train: evenly spaced in first 55%; test: evenly spaced in last 40%
    n = len(frames)
    cut_a = max(n_train, int(0.55 * n))
    cut_b = min(n - 1, int(0.60 * n))
    train_pool = frames[:cut_a]
    test_pool = frames[cut_b:] if cut_b < n else frames[-max(n_test, 2) :]
    def _pick(pool: List[np.ndarray], k: int) -> List[np.ndarray]:
        if not pool:
            return []
        if len(pool) <= k:
            return list(pool)
        idx = np.linspace(0, len(pool) - 1, k).astype(int)
        return [pool[i] for i in idx]

    train_frames = _pick(train_pool, n_train)
    test_frames = _pick(test_pool, n_test)
    if len(test_frames) < max(1, n_test // 2):
        test_frames = frames[-n_test:]

    prev = None
    for img in train_frames:
        v, prev = _frame_feats(img, prev)
        train.append(v)
    prev = None
    for img in test_frames:
        v, prev = _frame_feats(img, prev)
        test.append(v)
    return train, test, notes


def probe_real_media_pixel_id(
    *,
    n_classes: int = 4,
    n_train: int = 6,
    n_test: int = 4,
    roots: Optional[Sequence[Path]] = None,
    seed: int = 7,
) -> MediaPixelIdReport:
    """
    Tutor-ablated media-entity ID from real pixels via retina cascade features.
    """
    notes: List[str] = [
        "Tutor-ablated: features from pixels only (no path/title/subtitle in vector).",
        "Class labels = source video identity for scoring only.",
    ]
    roots_list = list(roots) if roots is not None else media_roots_from_env()
    files = discover_media_files(roots_list, max_files=max(40, n_classes * 8), kind="video")
    if len(files) < 2:
        # Fallback synthetic path
        from .frontier_probes import probe_pixel_identity

        syn = probe_pixel_identity(
            n_classes=n_classes, n_train=n_train, n_test=n_test * 2, seed=seed
        )
        return MediaPixelIdReport(
            ok=bool(syn.get("above_chance")),
            pixel_id_top1=float(syn.get("pixel_id_top1") or 0),
            pixel_id_chance=float(syn.get("pixel_id_chance") or 0.25),
            n_characters=int(syn.get("n_characters") or n_classes),
            n_heldout_clips=int(syn.get("n_heldout_clips") or 0),
            tutor_ablated=True,
            synthetic=True,
            feature_mode=str(syn.get("feature_mode") or "synthetic_fallback"),
            above_chance=bool(syn.get("above_chance")),
            notes=notes + ["no media roots — synthetic fallback"],
        )

    # Stable shuffle by seed
    rng = np.random.default_rng(seed)
    order = list(range(len(files)))
    rng.shuffle(order)
    picked: List[Path] = []
    banks: List[Tuple[List[np.ndarray], List[np.ndarray]]] = []
    names: List[str] = []
    for idx in order:
        if len(picked) >= n_classes:
            break
        p = files[idx]
        tr, te, nts = sample_video_feature_bank(
            p, n_train=n_train, n_test=n_test, train_stride=10, test_stride=22
        )
        notes.extend(nts)
        if len(tr) >= max(2, n_train // 2) and len(te) >= 1:
            picked.append(p)
            banks.append((tr, te))
            names.append(p.stem[:48])

    if len(picked) < 2:
        notes.append("could not decode enough distinct videos")
        return MediaPixelIdReport(
            ok=False,
            pixel_id_top1=0.0,
            pixel_id_chance=0.5,
            n_characters=len(picked),
            n_heldout_clips=0,
            tutor_ablated=True,
            synthetic=False,
            feature_mode="retina_real_media",
            above_chance=False,
            notes=notes,
        )

    # Prototypes: global mean + early/late sub-means (multi-view RF cascade)
    # Score = max cosine over a class's prototype set
    class_protos: List[List[np.ndarray]] = []
    for tr, _te in banks:
        stack = np.stack(tr, axis=0)
        protos_c = [_l2_normalize(stack.mean(axis=0))]
        if len(stack) >= 4:
            mid = len(stack) // 2
            protos_c.append(_l2_normalize(stack[:mid].mean(axis=0)))
            protos_c.append(_l2_normalize(stack[mid:].mean(axis=0)))
        class_protos.append(protos_c)

    correct = 0
    total = 0
    per: Dict[str, List[int]] = {n: [0, 0] for n in names}
    for c, (_tr, te) in enumerate(banks):
        for x in te:
            best_sims = []
            for protos_c in class_protos:
                best_sims.append(max(float(p @ x) for p in protos_c))
            pred = int(np.argmax(best_sims))
            correct += int(pred == c)
            total += 1
            per[names[c]][1] += 1
            per[names[c]][0] += int(pred == c)

    top1 = correct / max(1, total)
    chance = 1.0 / len(picked)
    per_top = {
        k: (v[0] / max(1, v[1])) for k, v in per.items()
    }
    above = top1 > chance + (1.0 / SEEDS.phi) * 0.05  # mild margin
    notes.append(
        f"entities={len(picked)} top1={top1:.3f} chance={chance:.3f} "
        f"train={n_train}/test={n_test} temporal split"
    )
    return MediaPixelIdReport(
        ok=above,
        pixel_id_top1=float(top1),
        pixel_id_chance=float(chance),
        n_characters=len(picked),
        n_heldout_clips=total,
        tutor_ablated=True,
        synthetic=False,
        feature_mode="retina_real_media_rf_cascade",
        above_chance=above,
        names=names,
        paths=[str(p) for p in picked],
        per_class_top1=per_top,
        notes=notes,
    )
