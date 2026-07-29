#!/usr/bin/env python3
"""
Biological accuracy + stack stress for Zig *fixed-point* mind path.

Runs fsot_mind fixed and checks FSOT_FIXED_BIO_ACCURATE_OK plus key metrics.
Compares Allen FI numbers to f64 bio path when available.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIG = ROOT / "embodiment" / "zig"
sys.path.insert(0, str(ROOT))


def mind() -> Path:
    for n in ("fsot_mind.exe", "fsot_mind"):
        p = ZIG / "zig-out" / "bin" / n
        if p.is_file():
            return p
    raise SystemExit("fsot_mind missing — zig build first")


def main() -> int:
    print("=== Zig FIXED-POINT bio accuracy stress ===")
    r = subprocess.run(
        [str(mind()), "fixed"],
        cwd=str(ZIG),
        capture_output=True,
        text=True,
        timeout=600,
    )
    text = (r.stdout or "") + (r.stderr or "")
    print(text[-4000:] if len(text) > 4000 else text)

    gates = {
        "stack_ok": "FSOT_FIXED_STACK_OK" in text,
        "bio_accurate_ok": "FSOT_FIXED_BIO_ACCURATE_OK" in text,
        "neuron_parity": "FSOT_FIXED_NEURON_PARITY PASS" in text,
        "genetic_w_pure": "FSOT_FIXED_GENETIC_W PASS" in text,
        "structure_match": "FSOT_FIXED_STRUCTURE PASS" in text,
        "bio_fi": "FSOT_FIXED_BIO PASS" in text,
    }
    m = re.search(r"FIXED_BIO_FI rate_Hz=([^\s]+) isi_ms=([^\s]+) adapt=([^\s]+)", text)
    metrics = {}
    if m:
        metrics = {
            "rate_Hz": float(m.group(1)),
            "isi_ms": float(m.group(2)),
            "adapt": float(m.group(3)),
        }
        # cortical / Allen-class bands
        gates["rate_band"] = 5.0 <= metrics["rate_Hz"] <= 80.0
        gates["isi_band"] = 10.0 <= metrics["isi_ms"] <= 200.0
        gates["adapt_band"] = -0.3 < metrics["adapt"] < 0.6

    print("--- gates ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")
    if metrics:
        print(f"  metrics: {metrics}")

    # Compare to prior f64 Allen FI if stress artifact exists
    try:
        import json

        art = ROOT / "artifacts" / "zig_mind_stress.json"
        if art.is_file() and metrics:
            prev = json.loads(art.read_text(encoding="utf-8"))
            zb = (prev.get("metrics") or {}).get("zig_bio") or {}
            pr = zb.get("BIO_FI_mean_rate_Hz")
            pi = zb.get("BIO_FI_mean_isi_ms")
            if pr and pi:
                re_r = abs(metrics["rate_Hz"] - pr) / max(pr, 1e-9)
                re_i = abs(metrics["isi_ms"] - pi) / max(pi, 1e-9)
                print(f"  vs f64 zig bio: rate_rel_err={re_r:.4f} isi_rel_err={re_i:.4f}")
                gates["match_f64_bio"] = re_r < 0.05 and re_i < 0.05
                print(f"  match_f64_bio: {gates['match_f64_bio']}")
    except Exception as e:
        print(f"  f64 compare skip: {e}")

    critical = all(
        gates.get(k)
        for k in (
            "stack_ok",
            "bio_accurate_ok",
            "neuron_parity",
            "genetic_w_pure",
            "structure_match",
            "bio_fi",
            "rate_band",
            "isi_band",
        )
        if k in gates
    )
    print(f"CRITICAL={'PASS' if critical and r.returncode == 0 else 'FAIL'}")
    return 0 if critical and r.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
