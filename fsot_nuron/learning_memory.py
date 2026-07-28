"""
Encode → retain → retrieve probe on FSOT multi-region brains.

Intelligence path grounded in accurate neuron dynamics:
  - items = trinary / float feature patterns (sensory inject)
  - encode under FI + pattern drive
  - store regional fingerprints (mean S, spike duty, band proxies)
  - retrieve by nearest-fingerprint under cue
  - SME-style: band power during encode vs later success

Biological time only (dt_ms). See docs/LEARNING_ALIGNMENT.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch

from .learning_bands import band_powers_from_fired, encoding_vs_rest_report
from .trinary_substrate import quantize_features_to_trits


def _cosine(a: torch.Tensor, b: torch.Tensor) -> float:
    a = a.flatten().float()
    b = b.flatten().float()
    na = torch.linalg.vector_norm(a)
    nb = torch.linalg.vector_norm(b)
    if float(na) < 1e-12 or float(nb) < 1e-12:
        return 0.0
    return float((a @ b) / (na * nb))


def make_item_patterns(
    n_items: int,
    feat_dim: int = 12,
    seed: int = 7,
) -> List[Dict[str, Any]]:
    """Deterministic item set: continuous features + trit quantize (legacy baseline)."""
    g = torch.Generator().manual_seed(seed)
    items = []
    for i in range(n_items):
        feat = torch.randn(feat_dim, generator=g)
        feat = feat / (feat.norm() + 1e-8)
        trits = quantize_features_to_trits(feat.tolist())
        items.append(
            {
                "id": i,
                "label": f"item_{i}",
                "features": feat.tolist(),
                "trits": trits,
                "source": "random_gaussian",
            }
        )
    return items


# Fixed vocabulary — machine-path text labels (not Morse), seed-indexed order
_FSOT_ITEM_VOCAB = (
    "alpha wave",
    "beta spike",
    "theta nest",
    "gamma burst",
    "hippocampus map",
    "sensory gate",
    "codon ATG start",
    "FSOT scalar K",
    "trinary fold",
    "neural substrate",
    "allen pyramid",
    "pv basket",
    "sst martinotti",
    "vip disinhibit",
    "machine word pack",
    "biology fold twelve",
)


def make_fsot_item_patterns(
    n_items: int,
    feat_dim: int = 12,
    seed: int = 7,
) -> List[Dict[str, Any]]:
    """
    Memory items through FSOT doctrine (not random free features):

      text label → machine lossless bit→trit (OS body)
                → bridge_machine_payload (Computer_Body fold → S)
                → couple_features_with_S
                → encode drive from sensory_strength

    Archive math modulates the domain engine; features stay real vectors.
    """
    from .machine_encode import text_to_utf8_trits, trits_to_drive_features
    from .fsot_bridge import bridge_machine_payload, couple_features_with_S
    from .seeds import SEEDS

    items: List[Dict[str, Any]] = []
    # rotate vocab by seed for determinism without free noise
    rot = int(seed) % len(_FSOT_ITEM_VOCAB)
    for i in range(n_items):
        base = _FSOT_ITEM_VOCAB[(rot + i) % len(_FSOT_ITEM_VOCAB)]
        label = f"{base} #{i}"
        br = bridge_machine_payload(label)
        mods = br["modulators"]
        trits = text_to_utf8_trits(label)
        feats = trits_to_drive_features(trits, n_features=feat_dim)
        feats = couple_features_with_S(feats, mods)
        # unit L2 for stable cosine retrieve (domain hygiene, not free fit)
        t = torch.tensor(feats, dtype=torch.float64)
        t = t / (t.norm() + 1e-8)
        strength = float(mods["sensory_strength"])
        # pattern strength seed-folded from gain + poof (fixed seeds only)
        pattern_strength = float(
            0.35 * SEEDS.phi / SEEDS.e + 0.20 * float(mods.get("feature_gain", 1.0))
        )
        pattern_strength = max(0.25, min(0.75, pattern_strength))
        items.append(
            {
                "id": i,
                "label": label,
                "features": t.tolist(),
                "trits": [int(x) for x in trits[:feat_dim]],
                "source": "fsot_machine_bridge",
                "drive_amp": strength,
                "pattern_strength": pattern_strength,
                "fsot": {
                    "fold": br["fold"],
                    "S": mods["S"],
                    "trit": mods["trit"],
                    "sensory_strength": strength,
                    "bridge": br["bridge"],
                },
            }
        )
    return items


@dataclass
class MemoryTrace:
    item_id: int
    fingerprint: torch.Tensor
    encode_bands: Dict[str, float]
    encode_mean_rate: float


@dataclass
class LearningReport:
    n_items: int
    top1_accuracy: float
    mean_correct_sim: float
    mean_incorrect_sim: float
    sme_theta_encode_gt_rest: bool
    sme_gamma_encode_gt_rest: bool
    delay_steps: int = 0
    consolidate: bool = False
    consolidate_steps: int = 0
    replay_rounds: int = 0
    top1_immediate: float = float("nan")  # accuracy if probed before delay (optional)
    top1_after_delay: float = float("nan")
    top1_after_consolidate: float = float("nan")
    consolidate_sigma_rel: float = float("nan")
    per_item: List[Dict[str, Any]] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def fingerprint_from_hist(
    hist: Dict[str, torch.Tensor],
    region_index: Dict[str, List[int]],
    onset: int = 0,
) -> torch.Tensor:
    """
    Concatenate per-region mean S and mean spike duty over [onset:).
    """
    S = hist["S"][onset:]  # [T, B]
    fired = hist["fired"][onset:].float()
    parts = []
    for rid in sorted(region_index.keys()):
        ids = region_index[rid]
        if not ids:
            continue
        idx = torch.tensor(ids, device=S.device)
        parts.append(S[:, idx].mean(dim=0))  # [n_reg]
        parts.append(fired[:, idx].mean(dim=0))
    if not parts:
        parts = [S.mean(dim=0), fired.mean(dim=0)]
    return torch.cat(parts).detach().cpu()


def run_encode_epoch(
    brain,
    item: Dict[str, Any],
    *,
    steps: int = 400,
    drive_amp: float = 0.55,
    pattern_strength: float = 0.45,
) -> Tuple[Dict[str, torch.Tensor], MemoryTrace]:
    """
    Encode one item: thalamic pulse + pattern drive into sens/assoc.
    Uses brain.step loop (same dynamics as design suite).
    """
    brain.reset()
    n = brain.n_units
    feats = item["features"]
    # Per-item FSOT modulators when present (machine bridge → strength)
    drive_amp = float(item.get("drive_amp", drive_amp))
    pattern_strength = float(item.get("pattern_strength", pattern_strength))
    sens_ids = brain.region_index.get("sens", [])
    assoc_ids = brain.region_index.get("assoc", [])
    thal_ids = brain.region_index.get("thal", [])

    hist_S = torch.empty(steps, n, device=brain.device, dtype=brain.net.dtype)
    hist_f = torch.empty(steps, n, device=brain.device, dtype=torch.bool)
    hist_syn = torch.empty(steps, n, device=brain.device, dtype=brain.net.dtype)

    for t in range(steps):
        ext = torch.zeros(n, device=brain.device, dtype=brain.net.dtype)
        # theta-ish packet: 80 ms period, 25% duty on thalamus
        if (t % 80) < 20:
            for i in thal_ids:
                ext[i] = drive_amp if brain.units[i].synapse_sign > 0 else drive_amp * 0.25
        # continuous pattern into sensory / association (encoding content)
        for k, uid in enumerate(sens_ids):
            ext[uid] = ext[uid] + pattern_strength * float(feats[k % len(feats)])
        for k, uid in enumerate(assoc_ids):
            ext[uid] = ext[uid] + 0.7 * pattern_strength * float(feats[k % len(feats)])
        ext = ext.clamp(-0.8, 1.5)
        S, fired, _, _, syn = brain.step(ext)
        hist_S[t] = S
        hist_f[t] = fired
        hist_syn[t] = syn

    hist = {
        "S": hist_S,
        "fired": hist_f,
        "synaptic": hist_syn,
        "firing_rate_Hz": hist_f.float().sum(0) / (steps * brain.cfg.dt_ms / 1000.0),
    }
    fp = fingerprint_from_hist(hist, brain.region_index, onset=50)
    bands = band_powers_from_fired(hist_f)
    trace = MemoryTrace(
        item_id=int(item["id"]),
        fingerprint=fp,
        encode_bands=bands,
        encode_mean_rate=float(hist["firing_rate_Hz"].mean().item()),
    )
    return hist, trace


def run_retrieve_epoch(
    brain,
    cue_item: Dict[str, Any],
    *,
    steps: int = 300,
    pattern_strength: float = 0.35,
) -> torch.Tensor:
    """Cue with partial/weaker pattern; return fingerprint for matching."""
    brain.reset()
    n = brain.n_units
    feats = cue_item["features"]
    # partial cue: zero out last third of features
    cue = list(feats)
    cut = max(1, (2 * len(cue)) // 3)
    for i in range(cut, len(cue)):
        cue[i] = 0.0

    sens_ids = brain.region_index.get("sens", [])
    assoc_ids = brain.region_index.get("assoc", [])
    thal_ids = brain.region_index.get("thal", [])

    hist_S = torch.empty(steps, n, device=brain.device, dtype=brain.net.dtype)
    hist_f = torch.empty(steps, n, device=brain.device, dtype=torch.bool)

    for t in range(steps):
        ext = torch.zeros(n, device=brain.device, dtype=brain.net.dtype)
        if (t % 80) < 15:
            for i in thal_ids:
                if brain.units[i].synapse_sign > 0:
                    ext[i] = 0.45
        for k, uid in enumerate(sens_ids):
            ext[uid] = ext[uid] + pattern_strength * float(cue[k % len(cue)])
        for k, uid in enumerate(assoc_ids):
            ext[uid] = ext[uid] + 0.5 * pattern_strength * float(cue[k % len(cue)])
        S, fired, _, _, _ = brain.step(ext.clamp(-0.8, 1.5))
        hist_S[t] = S
        hist_f[t] = fired

    hist = {"S": hist_S, "fired": hist_f}
    return fingerprint_from_hist(hist, brain.region_index, onset=40)


def _run_rest(brain, steps: int) -> torch.Tensor:
    """Pure rest (external 0). Returns fired [T,B]."""
    brain.reset()
    n = brain.n_units
    rest_f = torch.empty(steps, n, device=brain.device, dtype=torch.bool)
    for t in range(steps):
        _, fired, _, _, _ = brain.step(0.0)
        rest_f[t] = fired
    return rest_f


def offline_consolidate(
    brain,
    items: List[Dict[str, Any]],
    *,
    rest_steps: int = 400,
    replay_rounds: int = 2,
    replay_steps: int = 120,
    replay_strength: float = 0.22,
) -> Dict[str, Any]:
    """
    Sleep-like offline consolidation (Creery-style direction, computational):

    1) Quiet rest (low drive)
    2) Soft replay of stored item patterns (hipp/assoc bias)
    3) Optional second rest

    Does not free-fit W; uses existing recurrent structure + weak re-inject.
    """
    n = brain.n_units
    sens_ids = brain.region_index.get("sens", [])
    assoc_ids = brain.region_index.get("assoc", [])
    hipp_ids = brain.region_index.get("hipp", [])
    thal_ids = brain.region_index.get("thal", [])

    # Rest epoch 1
    rest1 = _run_rest(brain, rest_steps)
    bands_rest1 = band_powers_from_fired(rest1)

    # Replay rounds (offline reactivation)
    replay_fires = []
    for _rnd in range(max(0, replay_rounds)):
        for it in items:
            feats = it["features"]
            brain.reset()
            hist_f = torch.empty(replay_steps, n, device=brain.device, dtype=torch.bool)
            for t in range(replay_steps):
                ext = torch.zeros(n, device=brain.device, dtype=brain.net.dtype)
                # sparse thalamic "spindle-like" packets
                if (t % 90) < 12:
                    for i in thal_ids:
                        if brain.units[i].synapse_sign > 0:
                            ext[i] = 0.28
                # soft pattern into hipp + assoc (reactivation)
                for k, uid in enumerate(hipp_ids):
                    ext[uid] = ext[uid] + replay_strength * float(feats[k % len(feats)])
                for k, uid in enumerate(assoc_ids):
                    ext[uid] = ext[uid] + 0.8 * replay_strength * float(feats[k % len(feats)])
                for k, uid in enumerate(sens_ids):
                    ext[uid] = ext[uid] + 0.35 * replay_strength * float(feats[k % len(feats)])
                _, fired, _, _, _ = brain.step(ext.clamp(-0.8, 1.2))
                hist_f[t] = fired
            replay_fires.append(hist_f)

    bands_replay = {}
    if replay_fires:
        rf = torch.cat(replay_fires, dim=0)
        bands_replay = band_powers_from_fired(rf)

    rest2 = _run_rest(brain, max(100, rest_steps // 2))
    bands_rest2 = band_powers_from_fired(rest2)

    return {
        "rest_steps": rest_steps,
        "replay_rounds": replay_rounds,
        "replay_steps": replay_steps,
        "bands_rest1": bands_rest1,
        "bands_replay": bands_replay,
        "bands_rest2": bands_rest2,
        "sigma_rel_replay": bands_replay.get("sigma_rel", float("nan")),
        "gamma_rel_replay": bands_replay.get("gamma_rel", float("nan")),
        "theta_rel_replay": bands_replay.get("theta_rel", float("nan")),
    }


def _retrieve_all(
    brain,
    items: List[Dict[str, Any]],
    memories: List[MemoryTrace],
    retrieve_steps: int,
) -> Tuple[float, float, float, List[Dict[str, Any]]]:
    """Returns top1, mean_correct_sim, mean_incorrect_sim, per_item."""
    per_item = []
    correct = 0
    correct_sims: List[float] = []
    incorrect_sims: List[float] = []
    n_items = len(items)
    for true_i, it in enumerate(items):
        q = run_retrieve_epoch(brain, it, steps=retrieve_steps)
        sims = [_cosine(q, m.fingerprint) for m in memories]
        pred = int(max(range(len(sims)), key=lambda j: sims[j]))
        ok = pred == true_i
        if ok:
            correct += 1
            correct_sims.append(sims[true_i])
        else:
            incorrect_sims.append(sims[true_i])
        for j, s in enumerate(sims):
            if j != true_i:
                incorrect_sims.append(s)
        per_item.append(
            {
                "item_id": true_i,
                "predicted": pred,
                "correct": ok,
                "sims": sims,
                "encode_theta_rel": memories[true_i].encode_bands.get("theta_rel"),
                "encode_gamma_rel": memories[true_i].encode_bands.get("gamma_rel"),
            }
        )
    n = max(1, n_items)
    return (
        correct / n,
        sum(correct_sims) / len(correct_sims) if correct_sims else 0.0,
        sum(incorrect_sims) / len(incorrect_sims) if incorrect_sims else 0.0,
        per_item,
    )


def learning_probe(
    brain,
    *,
    n_items: int = 6,
    encode_steps: int = 400,
    retrieve_steps: int = 300,
    seed: int = 7,
    delay_steps: int = 0,
    consolidate: bool = False,
    consolidate_rest_steps: int = 400,
    replay_rounds: int = 2,
    replay_steps: int = 120,
    probe_immediate: bool = False,
    item_mode: str = "fsot_machine",
) -> LearningReport:
    """
    Encode-all → [optional immediate probe] → delay and/or offline consolidate
    → retrieve-each.

    item_mode:
      fsot_machine (default) — labels via machine encode + FSOT bridge couple
      random — legacy Gaussian features (baseline control)

    delay_steps: pure rest after encoding (retention delay in model-ms).
    consolidate: sleep-like rest + soft replay before final retrieve.
    """
    if item_mode in ("fsot_machine", "fsot", "machine"):
        items = make_fsot_item_patterns(n_items, seed=seed)
        mode_note = "items via FSOT machine bridge (Computer_Body → S couple)"
    else:
        items = make_item_patterns(n_items, seed=seed)
        mode_note = "items via random gaussian (legacy baseline)"
    memories: List[MemoryTrace] = []
    encode_hists = []

    for it in items:
        hist, tr = run_encode_epoch(brain, it, steps=encode_steps)
        memories.append(tr)
        encode_hists.append(hist)

    # rest baseline for SME-style bands
    rest_f = _run_rest(brain, 300)
    enc_fire = torch.cat([h["fired"] for h in encode_hists], dim=0)
    sme = encoding_vs_rest_report(enc_fire, rest_f)

    top1_imm = float("nan")
    if probe_immediate or (delay_steps > 0 or consolidate):
        # baseline immediate accuracy when testing retention/consolidation
        top1_imm, _, _, _ = _retrieve_all(brain, items, memories, retrieve_steps)

    # Retention delay (wake-like idle)
    top1_delay = float("nan")
    if delay_steps > 0:
        _run_rest(brain, delay_steps)
        if not consolidate:
            top1_delay, csim, isim, per_item = _retrieve_all(
                brain, items, memories, retrieve_steps
            )
            return LearningReport(
                n_items=n_items,
                top1_accuracy=top1_delay,
                mean_correct_sim=csim,
                mean_incorrect_sim=isim,
                sme_theta_encode_gt_rest=bool(sme.get("theta_encode_gt_rest")),
                sme_gamma_encode_gt_rest=bool(sme.get("gamma_encode_gt_rest")),
                delay_steps=delay_steps,
                consolidate=False,
                top1_immediate=top1_imm,
                top1_after_delay=top1_delay,
                per_item=per_item,
                notes=(
                    f"{mode_note}. Retention delay {delay_steps} model-ms "
                    "(no offline replay)."
                ),
            )
        # if consolidate after delay, record mid-probe optionally cheap skip
        top1_delay, _, _, _ = _retrieve_all(brain, items, memories, retrieve_steps)

    if consolidate:
        consol_meta = offline_consolidate(
            brain,
            items,
            rest_steps=consolidate_rest_steps,
            replay_rounds=replay_rounds,
            replay_steps=replay_steps,
        )
        top1_cons, csim, isim, per_item = _retrieve_all(
            brain, items, memories, retrieve_steps
        )
        return LearningReport(
            n_items=n_items,
            top1_accuracy=top1_cons,
            mean_correct_sim=csim,
            mean_incorrect_sim=isim,
            sme_theta_encode_gt_rest=bool(sme.get("theta_encode_gt_rest")),
            sme_gamma_encode_gt_rest=bool(sme.get("gamma_encode_gt_rest")),
            delay_steps=delay_steps,
            consolidate=True,
            consolidate_steps=consolidate_rest_steps,
            replay_rounds=replay_rounds,
            top1_immediate=top1_imm,
            top1_after_delay=top1_delay,
            top1_after_consolidate=top1_cons,
            consolidate_sigma_rel=float(consol_meta.get("sigma_rel_replay") or float("nan")),
            per_item=per_item,
            notes=(
                f"{mode_note}. Offline consolidate: rest + soft replay; "
                f"sigma_rel_replay={consol_meta.get('sigma_rel_replay')}"
            ),
        )

    # Immediate retrieve (default path)
    top1, csim, isim, per_item = _retrieve_all(brain, items, memories, retrieve_steps)
    return LearningReport(
        n_items=n_items,
        top1_accuracy=top1,
        mean_correct_sim=csim,
        mean_incorrect_sim=isim,
        sme_theta_encode_gt_rest=bool(sme.get("theta_encode_gt_rest")),
        sme_gamma_encode_gt_rest=bool(sme.get("gamma_encode_gt_rest")),
        delay_steps=0,
        consolidate=False,
        top1_immediate=top1,
        per_item=per_item,
        notes=(
            f"{mode_note}. Fingerprint retrieval on multi-region FSOT brain; "
            "not a transformer LM. Wet-lab class rates locked separately via scalpel."
        ),
    )
