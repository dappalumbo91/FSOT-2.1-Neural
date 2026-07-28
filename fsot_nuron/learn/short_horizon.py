"""
Short-horizon learning accuracy — human-like “pick up material quickly.”

Pipeline (minutes-scale, not epoch training):
  1. Chew a few media snippets + docs through sensory → brain → episode memory
  2. Immediately recall by query (title / symbol / dialogue cue) without
     re-injecting path tutors into the answer scorer
  3. Optionally: encode media frame prototypes as learning_probe items

Goal metric: high top-1 / recall@k after a short encode window — the snowball
base for longer curriculum. Wet-lab gates remain separate (Allen rates).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..paths import ARTIFACTS, DATA, ROOT
from ..seeds import SEEDS
from ..archive_pin import pin_archive
from ..brain_architecture import (
    FSOTBrainDesign,
    BrainDesignConfig,
    BRAIN_PROFILES,
    DEFAULT_PROJECTIONS,
)
from ..knowledge.document_read import discover_documents, read_document
from ..knowledge.episode_memory import (
    EpisodeMemory,
    save_episode,
    retrieve_by_query,
    _eid,
)
from ..sensory.media_stream import (
    media_roots_from_env,
    discover_media_files,
    iter_video_frames,
    _rgb_to_features,
)
from ..sensory.bus import SensoryBus
from ..learning_memory import learning_probe
from ..scalpel_brain import build_scalpel_brain
from ..benchmarks.media_pixel_id import probe_real_media_pixel_id


@dataclass
class ShortHorizonReport:
    ok: bool
    encode_minutes_est: float
    n_docs: int
    n_media: int
    n_memory: int
    recall_top1: float
    recall_at_k: float
    recall_k: int
    pixel_id_top1: float
    pixel_id_synthetic: bool
    caption_bind_top1: float
    caption_bind_names: int
    caption_bind_pairs: int
    learning_probe_top1: float
    learning_probe_margin: float
    sme_theta: bool
    sme_gamma: bool
    wetlab_note: str
    notes: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    finished_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _score_recall(
    queries: Sequence[Tuple[str, str]],
    *,
    root: Optional[Path] = None,
    k: int = 3,
) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    queries: list of (query_text, expected_title_substring)
    top1 = fraction where best hit title matches expected
    recall@k = fraction where any of top-k matches
    """
    rows = []
    top1_hits = 0
    atk_hits = 0
    for q, expect in queries:
        hits = retrieve_by_query(q, root=root, top_k=k)
        titles = [h.title.lower() for h in hits]
        exp = expect.lower()
        ok1 = bool(titles) and exp in titles[0]
        okk = any(exp in t for t in titles)
        top1_hits += int(ok1)
        atk_hits += int(okk)
        rows.append(
            {
                "query": q,
                "expect": expect,
                "hit_titles": [h.title for h in hits[:k]],
                "top1": ok1,
                "recall_at_k": okk,
            }
        )
    n = max(1, len(queries))
    return top1_hits / n, atk_hits / n, rows


def run_short_horizon_learn(
    *,
    max_docs: int = 4,
    max_videos: int = 5,
    media_frames: int = 12,
    profile: str = "ai_efficient",
    device: str = "cpu",
    seed: int = 7,
    memory_root: Optional[Path] = None,
    run_pixel_id: bool = True,
    run_learning_probe: bool = True,
    run_caption_bind: bool = True,
) -> ShortHorizonReport:
    """
    Short encode → immediate test. Expanded window (more videos/frames) plus
    optional subtitle↔pixel co-occurrence binding. Still minutes-scale on CPU.
    """
    notes: List[str] = []
    started = datetime.now(timezone.utc)
    mem_root = memory_root or (ARTIFACTS / "episode_memory_short")
    mem_root.mkdir(parents=True, exist_ok=True)

    pin = pin_archive(write_snapshot=False)
    notes.append(f"pin={pin.connected} mode={getattr(pin, 'pin_mode', '')}")

    prof = BRAIN_PROFILES.get(profile, BRAIN_PROFILES["ai_efficient"])
    brain = FSOTBrainDesign(
        BrainDesignConfig(
            regions=list(prof["regions"]),
            projections=list(DEFAULT_PROJECTIONS),
            seed=seed,
            device=device,
            dt_ms=0.5,
        )
    )

    queries: List[Tuple[str, str]] = []
    n_docs = 0
    n_media = 0
    n_mem = 0

    # --- Documents (always available in-repo) ---
    docs = discover_documents(None, max_files=max_docs * 4)
    def dscore(p: Path) -> int:
        low = str(p).lower()
        s = 0
        if "literature" in low or "thesis" in low:
            s += 10
        if p.suffix.lower() in (".md", ".txt"):
            s += 5
        if "shakespeare" in low:
            s += 4
        if p.suffix.lower() == ".py":
            s -= 20
        return s

    docs = sorted(set(docs), key=dscore, reverse=True)[:max_docs]
    for p in docs:
        try:
            rep, packets = read_document(p, max_chunks=6, chunk_chars=700)
            bus = SensoryBus()
            for pkt in packets[:24]:
                bus.push(pkt)
                ext = bus.build_external(
                    brain.n_units,
                    brain.region_index,
                    device=brain.device,
                    dtype=brain.net.dtype,
                )
                ext = (ext * 1.8 + 0.15).clamp(-0.5, 1.4)
                for _ in range(2):
                    brain.step(ext)
            mem = EpisodeMemory(
                episode_id=_eid(rep.title, rep.path),
                title=rep.title,
                path=rep.path,
                kind=f"document:{rep.kind}",
                symbols=rep.symbols_guessed,
                caption_source="document_text",
                caption_text=rep.sample_text,
                caption_cues_n=rep.n_chunks,
                plain_english=rep.plain_english,
                knowledge_keys=rep.knowledge_keys,
                n_trits=rep.n_trits_total,
                S_couple=rep.S_couple,
                sample_lines=(rep.sample_text or "").split(". ")[:4],
                notes=["short_horizon"] + list(rep.notes[:4]),
            )
            save_episode(mem, root=mem_root)
            n_docs += 1
            n_mem += 1
            # query from content words, not full path
            cue = (rep.title or p.stem).split()[0:3]
            q = " ".join(cue) if cue else p.stem
            queries.append((q, rep.title or p.stem))
            if rep.symbols_guessed:
                queries.append((rep.symbols_guessed[0], rep.title or p.stem))
        except Exception as e:
            notes.append(f"doc skip {p.name}: {e}")

    # --- Media (optional G: roots) ---
    roots = media_roots_from_env()
    videos = discover_media_files(roots, max_files=max_videos * 4, kind="video")[:max_videos]
    if videos:
        try:
            # Lightweight frame episodes — retina RF cascade only (no path tutor in feats)
            for vp in videos:
                prev = None
                feats_acc: List[List[float]] = []
                for img, t_sec in iter_video_frames(
                    vp, max_frames=media_frames, stride=18, max_side=72
                ):
                    feats, prev, st = _rgb_to_features(img, prev)
                    feats_acc.append(feats)
                    # mild brain drive from vision features
                    bus = SensoryBus()
                    from ..sensory.packets import SensoryPacket, SensoryModality

                    gate = SEEDS.phi / (1.0 + SEEDS.phi)
                    pkt = SensoryPacket(
                        modality=SensoryModality.VISION,
                        target_region="sens",
                        features=feats,
                        strength=0.5 * gate,
                        meta={"kind": "short_horizon_vision", "t_sec": t_sec},
                    )
                    bus.push(pkt)
                    ext = bus.build_external(
                        brain.n_units,
                        brain.region_index,
                        device=brain.device,
                        dtype=brain.net.dtype,
                    )
                    brain.step(ext.clamp(-0.5, 1.4))
                title = vp.stem[:60]
                # Prefer subtitles into episode if present (for recall + bind)
                cap_src = "none"
                cap_text = ""
                cap_n = 0
                try:
                    from ..knowledge.subtitles import load_subtitles, flatten_caption_text

                    cues = load_subtitles(vp)
                    if cues:
                        cap_src = cues[0].source if cues else "srt"
                        cap_text = flatten_caption_text(cues, max_chars=400)
                        cap_n = len(cues)
                except Exception:
                    pass
                mem = EpisodeMemory(
                    episode_id=_eid(title, str(vp)),
                    title=title,
                    path=str(vp),
                    kind="media:video_short",
                    symbols=["moving_image", "movie", "scene"]
                    + (["dialogue"] if cap_n else []),
                    caption_source=cap_src,
                    caption_text=cap_text,
                    caption_cues_n=cap_n,
                    plain_english=(
                        f"Short-horizon visual encode of “{title}”: "
                        f"{len(feats_acc)} frames through RF cascade retina features."
                    ),
                    knowledge_keys=["movie", "moving_image"],
                    n_trits=len(feats_acc) * 32,
                    mean_luma=float(np.mean([f[0] for f in feats_acc])) if feats_acc else 0.0,
                    mean_motion=float(np.mean([f[6] for f in feats_acc])) if feats_acc else 0.0,
                    sample_lines=[f"frames={len(feats_acc)}"],
                    notes=["short_horizon", "tutor_ablated_encode"],
                )
                save_episode(mem, root=mem_root)
                n_media += 1
                n_mem += 1
                # Query by distinctive stem tokens (not full path string as answer)
                token = title.replace(".", " ").replace("_", " ").split()[0]
                queries.append((token, title))
                queries.append((f"movie {token}", title))
            notes.append(f"media videos encoded: {[v.name for v in videos]}")
        except Exception as e:
            notes.append(f"media encode issue: {e}")
    else:
        notes.append("no media roots — doc-only short horizon")

    # --- Immediate recall ---
    # Dedup queries
    seen_q = set()
    uniq_q: List[Tuple[str, str]] = []
    for q, e in queries:
        key = (q.lower(), e.lower())
        if key in seen_q:
            continue
        seen_q.add(key)
        uniq_q.append((q, e))
    top1, atk, recall_rows = _score_recall(uniq_q, root=mem_root, k=3)

    # --- Real media pixel ID (parallel sensory accuracy) ---
    pix_top1 = 0.0
    pix_syn = True
    pix_detail: Dict[str, Any] = {}
    if run_pixel_id:
        try:
            pix = probe_real_media_pixel_id(
                n_classes=min(4, max(2, max_videos)),
                n_train=8,
                n_test=4,
                seed=seed,
            )
            pix_top1 = pix.pixel_id_top1
            pix_syn = pix.synthetic
            pix_detail = pix.to_dict()
            notes.append(
                f"pixel_id top1={pix.pixel_id_top1:.3f} synthetic={pix.synthetic} "
                f"mode={pix.feature_mode}"
            )
        except Exception as e:
            notes.append(f"pixel_id skip: {e}")

    # --- Subtitle ↔ pixel co-occurrence (name with look) ---
    cap_top1 = 0.0
    cap_names = 0
    cap_pairs = 0
    cap_detail: Dict[str, Any] = {}
    if run_caption_bind:
        try:
            from ..knowledge.vision_caption_bind import run_vision_caption_bind

            cap = run_vision_caption_bind(
                max_videos=min(5, max(2, max_videos)),
                max_frames=max(12, media_frames),
                stride=22,
                seed=seed,
            )
            cap_top1 = float(cap.pixel_to_name_top1)
            cap_names = int(cap.n_names)
            cap_pairs = int(cap.n_caption_binds)
            cap_detail = cap.to_dict()
            notes.append(
                f"caption_bind binds={cap.n_caption_binds} names={cap.n_names} "
                f"pixel→name top1={cap.pixel_to_name_top1:.3f} "
                f"heldout={cap.n_heldout}"
            )
            # Store a memory summary of caption-name clusters for recall
            if cap.top_names:
                mem = EpisodeMemory(
                    episode_id=_eid("vision_caption_clusters", "bind"),
                    title="Vision–caption name clusters",
                    path=cap.clusters_path or "vision_caption_clusters",
                    kind="bind:vision_caption",
                    symbols=["dialogue", "person", "face"] + list(cap.top_names[:6]),
                    caption_source="srt_cooccurrence",
                    caption_text=" ".join(cap.top_names[:20]),
                    caption_cues_n=cap.n_caption_binds,
                    plain_english=(
                        f"Bound {cap.n_caption_binds} caption–frame pairs into "
                        f"{cap.n_names} name clusters. Top names: "
                        f"{', '.join(cap.top_names[:8])}."
                    ),
                    knowledge_keys=list(cap.top_names[:12]),
                    n_trits=cap.n_names * 16,
                    sample_lines=list(cap.top_names[:6]),
                    notes=["short_horizon", "vision_caption_bind"],
                )
                save_episode(mem, root=mem_root)
                n_mem += 1
                queries.append(("vision caption clusters", "Vision–caption name clusters"))
                if cap.top_names:
                    queries.append((cap.top_names[0], "Vision–caption name clusters"))
        except Exception as e:
            notes.append(f"caption_bind skip: {e}")

    # Recompute recall if we added caption-cluster queries
    seen_q = set()
    uniq_q = []
    for q, e in queries:
        key = (q.lower(), e.lower())
        if key in seen_q:
            continue
        seen_q.add(key)
        uniq_q.append((q, e))
    top1, atk, recall_rows = _score_recall(uniq_q, root=mem_root, k=3)

    # --- Learning probe (machine items) — short delay ---
    lp_top1 = 0.0
    lp_margin = 0.0
    sme_th = sme_ga = False
    if run_learning_probe:
        try:
            br, scalpel_rep, _meta = build_scalpel_brain(
                profile=profile, device=device, tol=0.02
            )
            learn = learning_probe(
                br,
                n_items=10,
                encode_steps=220,
                retrieve_steps=180,
                delay_steps=100,
                consolidate=True,
                consolidate_rest_steps=140,
                item_mode="fsot_machine",
                seed=seed,
            )
            lp_top1 = float(learn.top1_accuracy)
            sim_p = float(learn.mean_correct_sim)
            sim_m = float(learn.mean_incorrect_sim)
            lp_margin = (sim_p - sim_m) / max(1e-6, sim_p + sim_m)
            sme_th = bool(learn.sme_theta_encode_gt_rest)
            sme_ga = bool(learn.sme_gamma_encode_gt_rest)
            notes.append(
                f"learning_probe top1={lp_top1:.3f} margin={lp_margin:.3f} "
                f"smeθ={sme_th} smeγ={sme_ga} scalpel={getattr(scalpel_rep, 'ok', None)}"
            )
        except Exception as e:
            notes.append(f"learning_probe skip: {e}")

    finished = datetime.now(timezone.utc)
    elapsed_min = (finished - started).total_seconds() / 60.0
    # Success: recall + learning probe healthy; caption bind optional bonus
    ok = (
        (top1 >= 0.4 or atk >= 0.55)
        and (lp_top1 >= 0.5 or not run_learning_probe)
        and sme_th
        and sme_ga
    ) if run_learning_probe else (top1 >= 0.4 or atk >= 0.55)

    rep = ShortHorizonReport(
        ok=ok,
        encode_minutes_est=elapsed_min,
        n_docs=n_docs,
        n_media=n_media,
        n_memory=n_mem,
        recall_top1=top1,
        recall_at_k=atk,
        recall_k=3,
        pixel_id_top1=pix_top1,
        pixel_id_synthetic=pix_syn,
        caption_bind_top1=cap_top1,
        caption_bind_names=cap_names,
        caption_bind_pairs=cap_pairs,
        learning_probe_top1=lp_top1,
        learning_probe_margin=lp_margin,
        sme_theta=sme_th,
        sme_gamma=sme_ga,
        wetlab_note="Allen/scalpel separate — run wetlab battery to gate commit",
        notes=notes,
        details={
            "recall_rows": recall_rows,
            "pixel_id": pix_detail,
            "caption_bind": cap_detail,
            "queries_n": len(uniq_q),
            "memory_root": str(mem_root),
        },
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
    )

    # Persist
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out_j = ARTIFACTS / "short_horizon_last.json"
    import json

    out_j.write_text(json.dumps(rep.to_dict(), indent=2, default=str), encoding="utf-8")
    md = DATA / "results" / "SHORT_HORIZON_LEARN.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Short-horizon learning",
        "",
        f"Time: `{rep.started_at}` → `{rep.finished_at}` ({rep.encode_minutes_est:.2f} min)",
        f"OK: **{rep.ok}**",
        "",
        f"- docs={rep.n_docs} media={rep.n_media} memories={rep.n_memory}",
        f"- recall top1=**{rep.recall_top1:.3f}** recall@3=**{rep.recall_at_k:.3f}**",
        f"- pixel_id top1=**{rep.pixel_id_top1:.3f}** synthetic={rep.pixel_id_synthetic}",
        f"- caption↔pixel binds=**{rep.caption_bind_pairs}** names=**{rep.caption_bind_names}** "
        f"pixel→name top1=**{rep.caption_bind_top1:.3f}**",
        f"- learning_probe top1=**{rep.learning_probe_top1:.3f}** margin={rep.learning_probe_margin:.3f}",
        f"- SME θ/γ: {rep.sme_theta} / {rep.sme_gamma}",
        "",
        "## Notes",
        "",
    ]
    for n in notes:
        lines.append(f"- {n}")
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")
    return rep
