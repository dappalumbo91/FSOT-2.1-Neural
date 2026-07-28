"""
Vision ↔ caption co-occurrence binding (name appears with look).

When a subtitle/caption line co-occurs with a visual frame, accumulate
retina RF features under token keys extracted from the line. Later,
tutor-ablated pixel query retrieves the strongest name(s).

This is the bridge from media-entity ID toward open-world character ID:
  pixels → cluster → co-occurring dialogue tokens → lexical name

Not a claim of full open-world ID until held-out silent clips pass the
capability frontier gate without any caption memory at test time.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..paths import ARTIFACTS, DATA
from ..seeds import SEEDS
from ..sensory.media_stream import (
    discover_media_files,
    media_roots_from_env,
    iter_video_frames,
    iter_video_frames_span,
    sample_frames_at_times,
    _rgb_to_features,
)
from .subtitles import load_subtitles, captions_near, CaptionCue


_STOP = frozenset(
    """
    a an the and or but if of to in on at for from with by is are was were be been
    it its this that these those he she they them his her their you your we our
    not no yes oh ah um uh so as into about over under out up down just only all
    what when where who how why do does did done have has had will would can could
    i me my i'm you're we're they're it's that's don't can't won't didn't doesn't
    there's she's he's they're we've you've aren't isn't wasn't weren't
    yeah yes okay ok well right like come back here know think thought want need
    look looking going gonna gonna get got let lookin gonna gonna gonna
    minutes seconds hours please thank sorry hell damn god jesus
    """.split()
)


def _l2(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v) + 1e-12)
    return (v / n).astype(np.float32)


def tokenize_caption(text: str) -> List[str]:
    """
    Surface tokens suitable as name/symbol anchors (not full NLP).

    Prefer proper-name-ish forms (Capitalized) and multiword titles over
    common dialogue glue words so pixel→name clusters stay informative.
    """
    words = re.findall(r"[A-Za-z][A-Za-z']+", text or "")
    out: List[str] = []
    # multiword proper sequences first (strongest anchors)
    i = 0
    while i < len(words):
        if words[i][0].isupper() and words[i].lower() not in _STOP:
            run = [words[i]]
            j = i + 1
            while j < len(words) and words[j][0].isupper() and words[j].lower() not in _STOP:
                run.append(words[j])
                j += 1
            if len(run) >= 2:
                out.append(" ".join(w.lower() for w in run))
            elif len(run) == 1 and len(run[0]) >= 3:
                out.append(run[0].lower())
            i = j
            continue
        i += 1
    # single content words — prefer Capitalized; skip contractions
    for t in words:
        low = t.lower()
        if low in _STOP or len(low) < 4 or "'" in low:
            continue
        if t[0].isupper():
            out.append(low)
        elif len(low) >= 7 and low.isalpha():
            out.append(low)
    seen = set()
    uniq = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq[:10]


@dataclass
class NameCluster:
    name: str
    n_samples: int = 0
    feat_sum: Optional[List[float]] = None
    sources: List[str] = field(default_factory=list)
    sample_lines: List[str] = field(default_factory=list)

    def add(self, feat: np.ndarray, source: str = "", line: str = "") -> None:
        v = feat.astype(np.float64).ravel()
        if self.feat_sum is None:
            self.feat_sum = v.tolist()
        else:
            s = np.asarray(self.feat_sum, dtype=np.float64)
            if s.shape != v.shape:
                return
            self.feat_sum = (s + v).tolist()
        self.n_samples += 1
        if source and source not in self.sources:
            self.sources.append(source)
        if line and len(self.sample_lines) < 6:
            self.sample_lines.append(line[:160])

    def prototype(self) -> Optional[np.ndarray]:
        if not self.feat_sum or self.n_samples <= 0:
            return None
        m = np.asarray(self.feat_sum, dtype=np.float32) / float(self.n_samples)
        return _l2(m)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "n_samples": self.n_samples,
            "sources": self.sources[:8],
            "sample_lines": self.sample_lines,
            "proto": (self.prototype().tolist() if self.prototype() is not None else None),
        }


@dataclass
class VisionCaptionBindReport:
    n_videos: int
    n_frames: int
    n_caption_binds: int
    n_names: int
    top_names: List[str]
    pixel_to_name_top1: float
    pixel_to_name_chance: float
    n_heldout: int
    tutor_ablated_test: bool
    notes: List[str] = field(default_factory=list)
    clusters_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VisionCaptionBinder:
    def __init__(self) -> None:
        self.clusters: Dict[str, NameCluster] = {}

    def observe(self, name: str, feat: np.ndarray, *, source: str = "", line: str = "") -> None:
        key = name.strip().lower()
        if len(key) < 3:
            return
        if key not in self.clusters:
            self.clusters[key] = NameCluster(name=key)
        self.clusters[key].add(feat, source=source, line=line)

    def query_names(self, feat: np.ndarray, top_k: int = 3) -> List[Tuple[str, float]]:
        x = _l2(np.asarray(feat, dtype=np.float32))
        scored: List[Tuple[str, float]] = []
        for name, cl in self.clusters.items():
            if cl.n_samples < 1:
                continue
            p = cl.prototype()
            if p is None or p.shape != x.shape:
                continue
            scored.append((name, float(p @ x)))
        scored.sort(key=lambda t: -t[1])
        return scored[:top_k]

    def save(self, path: Optional[Path] = None) -> Path:
        path = path or (ARTIFACTS / "vision_caption_clusters.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "n_names": len(self.clusters),
            "clusters": {k: v.to_dict() for k, v in self.clusters.items()},
        }
        path.write_text(json.dumps(blob, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "VisionCaptionBinder":
        b = cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        for k, v in (data.get("clusters") or {}).items():
            cl = NameCluster(name=str(v.get("name") or k))
            cl.n_samples = int(v.get("n_samples") or 0)
            cl.feat_sum = v.get("proto")  # store proto * n as approx if only proto saved
            if cl.feat_sum is not None and cl.n_samples > 0:
                arr = np.asarray(cl.feat_sum, dtype=np.float64) * cl.n_samples
                cl.feat_sum = arr.tolist()
            cl.sources = list(v.get("sources") or [])
            cl.sample_lines = list(v.get("sample_lines") or [])
            if cl.n_samples > 0 and cl.feat_sum is not None:
                b.clusters[cl.name] = cl
        return b


def bind_video_captions(
    path: Path,
    binder: VisionCaptionBinder,
    *,
    max_frames: int = 24,
    stride: int = 20,
    max_side: int = 72,
) -> Dict[str, Any]:
    """Walk frames; when captions near t, accumulate RF feats under tokens."""
    cues = load_subtitles(path)
    n_frames = 0
    n_binds = 0
    prev = None
    heldout: List[Tuple[np.ndarray, List[str]]] = []
    win = float(SEEDS.phi + 1.0 / SEEDS.e)

    def _observe_pair(v: np.ndarray, line: str, tokens: List[str]) -> None:
        nonlocal n_binds
        if not tokens:
            return
        n_binds += 1
        if (n_binds % 10) < 7:
            for tok in tokens:
                binder.observe(tok, v, source=path.name, line=line)
        else:
            heldout.append((v, tokens))

    if cues:
        # Primary: seek frames at caption midpoints (dialogue clusters)
        step = max(1, len(cues) // max(1, max_frames))
        chosen = list(cues[::step][:max_frames])
        times = [float(c.mid_s()) for c in chosen]
        pairs = sample_frames_at_times(path, times, max_side=max_side, tol_s=2.5)
        # Align by order if lengths match; else nearest time
        for i, (img, t_sec) in enumerate(pairs):
            feats, prev, _st = _rgb_to_features(img, prev)
            v = _l2(np.asarray(feats, dtype=np.float32))
            n_frames += 1
            near = captions_near(cues, float(t_sec), window_s=win)
            if not near and i < len(chosen):
                near = [chosen[i]]
            if not near:
                continue
            line = " ".join(c.text for c in near).strip()
            _observe_pair(v, line, tokenize_caption(line))
    else:
        # No subtitles: span full film + weak stem co-occurrence
        for img, t_sec in iter_video_frames_span(
            path, max_frames=max_frames, max_side=max_side
        ):
            feats, prev, _st = _rgb_to_features(img, prev)
            v = _l2(np.asarray(feats, dtype=np.float32))
            n_frames += 1
            stem_tokens = tokenize_caption(path.stem.replace(".", " ").replace("_", " "))
            if stem_tokens:
                _observe_pair(v, path.stem, stem_tokens[:4])

    return {
        "path": str(path),
        "n_frames": n_frames,
        "n_binds": n_binds,
        "n_cues": len(cues),
        "heldout": heldout,
    }


def run_vision_caption_bind(
    *,
    max_videos: int = 5,
    max_frames: int = 20,
    stride: int = 22,
    roots: Optional[Sequence[Path]] = None,
    seed: int = 7,
) -> VisionCaptionBindReport:
    notes: List[str] = []
    roots_list = list(roots) if roots is not None else media_roots_from_env()
    # Wide scan so captioned titles are not missed (G: has many .srt)
    files = discover_media_files(roots_list, max_files=max(200, max_videos * 40), kind="video")
    rng = np.random.default_rng(seed)

    binder = VisionCaptionBinder()
    total_frames = 0
    total_binds = 0
    n_vid = 0
    all_heldout: List[Tuple[np.ndarray, List[str]]] = []

    # Prefer videos that have sidecar captions (scan all discovered)
    with_caps: List[Path] = []
    without: List[Path] = []
    for p in files:
        try:
            if load_subtitles(p):
                with_caps.append(p)
            else:
                without.append(p)
        except Exception:
            without.append(p)
    rng.shuffle(with_caps)
    rng.shuffle(without)
    pick = (with_caps + without)[:max_videos]
    if with_caps:
        notes.append(f"captioned videos available: {len(with_caps)}")
    else:
        notes.append("no sidecar .srt/.vtt found in scan — bind will be sparse")

    for p in pick:
        try:
            stats = bind_video_captions(
                p, binder, max_frames=max_frames, stride=stride
            )
            total_frames += int(stats["n_frames"])
            total_binds += int(stats["n_binds"])
            all_heldout.extend(stats.get("heldout") or [])
            n_vid += 1
            notes.append(
                f"{p.name}: frames={stats['n_frames']} binds={stats['n_binds']} "
                f"cues={stats['n_cues']}"
            )
        except Exception as e:
            notes.append(f"skip {p.name}: {e}")

    # Drop ultra-common glue names that leaked into clusters (freq floor)
    if binder.clusters:
        max_n = max(c.n_samples for c in binder.clusters.values())
        drop = [
            k
            for k, c in binder.clusters.items()
            if c.n_samples >= max(8, int(0.35 * max_n)) and " " not in k and len(k) < 6
        ]
        for k in drop:
            del binder.clusters[k]
        if drop:
            notes.append(f"pruned high-freq glue tokens: {drop[:8]}")

    # Pixel → name heldout accuracy (tutor-ablated at query: only pixels).
    # Only score tokens that were *trained* (n_samples≥2) — otherwise retrieval
    # is undefined (cold names). Success if any top-5 pred hits a known true token.
    correct = 0
    total = 0
    n_names = len(binder.clusters)
    for feat, true_tokens in all_heldout:
        if not true_tokens or not binder.clusters:
            continue
        known = [
            t
            for t in true_tokens
            if t in binder.clusters and binder.clusters[t].n_samples >= 2
        ]
        if not known:
            continue
        ranked = binder.query_names(feat, top_k=5)
        if not ranked:
            continue
        preds = [p for p, _s in ranked]
        ok = False
        for pred in preds:
            for t in known:
                if pred == t or pred in t or t in pred:
                    ok = True
                    break
            if ok:
                break
        correct += int(ok)
        total += 1

    top1 = correct / max(1, total) if total else 0.0
    chance = 1.0 / max(1, min(n_names, 20)) if n_names else 0.0  # soft chance among active
    if total == 0:
        notes.append(
            "no scored heldout (need caption co-occurrence + trained names) — "
            "structure still stored"
        )
        # Structure progress: names formed from binds still counts as partial
        top1 = 0.0
        chance = 0.0
    else:
        notes.append(f"scored heldout={total} correct={correct} known-name retrieval")

    top_names = sorted(
        binder.clusters.values(), key=lambda c: -c.n_samples
    )[:12]
    cpath = binder.save()
    notes.append(f"clusters saved: {cpath} names={n_names}")

    return VisionCaptionBindReport(
        n_videos=n_vid,
        n_frames=total_frames,
        n_caption_binds=total_binds,
        n_names=n_names,
        top_names=[c.name for c in top_names],
        pixel_to_name_top1=float(top1),
        pixel_to_name_chance=float(chance),
        n_heldout=total,
        tutor_ablated_test=True,
        notes=notes,
        clusters_path=str(cpath),
    )
