#!/usr/bin/env python3
"""
Verify Lean formal panel for FSOT-2.1-Neural (local lake build).

No network. Exit 0 if `lake build` succeeds under formal/.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formal"


def main() -> int:
    print("=== FSOT-2.1-Neural formal panel (Lean 4) ===")
    print(f"dir: {FORMAL}")
    if not (FORMAL / "lakefile.lean").is_file():
        print("FAIL: formal/lakefile.lean missing")
        return 1
    try:
        r = subprocess.run(
            ["lake", "build"],
            cwd=str(FORMAL),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError:
        print("FAIL: lake not on PATH (install elan/lean 4.31)")
        return 2
    except subprocess.TimeoutExpired:
        print("FAIL: lake build timeout")
        return 3

    sys.stdout.write(r.stdout or "")
    sys.stderr.write(r.stderr or "")
    if r.returncode != 0:
        print("FAIL: lake build")
        return r.returncode

    print("PASS: formal panel builds (codon · neuro fold · cell types · expression)")
    # thesis ledger optional
    try:
        sys.path.insert(0, str(ROOT))
        from fsot_nuron.thesis_ledger import record_run

        record_run(
            "formal_lean_panel",
            profile="lean4",
            gates={"lake_build": True},
            metrics={},
            notes="formal/ FSOTNeural lake build ok",
            formulas_ref="docs/FORMULAS.md",
        )
    except Exception as e:
        print(f"ledger skip: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
