#!/usr/bin/env python3
"""
Verify full FSOT spine is live in Neural (consciousness, observer, yin-yang, POOF).

  python run_full_spine_check.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_PHYSICAL_ARCHIVE", r"I:\FSOT-Physical-Archive")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    from fsot_nuron.fsot_full_spine import (
        full_spine_snapshot,
        observer_effect_report,
        poof_factor,
        suction_factor,
        consciousness_factor,
        quirk_mod,
        yin_yang_balance,
        term3_dual_report,
    )
    from fsot_nuron.archive_pin import pin_archive
    from fsot_nuron.paths import ARTIFACTS, DATA

    print("=== FSOT full spine check (Neural) ===")
    print("consciousness · observer · yin–yang · POOF/SUCTION")
    pin = pin_archive(write_snapshot=False)
    print(f"pin seed_ok={pin.seed_match_ok}")

    snap = full_spine_snapshot()
    obs = observer_effect_report()
    t3 = term3_dual_report()
    yy = yin_yang_balance(S=0.5, e_rate=16.0, i_rate=40.0)

    print("\n--- Consciousness ---")
    print(f"  C_factor={consciousness_factor():.6f}  psi_con={snap['consciousness']['psi_con']:.6f}")
    print(f"  Gate φ/(1+φ)={snap['consciousness']['table']['Consciousness_Gate']:.4f}")

    print("\n--- Observer ---")
    print(f"  quirk_mod(observed)={quirk_mod(True):.6f}")
    print(f"  S_obs={obs['S_observed']:+.6f}  S_unobs={obs['S_unobserved']:+.6f}  ΔS={obs['delta_S']:+.6f}")

    print("\n--- POOF / SUCTION (T3 valves) ---")
    print(f"  POOF={poof_factor():.6f}  SUCTION={suction_factor():.6f}")
    print(f"  valve_factor={t3['valve_poof_suction_factor']:.6f}")
    print(f"  bleed(yin)={t3['acoustic_bleed_yin']:.6f}  inflow(yang)={t3['acoustic_inflow_yang']:.6f}")

    print("\n--- Yin–Yang (E/I example) ---")
    print(f"  EI_balance={yy['EI_balance']:.4f}  dual_product={yy['yin_yang_duality_product']:.4f}")
    print(f"  pairs: {[p['name'] for p in snap['yin_yang_pairs']]}")

    gates = {
        "pin_ok": pin.seed_match_ok,
        "c_factor_positive": consciousness_factor() > 0,
        "poof_positive": poof_factor() > 0,
        "suction_finite": suction_factor() == suction_factor(),
        "observer_changes_S": abs(obs["delta_S"]) > 1e-9,
        "quirk_not_unity_when_observed": abs(quirk_mod(True) - 1.0) > 1e-9,
        "yin_yang_pairs_ge_5": len(snap["yin_yang_pairs"]) >= 5,
    }
    print("\n--- Gates ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gates": gates,
        "snapshot": snap,
        "observer": obs,
        "term3": t3,
        "yin_yang_example": yy,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "full_spine_check.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    res = DATA / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "full_spine_check.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    md = [
        "# Full FSOT spine check",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        f"- POOF={poof_factor():.6f} · SUCTION={suction_factor():.6f}",
        f"- C_factor={consciousness_factor():.6f}",
        f"- Observer ΔS={obs['delta_S']:+.6f}",
        "",
        "## Gates",
        "",
        *[f"- `{k}`: **{v}**" for k, v in gates.items()],
        "",
        "See `docs/FSOT_FULL_SPINE_NEURAL.md`.",
        "",
    ]
    (res / "FULL_SPINE_CHECK.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {res / 'FULL_SPINE_CHECK.md'}")

    ok = all(gates.values())
    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
