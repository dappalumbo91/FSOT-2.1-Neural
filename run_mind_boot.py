#!/usr/bin/env python3
"""
Boot the FSOT *mind* — Zig authority, not Python dynamics.

Python only:
  - locates / builds the Zig mind binary
  - optional lab reports (pin, bio sensory audit)
  - never owns neuron.step / multi-region dynamics

Primary product path for the mind:
  embodiment/zig → zig-out/bin/fsot_mind.exe
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZIG_DIR = ROOT / "embodiment" / "zig"
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")


def find_zig() -> str | None:
    z = shutil.which("zig")
    if z:
        return z
    pkgs = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    if pkgs.is_dir():
        for p in pkgs.rglob("zig.exe"):
            return str(p)
    return None


def mind_exe() -> Path | None:
    for name in ("fsot_mind.exe", "fsot_mind"):
        p = ZIG_DIR / "zig-out" / "bin" / name
        if p.is_file():
            return p
    return None


def ensure_mind_built() -> Path:
    exe = mind_exe()
    if exe is not None:
        return exe
    zig = find_zig()
    if not zig:
        raise SystemExit("zig not found — install Zig 0.15+ or put zig on PATH")
    # install only (no run) so Defender quirks don't fail the build step
    r = subprocess.run(
        [zig, "build", "-Doptimize=ReleaseSafe"],
        cwd=str(ZIG_DIR),
        capture_output=True,
        text=True,
        timeout=300,
    )
    exe = mind_exe()
    if exe is None:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        raise SystemExit(f"fsot_mind binary missing after zig build (code={r.returncode})")
    return exe


def run_zig_mind(mode: str = "all") -> int:
    exe = ensure_mind_built()
    print("=== FSOT MIND BOOT (Zig FIXED authority) ===")
    print(f"binary: {exe}")
    print(f"mode:   {mode}")
    print("doctrine: lattice dynamics + codon genetics in Zig; Python is optional I/O only")
    print("modes: all|fixed|intel|organism|learn|curriculum|stress|float-lab|…\n")
    r = subprocess.run([str(exe), mode], cwd=str(ZIG_DIR))
    return int(r.returncode)


def optional_lab_banner() -> None:
    """Non-authoritative context (pin / sensory audit). Never steps the brain."""
    try:
        from fsot_nuron.archive_pin import pin_archive

        pin = pin_archive(write_snapshot=False)
        print(
            f"[lab] pin connected={pin.connected} seed_ok={pin.seed_match_ok} "
            f"mode={getattr(pin, 'pin_mode', '')}"
        )
    except Exception as e:
        print(f"[lab] pin skipped: {e}")
    try:
        from fsot_nuron.sensory.bio_pathways import audit_bio_sensory

        aud = audit_bio_sensory()
        print(
            f"[lab] bio_sensory ok={aud.ok} free_params={aud.free_parameters} "
            f"(analysis only — not the live mind)"
        )
    except Exception as e:
        print(f"[lab] bio_sensory skipped: {e}")
    print()


def main() -> int:
    mode = "all"
    if len(sys.argv) >= 2:
        mode = sys.argv[1]
    optional_lab_banner()
    code = run_zig_mind(mode)
    if code == 0:
        print("\nMIND BOOT OK — authority is Zig fsot_mind")
    else:
        print(f"\nMIND BOOT FAIL exit={code}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
