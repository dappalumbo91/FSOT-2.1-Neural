#!/usr/bin/env python3
"""
FSOT bridge verification for Neural — marry body I/O through the math.

  pin → domain fold → ScalarInput bridge → S/trinary couple → domain engine

Authority: I:\\FSOT-Physical-Archive (D1D38A…)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    import os

    os.environ.setdefault("FSOT_PHYSICAL_ARCHIVE", r"I:\FSOT-Physical-Archive")
    os.environ.setdefault("PYTHONPATH", str(ROOT))

    from fsot_nuron.fsot_bridge import (
        require_pin,
        verify_fsot_bridge,
        bridge_machine_payload,
        bridge_chemical_dna,
        compute_S,
        FOLDS,
    )
    from fsot_nuron.machine_encode import encode_to_sensory_packet, EncodePath
    from fsot_nuron.sensory import SensoryBus

    print("=== FSOT-2.1-Neural bridge (through archive mathematics) ===")
    pin = require_pin(write_snapshot=False)
    print(f"pin connected={pin.connected} seed_ok={pin.seed_match_ok}")
    print(f"authority={pin.compute_sha256}")
    print(f"matches_cert={pin.compute_matches_certificate}")
    print()

    rep = verify_fsot_bridge()
    print("--- verify_fsot_bridge ---")
    print(json.dumps({k: rep[k] for k in rep if k != "ok"}, indent=2, default=str))
    print(f"\nok: {rep['ok']}")

    print("\n--- preregistered folds ---")
    for name, f in FOLDS.items():
        snap = compute_S(f)
        print(f"  {name:18} D_eff={f.D_eff:5.1f} S={snap.S:+.6f} trit={snap.trit} src={snap.source}")

    print("\n--- machine bridge (OS body) ---")
    m = bridge_machine_payload("FSOT neural intelligence")
    print(json.dumps({"drivers": m["drivers"], "modulators": m["modulators"], "fold": m["fold"]}, indent=2))

    print("\n--- chemical bridge (genetics) ---")
    c = bridge_chemical_dna("ATGAAACGGTTTGCGCAT")
    print(json.dumps({"drivers": c["drivers"], "modulators": c["modulators"], "fold": c["fold"]}, indent=2))

    print("\n--- encode → sensory with FSOT couple ---")
    bus = SensoryBus()
    pkt = encode_to_sensory_packet("stimulus via FSOT", path=EncodePath.MACHINE)
    bus.push(pkt)
    ext = bus.build_external(32, {"sens": list(range(32))})
    print(
        json.dumps(
            {
                "strength": pkt.strength,
                "meta_S": pkt.meta.get("S"),
                "meta_fold": pkt.meta.get("fold"),
                "meta_bridge": pkt.meta.get("fsot_bridge"),
                "drive_nonzero": int((ext != 0).sum()),
            },
            indent=2,
        )
    )

    if not rep["ok"]:
        print("\nFAIL: bridge verification failed — claim-sensitive work blocked")
        return 1
    print("\nPASS: mathematics pinned; bridges couple through S = K(T1+T2+T3)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
