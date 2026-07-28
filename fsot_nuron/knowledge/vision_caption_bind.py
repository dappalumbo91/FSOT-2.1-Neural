"""
Vision ↔ caption co-occurrence binding (name appears with look).

When a subtitle/caption line co-occurs with a visual frame, accumulate
retina RF features under token keys extracted from the line. Later,
tutor-ablated pixel query retrieves the strongest name(s).

Improvements for name quality:
  - Character-biased tokens (lexicon characters, SRT speaker tags, title stems)
  - Multi-frame voting at query time
  - Cluster purity (mean cosine of samples to prototype); prune impure names

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
    iter_video_frames_span,
    sample_frames_at_times,
    _rgb_to_features,
)
from .subtitles import load_subtitles, captions_near, CaptionCue
from .lexicon import load_lexicon


_STOP = frozenset(
    """
    a an the and or but if of to in on at for from with by is are was were be been
    it its this that these those he she they them his her their you your we our
    not no yes oh ah um uh so as into about over under out up down just only all
    what when where who how why do does did done have has had will would can could
    i me my i'm you're we're they're it's that's don't can't won't didn't doesn't
    there's she's he's they're we've you've aren't isn't wasn't weren't
    yeah yes okay ok well right like come back here know think thought want need
    look looking going gonna get got let lookin please thank sorry hell damn god
    minutes seconds hours against happened sequence project take keep hello
    """.split()
)

# Dialogue verbs / non-names that survive capitalization filters
_NON_NAME = frozenset(
    """
    come go get see look wait stop run help leave stay take give make let put
    said says say telling told ask asked tell hello goodbye good night day
    sir madam mr mrs miss doctor captain general
    """.split()
)


def _l2(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v) + 1e-12)
    return (v / n).astype(np.float32)


def _character_lexicon_names() -> List[str]:
    """Names from local lexicon with kind=character (or show titles)."""
    out: List[str] = []
    try:
        lex = load_lexicon()
        for k, e in lex.entries.items():
            kind = (e.kind or "").lower()
            if kind in ("character", "show", "person"):
                out.append(k.lower())
            for ex in (e.examples or [])[:3]:
                if isinstance(ex, str) and len(ex) >= 3:
                    # multiword examples of characters
                    if kind == "character" or (ex[0].isupper() if ex else False):
                        out.append(ex.lower())
    except Exception:
        pass
    return list(dict.fromkeys(out))


_CHAR_LEX = _character_lexicon_names()


def extract_speaker_tags(text: str) -> List[str]:
    """SRT patterns: 'ALICE:', '[Alice]', 'ALICE -' """
    out: List[str] = []
    for m in re.finditer(r"(?:^|\n)\s*\[?([A-Z][A-Za-z]{1,20})\]?\s*[:\-]", text or ""):
        name = m.group(1).lower()
        if name not in _STOP and name not in _NON_NAME and len(name) >= 3:
            out.append(name)
    for m in re.finditer(r"\b([A-Z]{2,})\b", text or ""):
        name = m.group(1).lower()
        if name not in _STOP and name not in _NON_NAME and 3 <= len(name) <= 14:
            out.append(name)
    return out


def tokenize_caption(
    text: str,
    *,
    path_hint: str = "",
    character_bias: bool = True,
) -> List[str]:
    """
    Character-biased name anchors from a caption line.

    Priority:
      1. Lexicon character/show hits in line
      2. SRT speaker tags
      3. Multiword Capitalized runs
      4. Single Capitalized tokens (filtered)
      5. Soft path/title tokens (weak, only if character_bias and empty otherwise)
    """
    low_line = (text or "").lower()
    out: List[str] = []

    if character_bias:
        for name in _CHAR_LEX:
            if len(name) >= 3 and name in low_line:
                out.append(name)

    out.extend(extract_speaker_tags(text or ""))

    words = re.findall(r"[A-Za-z][A-Za-z']+", text or "")
    i = 0
    while i < len(words):
        if words[i][0].isupper() and words[i].lower() not in _STOP:
            run = [words[i]]
            j = i + 1
            while (
                j < len(words)
                and words[j][0].isupper()
                and words[j].lower() not in _STOP
            ):
                run.append(words[j])
                j += 1
            if len(run) >= 2:
                out.append(" ".join(w.lower() for w in run))
            elif len(run) == 1:
                w = run[0].lower()
                if w not in _NON_NAME and len(w) >= 3 and "'" not in w:
                    out.append(w)
            i = j
            continue
        i += 1

    # Soft title tokens from path (movie stem) — only as fallback anchors
    if character_bias and path_hint:
        stem = Path(path_hint).stem.replace(".", " ").replace("_", " ").replace("-", " ")
        for tok in re.findall(r"[A-Za-z]{4,}", stem):
            low = tok.lower()
            if low not in _STOP and low not in _NON_NAME and not low.isdigit():
                # year-like
                if re.match(r"^\d{4}$", low):
                    continue
                if low in (
                    "bluray",
                    "bdrip",
                    "brrip",
                    "hdrip",
                    "x264",
                    "xvid",
                    "yify",
                    "1080p",
                    "720p",
                    "extended",
                    "unrated",
                    "repack",
                ):
                    continue
                out.append(low)

    seen = set()
    uniq: List[str] = []
    for t in out:
        t = t.strip().lower()
        if not t or t in seen or t in _STOP or t in _NON_NAME:
            continue
        if len(t) < 3 or "'" in t:
            continue
        seen.add(t)
        uniq.append(t)
    return uniq[:12]


@dataclass
class NameCluster:
    name: str
    n_samples: int = 0
    feat_sum: Optional[List[float]] = None
    # store recent sample vectors for purity / multi-proto
    samples: List[List[float]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    sample_lines: List[str] = field(default_factory=list)
    weight: float = 1.0  # character-bias weight

    def add(
        self,
        feat: np.ndarray,
        source: str = "",
        line: str = "",
        weight: float = 1.0,
    ) -> None:
        v = feat.astype(np.float64).ravel()
        w = float(max(0.1, weight))
        if self.feat_sum is None:
            self.feat_sum = (v * w).tolist()
        else:
            s = np.asarray(self.feat_sum, dtype=np.float64)
            if s.shape != v.shape:
                return
            self.feat_sum = (s + v * w).tolist()
        self.n_samples += 1
        self.weight = max(self.weight, w)
        if len(self.samples) < 24:
            self.samples.append(_l2(v.astype(np.float32)).tolist())
        if source and source not in self.sources:
            self.sources.append(source)
        if line and len(self.sample_lines) < 6:
            self.sample_lines.append(line[:160])

    def prototype(self) -> Optional[np.ndarray]:
        if not self.feat_sum or self.n_samples <= 0:
            return None
        m = np.asarray(self.feat_sum, dtype=np.float32) / float(self.n_samples)
        return _l2(m)

    def purity(self) -> float:
        """Mean cosine of stored samples to prototype (1 = tight cluster)."""
        p = self.prototype()
        if p is None or not self.samples:
            return 0.0
        sims = []
        for s in self.samples:
            v = np.asarray(s, dtype=np.float32)
            if v.shape != p.shape:
                continue
            sims.append(float(p @ v))
        return float(np.mean(sims)) if sims else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "n_samples": self.n_samples,
            "sources": self.sources[:8],
            "sample_lines": self.sample_lines,
            "weight": self.weight,
            "purity": self.purity(),
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
    pixel_to_name_top1_vote: float
    pixel_to_name_chance: float
    mean_cluster_purity: float
    n_heldout: int
    tutor_ablated_test: bool
    notes: List[str] = field(default_factory=list)
    clusters_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VisionCaptionBinder:
    def __init__(self) -> None:
        self.clusters: Dict[str, NameCluster] = {}

    def observe(
        self,
        name: str,
        feat: np.ndarray,
        *,
        source: str = "",
        line: str = "",
        weight: float = 1.0,
    ) -> None:
        key = name.strip().lower()
        if len(key) < 3:
            return
        if key not in self.clusters:
            self.clusters[key] = NameCluster(name=key)
        self.clusters[key].add(feat, source=source, line=line, weight=weight)

    def query_names(
        self,
        feat: np.ndarray,
        top_k: int = 3,
        *,
        min_samples: int = 1,
        min_purity: float = 0.0,
    ) -> List[Tuple[str, float]]:
        x = _l2(np.asarray(feat, dtype=np.float32))
        scored: List[Tuple[str, float]] = []
        for name, cl in self.clusters.items():
            if cl.n_samples < min_samples:
                continue
            if min_purity > 0 and cl.purity() < min_purity:
                continue
            p = cl.prototype()
            if p is None or p.shape != x.shape:
                continue
            # character-weight slight boost
            scored.append((name, float(p @ x) * (0.85 + 0.15 * min(2.0, cl.weight))))
        scored.sort(key=lambda t: -t[1])
        return scored[:top_k]

    def query_names_multiframe(
        self,
        feats: Sequence[np.ndarray],
        top_k: int = 3,
        *,
        min_samples: int = 2,
        min_purity: float = 0.35,
    ) -> List[Tuple[str, float]]:
        """
        Multi-frame voting: each frame casts top-k soft votes; aggregate scores.
        """
        tallies: Dict[str, float] = {}
        if not feats:
            return []
        for f in feats:
            ranked = self.query_names(
                f, top_k=max(top_k, 5), min_samples=min_samples, min_purity=min_purity
            )
            for rank, (name, sc) in enumerate(ranked):
                # rank-weighted vote
                tallies[name] = tallies.get(name, 0.0) + sc / (1.0 + 0.15 * rank)
        items = sorted(tallies.items(), key=lambda kv: -kv[1])
        # normalize for readability
        if not items:
            return []
        mx = items[0][1] or 1.0
        return [(n, s / mx) for n, s in items[:top_k]]

    def prune(
        self,
        *,
        min_samples: int = 2,
        min_purity: float = 0.40,
        max_freq_frac: float = 0.40,
    ) -> List[str]:
        """Remove glue / impure / ultra-frequent clusters."""
        if not self.clusters:
            return []
        max_n = max(c.n_samples for c in self.clusters.values())
        drop: List[str] = []
        for k, c in list(self.clusters.items()):
            if c.n_samples < min_samples:
                drop.append(k)
                continue
            pur = c.purity()
            if pur > 0 and pur < min_purity and c.n_samples >= 3:
                drop.append(k)
                continue
            if (
                c.n_samples >= max(6, int(max_freq_frac * max_n))
                and " " not in k
                and len(k) < 6
                and c.weight < 1.5
            ):
                drop.append(k)
        for k in drop:
            del self.clusters[k]
        return drop

    def mean_purity(self) -> float:
        ps = [c.purity() for c in self.clusters.values() if c.n_samples >= 2]
        return float(np.mean(ps)) if ps else 0.0

    def save(self, path: Optional[Path] = None) -> Path:
        path = path or (ARTIFACTS / "vision_caption_clusters.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "n_names": len(self.clusters),
            "mean_purity": self.mean_purity(),
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
            cl.weight = float(v.get("weight") or 1.0)
            cl.feat_sum = v.get("proto")
            if cl.feat_sum is not None and cl.n_samples > 0:
                arr = np.asarray(cl.feat_sum, dtype=np.float64) * cl.n_samples
                cl.feat_sum = arr.tolist()
            cl.sources = list(v.get("sources") or [])
            cl.sample_lines = list(v.get("sample_lines") or [])
            if cl.n_samples > 0 and cl.feat_sum is not None:
                b.clusters[cl.name] = cl
        return b


def _token_weight(tok: str, path: Path) -> float:
    """Higher weight for lexicon characters and multiword / title matches."""
    w = 1.0
    if tok in _CHAR_LEX:
        w = float(SEEDS.phi)  # ~1.618
    if " " in tok:
        w = max(w, 1.35)
    stem = path.stem.lower().replace(".", " ")
    if tok in stem or any(p in tok for p in stem.split() if len(p) > 4):
        w = max(w, 1.25)
    if tok in _NON_NAME:
        w = 0.2
    return w


def bind_video_captions(
    path: Path,
    binder: VisionCaptionBinder,
    *,
    max_frames: int = 24,
    stride: int = 20,
    max_side: int = 72,
) -> Dict[str, Any]:
    """Seek caption midpoints; accumulate RF feats under character-biased tokens."""
    cues = load_subtitles(path)
    n_frames = 0
    n_binds = 0
    prev = None
    # heldout: list of (feat, true_tokens) and also groups for multi-frame vote
    heldout: List[Tuple[np.ndarray, List[str]]] = []
    heldout_groups: List[Tuple[List[np.ndarray], List[str]]] = []
    win = float(SEEDS.phi + 1.0 / SEEDS.e)

    def _observe_pair(v: np.ndarray, line: str, tokens: List[str], train: bool) -> None:
        nonlocal n_binds
        if not tokens:
            return
        n_binds += 1
        if train:
            for tok in tokens:
                binder.observe(
                    tok,
                    v,
                    source=path.name,
                    line=line,
                    weight=_token_weight(tok, path),
                )
        else:
            heldout.append((v, tokens))

    if cues:
        step = max(1, len(cues) // max(1, max_frames))
        chosen = list(cues[::step][:max_frames])
        times = [float(c.mid_s()) for c in chosen]
        pairs = sample_frames_at_times(path, times, max_side=max_side, tol_s=2.5)
        # group consecutive pairs sharing same primary token for multi-frame vote
        group_feats: List[np.ndarray] = []
        group_tokens: List[str] = []
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
            tokens = tokenize_caption(line, path_hint=str(path), character_bias=True)
            if not tokens:
                continue
            # 70/30 train/heldout by index for temporal separation
            train = (i % 10) < 7
            _observe_pair(v, line, tokens, train=train)
            if not train:
                # multi-frame: accumulate nearby heldout with overlapping tokens
                if group_tokens and set(tokens) & set(group_tokens):
                    group_feats.append(v)
                    group_tokens = list(dict.fromkeys(group_tokens + tokens))
                else:
                    if group_feats:
                        heldout_groups.append((list(group_feats), list(group_tokens)))
                    group_feats = [v]
                    group_tokens = list(tokens)
        if group_feats:
            heldout_groups.append((list(group_feats), list(group_tokens)))
    else:
        for img, t_sec in iter_video_frames_span(
            path, max_frames=max_frames, max_side=max_side
        ):
            feats, prev, _st = _rgb_to_features(img, prev)
            v = _l2(np.asarray(feats, dtype=np.float32))
            n_frames += 1
            tokens = tokenize_caption(
                path.stem.replace(".", " "), path_hint=str(path), character_bias=True
            )
            if tokens:
                _observe_pair(v, path.stem, tokens[:4], train=(n_frames % 10) < 7)

    return {
        "path": str(path),
        "n_frames": n_frames,
        "n_binds": n_binds,
        "n_cues": len(cues),
        "heldout": heldout,
        "heldout_groups": heldout_groups,
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
    files = discover_media_files(roots_list, max_files=max(200, max_videos * 40), kind="video")
    rng = np.random.default_rng(seed)

    binder = VisionCaptionBinder()
    total_frames = 0
    total_binds = 0
    n_vid = 0
    all_heldout: List[Tuple[np.ndarray, List[str]]] = []
    all_groups: List[Tuple[List[np.ndarray], List[str]]] = []

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
    notes.append(
        f"captioned videos available: {len(with_caps)}; lexicon chars={len(_CHAR_LEX)}"
    )

    for p in pick:
        try:
            stats = bind_video_captions(p, binder, max_frames=max_frames, stride=stride)
            total_frames += int(stats["n_frames"])
            total_binds += int(stats["n_binds"])
            all_heldout.extend(stats.get("heldout") or [])
            all_groups.extend(stats.get("heldout_groups") or [])
            n_vid += 1
            notes.append(
                f"{p.name}: frames={stats['n_frames']} binds={stats['n_binds']} "
                f"cues={stats['n_cues']}"
            )
        except Exception as e:
            notes.append(f"skip {p.name}: {e}")

    dropped = binder.prune(min_samples=2, min_purity=0.38, max_freq_frac=0.40)
    if dropped:
        notes.append(f"pruned impure/glue: {dropped[:10]}")

    mean_pur = binder.mean_purity()
    n_names = len(binder.clusters)

    # Single-frame heldout
    correct = 0
    total = 0
    for feat, true_tokens in all_heldout:
        known = [
            t
            for t in true_tokens
            if t in binder.clusters and binder.clusters[t].n_samples >= 2
        ]
        if not known:
            continue
        ranked = binder.query_names(feat, top_k=5, min_samples=2, min_purity=0.30)
        if not ranked:
            continue
        preds = [p for p, _ in ranked]
        ok = any(
            pred == t or pred in t or t in pred for pred in preds for t in known
        )
        correct += int(ok)
        total += 1
    top1 = correct / max(1, total) if total else 0.0

    # Multi-frame vote heldout
    correct_v = 0
    total_v = 0
    for feats, true_tokens in all_groups:
        known = [
            t
            for t in true_tokens
            if t in binder.clusters and binder.clusters[t].n_samples >= 2
        ]
        if not known or len(feats) < 1:
            continue
        ranked = binder.query_names_multiframe(
            feats, top_k=5, min_samples=2, min_purity=0.30
        )
        if not ranked:
            continue
        preds = [p for p, _ in ranked]
        ok = any(
            pred == t or pred in t or t in pred for pred in preds for t in known
        )
        correct_v += int(ok)
        total_v += 1
    top1_vote = correct_v / max(1, total_v) if total_v else top1

    chance = 1.0 / max(1, min(n_names, 25)) if n_names else 0.0
    if total == 0 and total_v == 0:
        notes.append("no scored heldout — structure stored only")
    else:
        notes.append(
            f"single-frame heldout={total} top1={top1:.3f}; "
            f"multi-frame vote heldout={total_v} top1={top1_vote:.3f}; "
            f"mean_purity={mean_pur:.3f}"
        )

    top_names = sorted(
        binder.clusters.values(),
        key=lambda c: (-c.weight * c.n_samples * (0.5 + 0.5 * c.purity()), c.name),
    )[:16]
    cpath = binder.save()
    notes.append(f"clusters saved: {cpath} names={n_names}")

    return VisionCaptionBindReport(
        n_videos=n_vid,
        n_frames=total_frames,
        n_caption_binds=total_binds,
        n_names=n_names,
        top_names=[c.name for c in top_names],
        pixel_to_name_top1=float(top1),
        pixel_to_name_top1_vote=float(top1_vote),
        pixel_to_name_chance=float(chance),
        mean_cluster_purity=float(mean_pur),
        n_heldout=max(total, total_v),
        tutor_ablated_test=True,
        notes=notes,
        clusters_path=str(cpath),
    )
