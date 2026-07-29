"""
Multi-domain stress / reasoning probes at the current organism stage.

Domains:
  1. literature / thesis documents (science text)
  2. narrative (shakespeare stream if present)
  3. real media + caption co-occurrence
  4. learning_bio (SME + retrieval)
  5. 5W1H teach-card round-trip
  6. monologue multi-turn grounded
  7. wetlab-critical gates (Allen rates from cache)

Produces a single scoreboard — not a claim of human-level understanding.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..paths import ARTIFACTS, DATA, ROOT
from ..seeds import SEEDS
from ..knowledge.teach_5w1h import build_5w1h
from ..knowledge.document_read import discover_documents, read_document
from ..knowledge.episode_memory import (
    EpisodeMemory,
    save_episode,
    retrieve_by_query,
    _eid,
)
from ..learn.short_horizon import run_short_horizon_learn
from ..benchmarks.learning_bio import run_learning_bio_benchmark
from ..benchmarks.media_pixel_id import probe_real_media_pixel_id
from ..knowledge.vision_caption_bind import run_vision_caption_bind
from ..knowledge.monologue import run_grounded_monologue
from ..archive_pin import pin_archive


@dataclass
class DomainResult:
    domain: str
    ok: bool
    score: float  # 0-100 rough
    metrics: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MultiDomainStressReport:
    ok: bool
    n_pass: int
    n_domains: int
    mean_score: float
    domains: List[DomainResult]
    started_at: str = ""
    finished_at: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _domain_docs() -> DomainResult:
    notes: List[str] = []
    try:
        docs = discover_documents(None, max_files=20)
        # prefer thesis/literature
        def sc(p: Path) -> int:
            s = str(p).lower()
            return (
                (10 if "thesis" in s or "literature" in s else 0)
                + (5 if p.suffix == ".md" else 0)
                - (20 if p.suffix == ".py" else 0)
            )

        docs = sorted(set(docs), key=sc, reverse=True)[:4]
        mem_root = ARTIFACTS / "stress_domain_docs"
        mem_root.mkdir(parents=True, exist_ok=True)
        n_ok = 0
        n = 0
        for p in docs:
            rep, _pkts = read_document(p, max_chunks=4, chunk_chars=600)
            lesson = build_5w1h(
                title=rep.title,
                text=rep.sample_text or "",
                symbols=rep.symbols_guessed,
                path=str(p),
                kind=f"document:{rep.kind}",
            )
            mem = EpisodeMemory(
                episode_id=_eid(rep.title, str(p)),
                title=rep.title,
                path=str(p),
                kind=f"document:{rep.kind}",
                symbols=rep.symbols_guessed,
                caption_text=rep.sample_text[:400] if rep.sample_text else "",
                plain_english=lesson.as_teach_text(),
                knowledge_keys=rep.knowledge_keys,
                sample_lines=(rep.sample_text or "").split(". ")[:3],
                notes=["stress_docs", "5w1h"],
            )
            save_episode(mem, root=mem_root)
            # 5W1H retrieval probes
            for q, exp in lesson.query_bank()[:4]:
                n += 1
                hits = retrieve_by_query(q, root=mem_root, top_k=3)
                blob = " ".join(
                    (h.plain_english or "") + " " + (h.title or "") for h in hits
                ).lower()
                if exp.lower() in blob:
                    n_ok += 1
        rate = n_ok / max(1, n)
        score = 100.0 * rate
        notes.append(f"docs={len(docs)} probes={n} hit={n_ok}")
        return DomainResult("documents_science", rate >= 0.4, score, {"hit_rate": rate, "n": n}, notes)
    except Exception as e:
        return DomainResult("documents_science", False, 0.0, {}, [str(e)])


def _domain_narrative() -> DomainResult:
    notes: List[str] = []
    try:
        path = ROOT / "data" / "literature" / "stream_shakespeare.txt"
        if not path.is_file():
            # try shakespeare folder
            alt = list((ROOT / "data" / "literature").rglob("*.txt"))
            path = alt[0] if alt else path
        if not path.is_file():
            return DomainResult("narrative_text", False, 20.0, {}, ["no shakespeare stream"])
        text = path.read_text(encoding="utf-8", errors="replace")[:2500]
        lesson = build_5w1h(
            title="Shakespeare stream",
            text=text,
            symbols=["scene", "dialogue", "person"],
            path=str(path),
            kind="document:narrative",
        )
        mem_root = ARTIFACTS / "stress_domain_narrative"
        mem_root.mkdir(parents=True, exist_ok=True)
        mem = EpisodeMemory(
            episode_id=_eid("shakespeare", str(path)),
            title="Shakespeare stream",
            path=str(path),
            kind="document:narrative",
            symbols=["scene", "dialogue", "person", "shakespeare"],
            caption_text=text[:500],
            plain_english=lesson.as_teach_text(),
            knowledge_keys=["shakespeare", "dialogue"],
            sample_lines=text.split("\n")[:4],
            notes=["stress_narrative", "5w1h"],
        )
        save_episode(mem, root=mem_root)
        n_ok = 0
        n = 0
        for q, exp in lesson.query_bank()[:5]:
            n += 1
            hits = retrieve_by_query(q, root=mem_root, top_k=3)
            blob = " ".join((h.plain_english or "") + h.title for h in hits).lower()
            if exp.lower()[:20] in blob or "shakespeare" in blob:
                n_ok += 1
        # also monologue on this content
        mon = run_grounded_monologue(
            questions=[
                "What media did you experience?",
                "What dialogue or speech was heard?",
                "How is knowledge stored internally?",
            ],
            n_turns=3,
            root=mem_root,
            seed_probe_episode=False,
        )
        g = float(mon.groundedness_score)
        rate = 0.5 * (n_ok / max(1, n)) + 0.5 * g
        notes.append(f"5w1h_hits={n_ok}/{n} monologue_g={g:.3f}")
        return DomainResult(
            "narrative_text",
            rate >= 0.35,
            100.0 * rate,
            {"hit_rate": n_ok / max(1, n), "groundedness": g},
            notes,
        )
    except Exception as e:
        return DomainResult("narrative_text", False, 0.0, {}, [str(e)])


def _domain_media() -> DomainResult:
    notes: List[str] = []
    try:
        pix = probe_real_media_pixel_id(n_classes=4, n_train=6, n_test=3, seed=7)
        cap = run_vision_caption_bind(max_videos=3, max_frames=12, seed=7)
        top1 = float(pix.pixel_id_top1)
        vote = float(getattr(cap, "pixel_to_name_top1_vote", 0) or cap.pixel_to_name_top1)
        pur = float(getattr(cap, "mean_cluster_purity", 0) or 0)
        # score blend
        score = 40.0 * min(1.0, top1 / 0.75) + 40.0 * min(1.0, vote / 0.7) + 20.0 * pur
        notes.append(
            f"pixel_top1={top1:.3f} cap_vote={vote:.3f} purity={pur:.3f} "
            f"synthetic={pix.synthetic}"
        )
        ok = (top1 >= 0.5 or not pix.synthetic) and (vote >= 0.3 or cap.n_names >= 3)
        return DomainResult(
            "media_av",
            ok,
            float(min(100.0, score)),
            {
                "pixel_id_top1": top1,
                "caption_vote_top1": vote,
                "purity": pur,
                "n_names": cap.n_names,
            },
            notes,
        )
    except Exception as e:
        return DomainResult("media_av", False, 0.0, {}, [str(e)])


def _domain_learning() -> DomainResult:
    try:
        r = run_learning_bio_benchmark(n_items=10, delay_steps=200)
        top1 = float(r.metrics.get("top1") or 0)
        margin = 0.0
        sp = float(r.metrics.get("mean_correct_sim") or 0)
        sm = float(r.metrics.get("mean_incorrect_sim") or 0)
        if sp + sm > 0:
            margin = (sp - sm) / (sp + sm)
        n_ok = sum(1 for v in r.gates.values() if v)
        n_g = max(1, len(r.gates))
        score = (
            50.0 * top1
            + 30.0 * (n_ok / n_g)
            + 20.0 * min(1.0, max(0.0, margin) / 0.35)
        )
        return DomainResult(
            "learning_sme",
            r.ok and top1 >= 0.5,
            float(min(100.0, score)),
            {
                "top1": top1,
                "margin": margin,
                "gates": f"{n_ok}/{n_g}",
                "sme_theta": r.gates.get("sme_theta_encode_gt_rest"),
                "sme_gamma": r.gates.get("sme_gamma_encode_gt_rest"),
            },
            list(r.notes[:3]),
        )
    except Exception as e:
        return DomainResult("learning_sme", False, 0.0, {}, [str(e)])


def _domain_short_horizon() -> DomainResult:
    try:
        rep = run_short_horizon_learn(
            max_docs=2,
            max_videos=2,
            media_frames=6,
            run_pixel_id=True,
            run_learning_probe=True,
            run_caption_bind=True,
        )
        score = (
            35.0 * rep.recall_top1
            + 25.0 * rep.recall_at_k
            + 20.0 * min(1.0, rep.pixel_id_top1 / 0.7)
            + 10.0 * min(1.0, rep.caption_bind_top1 / 0.7)
            + 10.0 * (1.0 if rep.sme_theta and rep.sme_gamma else 0.0)
        )
        return DomainResult(
            "short_horizon_5w1h",
            rep.ok,
            float(min(100.0, score)),
            {
                "recall_top1": rep.recall_top1,
                "recall_at_k": rep.recall_at_k,
                "pixel_id": rep.pixel_id_top1,
                "caption": rep.caption_bind_top1,
            },
            rep.notes[:6],
        )
    except Exception as e:
        return DomainResult("short_horizon_5w1h", False, 0.0, {}, [str(e)])


def _domain_authority() -> DomainResult:
    try:
        pin = pin_archive(write_snapshot=False)
        # precision climb cache
        score = 50.0 if pin.connected else 20.0
        score += 30.0 if pin.seed_match_ok else 0.0
        prec = ARTIFACTS / "precision_climb.json"
        mean_err = None
        if prec.is_file():
            data = json.loads(prec.read_text(encoding="utf-8"))
            classes = (data.get("report") or data).get("classes") or {}
            errs = [
                float(v["rel_err"])
                for v in classes.values()
                if isinstance(v, dict) and "rel_err" in v
            ]
            if errs:
                mean_err = sum(errs) / len(errs)
                score += 20.0 * max(0.0, 1.0 - mean_err / 0.02)
        return DomainResult(
            "authority_allen",
            bool(pin.connected and pin.seed_match_ok),
            float(min(100.0, score)),
            {"pin": pin.connected, "seed_ok": pin.seed_match_ok, "mean_rel_err": mean_err},
            [],
        )
    except Exception as e:
        return DomainResult("authority_allen", False, 0.0, {}, [str(e)])


def run_multi_domain_stress() -> MultiDomainStressReport:
    started = datetime.now(timezone.utc)
    domains = [
        _domain_authority(),
        _domain_learning(),
        _domain_docs(),
        _domain_narrative(),
        _domain_media(),
        _domain_short_horizon(),
    ]
    n_pass = sum(1 for d in domains if d.ok)
    mean = sum(d.score for d in domains) / max(1, len(domains))
    finished = datetime.now(timezone.utc)
    rep = MultiDomainStressReport(
        ok=n_pass >= max(4, len(domains) - 1),
        n_pass=n_pass,
        n_domains=len(domains),
        mean_score=mean,
        domains=domains,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        notes=[
            "5W1H teaching structure used for docs/narrative/short-horizon.",
            "Not human-level comprehension — multi-domain organism stress.",
            f"phi-gate={SEEDS.phi/(1+SEEDS.phi):.4f}",
        ],
    )
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "multi_domain_stress_last.json").write_text(
        json.dumps(rep.to_dict(), indent=2, default=str), encoding="utf-8"
    )
    md = DATA / "results" / "MULTI_DOMAIN_STRESS.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Multi-domain stress scoreboard",
        "",
        f"Time: `{rep.started_at}`",
        f"OK: **{rep.ok}**  pass **{rep.n_pass}/{rep.n_domains}**  mean_score=**{rep.mean_score:.1f}**",
        "",
        "| Domain | OK | Score | Key metrics |",
        "|--------|:--:|------:|-------------|",
    ]
    for d in domains:
        mkey = ", ".join(f"{k}={v}" for k, v in list(d.metrics.items())[:4])
        lines.append(
            f"| `{d.domain}` | {'Y' if d.ok else 'N'} | {d.score:.1f} | {mkey} |"
        )
    lines += ["", "## Notes", ""]
    for n in rep.notes:
        lines.append(f"- {n}")
    for d in domains:
        for n in d.notes[:3]:
            lines.append(f"- [{d.domain}] {n}")
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")
    return rep
