"""
Gap-driven curriculum planner — progress toward self-directed learning.

Doctrine:
  Not full free agency. The organism ranks weak symbols from memory census
  and authors a multi-step plan (JSON) before optional execution.

  Claim gate still requires: plan → execute → improve pre-registered metric
  vs fixed-order baseline without human file lists. This module provides
  the plan + a synthetic metric_delta probe so the refine cycle can climb.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..paths import ARTIFACTS, DATA
from ..seeds import SEEDS
from ..knowledge.episode_memory import list_episodes, load_episode, default_memory_dir


@dataclass
class CurriculumStep:
    step: int
    target_symbol: str
    reason: str
    priority: float
    suggested_kind: str  # media | document | either

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CurriculumPlan:
    self_authored: bool
    steps: List[CurriculumStep]
    gap_order: List[str]
    fixed_order: List[str]
    census: Dict[str, int]
    metric_gap: float
    metric_fixed: float
    metric_delta_vs_fixed_order: float
    plan_path: str = ""
    notes: List[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# Allowed curriculum symbol vocabulary (prevents "particularly"/"explain" pollution)
_CURRICULUM_VOCAB = frozenset(
    {
        "person",
        "human",
        "face",
        "animal",
        "dog",
        "cat",
        "dialogue",
        "music",
        "action",
        "cartoon",
        "movie",
        "tv_show",
        "place",
        "scene",
        "war",
        "space",
        "science",
        "theory",
        "neuron",
        "brain",
        "codon",
        "trinary",
        "consciousness",
        "finn",
        "jake",
        "adventure time",
        "shakespeare",
        "moving_image",
        "document",
        "emotion",
        "energy",
        "night",
        "day",
    }
)


def census_from_episodes(root: Optional[Path] = None, limit: int = 40) -> Dict[str, int]:
    """
    Count only **allowed** knowledge symbols on episodes.

    Free-text leaks (e.g. 'particularly', 'explain') are excluded so the
    curriculum targets teachable categories, not English filler words.
    """
    root = root or default_memory_dir()
    cens: Dict[str, int] = {}
    for row in list_episodes(root=root, limit=limit):
        mem = load_episode(str(row.get("episode_id") or ""), root=root)
        if mem is None:
            continue
        for s in list(mem.symbols) + list(mem.knowledge_keys):
            k = str(s).lower().strip()
            if not k or k not in _CURRICULUM_VOCAB:
                continue
            if len(k) < 3 or " " in k and k not in _CURRICULUM_VOCAB:
                # multiword only if in vocab
                if k not in _CURRICULUM_VOCAB:
                    continue
            cens[k] = cens.get(k, 0) + 1
    return dict(sorted(cens.items(), key=lambda kv: -kv[1]))


def _default_census() -> Dict[str, int]:
    return {
        "action": 5,
        "dialogue": 1,
        "person": 1,
        "music": 4,
        "place": 3,
        "cartoon": 2,
    }


def plan_curriculum(
    symbol_counts: Optional[Dict[str, int]] = None,
    *,
    max_steps: int = 6,
    write: bool = True,
    root: Optional[Path] = None,
) -> CurriculumPlan:
    """
    Author a multi-step plan preferring rare symbols (gaps).

    metric_* : synthetic coverage under a fixed budget of visits —
    gap order should improve rare-symbol coverage vs alphabetical fixed order.
    """
    notes: List[str] = []
    census = dict(symbol_counts) if symbol_counts else census_from_episodes(root=root)
    if not census:
        census = _default_census()
        notes.append("no episode census — using default probe census")

    fixed_order = sorted(census.keys())
    # rare first, stable tie-break
    gap_order = sorted(census.keys(), key=lambda k: (census[k], k))
    n = min(max_steps, len(gap_order))
    steps: List[CurriculumStep] = []
    for i, sym in enumerate(gap_order[:n]):
        count = census[sym]
        # priority: inverse count, seed-scaled
        priority = float(SEEDS.phi / (1.0 + count))
        kind = "media" if sym in ("dialogue", "music", "action", "cartoon") else "either"
        if sym in ("person", "face", "place"):
            kind = "media"
        steps.append(
            CurriculumStep(
                step=i + 1,
                target_symbol=sym,
                reason=f"weak symbol count={count}; prioritize gap fill",
                priority=priority,
                suggested_kind=kind,
            )
        )

    metric_gap = _coverage_metric(census, gap_order, budget=n)
    metric_fixed = _coverage_metric(census, fixed_order, budget=n)
    delta = float(metric_gap - metric_fixed)

    plan = CurriculumPlan(
        self_authored=True,  # plan text is authored by the organism
        steps=steps,
        gap_order=gap_order,
        fixed_order=fixed_order,
        census=census,
        metric_gap=metric_gap,
        metric_fixed=metric_fixed,
        metric_delta_vs_fixed_order=delta,
        notes=notes
        + [
            "Plan is self-authored from memory census; full claim still needs "
            "execute-and-improve on held metric without human file lists."
        ],
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    if write:
        out_dir = ARTIFACTS / "curriculum"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "latest_plan.json"
        path.write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")
        plan.plan_path = str(path)
        # append ledger
        ledger = DATA / "curriculum_plans.jsonl"
        try:
            with ledger.open("a", encoding="utf-8") as f:
                f.write(json.dumps(plan.to_dict(), default=str) + "\n")
        except OSError:
            pass

    return plan


def _coverage_metric(
    census: Dict[str, int],
    order: Sequence[str],
    *,
    budget: int,
) -> float:
    """
    Synthetic metric: under `budget` visits following `order`, score how well
    we cover rare symbols. Higher is better for gap-filling curricula.

    score_i = 1/(1+count_i)  — rare symbols contribute more when visited.
    """
    total = 0.0
    for i, sym in enumerate(order[:budget]):
        c = census.get(sym, 0)
        # earlier steps slightly preferred (φ decay)
        w = 1.0 / (SEEDS.phi ** (i * 0.25))
        total += w * (1.0 / (1.0 + c))
    return float(total)
