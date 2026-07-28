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


def probe_pixel_identity(
    *,
    n_classes: int = 4,
    n_train: int = 8,
    n_test: int = 16,
    noise: float = 0.35,
    seed: int = 7,
) -> Dict[str, Any]:
    """
    Tutor-ablated nearest-template ID on synthetic patterns.
    Progress metric only — not open-world claim.
    """
    templates, names = _synthetic_templates(n_classes=n_classes, seed=seed)
    g = torch.Generator().manual_seed(seed + 1)
    # train: noisy copies (would be co-occurrence with names in full system)
    train_x, train_y = [], []
    for c in range(n_classes):
        for _ in range(n_train):
            x = templates[c] + noise * torch.randn(templates.shape[1], generator=g)
            train_x.append(F.normalize(x, dim=0))
            train_y.append(c)
    # prototype = mean train
    protos = []
    for c in range(n_classes):
        xs = torch.stack([train_x[i] for i, y in enumerate(train_y) if y == c])
        protos.append(F.normalize(xs.mean(0), dim=0))
    protos = torch.stack(protos)

    # test tutor-ablated: only pixels (features), no labels at query
    correct = 0
    for _ in range(n_test):
        c = int(torch.randint(0, n_classes, (1,), generator=g).item())
        x = templates[c] + noise * torch.randn(templates.shape[1], generator=g)
        x = F.normalize(x, dim=0)
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
        "above_chance": top1 > chance + 0.05,
        "note": "Synthetic templates only — real Jake/Finn crops later",
    }


def probe_curriculum_gap(
    *,
    symbol_counts: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Gap-driven next-topic pick vs fixed order.
    Self-authored = False still; we only measure if gap heuristic differs from fixed.
    """
    # default fake census if none
    census = symbol_counts or {
        "action": 5,
        "dialogue": 1,
        "person": 1,
        "music": 4,
        "place": 3,
    }
    fixed_order = sorted(census.keys())
    # gap-driven: prefer rare symbols
    gap_order = sorted(census.keys(), key=lambda k: (census[k], k))
    self_authored = False
    gap_driven_fraction = 1.0 if gap_order != fixed_order else 0.0
    return {
        "curriculum_steps_planned": len(gap_order),
        "curriculum_self_authored": self_authored,
        "gap_driven_fraction": gap_driven_fraction,
        "fixed_order": fixed_order,
        "gap_order": gap_order,
        "metric_delta_vs_fixed_order": None,  # needs A/B learn run
        "note": "Heuristic gap order only — not full self-directed curriculum",
    }


def probe_monologue_grounded(
    plain_english: str = "",
) -> Dict[str, Any]:
    """
    Score compositional recall text — not free LLM monologue.
    """
    text = plain_english or (
        "While experiencing media, patterns linked to action and dialogue. "
        "Associated knowledge compact to trinary. "
        "Internal form is not English."
    )
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    n_sent = len(sentences)
    # groundedness proxy: presence of organism vocabulary
    keys = ("pattern", "trinary", "associated", "experiencing", "dialogue", "memory")
    hits = sum(1 for k in keys if k in text.lower())
    grounded = hits / max(1, len(keys))
    return {
        "monologue_mode": "compositional_regurgitation",
        "max_coherent_sentences": n_sent,
        "groundedness_score": grounded,
        "external_llm_used": False,
        "n_turns": 1,
        "note": "Single-shot grounded expansion; multi-turn chat not claimed",
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
