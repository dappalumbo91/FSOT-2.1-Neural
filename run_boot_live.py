#!/usr/bin/env python3
"""
Lab boot: pin + short-horizon media probes.

NEURAL AUTHORITY is Zig — see run_mind_boot.py / docs/ZIG_MIND_AUTHORITY.md.
This script no longer steps Python FSOTBrainDesign as the live mind; it only
runs optional lab media/5W1H probes after spawning the Zig mind host.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    from fsot_nuron.archive_pin import pin_archive
    from fsot_nuron.sensory.bio_pathways import audit_bio_sensory
    from fsot_nuron.learn.short_horizon import run_short_horizon_learn
    from fsot_nuron.knowledge.visual_individual import run_visual_individual_probe

    print("=== FSOT BOOT / LIVE ===")
    print("NOTE: mind dynamics → Zig (run_mind_boot.py). This path is lab media only.\n")

    # 1) Zig mind authority first
    mind_code = 0
    try:
        from run_mind_boot import run_zig_mind

        mind_code = run_zig_mind("all")
    except SystemExit as e:
        mind_code = int(e.code or 1)
    except Exception as e:
        print(f"Zig mind boot failed: {e}", file=sys.stderr)
        mind_code = 1
    if mind_code != 0:
        print("MIND FAIL — aborting lab media stack", file=sys.stderr)
        return mind_code

    pin = pin_archive(write_snapshot=False)
    print(
        f"[lab] pin connected={pin.connected} mode={getattr(pin, 'pin_mode', '')} "
        f"seed_ok={pin.seed_match_ok}"
    )
    sha = (pin.cert_authority_sha256 or "")[:20]
    print(f"[lab] authority {sha}…")

    aud = audit_bio_sensory()
    print(
        f"[lab] bio_sensory ok={aud.ok} free_params={aud.free_parameters} "
        f"gate={aud.consciousness_gate:.4f}"
    )
    print(f"  gains primary={aud.pathway_gains.get('primary'):.4f} "
          f"relay={aud.pathway_gains.get('relay'):.4f}")

    print("Zig MIND OK — optional lab short-horizon + visual individuals…\n")

    print("=== SHORT-HORIZON LEARN (5W1H) ===")
    sh = run_short_horizon_learn(
        max_docs=3,
        max_videos=3,
        media_frames=8,
        run_pixel_id=True,
        run_learning_probe=True,
        run_caption_bind=True,
    )
    print(f"ok={sh.ok} elapsed_min={sh.encode_minutes_est:.2f}")
    print(f"recall top1={sh.recall_top1:.3f} @3={sh.recall_at_k:.3f}")
    print(
        f"pixel_id={sh.pixel_id_top1:.3f} caption_bind={sh.caption_bind_top1:.3f} "
        f"names={sh.caption_bind_names}"
    )
    print(
        f"learning_probe top1={sh.learning_probe_top1:.3f} "
        f"SME θ/γ={sh.sme_theta}/{sh.sme_gamma}"
    )
    print(f"memories={sh.n_memory} docs={sh.n_docs} media={sh.n_media}")

    print("\n=== VISUAL INDIVIDUAL (look first) ===")
    viu = run_visual_individual_probe(max_videos=4, max_frames=20, seed=7)
    print(f"ok={viu.ok}")
    print(
        f"VIU re-ID top1={viu.viu_reid_top1:.3f} chance≈{viu.viu_reid_chance:.3f} "
        f"heldout={viu.n_heldout}"
    )
    print(
        f"unique-name={viu.unique_name_top1:.3f} trials={viu.n_unique_name_trials} "
        f"n_viu={viu.n_viu} named={viu.n_named_viu}"
    )
    for n in viu.notes[-4:]:
        print(f"  · {n}")

    print("\n=== LIVE STACK COMPLETE ===")
    print("artifacts: short_horizon_last.json, visual_individuals_last.json")
    print("results: data/results/SHORT_HORIZON_LEARN.md, VISUAL_INDIVIDUAL.md")
    return 0 if (pin.connected and sh.ok and viu.ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
