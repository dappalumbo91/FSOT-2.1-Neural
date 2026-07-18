"""
Auto wire-around policy: map observed failure signature hits → actions.

Used after lesion probes so the substrate selects recovery strategy
from what actually broke, not only the catalog default.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


# Signature → candidate actions (priority order)
SIGNATURE_ACTIONS: Dict[str, List[str]] = {
    "rate_drop": ["boost_fi_stim_on_survivors", "lower_adapt_step", "shorten_ref_on_healthy"],
    "rate_runaway": ["raise_fire_thr", "increase_adapt_step", "consensus_collapse_gate"],
    "isi_prolonged": ["shorten_ref_on_healthy", "boost_fi_stim_on_survivors", "subms_timing_compensate"],
    "adaptation_runaway": ["lower_adapt_step", "boost_fi_stim_on_survivors"],
    "adaptation_collapse": ["increase_adapt_step", "raise_fire_thr"],
    "global_silence": ["checkpoint_restore_revive", "boost_fi_stim_on_survivors", "lower_fire_thr"],
    "population_sparsity": ["recruit_reserve_units", "load_balance_consensus", "boost_fi_stim_on_survivors"],
    "survivor_hyperexcitability": ["cap_survivor_rate", "raise_fire_thr", "increase_adapt_step"],
    "late_silence": ["recruit_reserve_units", "boost_fi_stim_on_survivors"],
    "progressive_sparsity": ["consensus_quarantine_failed", "isolate_hot_units", "load_balance_consensus"],
    "isi_cv_high": ["clamp_isi_cv", "inject_phase_noise", "consensus_sparse_gate"],
    "burst_clustering": ["inject_phase_noise", "clamp_isi_cv", "raise_fire_thr"],
    "s_collapse": ["checkpoint_restore_revive", "lower_metabolic_load"],
    "emergent_fraction_drop": ["boost_fi_stim_on_survivors", "lower_adapt_step"],
}

STRATEGY_FROM_DOMINANT: Dict[str, str] = {
    "rate_runaway": "inhibitory_clamp",
    "global_silence": "checkpoint_restore",
    "population_sparsity": "recruit_reserve_pool",
    "progressive_sparsity": "quarantine_and_reroute",
    "isi_cv_high": "desync_and_regularize",
    "burst_clustering": "desync_and_regularize",
    "isi_prolonged": "parallel_paths",
    "rate_drop": "distributed_redundancy",
    "adaptation_runaway": "distributed_redundancy",
    "s_collapse": "checkpoint_restore",
}


def select_wire_around(
    signature_hits: Sequence[str],
    *,
    relative_flags: Optional[Dict[str, bool]] = None,
    catalog_default: Optional[Dict[str, Any]] = None,
    max_actions: int = 5,
) -> Dict[str, Any]:
    """
    Build an action list from signature hits. Falls back to catalog_default.
    """
    hits = list(signature_hits or [])
    if relative_flags:
        for k, v in relative_flags.items():
            if v and k not in hits:
                hits.append(k)

    scored: Dict[str, float] = {}
    for h in hits:
        for i, act in enumerate(SIGNATURE_ACTIONS.get(h, [])):
            scored[act] = scored.get(act, 0.0) + (1.0 / (1 + i))

    # merge catalog defaults at lower weight
    if catalog_default:
        for i, act in enumerate(catalog_default.get("actions") or []):
            scored[act] = scored.get(act, 0.0) + 0.35 / (1 + i)

    actions = [a for a, _ in sorted(scored.items(), key=lambda x: -x[1])][:max_actions]

    strategy = None
    for h in hits:
        if h in STRATEGY_FROM_DOMINANT:
            strategy = STRATEGY_FROM_DOMINANT[h]
            break
    if not strategy and catalog_default:
        strategy = catalog_default.get("strategy")
    if not strategy:
        strategy = "distributed_redundancy"

    return {
        "strategy": strategy,
        "actions": actions,
        "from_signatures": hits,
        "auto": True,
        "score": scored,
    }


