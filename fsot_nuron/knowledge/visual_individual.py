"""
Visual individual identity — look first, name second.

Doctrine (see docs/VISUAL_INDIVIDUAL_IDENTITY.md):
  1. Cluster RF features into Visual Identity Units (VIUs) without names.
  2. Bind caption name tokens to the *active VIU* at co-occurrence time.
  3. Query with pixels alone → nearest VIU (tutor-ablated).
     Names are labels on individuals; the same string can label many VIUs.

This replaces name-bag prototypes as the primary identity model.
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
    iter_video_frames_span,
    sample_frames_at_times,
    _rgb_to_features,
)
from ..knowledge.subtitles import load_subtitles, captions_near
from ..knowledge.vision_caption_bind import tokenize_caption, _STOP


def _l2(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v) + 1e-12)
    return (v / n).astype(np.float32)


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(_l2(a) @ _l2(b))


@dataclass
class VisualIndividual:
    """One appearance-based individual (not a name string)."""

    viu_id: str
    n_samples: int = 0
    feat_sum: Optional[List[float]] = None
    samples: List[List[float]] = field(default_factory=list)
    # name → co-occurrence count (labels, not identity keys)
    name_counts: Dict[str, int] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    times: List[float] = field(default_factory=list)

    def add(
        self,
        feat: np.ndarray,
        *,
        names: Optional[Sequence[str]] = None,
        source: str = "",
        t_sec: float = 0.0,
    ) -> None:
        v = feat.astype(np.float64).ravel()
        if self.feat_sum is None:
            self.feat_sum = v.tolist()
        else:
            s = np.asarray(self.feat_sum, dtype=np.float64)
            if s.shape != v.shape:
                return
            self.feat_sum = (s + v).tolist()
        self.n_samples += 1
        if len(self.samples) < 32:
            self.samples.append(_l2(v.astype(np.float32)).tolist())
        for n in names or []:
            n = n.strip().lower()
            if len(n) < 3 or n in _STOP:
                continue
            self.name_counts[n] = self.name_counts.get(n, 0) + 1
        if source and source not in self.sources:
            self.sources.append(source)
        if len(self.times) < 48:
            self.times.append(float(t_sec))

    def prototype(self) -> Optional[np.ndarray]:
        if not self.feat_sum or self.n_samples <= 0:
            return None
        m = np.asarray(self.feat_sum, dtype=np.float32) / float(self.n_samples)
        return _l2(m)

    def primary_name(self) -> Optional[str]:
        if not self.name_counts:
            return None
        return max(self.name_counts.items(), key=lambda kv: kv[1])[0]

    def name_purity(self) -> float:
        """Fraction of name mass on the top name (1 = unique label)."""
        if not self.name_counts:
            return 0.0
        tot = sum(self.name_counts.values())
        top = max(self.name_counts.values())
        return float(top / max(1, tot))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "viu_id": self.viu_id,
            "n_samples": self.n_samples,
            "name_counts": dict(self.name_counts),
            "primary_name": self.primary_name(),
            "name_purity": self.name_purity(),
            "sources": self.sources[:6],
            "proto": (self.prototype().tolist() if self.prototype() is not None else None),
        }


class VisualIndividualStore:
    """
    Online appearance clustering with optional name binding.
    Threshold from seeds (φ-scaled), not free-fit.
    """

    def __init__(self, *, sim_threshold: Optional[float] = None):
        # Higher threshold → more individuals (finer individuation).
        # Global RF features are highly correlated within a film (grade/lighting);
        # a low threshold collapses everyone into one VIU (trivial re-ID).
        # Use tight match: ~0.88–0.92 so only near-duplicate looks merge.
        self.sim_threshold = float(
            sim_threshold
            if sim_threshold is not None
            else (0.82 + 0.08 * (SEEDS.phi / (1.0 + SEEDS.phi)))  # ~0.87
        )
        self.individuals: List[VisualIndividual] = []
        self._next_id = 0

    def _new_id(self) -> str:
        self._next_id += 1
        return f"VIU_{self._next_id:04d}"

    def observe(
        self,
        feat: np.ndarray,
        *,
        names: Optional[Sequence[str]] = None,
        source: str = "",
        t_sec: float = 0.0,
    ) -> str:
        x = _l2(np.asarray(feat, dtype=np.float32))
        best_i = -1
        best_s = -1.0
        for i, ind in enumerate(self.individuals):
            p = ind.prototype()
            if p is None:
                continue
            s = _cos(x, p)
            if s > best_s:
                best_s = s
                best_i = i
        if best_i >= 0 and best_s >= self.sim_threshold:
            self.individuals[best_i].add(x, names=names, source=source, t_sec=t_sec)
            return self.individuals[best_i].viu_id
        # new individual
        ind = VisualIndividual(viu_id=self._new_id())
        ind.add(x, names=names, source=source, t_sec=t_sec)
        self.individuals.append(ind)
        return ind.viu_id

    def query(self, feat: np.ndarray) -> Tuple[Optional[str], float, Optional[str]]:
        """Return (viu_id, similarity, primary_name). Tutor-ablated: feat only."""
        x = _l2(np.asarray(feat, dtype=np.float32))
        best_id = None
        best_s = -1.0
        best_name = None
        for ind in self.individuals:
            p = ind.prototype()
            if p is None or ind.n_samples < 2:
                continue
            s = _cos(x, p)
            if s > best_s:
                best_s = s
                best_id = ind.viu_id
                best_name = ind.primary_name()
        return best_id, float(best_s), best_name

    def stats(self) -> Dict[str, Any]:
        named = [i for i in self.individuals if i.name_counts]
        pure = [i for i in named if i.name_purity() >= 0.7]
        return {
            "n_viu": len(self.individuals),
            "n_named_viu": len(named),
            "n_pure_name_viu": len(pure),
            "sim_threshold": self.sim_threshold,
            "mean_samples": float(
                np.mean([i.n_samples for i in self.individuals])
                if self.individuals
                else 0
            ),
        }


@dataclass
class VisualIndividualReport:
    ok: bool
    n_viu: int
    n_named_viu: int
    # Primary human-like metric: held-out frames re-identify same VIU
    viu_reid_top1: float
    viu_reid_chance: float
    n_heldout: int
    # Secondary: when VIU has unique name, does name match co-train label?
    unique_name_top1: float
    n_unique_name_trials: int
    tutor_ablated: bool
    notes: List[str] = field(default_factory=list)
    store_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def ingest_video_individuals(
    path: Path,
    store: VisualIndividualStore,
    *,
    max_frames: int = 36,
    use_captions: bool = True,
) -> Dict[str, Any]:
    """
    Span film: each frame updates VIUs; captions bind names to the active VIU.
    """
    cues = load_subtitles(path) if use_captions else []
    win = float(SEEDS.phi + 1.0 / SEEDS.e)
    n_frames = 0
    n_binds = 0
    # Collect (feat, t, names) then second pass for held-out re-ID
    records: List[Tuple[np.ndarray, float, List[str], str]] = []
    prev = None

    if cues:
        # Sample at caption times for denser name bind + span
        step = max(1, len(cues) // max(1, max_frames))
        chosen = list(cues[::step][:max_frames])
        times = [float(c.mid_s()) for c in chosen]
        pairs = sample_frames_at_times(path, times, max_side=72, tol_s=2.0)
        for i, (img, t_sec) in enumerate(pairs):
            feats, prev, _ = _rgb_to_features(img, prev)
            v = _l2(np.asarray(feats, dtype=np.float32))
            n_frames += 1
            names: List[str] = []
            near = captions_near(cues, float(t_sec), window_s=win)
            if not near and i < len(chosen):
                near = [chosen[i]]
            if near:
                line = " ".join(c.text for c in near)
                names = tokenize_caption(line, path_hint="", character_bias=True)[:6]
                if names:
                    n_binds += 1
            records.append((v, float(t_sec), names, path.name))
    else:
        for img, t_sec in iter_video_frames_span(path, max_frames=max_frames, max_side=72):
            feats, prev, _ = _rgb_to_features(img, prev)
            v = _l2(np.asarray(feats, dtype=np.float32))
            n_frames += 1
            records.append((v, float(t_sec), [], path.name))

    # Temporal train/test split for re-ID (first 65% train, rest test)
    if not records:
        return {"n_frames": 0, "n_binds": 0, "heldout": []}

    cut = max(2, int(0.65 * len(records)))
    train_recs = records[:cut]
    test_recs = records[cut:]

    # Train: form VIUs; remember each train sample's assigned VIU
    train_labeled: List[Tuple[np.ndarray, str]] = []
    for v, t, names, src in train_recs:
        vid = store.observe(
            v, names=names if use_captions else None, source=src, t_sec=t
        )
        train_labeled.append((v, vid))

    def _nearest_train_viu(x: np.ndarray) -> Optional[str]:
        """Ground truth: which train observation is this test frame most like?"""
        if not train_labeled:
            return None
        best_id = None
        best_s = -1.0
        for tv, tid in train_labeled:
            s = _cos(x, tv)
            if s > best_s:
                best_s = s
                best_id = tid
        # only score if test is close enough to some train individual
        if best_s < 0.45:
            return None
        return best_id

    # Held-out: true VIU from nearest train look; pred from store.query
    heldout: List[Tuple[np.ndarray, str, Optional[str]]] = []
    for v, t, names, src in test_recs:
        true_id = _nearest_train_viu(v)
        if true_id is None:
            continue
        pname = names[0] if names else None
        heldout.append((v, true_id, pname))

    return {
        "n_frames": n_frames,
        "n_binds": n_binds,
        "n_train": len(train_recs),
        "n_test": len(test_recs),
        "heldout": heldout,
        "path": str(path),
    }


def run_visual_individual_probe(
    *,
    max_videos: int = 6,
    max_frames: int = 28,
    roots: Optional[Sequence[Path]] = None,
    seed: int = 7,
) -> VisualIndividualReport:
    """
    Multi-film VIU formation + held-out visual re-identification.
    Primary metric: viu_reid_top1 (not global name-bag accuracy).
    """
    notes: List[str] = [
        "Identity unit = visual individual (VIU), not the name string.",
        "Names bind to VIUs by co-occurrence; same name may label many VIUs.",
        "Tutor-ablated query: pixels → nearest VIU.",
    ]
    roots_list = list(roots) if roots is not None else media_roots_from_env()
    files = discover_media_files(roots_list, max_files=180, kind="video")
    captioned = [p for p in files if load_subtitles(p)]
    rng = np.random.default_rng(seed)
    # Prefer diverse franchise titles
    def pri(p: Path) -> int:
        n = p.name.lower()
        s = 0
        for k, w in (
            ("matrix", 5),
            ("terminator", 5),
            ("resident", 5),
            ("jurassic", 4),
            ("brave", 3),
            ("chucky", 3),
        ):
            if k in n:
                s = max(s, w)
        return s

    pool = sorted(captioned or files, key=lambda p: (-pri(p), p.name))
    if not pool:
        return VisualIndividualReport(
            ok=False,
            n_viu=0,
            n_named_viu=0,
            viu_reid_top1=0.0,
            viu_reid_chance=0.0,
            n_heldout=0,
            unique_name_top1=0.0,
            n_unique_name_trials=0,
            tutor_ablated=True,
            notes=notes + ["no media"],
        )

    # One store per film (individuals are local to a viewing session / episode)
    # Aggregate re-ID rates across films
    reid_hits = 0
    reid_tot = 0
    name_hits = 0
    name_tot = 0
    n_viu_total = 0
    n_named = 0
    all_held: List[Tuple[np.ndarray, str, Optional[str], VisualIndividualStore]] = []

    pick = pool[:max_videos]
    notes.append(f"films={[p.name[:40] for p in pick]}")

    for vp in pick:
        store = VisualIndividualStore()
        try:
            stats = ingest_video_individuals(
                vp, store, max_frames=max_frames, use_captions=True
            )
        except Exception as e:
            notes.append(f"skip {vp.name}: {e}")
            continue
        n_viu_total += len(store.individuals)
        n_named += sum(1 for i in store.individuals if i.name_counts)
        notes.append(
            f"{vp.name[:40]}: frames={stats.get('n_frames')} binds={stats.get('n_binds')} "
            f"viu={len(store.individuals)} held={len(stats.get('heldout') or [])}"
        )
        for v, true_id, pname in stats.get("heldout") or []:
            all_held.append((v, true_id, pname, store))

    # Evaluate held-out
    for v, true_id, pname, store in all_held:
        pred_id, sim, pred_name = store.query(v)
        reid_tot += 1
        if pred_id == true_id:
            reid_hits += 1
        # secondary: unique-name VIUs only
        ind = next((i for i in store.individuals if i.viu_id == true_id), None)
        if ind and ind.primary_name() and ind.name_purity() >= 0.75:
            name_tot += 1
            if pred_name == ind.primary_name():
                name_hits += 1

    # Chance for re-ID ≈ 1 / mean n_viu per film (rough)
    mean_viu = n_viu_total / max(1, len(pick))
    chance = 1.0 / max(1.0, mean_viu)
    reid = reid_hits / max(1, reid_tot)
    uname = name_hits / max(1, name_tot) if name_tot else 0.0

    ok = reid_tot >= 8 and reid > chance + 0.05
    notes.append(
        f"viu_reid={reid:.3f} chance≈{chance:.3f} unique_name={uname:.3f} "
        f"trials_name={name_tot} heldout={reid_tot}"
    )
    notes.append(
        "Primary success = re-identify the same visual individual, "
        "not bag-average all people who share a string name."
    )

    # persist store snapshot (last film only for size; full stats in report)
    out_path = ARTIFACTS / "visual_individuals_last.json"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    blob = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "doctrine": "docs/VISUAL_INDIVIDUAL_IDENTITY.md",
        "n_viu_total": n_viu_total,
        "n_named": n_named,
        "viu_reid_top1": reid,
        "unique_name_top1": uname,
        "notes": notes,
    }
    out_path.write_text(json.dumps(blob, indent=2), encoding="utf-8")

    rep = VisualIndividualReport(
        ok=ok,
        n_viu=n_viu_total,
        n_named_viu=n_named,
        viu_reid_top1=float(reid),
        viu_reid_chance=float(chance),
        n_heldout=reid_tot,
        unique_name_top1=float(uname),
        n_unique_name_trials=name_tot,
        tutor_ablated=True,
        notes=notes,
        store_path=str(out_path),
    )
    md = DATA / "results" / "VISUAL_INDIVIDUAL.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Visual individual identity",
        "",
        f"OK: **{rep.ok}**  tutor_ablated=**{rep.tutor_ablated}**",
        "",
        f"- **VIU re-ID top1=** {rep.viu_reid_top1:.3f} (chance≈{rep.viu_reid_chance:.3f})",
        f"- unique-name top1=**{rep.unique_name_top1:.3f}** (trials={rep.n_unique_name_trials})",
        f"- n_viu=**{rep.n_viu}** named=**{rep.n_named_viu}** heldout=**{rep.n_heldout}**",
        "",
        "Primary metric is visual re-identification of **individuals**, not global name bags.",
        "",
        "## Notes",
        "",
    ]
    for n in notes:
        lines.append(f"- {n}")
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")
    return rep
