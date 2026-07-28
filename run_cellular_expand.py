#!/usr/bin/env python3
"""
Cellular expand / genome-as-code check.

  python run_cellular_expand.py --check
  python run_cellular_expand.py --expand 128
"""

from __future__ import annotations

import argparse
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
    ap = argparse.ArgumentParser(description="Genome-as-code / cellular expand")
    ap.add_argument("--check", action="store_true", help="immune-style health check")
    ap.add_argument("--expand", type=int, default=0, help="grow population to N units")
    args = ap.parse_args()

    from fsot_nuron.cellular_expand import (
        cellular_health_check,
        expand_population,
        genome_summary,
        python_zig_alignment,
    )
    from fsot_nuron.paths import ARTIFACTS, DATA

    print("=== FSOT genome-as-code / cellular expand ===")
    print("Python lab → wet-lab gates → Zig body promote")
    print("DNA/codons/chemistry = source code; FSOT = cellular physics\n")

    if args.check or (not args.expand):
        health = cellular_health_check()
        g = health["genome"]
        print("--- Genome ---")
        print(f"  codon perfect: {g['codon_map_perfect']}  {g['codon_roundtrip']}")
        for name, info in g["channel_ORFs"].items():
            print(f"  {name:6} {info['dna']}  ({info['role']})")
        print(f"  K={g['seeds_K']}  free_parameters={g['free_parameters']}")
        print("\n--- Python ↔ Zig dual surfaces ---")
        for name in health["python_zig"]["dual"]:
            print(f"  dual: {name}")
        print(f"  promote_rule: {health['python_zig']['promote_rule']}")
        print(f"\nhealth ok: {health['ok']}")

    if args.expand and args.expand > 0:
        exp = expand_population(args.expand, seed=42, diversity=True)
        print("\n--- Cellular expand (division analog) ---")
        print(json.dumps(exp, indent=2))

    align = python_zig_alignment()
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": cellular_health_check() if (args.check or not args.expand) else None,
        "expand": expand_population(args.expand, seed=42) if args.expand else None,
        "alignment": align,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "cellular_expand.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    res = DATA / "results"
    res.mkdir(parents=True, exist_ok=True)
    (res / "cellular_expand.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote artifacts/cellular_expand.json")
    print("See docs/GENOME_AS_CODE.md")
    return 0 if (not args.check or cellular_health_check()["ok"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
