#!/usr/bin/env python3
"""
Deep Lean audit: list theorems/defs; fail if sorry/admit present.

  python scripts/audit_lean_nosorry.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formal"

SORRY_RE = re.compile(r"\b(sorry|admit)\b")
THM_RE = re.compile(r"^\s*(theorem|lemma|def|structure|inductive|proposition)\s+(\S+)")


def main() -> int:
    lean_files = sorted(FORMAL.rglob("*.lean"))
    lean_files = [p for p in lean_files if ".lake" not in p.parts]
    print("=== Lean no-sorry + inventory audit ===")
    print(f"files: {len(lean_files)}")

    sorries = []
    inventory = []
    for p in lean_files:
        text = p.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            # ignore comments that mention sorry
            stripped = line.strip()
            if stripped.startswith("--") or stripped.startswith("/-") or "No `sorry`" in line or "No sorry" in line:
                if "No `sorry`" in line or "no sorry" in line.lower():
                    continue
                if stripped.startswith("--") or stripped.startswith("/-"):
                    # still flag if it's actual sorry code
                    if re.search(r"\bsorry\b|\badmit\b", line) and "No" not in line:
                        # comment only
                        pass
            code = line.split("--")[0]
            if SORRY_RE.search(code):
                sorries.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()}")
            m = THM_RE.match(line)
            if m:
                inventory.append(
                    {
                        "kind": m.group(1),
                        "name": m.group(2).rstrip(":"),
                        "file": str(p.relative_to(ROOT)).replace("\\", "/"),
                    }
                )

    print(f"theorems/defs/structures found: {len(inventory)}")
    for item in inventory:
        print(f"  {item['kind']:10} {item['name']:40} ({item['file']})")

    if sorries:
        print("\nFAIL: sorry/admit found:")
        for s in sorries:
            print(" ", s)
        return 1

    print("\nPASS: no sorry/admit in Lean sources")

    # rebuild
    try:
        r = subprocess.run(
            ["lake", "build"],
            cwd=str(FORMAL),
            capture_output=True,
            text=True,
            timeout=600,
        )
        print("lake build:", "PASS" if r.returncode == 0 else "FAIL")
        if r.returncode != 0:
            sys.stderr.write(r.stderr or r.stdout or "")
            return r.returncode
    except FileNotFoundError:
        print("lake not on PATH — skip rebuild")
        return 0

    out = ROOT / "data" / "results" / "lean_inventory.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    import json
    from datetime import datetime, timezone

    out.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "n_declarations": len(inventory),
                "sorry_count": 0,
                "lake_build_ok": True,
                "inventory": inventory,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
