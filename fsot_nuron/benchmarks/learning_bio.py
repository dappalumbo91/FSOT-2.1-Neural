"""
Learning / understanding benchmarks vs public literature targets.

Uses existing learning_probe + band SME gates (Sederberg-style direction).
Does not claim human comprehension of film — scores *learning dynamics*.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

from ..scalpel_brain import build_scalpel_brain
from ..learning_memory import learning_probe


@dataclass
class LearningBioResult:
    ok: bool
    gates: Dict[str, bool]
    metrics: Dict[str, Any]
    literature: Dict[str, str]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def run_learning_bio_benchmark(
    *,
    device: str = "cpu",
    n_items: int = 8,
    delay_steps: int = 200,
) -> LearningBioResult:
    """
    Encode–delay–retrieve + SME direction on FSOT machine items.
    Literature: Sederberg et al. 2003 (theta/gamma encode success direction).
    """
    notes: List[str] = []
    literature = {
        "sme": "Sederberg et al. 2003 J Neurosci — theta/gamma at encode predict later recall",
        "consolidate": "Creery et al. 2022 PNAS — sleep markers / consolidation (partial here)",
    }
    brain, scalpel_rep, meta = build_scalpel_brain(
        profile="ai_efficient", device=device, tol=0.02
    )
    notes.append(f"scalpel_ok={getattr(scalpel_rep, 'ok', None)} meta={meta}")

    learn = learning_probe(
        brain,
        n_items=n_items,
        encode_steps=280,
        retrieve_steps=220,
        delay_steps=delay_steps,
        consolidate=True,
        consolidate_rest_steps=200,
        item_mode="fsot_machine",
        seed=7,
    )
    chance = 1.0 / max(1, n_items)
    gates = {
        "scalpel_brain": bool(getattr(scalpel_rep, "ok", False)),
        "top1_above_chance": learn.top1_accuracy > chance,
        "top1_ge_half": learn.top1_accuracy >= 0.5,
        "sme_theta_encode_gt_rest": bool(learn.sme_theta_encode_gt_rest),
        "sme_gamma_encode_gt_rest": bool(learn.sme_gamma_encode_gt_rest),
        "sim_plus_gt_sim_minus": learn.mean_correct_sim > learn.mean_incorrect_sim,
    }
    # partial consolidation metric if present
    if learn.top1_after_consolidate == learn.top1_after_consolidate:  # not NaN
        gates["consolidate_top1_ge_chance"] = learn.top1_after_consolidate > chance

    metrics = {
        "n_items": n_items,
        "delay_steps": delay_steps,
        "top1": learn.top1_accuracy,
        "chance": chance,
        "mean_correct_sim": learn.mean_correct_sim,
        "mean_incorrect_sim": learn.mean_incorrect_sim,
        "top1_after_consolidate": learn.top1_after_consolidate,
        "sme_theta": learn.sme_theta_encode_gt_rest,
        "sme_gamma": learn.sme_gamma_encode_gt_rest,
    }
    # fidelity band estimate for learning layer (not overall organism)
    n_ok = sum(1 for v in gates.values() if v)
    fidelity_est = n_ok / max(1, len(gates))
    metrics["learning_layer_fidelity_est"] = fidelity_est
    notes.append(
        f"Learning-layer gate pass {n_ok}/{len(gates)} "
        f"(SME direction + retrieval; not film comprehension)."
    )
    ok = gates["sme_theta_encode_gt_rest"] and gates["sme_gamma_encode_gt_rest"] and gates["top1_above_chance"]
    return LearningBioResult(ok=ok, gates=gates, metrics=metrics, literature=literature, notes=notes)
