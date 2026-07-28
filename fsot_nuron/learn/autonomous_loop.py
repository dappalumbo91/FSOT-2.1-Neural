"""
Autonomous multi-modal learning — minimal instruction.

The organism is given *access* to optional worlds (media, literature, docs)
and neurological pathways already built:

  vision + audio co-stream · subtitle dialogue · document reading
  · symbolic association · knowledge lexicon · machine/trinary compactification
  · episodic memory

It chews what it finds, binds patterns without a human prompt per item,
and reports what co-occurrence structure it formed.

This is **not** next-token LLM training. It is pattern recognition + compact
memory on FSOT genetic multi-region dynamics.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..paths import ROOT, DATA, ARTIFACTS
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
    list_episodes,
    _eid,
)
from ..sensory.media_stream import (
    media_roots_from_env,
    discover_media_files,
    MediaChewConfig,
    chew_media,
)


@dataclass
class AutonomousLearnReport:
    ok: bool
    pin_connected: bool
    pin_mode: str
    started_at: str
    finished_at: str
    n_documents: int
    n_media_episodes: int
    n_memory_saved: int
    document_summaries: List[Dict[str, Any]] = field(default_factory=list)
    media_summaries: List[Dict[str, Any]] = field(default_factory=list)
    pattern_census: Dict[str, int] = field(default_factory=dict)
    plain_english_digest: str = ""
    notes: List[str] = field(default_factory=list)
    brain_spikes: int = 0
    mean_S: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _count_symbols(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    cens: Dict[str, int] = {}
    for r in rows:
        for s in r.get("symbols") or []:
            if not s:
                continue
            k = str(s).lower()
            cens[k] = cens.get(k, 0) + 1
    return dict(sorted(cens.items(), key=lambda kv: -kv[1]))


def run_autonomous_learn(
    *,
    max_docs: int = 6,
    max_videos: int = 1,
    max_audio: int = 1,
    media_frames: int = 10,
    seed: int = 7,
    include_media: bool = True,
    include_docs: bool = True,
    doc_roots: Optional[Sequence[Path]] = None,
    profile: str = "ai_efficient",
    device: str = "cpu",
) -> AutonomousLearnReport:
    """
    Boot pin, then freely chew documents + optional media, store memories.
    No per-item human prompts.
    """
    notes: List[str] = []
    started = datetime.now(timezone.utc).isoformat()
    pin = pin_archive(write_snapshot=False)
    notes.append(
        f"pin connected={pin.connected} mode={getattr(pin, 'pin_mode', 'standalone')}"
    )

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
    notes.append(f"brain n_units={brain.n_units} regions={list(brain.region_index)}")

    doc_summaries: List[Dict[str, Any]] = []
    media_summaries: List[Dict[str, Any]] = []
    mem_saved = 0
    total_spikes = 0
    last_S = 0.0

    # --- Documents (always local, in-repo literature/docs) ---
    if include_docs:
        docs = discover_documents(doc_roots, max_files=max_docs * 4)
        # Prefer literature + thesis over random code dumps; unique paths
        def score(p: Path) -> int:
            s = 0
            low = str(p).lower()
            if "literature" in low:
                s += 10
            if "thesis" in low or "formula" in low:
                s += 8
            if p.suffix.lower() == ".md":
                s += 5
            if p.suffix.lower() == ".txt" and "shakespeare" in low:
                s += 6
            if p.suffix.lower() == ".pdf":
                s += 4
            if p.suffix.lower() == ".py":
                s -= 20  # prefer prose literature over source dumps
            if "shakespeare" in low:
                s += 5
            return s

        seen_paths = set()
        uniq: List[Path] = []
        for p in sorted(docs, key=score, reverse=True):
            rp = str(p.resolve())
            if rp in seen_paths:
                continue
            seen_paths.add(rp)
            uniq.append(p)
        docs = uniq[:max_docs]
        notes.append(f"documents selected: {[p.name for p in docs]}")
        for p in docs:
            try:
                rep, packets = read_document(p, max_chunks=8, chunk_chars=900)
                # drive packets through living brain
                for pkt in packets[:32]:
                    from ..sensory.bus import SensoryBus

                    bus = SensoryBus()
                    bus.push(pkt)
                    ext = bus.build_external(
                        brain.n_units,
                        brain.region_index,
                        device=brain.device,
                        dtype=brain.net.dtype,
                    )
                    # mild gain
                    ext = (ext * 1.8 + 0.15).clamp(-0.5, 1.4)
                    for _ in range(3):
                        S, fired, *_ = brain.step(ext)
                        total_spikes += int(fired.sum().item())
                        last_S = float(S.mean().item())
                # store episodic memory of the document
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
                    sample_lines=rep.sample_text.split(". ")[:4],
                    notes=rep.notes[:6],
                )
                save_episode(mem)
                mem_saved += 1
                doc_summaries.append(
                    {
                        "title": rep.title,
                        "kind": rep.kind,
                        "n_chars": rep.n_chars,
                        "n_chunks": rep.n_chunks,
                        "n_trits": rep.n_trits_total,
                        "symbols": rep.symbols_guessed[:10],
                        "knowledge_keys": rep.knowledge_keys[:10],
                        "S": rep.S_couple,
                    }
                )
                notes.append(
                    f"read {p.name}: chunks={rep.n_chunks} trits={rep.n_trits_total} "
                    f"keys={rep.knowledge_keys[:5]}"
                )
            except Exception as e:
                notes.append(f"doc fail {p.name}: {e}")

    # --- Optional media (if G: or FSOT_MEDIA_ROOTS present) ---
    if include_media:
        roots = media_roots_from_env()
        if not roots:
            notes.append("no media roots — document-only autonomy (standalone OK)")
        else:
            try:
                cfg = MediaChewConfig(
                    roots=[str(r) for r in roots],
                    max_video_files=max_videos,
                    max_audio_files=max_audio,
                    frames_per_video=media_frames,
                    frame_stride=40,
                    audio_windows=4,
                    associate=True,
                    av_costream=True,
                    use_subtitles=True,
                    speech_to_text=False,
                    knowledge_crossfeed=True,
                    save_episode_memory=True,
                    seed=seed,
                    profile=profile,
                    device=device,
                )
                mrep = chew_media(cfg, brain=brain)
                total_spikes += mrep.total_spikes
                last_S = mrep.mean_S
                for ep in mrep.episodes or []:
                    media_summaries.append(
                        {
                            "title": ep.get("title"),
                            "kind": ep.get("kind"),
                            "symbols": ep.get("top_symbols"),
                            "meta_bind": ep.get("meta_bind_score"),
                            "dialogue": (ep.get("dialogue_memory") or {}),
                            "av": {
                                k: (ep.get("av_cross_modal") or {}).get(k)
                                for k in (
                                    "mean_bind",
                                    "has_soundtrack",
                                    "subtitle_source",
                                    "moments_with_dialogue",
                                )
                            },
                        }
                    )
                    if ep.get("dialogue_memory") or ep.get("plain_english"):
                        mem_saved += 1
                notes.extend(mrep.notes[:20])
            except Exception as e:
                notes.append(f"media autonomy: {e}")

    # Pattern census across what was experienced
    pattern_rows = []
    for d in doc_summaries:
        pattern_rows.append({"symbols": d.get("symbols")})
    for m in media_summaries:
        pattern_rows.append({"symbols": m.get("symbols")})
    census = _count_symbols(pattern_rows)

    # Self-summary without extra human instruction
    digest_lines = [
        "Autonomous multi-modal session (no per-item prompts).",
        f"Pin: {'OK' if pin.connected else 'FAIL'} ({getattr(pin, 'pin_mode', 'standalone')}).",
        f"Documents read: {len(doc_summaries)}. Media episodes: {len(media_summaries)}. "
        f"Memories saved: {mem_saved}.",
        f"Brain spikes this session: {total_spikes}. mean S: {last_S:.4f}.",
    ]
    if census:
        top = list(census.items())[:12]
        digest_lines.append(
            "Recurring patterns (co-occurrence census): "
            + ", ".join(f"{k}×{v}" for k, v in top)
        )
    if doc_summaries:
        digest_lines.append(
            "Documents included: "
            + ", ".join(d["title"] for d in doc_summaries[:8])
        )
    if media_summaries:
        digest_lines.append(
            "Media included: "
            + ", ".join(str(m.get("title")) for m in media_summaries[:6])
        )
    digest_lines.append(
        "Internal storage is machine/trinary compact codes; this digest is host-facing English."
    )
    digest = "\n".join(digest_lines)

    finished = datetime.now(timezone.utc).isoformat()
    report = AutonomousLearnReport(
        ok=bool(pin.connected),
        pin_connected=bool(pin.connected),
        pin_mode=str(getattr(pin, "pin_mode", "standalone")),
        started_at=started,
        finished_at=finished,
        n_documents=len(doc_summaries),
        n_media_episodes=len(media_summaries),
        n_memory_saved=mem_saved,
        document_summaries=doc_summaries,
        media_summaries=media_summaries,
        pattern_census=census,
        plain_english_digest=digest,
        notes=notes,
        brain_spikes=total_spikes,
        mean_S=last_S,
    )

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    import json

    (ARTIFACTS / "autonomous_learn_last.json").write_text(
        json.dumps(report.to_dict(), indent=2), encoding="utf-8"
    )
    # Track capability frontier gaps (open-world / curriculum / monologue)
    try:
        from ..capability_frontier import snapshot_from_autonomous

        snapshot_from_autonomous(report)
        notes.append("capability_frontier: snapshot logged")
    except Exception as e:
        notes.append(f"capability_frontier log skip: {e}")
    return report
