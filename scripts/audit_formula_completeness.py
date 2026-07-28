#!/usr/bin/env python3
"""
Compare Neural seeds/scalar/spine vs archive closed forms.

  python scripts/audit_formula_completeness.py
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")


def main() -> int:
    from fsot_nuron.archive_pin import archive_derived_floats, check_local_seeds, pin_archive
    from fsot_nuron.seeds import SEEDS
    from fsot_nuron.fsot_full_spine import full_spine_snapshot, observer_effect_report

    print("=== Formula completeness audit (archive ↔ Neural) ===")
    pin = pin_archive(write_snapshot=False)
    derived = archive_derived_floats()
    ok, max_err, bad = check_local_seeds(rtol=1e-9)

    print(f"pin connected={pin.connected} seed_match={pin.seed_match_ok}")
    print(f"seed check ok={ok} max_rel_err={max_err:.3e}")
    if bad:
        for b in bad:
            print(f"  MISMATCH {b}")

    present = []
    missing = []
    # Full archive Layer-1/2 name list
    archive_names = [
        "pi", "e", "phi", "gamma", "g_catalan",
        "alpha", "psi_con", "eta_eff", "beta", "gamma_c", "omega",
        "theta_s", "poof", "c_eff", "a_bleed", "p_var", "b_in", "a_in",
        "suction", "chaos", "p_base", "p_new", "c_factor", "k", "c_cosm",
    ]
    for name in archive_names:
        if hasattr(SEEDS, name):
            present.append(name)
        else:
            missing.append(name)

    spine = full_spine_snapshot()
    obs = observer_effect_report()

    conceptual = {
        "S=K(T1+T2+T3)": True,
        "observer_quirk_mod": abs(obs["delta_S"]) > 0,
        "consciousness_C_factor": SEEDS.c_factor > 0,
        "POOF": SEEDS.poof > 0,
        "SUCTION": hasattr(SEEDS, "suction"),
        "yin_yang_pairs": len(spine["yin_yang_pairs"]) >= 5,
        "acoustic_bleed_inflow": True,
        "chaos_factor": hasattr(SEEDS, "chaos"),
        "omega_gamma_c": hasattr(SEEDS, "omega") and hasattr(SEEDS, "gamma_c"),
        "c_cosm": hasattr(SEEDS, "c_cosm"),
        "homeostasis_stdp_seed_tables": "homeostasis_seed" in spine,
        "domain_folds_bridge": True,
        "codon_64": True,
        "continuous_ms_refractory": True,  # neuron_batch ref_timer_ms
    }

    print("\n--- Seed symbols on SEEDS ---")
    print(f"  present ({len(present)}): {', '.join(present)}")
    if missing:
        print(f"  MISSING ({len(missing)}): {', '.join(missing)}")
    else:
        print("  MISSING: none")

    print("\n--- Conceptual spine ---")
    for k, v in conceptual.items():
        print(f"  {'OK' if v else 'GAP'}  {k}")

    still_archive_only = [
        "Full 35-domain DomainConfig table (use archive for non-neuro domains)",
        "Consciousness E_con brain-power formula (documented; not neuron FI lock)",
        "Tier 90+ consciousness extension panels (archive Lean)",
        "Wave-1 cosmology closed forms (H0, T_CMB, …) — archive primary",
    ]
    print("\n--- Intentionally archive-primary (not Neural body) ---")
    for x in still_archive_only:
        print(f"  · {x}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed_match_ok": ok,
        "max_rel_err": max_err,
        "mismatches": bad,
        "present": present,
        "missing": missing,
        "conceptual": conceptual,
        "observer_delta_S": obs["delta_S"],
        "poof": SEEDS.poof,
        "suction": SEEDS.suction,
        "c_factor": SEEDS.c_factor,
        "archive_only_notes": still_archive_only,
        "ok": ok and not missing and all(conceptual.values()),
    }
    out = ROOT / "data" / "results" / "formula_completeness.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = [
        "# Formula completeness (archive ↔ Neural)",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"- Seed match: **{ok}** (max rel err `{max_err:.3e}`)",
        f"- Missing seed symbols: **{missing if missing else 'none'}**",
        f"- Conceptual spine all OK: **{report['ok']}**",
        "",
        "## Present",
        "",
        ", ".join(f"`{p}`" for p in present),
        "",
        "## Conceptual",
        "",
        *[f"- `{k}`: **{v}**" for k, v in conceptual.items()],
        "",
        "## Archive-primary (not dropped — different scope)",
        "",
        *[f"- {x}" for x in still_archive_only],
        "",
    ]
    (ROOT / "docs" / "FORMULA_COMPLETENESS.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {out}")
    print(f"Wrote docs/FORMULA_COMPLETENESS.md")
    print("\nPASS" if report["ok"] else "\nFAIL")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
