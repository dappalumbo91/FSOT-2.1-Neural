#!/usr/bin/env python3
"""
Biological equivalence scorecard + multi-species motifs + frontier probes.

  python run_bio_equivalence_scorecard.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    from fsot_nuron.archive_pin import pin_archive
    from fsot_nuron.fsot_bridge import verify_fsot_bridge
    from fsot_nuron.sensory.bio_pathways import audit_bio_sensory
    from fsot_nuron.benchmarks.learning_bio import run_learning_bio_benchmark
    from fsot_nuron.benchmarks.frontier_probes import run_frontier_probes
    from fsot_nuron.species.fly_connectome import fly_motif_report
    from fsot_nuron.brain_architecture import (
        FSOTBrainDesign,
        BrainDesignConfig,
        BRAIN_PROFILES,
        DEFAULT_PROJECTIONS,
    )
    from fsot_nuron.paths import ARTIFACTS

    print("=== FSOT biological equivalence scorecard ===")
    print("Functional fidelity under named mappings — not 'silicon is living tissue'.\n")

    pin = pin_archive(write_snapshot=False)
    br = verify_fsot_bridge()
    sensory = audit_bio_sensory()
    print(f"pin={pin.connected} bridge_free={br.get('free_parameters')} sensory_ok={sensory.ok}")

    print("\n[1] Learning dynamics (Sederberg-style SME + retrieval)…")
    learn = run_learning_bio_benchmark(n_items=8, delay_steps=150)
    for k, v in learn.gates.items():
        print(f"  [{'Y' if v else 'N'}] {k}")
    print(f"  top1={learn.metrics.get('top1'):.3f} learning_fidelity_est={learn.metrics.get('learning_layer_fidelity_est'):.2f}")

    print("\n[2] Fly / multi-species motif comparison…")
    brain = FSOTBrainDesign(
        BrainDesignConfig(
            regions=list(BRAIN_PROFILES["ai_efficient"]["regions"]),
            projections=list(DEFAULT_PROJECTIONS),
            seed=7,
            device="cpu",
        )
    )
    fly = fly_motif_report(brain)
    sc = fly["score"]
    print(f"  n={sc['n_units']} edges={sc['n_edges']} density={sc['density']:.4f} recip={sc['reciprocity']:.3f}")
    print(f"  hub_frac={sc['hub_edge_fraction']:.3f} recip_in_fly_band={sc['vs_fly']['reciprocity_in_fly_band']}")
    print(f"  lesson: {fly['literature']['computer_centric_lesson'][:80]}…")

    print("\n[3] Frontier probes (progress only — claims stay non-green)…")
    fr = run_frontier_probes(
        pattern_census={"action": 5, "dialogue": 1, "person": 2, "music": 4},
        plain_english="Patterns linked to dialogue and action. Knowledge compact to trinary.",
    )
    for name, blob in fr.probes.items():
        print(f"  {name}: { {k: blob[k] for k in list(blob)[:6]} }")

    # Layer scorecard (documented bands)
    layers = {
        "cell_class_rates": {"band": "95-99%", "note": "Allen scalpel/precision (separate runners)"},
        "sensory_routing": {
            "band": "55-70%",
            "score": 1.0 if sensory.ok else 0.0,
            "note": "bio_pathways seed-lawful",
        },
        "learning_dynamics": {
            "band": "45-60%",
            "score": learn.metrics.get("learning_layer_fidelity_est"),
            "note": "SME + retrieval gates",
        },
        "film_semantics": {
            "band": "15-35%",
            "score": None,
            "note": "association+subtitles early; not human comprehension",
        },
        "open_world_pixel_id": {
            "band": "0-10%",
            "score": fr.probes["open_world_pixel_identity"].get("pixel_id_top1"),
            "note": "synthetic probe only",
        },
    }

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pin": {"connected": pin.connected, "mode": getattr(pin, "pin_mode", "")},
        "bridge_free_parameters": br.get("free_parameters"),
        "sensory_audit": sensory.to_dict(),
        "learning": learn.to_dict(),
        "fly_motifs": fly,
        "frontier_probes": fr.to_dict(),
        "layer_scorecard": layers,
        "doctrine": [
            "docs/BIO_EQUIVALENCE_DISTANCE.md",
            "docs/BIO_SENSORY_SYSTEM.md",
            "docs/MULTI_SPECIES_COMPUTER_CENTRIC.md",
            "docs/CAPABILITY_FRONTIER.md",
        ],
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    jp = ARTIFACTS / "bio_equivalence_scorecard.json"
    jp.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")

    md = ROOT / "data" / "results" / "BIO_EQUIVALENCE_SCORECARD.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Biological equivalence scorecard",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        "Functional fidelity under named mapping — implements what sensory systems *do*,",
        "not a claim that silicon *is* living retina/tissue.",
        "",
        "## Layer bands (honest)",
        "",
        "| Layer | ~fidelity band | note |",
        "|-------|----------------|------|",
    ]
    for k, v in layers.items():
        lines.append(f"| {k} | {v.get('band')} | {v.get('note')} |")
    lines += [
        "",
        f"## Learning gates: **{sum(learn.gates.values())}/{len(learn.gates)}** pass · ok={learn.ok}",
        "",
        f"- top1={learn.metrics.get('top1'):.3f} (chance={learn.metrics.get('chance'):.3f})",
        f"- SME θ/γ encode>rest: {learn.metrics.get('sme_theta')} / {learn.metrics.get('sme_gamma')}",
        "",
        "## Fly motif snapshot",
        "",
        f"- density={sc['density']:.4f} reciprocity={sc['reciprocity']:.3f} hub_frac={sc['hub_edge_fraction']:.3f}",
        f"- reciprocity_in_fly_band={sc['vs_fly']['reciprocity_in_fly_band']}",
        "",
        f"JSON: `{jp}`",
        "",
        "See docs/BIO_EQUIVALENCE_DISTANCE.md",
        "",
    ]
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {jp}")
    print(f"Wrote {md}")
    return 0 if learn.ok and sensory.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
