#!/usr/bin/env python3
"""One-shot: build PFLT-style math sense bindings (thousands), not drip schemas.

  python scripts/densify_math_sense_bindings.py
  python scripts/densify_math_sense_bindings.py --smoke

Local only. No cloud APIs. Doctrine: form → SENSE → formula.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--no-pflt", action="store_true")
    ap.add_argument("--no-rulebook", action="store_true")
    args = ap.parse_args()

    from fsot_nuron.math_sense_interlingua import (
        MathSenseInterlingua,
        densify_from_gsm8k_cues,
        smoke_math_sense,
    )

    dens = densify_from_gsm8k_cues(limit=1319, max_new=3000)
    print(json.dumps({"densify": dens}, indent=2))

    ix = MathSenseInterlingua(
        load_rulebook=not args.no_rulebook,
        load_pflt=not args.no_pflt,
    )
    pack = ix.export_pack()
    print(json.dumps({"stats": pack["stats"]}, indent=2))

    if args.smoke:
        sm = smoke_math_sense()
        print(json.dumps(sm, indent=2)[:4000])

    # show one resolution path like pflt_sense_translate
    demo = (
        "She sold a third of her vacuum cleaners, 2 more, and half of what was left. "
        "How many did she start with if 5 are left?"
    )
    r = ix.translate_cues(demo)
    print("\nDEMO resolution (form → sense → formula):")
    print("Q:", demo)
    for line in r.resolution[:12]:
        print(" ", line)
    print("strategies:", r.strategies)
    print(
        f"\nPFLT-style mass: {pack['stats']['n_senses']} senses, "
        f"{pack['stats']['n_form_bindings']} form bindings, "
        f"{pack['stats']['n_index_keys']} index keys"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
