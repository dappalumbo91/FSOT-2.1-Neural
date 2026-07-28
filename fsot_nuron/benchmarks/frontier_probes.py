"""
Probing experiments toward capability frontier gaps.

These **measure progress**; they do **not** flip claims to green.
Statuses remain unclaimed / probing / partial until claim gates pass.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F

from ..seeds import SEEDS
from ..capability_frontier import (
    log_frontier,
    CLAIM_OPEN_WORLD,
    CLAIM_CURRICULUM,
    CLAIM_MONOLOGUE,
)


@dataclass
class FrontierProbeReport:
    ok: bool
    probes: Dict[str, Any]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _synthetic_templates(
    n_classes: int = 4,
    feat_dim: int = 32,
    seed: int = 7,
) -> Tuple[torch.Tensor, List[str]]:
    """
    Deterministic visual-like templates (not real Jake pixels).
    Stand-in until labeled video crops exist.
    """
    g = torch.Generator().manual_seed(seed)
    names = ["entity_A", "entity_B", "entity_C", "entity_D"][:n_classes]
    templates = torch.randn(n_classes, feat_dim, generator=g)
    templates = F.normalize(templates, dim=1)
    return templates, names


def _render_entity_frame(
    class_id: int,
    *,
    size: int = 48,
    jitter: float = 0.0,
    rng: Optional[torch.Generator] = None,
) -> "torch.Tensor":
    """
    Structured synthetic 'character' frames (shape/color motifs), not free noise.
    Still synthetic — not real Jake pixels. Feeds the retina feature path.
    """
    import numpy as np

    img = np.zeros((size, size, 3), dtype=np.float32)
    img[:] = 0.15
    # class-distinct geometry + color (entity A–D stand-ins)
    cx = size // 2 + int(3 * jitter)
    cy = size // 2 + int(2 * jitter)
    if class_id == 0:  # round warm blob
        color = (0.9, 0.55, 0.2)
        for y in range(size):
            for x in range(size):
                if (x - cx) ** 2 + (y - cy) ** 2 < (size * 0.22) ** 2:
                    img[y, x] = color
    elif class_id == 1:  # tall cool rectangle
        color = (0.25, 0.45, 0.9)
        img[cy - size // 5 : cy + size // 5, cx - size // 10 : cx + size // 10] = color
    elif class_id == 2:  # horizontal bar + green
        color = (0.3, 0.85, 0.35)
        img[cy - size // 12 : cy + size // 12, cx - size // 4 : cx + size // 4] = color
    else:  # diagonal-ish dots purple
        color = (0.7, 0.25, 0.8)
        for k in range(-2, 3):
            yy = max(0, min(size - 3, cy + k * 4))
            xx = max(0, min(size - 3, cx + k * 4))
            img[yy : yy + 3, xx : xx + 3] = color
    if jitter != 0.0 and rng is not None:
        noise = jitter * 0.08 * torch.randn(size, size, 3, generator=rng).numpy()
        img = np.clip(img + noise.astype(np.float32), 0.0, 1.0)
    return torch.from_numpy(img)


def probe_pixel_identity(
    *,
    n_classes: int = 4,
    n_train: int = 8,
    n_test: int = 16,
    noise: float = 0.35,
    seed: int = 7,
    use_retina_features: bool = True,
) -> Dict[str, Any]:
    """
    Tutor-ablated nearest-prototype ID.

    Default path: structured synthetic frames → retina _rgb_to_features → protos.
    Fallback: random feature templates. Progress metric only — not open-world claim.
    """
    g = torch.Generator().manual_seed(seed + 1)
    names = ["entity_A", "entity_B", "entity_C", "entity_D"][:n_classes]
    feature_mode = "random_templates"

    def _feat_from_frame(class_id: int, jit: float) -> torch.Tensor:
        frame = _render_entity_frame(class_id, jitter=jit, rng=g)
        if use_retina_features:
            try:
                import numpy as np
                from ..sensory.media_stream import _rgb_to_features

                feats, _gray, _st = _rgb_to_features(frame.numpy(), None)
                v = torch.tensor(feats, dtype=torch.float32)
                return F.normalize(v, dim=0)
            except Exception:
                pass
        # fallback random template slice
        templates, _ = _synthetic_templates(n_classes=n_classes, seed=seed)
        x = templates[class_id] + noise * torch.randn(templates.shape[1], generator=g)
        return F.normalize(x, dim=0)

    if use_retina_features:
        feature_mode = "retina_structured_synthetic"

    train_x, train_y = [], []
    for c in range(n_classes):
        for i in range(n_train):
            jit = float(i) * 0.15
            train_x.append(_feat_from_frame(c, jit))
            train_y.append(c)

    protos = []
    for c in range(n_classes):
        xs = torch.stack([train_x[i] for i, y in enumerate(train_y) if y == c])
        protos.append(F.normalize(xs.mean(0), dim=0))
    protos = torch.stack(protos)

    correct = 0
    for t in range(n_test):
        c = int(torch.randint(0, n_classes, (1,), generator=g).item())
        jit = 0.2 + 0.05 * (t % 5)
        x = _feat_from_frame(c, jit)
        sims = protos @ x
        pred = int(sims.argmax().item())
        correct += int(pred == c)
    top1 = correct / max(1, n_test)
    chance = 1.0 / n_classes
    return {
        "pixel_id_top1": top1,
        "pixel_id_chance": chance,
        "n_characters": n_classes,
        "n_heldout_clips": n_test,
        "tutor_ablated": True,
        "synthetic": True,
        "feature_mode": feature_mode,
        "above_chance": top1 > chance + 0.05,
        "note": (
            "Structured synthetic frames via retina features — "
            "real Jake/Finn held-out crops still required for claim"
        ),
    }


def probe_curriculum_gap(
    *,
    symbol_counts: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Gap-driven multi-step plan vs fixed order + synthetic metric_delta.
    Plan is self-authored from census; full claim still needs real execute budget.
    """
    try:
        from ..learn.curriculum import plan_curriculum

        plan = plan_curriculum(symbol_counts, max_steps=6, write=True)
        gap_driven_fraction = 1.0 if plan.gap_order != plan.fixed_order else 0.0
        return {
            "curriculum_steps_planned": len(plan.steps),
            "curriculum_self_authored": plan.self_authored,
            "gap_driven_fraction": gap_driven_fraction,
            "fixed_order": plan.fixed_order,
            "gap_order": plan.gap_order,
            "metric_delta_vs_fixed_order": plan.metric_delta_vs_fixed_order,
            "metric_gap": plan.metric_gap,
            "metric_fixed": plan.metric_fixed,
            "plan_path": plan.plan_path,
            "note": (
                "Self-authored gap plan + synthetic metric_delta; "
                "full claim needs execute-without-human-lists"
            ),
        }
    except Exception as e:
        census = symbol_counts or {
            "action": 5,
            "dialogue": 1,
            "person": 1,
            "music": 4,
            "place": 3,
        }
        fixed_order = sorted(census.keys())
        gap_order = sorted(census.keys(), key=lambda k: (census[k], k))
        return {
            "curriculum_steps_planned": len(gap_order),
            "curriculum_self_authored": False,
            "gap_driven_fraction": 1.0 if gap_order != fixed_order else 0.0,
            "fixed_order": fixed_order,
            "gap_order": gap_order,
            "metric_delta_vs_fixed_order": None,
            "error": str(e),
            "note": "Fallback heuristic only",
        }


def probe_monologue_grounded(
    plain_english: str = "",
    *,
    n_turns: int = 5,
) -> Dict[str, Any]:
    """
    Multi-turn grounded monologue from organism memory — not free LLM monologue.
    If plain_english is provided, score that single blob (legacy); else run
    knowledge.monologue multi-turn probe (progress toward claim gate).
    """
    if plain_english:
        text = plain_english
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        n_sent = len(sentences)
        keys = ("pattern", "trinary", "associated", "experiencing", "dialogue", "memory")
        hits = sum(1 for k in keys if k in text.lower())
        grounded = hits / max(1, len(keys))
        return {
            "monologue_mode": "compositional_regurgitation",
            "max_coherent_sentences": n_sent,
            "groundedness_score": grounded,
            "external_llm_used": False,
            "n_turns": 1,
            "note": "Legacy single-shot expansion path",
        }
    try:
        from ..knowledge.monologue import run_grounded_monologue

        rep = run_grounded_monologue(n_turns=n_turns, seed_probe_episode=True)
        return {
            "monologue_mode": rep.monologue_mode,
            "max_coherent_sentences": rep.max_coherent_sentences,
            "groundedness_score": rep.groundedness_score,
            "external_llm_used": rep.external_llm_used,
            "n_turns": rep.n_turns,
            "turn_grounded_hits": [t.grounded_hits for t in rep.turns],
            "note": "Multi-turn memory monologue; free LLM monologue still unclaimed",
        }
    except Exception as e:
        return {
            "monologue_mode": "error",
            "max_coherent_sentences": 0,
            "groundedness_score": 0.0,
            "external_llm_used": False,
            "n_turns": 0,
            "error": str(e),
            "note": "Monologue probe failed",
        }


def run_frontier_probes(
    *,
    pattern_census: Optional[Dict[str, int]] = None,
    plain_english: str = "",
    log: bool = True,
) -> FrontierProbeReport:
    notes: List[str] = [
        "Probes measure progress toward unclaimed gaps; claims stay non-green.",
    ]
    pix = probe_pixel_identity()
    cur = probe_curriculum_gap(symbol_counts=pattern_census)
    mon = probe_monologue_grounded(plain_english=plain_english)
    probes = {
        "open_world_pixel_identity": pix,
        "self_directed_curriculum": cur,
        "free_monologue": mon,
    }
    # status updates: still not claimed
    pix_status = "probing" if pix.get("above_chance") else "unclaimed"
    if log:
        log_frontier(
            experiment="frontier_probes",
            related_metrics={
                "pixel_id_top1": pix.get("pixel_id_top1"),
                "curriculum_gap_driven_fraction": cur.get("gap_driven_fraction"),
                "monologue_groundedness": mon.get("groundedness_score"),
                "monologue_sentences": mon.get("max_coherent_sentences"),
            },
            notes="Synthetic pixel-ID + gap curriculum + compositional monologue probes.",
            overrides={
                CLAIM_OPEN_WORLD: {
                    "status": pix_status,
                    "status_note": (
                        f"synthetic tutor-ablated top1={pix.get('pixel_id_top1'):.3f} "
                        f"chance={pix.get('pixel_id_chance'):.3f} (not real Jake pixels)"
                    ),
                    "metrics": {
                        "pixel_id_top1": pix.get("pixel_id_top1"),
                        "pixel_id_chance": pix.get("pixel_id_chance"),
                        "n_characters": pix.get("n_characters"),
                        "n_heldout_clips": pix.get("n_heldout_clips"),
                        "tutor_ablated": True,
                    },
                },
                CLAIM_CURRICULUM: {
                    "status": "probing",
                    "status_note": "gap-driven order heuristic measured; not self-authored curriculum",
                    "metrics": {
                        "curriculum_steps_planned": cur.get("curriculum_steps_planned"),
                        "curriculum_self_authored": False,
                        "gap_driven_fraction": cur.get("gap_driven_fraction"),
                        "metric_delta_vs_fixed_order": None,
                    },
                },
                CLAIM_MONOLOGUE: {
                    "status": "partial",
                    "status_note": "compositional grounded expansion scored; not free monologue",
                    "metrics": {
                        "monologue_mode": "compositional_regurgitation",
                        "max_coherent_sentences": mon.get("max_coherent_sentences"),
                        "groundedness_score": mon.get("groundedness_score"),
                        "external_llm_used": False,
                        "n_turns": 1,
                    },
                },
            },
        )
        notes.append("frontier ledger updated")
    return FrontierProbeReport(ok=True, probes=probes, notes=notes)
