#!/usr/bin/env python3
"""
Run the four climbs: scalpel 1%, retention, consolidation, (Zig via separate script).
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> int:
    print("\n>>>", " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(ROOT))
    return r.returncode


def main() -> int:
    py = sys.executable
    env_hint = {"PYTHONPATH": str(ROOT)}
    import os

    os.environ["PYTHONPATH"] = str(ROOT)

    codes = {}
    codes["scalpel_1pct"] = run(
        [py, "run_scalpel_rates.py", "--focus", "Pyr,PV,SST,VIP", "--tol", "0.01", "--max-iters", "40", "--steps", "1400"]
    )
    if codes["scalpel_1pct"] != 0:
        print("scalpel 1% failed — recording 2% fallback")
        codes["scalpel_2pct"] = run(
            [py, "run_scalpel_rates.py", "--focus", "Pyr,PV,SST,VIP", "--tol", "0.02", "--max-iters", "24", "--steps", "1200"]
        )
    codes["intelligence"] = run(
        [
            py,
            "run_intelligence_probe.py",
            "--suite",
            "--items",
            "12",
            "--delay-steps",
            "600",
            "--tol",
            "0.01",
            "--encode-steps",
            "320",
            "--retrieve-steps",
            "260",
        ]
    )

    # Zig host + optional QEMU
    zig_dir = ROOT / "embodiment" / "zig"
    codes["zig_host"] = run(
        ["powershell", "-NoProfile", "-Command", f"cd '{zig_dir}'; if (Get-Command zig -ErrorAction SilentlyContinue) {{ zig build host }} else {{ $z=Get-ChildItem \"$env:LOCALAPPDATA\\Microsoft\\WinGet\\Packages\" -Recurse -Filter zig.exe -EA SilentlyContinue | Select -First 1 -Expand FullName; & $z build host }}"]
    )
    codes["zig_qemu"] = run(
        ["powershell", "-NoProfile", "-File", str(zig_dir / "run_qemu.ps1")]
    )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exit_codes": codes,
        "ok": all(v == 0 for k, v in codes.items() if k != "scalpel_1pct")
        or (codes.get("scalpel_1pct") == 0 and codes.get("intelligence") == 0),
    }
    # Prefer: scalpel 1% or 2% ok, intelligence ok, zig at least host ok
    scalpel_ok = codes.get("scalpel_1pct") == 0 or codes.get("scalpel_2pct") == 0
    summary["ok"] = (
        scalpel_ok
        and codes.get("intelligence") == 0
        and codes.get("zig_host") == 0
    )
    out = ROOT / "data" / "results" / "climb_suite.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n=== CLIMB SUITE ===")
    print(json.dumps(summary, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
