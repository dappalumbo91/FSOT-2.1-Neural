#!/usr/bin/env python3
"""
Wet-lab class ephys: Allen Cre-line targets → FSOT cell-type population → gates.

Biological accuracy under public wet-lab authority (Allen Cell Types).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    import torch
    from fsot_nuron.class_ephys import (
        build_class_targets,
        class_order_gates,
        apply_class_targets_to_genotype_phenotype,
    )
    from fsot_nuron.cell_types import build_typed_population, CELL_TYPES
    from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
    from fsot_nuron.bio_metrics import population_profiles, summarize_profiles
    from fsot_nuron.thesis_ledger import record_run
    from fsot_nuron.paths import ARTIFACTS, DATA

    print("=== FSOT class ephys (Allen wet-lab Cre lines) ===")
    print("Authority: public Allen Cell Types cells.json + ephys fields")
    print("Goal: biological class order (PV faster than Pyr), not 'fake wet lab identity'")

    targets = build_class_targets(min_cells=15, mouse_only=True)
    if not targets:
        print("FAIL: no class targets (cells.json missing?)")
        return 1

    print("\n--- Wet-lab class targets (mouse) ---")
    for k, t in sorted(targets.items()):
        print(
            f"  {k:4} n={t.n_cells:4}  ISI={t.mean_isi_ms:6.2f} ms  "
            f"rate={t.mean_rate_Hz:6.2f} Hz  adapt={t.mean_adapt:.4f}  "
            f"Vrest={t.mean_vrest_mV:.1f}"
        )

    wet_gates = class_order_gates(targets)
    print("\n--- Wet-lab order (data itself) ---")
    for k, v in wet_gates.items():
        print(f"  {k}: {v}")

    # Build typed population locked to class wet-lab timing
    n_units = 64
    genotypes = build_typed_population(n_units, seed=42, diversity=True)
    cfg = NeuronConfig(n_units=n_units)
    net = FSOTNeuronBatch(cfg, device="cpu")

    refs, thr, d_eff, vrest, fi, ad_step, again, adec = [], [], [], [], [], [], [], []
    labels = []
    for g in genotypes:
        ct = getattr(g, "cell_type", "Pyr")
        labels.append(ct)
        ph = apply_class_targets_to_genotype_phenotype(ct, g.phenotype, targets, mode="bio_match")
        refs.append(int(round(ph["refractory_steps"])))
        thr.append(ph["fire_threshold"])
        d_eff.append(ph["d_eff"])
        vrest.append(ph.get("vrest_mV", -70.0))
        fi.append(ph["fi_stim"])
        ad_step.append(ph["adapt_step"])
        again.append(ph["adapt_gain"])
        adec.append(ph["adapt_decay"])

    net.apply_bio_params(
        d_eff=torch.tensor(d_eff, dtype=net.dtype),
        fire_threshold=torch.tensor(thr, dtype=net.dtype),
        vrest_mV=torch.tensor(vrest, dtype=net.dtype),
        adapt_gain=torch.tensor(again, dtype=net.dtype),
        adapt_decay=torch.tensor(adec, dtype=net.dtype),
        refractory_steps=torch.tensor(refs, dtype=torch.int32),
        fi_stim=torch.tensor(fi, dtype=net.dtype),
        adapt_step=torch.tensor(ad_step, dtype=net.dtype),
        mode_name="allen_class_lock",
    )

    net.reset()
    hist = net.run(1200, stimulus_pattern="fi_step", record=True)
    rates = hist["firing_rate_Hz"].detach().cpu().tolist()
    profiles = population_profiles(hist["fired"], hist["S"])

    by_type: Dict[str, List[float]] = {}
    isi_by: Dict[str, List[float]] = {}
    for lab, rate, prof in zip(labels, rates, profiles):
        by_type.setdefault(lab, []).append(rate)
        if prof.mean_isi_ms == prof.mean_isi_ms:
            isi_by.setdefault(lab, []).append(prof.mean_isi_ms)

    def mean(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    print("\n--- FSOT sim class rates (FI step) ---")
    sim_rate = {k: mean(v) for k, v in by_type.items()}
    sim_isi = {k: mean(v) for k, v in isi_by.items()}
    for k in sorted(sim_rate.keys()):
        print(f"  {k:4} rate={sim_rate[k]:6.2f} Hz  ISI={sim_isi.get(k, float('nan')):6.2f} ms  n={len(by_type[k])}")

    # relative rate error vs wet-lab class means (when both exist)
    rel = {}
    for k in ("Pyr", "PV", "SST", "VIP"):
        if k in targets and k in sim_rate and targets[k].mean_rate_Hz > 1:
            rel[k] = abs(sim_rate[k] - targets[k].mean_rate_Hz) / targets[k].mean_rate_Hz

    # Biological order + absolute fidelity gates (bio first, performance later)
    sim_gates = {
        "sim_pv_rate_gt_pyr": sim_rate.get("PV", 0) > sim_rate.get("Pyr", 1e9),
        "sim_pv_isi_lt_pyr": sim_isi.get("PV", 1e9) < sim_isi.get("Pyr", 0),
        "wet_lab_pv_faster_than_pyr": bool(wet_gates.get("pv_rate_gt_pyr")),
        "has_pv_target": "PV" in targets,
        "has_pyr_target": "Pyr" in targets,
        # Absolute wet-lab rate fidelity (relaxed bands while we climb)
        "pv_rate_within_35pct": rel.get("PV", 1.0) <= 0.35,
        "pyr_rate_within_35pct": rel.get("Pyr", 1.0) <= 0.35,
    }

    print("\n--- Gates ---")
    for k, v in sim_gates.items():
        print(f"  {k}: {v}")
    print(f"  rate_rel_err: { {k: round(v, 3) for k, v in rel.items()} }")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": "Allen Cell Types public wet-lab (cells.json Cre lines + ef__*)",
        "targets": {k: v.to_dict() for k, v in targets.items()},
        "wet_lab_order_gates": wet_gates,
        "sim_rate_Hz": sim_rate,
        "sim_isi_ms": sim_isi,
        "sim_gates": sim_gates,
        "rate_rel_err": rel,
        "note": (
            "Biological accuracy vs public wet-lab class statistics. "
            "Not a claim that the PC is a physical patch-clamp rig."
        ),
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "class_ephys_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    res = DATA / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "class_ephys_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    md = [
        "# Class ephys — Allen wet-lab → FSOT",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        "## Wet-lab targets (mouse Cre lines)",
        "",
    ]
    for k, t in sorted(targets.items()):
        md.append(
            f"- **{k}** (n={t.n_cells}): ISI {t.mean_isi_ms:.1f} ms, "
            f"rate {t.mean_rate_Hz:.1f} Hz, adapt {t.mean_adapt:.3f}"
        )
    md += [
        "",
        "## Simulation (class-locked FI)",
        "",
        *[f"- **{k}**: rate {sim_rate[k]:.1f} Hz, ISI {sim_isi.get(k, float('nan')):.1f} ms" for k in sorted(sim_rate)],
        "",
        "## Gates",
        "",
        *[f"- `{k}`: **{v}**" for k, v in sim_gates.items()],
        "",
        "See `docs/BIO_ACCURACY.md` for how we use wet-lab data without owning a lab.",
        "",
    ]
    (res / "CLASS_EPHYS.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {res / 'CLASS_EPHYS.md'}")

    # Learning-band proxies (model-Hz; independent of silicon wall-clock)
    from fsot_nuron.learning_bands import band_powers_from_fired, encoding_vs_rest_report

    bands_fi = band_powers_from_fired(hist["fired"])
    net.reset()
    hist_rest = net.run(600, stimulus_pattern="rest", record=True)
    sme = encoding_vs_rest_report(hist["fired"], hist_rest["fired"])
    print("\n--- Learning band proxies (model-Hz, not wall-clock) ---")
    print(f"  FI theta_rel={bands_fi.get('theta_rel'):.4f} gamma_rel={bands_fi.get('gamma_rel'):.4f}")
    print(f"  SME-style theta_encode>rest: {sme.get('theta_encode_gt_rest')} gamma: {sme.get('gamma_encode_gt_rest')}")

    record_run(
        "class_ephys_allen",
        profile="bio_match_class_lock",
        gates=sim_gates,
        metrics={
            "sim_rate": sim_rate,
            "sim_isi": sim_isi,
            "rate_rel_err": rel,
            "targets_n": {k: v.n_cells for k, v in targets.items()},
            "bands_fi": bands_fi,
            "sme_directional": {
                "theta": sme.get("theta_encode_gt_rest"),
                "gamma": sme.get("gamma_encode_gt_rest"),
            },
        },
        notes="Allen Cre-line wet-lab class lock; PV rate within 35%; learning band proxies",
    )

    ok = all(
        [
            sim_gates.get("has_pv_target"),
            sim_gates.get("has_pyr_target"),
            sim_gates.get("wet_lab_pv_faster_than_pyr"),
            sim_gates.get("sim_pv_rate_gt_pyr"),
            sim_gates.get("sim_pv_isi_lt_pyr"),
            sim_gates.get("pv_rate_within_35pct"),
            sim_gates.get("pyr_rate_within_35pct"),
        ]
    )
    print("\nPASS" if ok else "\nFAIL (class order / absolute wet-lab rate fidelity)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
