#!/usr/bin/env python3
"""
Biological + FSOT sensory system self-check.

  python run_bio_sensory_check.py
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
    from fsot_nuron.sensory.bio_pathways import (
        audit_bio_sensory,
        apply_bio_routing,
        pathway_gain,
        consciousness_gate,
        MODALITY_ROUTE,
    )
    from fsot_nuron.sensory.packets import SensoryPacket, SensoryModality
    from fsot_nuron.sensory.bus import SensoryBus
    from fsot_nuron.brain_architecture import (
        FSOTBrainDesign,
        BrainDesignConfig,
        BRAIN_PROFILES,
        DEFAULT_PROJECTIONS,
    )
    from fsot_nuron.archive_pin import pin_archive
    from fsot_nuron.fsot_bridge import verify_fsot_bridge, fold_diagnostics
    from fsot_nuron.paths import ARTIFACTS
    from fsot_nuron.capability_frontier import log_frontier

    print("=== FSOT bio-equivalent sensory check ===")
    pin = pin_archive(write_snapshot=False)
    br = verify_fsot_bridge()
    folds = fold_diagnostics()
    audit = audit_bio_sensory()

    print(f"pin: {pin.connected} mode={getattr(pin, 'pin_mode', '')}")
    print(f"bridge free_parameters={br.get('free_parameters')} ok={br.get('ok')}")
    print(f"consciousness_gate={audit.consciousness_gate:.6f} (φ/(1+φ))")
    print(f"pathway_gains={audit.pathway_gains}")
    print(f"audit.ok={audit.ok} free={audit.free_parameters}")

    gates = {
        "pin_connected": bool(pin.connected),
        "bridge_ok": bool(br.get("ok")),
        "bridge_zero_free": br.get("free_parameters") == 0,
        "audit_ok": audit.ok,
        "relay_lt_primary": audit.pathway_gains["relay"] < audit.pathway_gains["primary"],
        "vision_primary_sens": MODALITY_ROUTE["vision"]["primary"] == "sens",
        "audio_primary_sens": MODALITY_ROUTE["audio"]["primary"] == "sens",
        "intero_primary_thal": MODALITY_ROUTE["sys_metric"]["primary"] == "thal",
        "text_primary_assoc": MODALITY_ROUTE["text"]["primary"] == "assoc",
    }

    # Live inject: vision packet should hit thal + sens when bio_route
    pkt = SensoryPacket(
        modality=SensoryModality.VISION,
        target_region="sens",
        features=[0.5, 0.2, 0.1],
        strength=0.6,
    )
    routed = apply_bio_routing(pkt, couple_S=float(folds.get("S_Neuroscience") or 0.5))
    regions = {p.target_region for p in routed}
    gates["vision_routes_thal_and_sens"] = "thal" in regions and "sens" in regions
    print(f"vision bio-route regions={regions} n_packets={len(routed)}")

    # Bus + brain: prefer excitatory, finite drive
    prof = BRAIN_PROFILES["ai_efficient"]
    brain = FSOTBrainDesign(
        BrainDesignConfig(
            regions=list(prof["regions"]),
            projections=list(DEFAULT_PROJECTIONS),
            seed=7,
            device="cpu",
            dt_ms=0.5,
        )
    )
    bus = SensoryBus(bio_route=True)
    bus.push(pkt)
    bus.push_metric(
        __import__("fsot_nuron.sensory.packets", fromlist=["MetricPacket"]).MetricPacket(
            cpu_util=0.2, mem_util=0.3
        )
    )
    ext = bus.build_external(
        brain.n_units,
        brain.region_index,
        device=brain.device,
        dtype=brain.net.dtype,
        units=brain.units,
        couple_S=float(folds.get("S_Neuroscience") or 0.0),
    )
    gates["drive_finite"] = bool(ext.isfinite().all().item())
    gates["drive_nonzero"] = float(ext.abs().sum().item()) > 0
    print(f"drive mean={float(ext.mean()):.4f} max={float(ext.max()):.4f}")

    all_ok = all(gates.values())
    print("\n--- gates ---")
    for k, v in gates.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gates": gates,
        "all_ok": all_ok,
        "audit": audit.to_dict(),
        "bridge": {"ok": br.get("ok"), "free_parameters": br.get("free_parameters")},
        "pin": {"connected": pin.connected, "mode": getattr(pin, "pin_mode", "")},
        "S_Neuroscience": folds.get("S_Neuroscience"),
        "doctrine": "docs/BIO_SENSORY_SYSTEM.md",
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / "bio_sensory_check.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    md = ROOT / "data" / "results" / "BIO_SENSORY_CHECK.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(
        "\n".join(
            [
                "# Bio sensory check",
                "",
                f"Generated: `{out['generated_at']}`  ",
                f"**all_ok={all_ok}**",
                "",
                "| Gate | OK |",
                "|------|:--:|",
                *[f"| `{k}` | {'Y' if v else 'N'} |" for k, v in gates.items()],
                "",
                f"consciousness_gate={audit.consciousness_gate}",
                f"pathway_gains={audit.pathway_gains}",
                "",
                "See docs/BIO_SENSORY_SYSTEM.md",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # frontier note: sensory bio accuracy progress, not the three unclaimed AGI claims
    try:
        log_frontier(
            experiment="bio_sensory_check",
            related_metrics={"bio_sensory_all_ok": all_ok, **{f"gate_{k}": v for k, v in gates.items()}},
            notes="Bio-equivalent sensory routing/gains check; does not claim open-world pixel ID.",
        )
    except Exception:
        pass
    print(f"\nWrote {path}")
    print(f"Wrote {md}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
