#!/usr/bin/env python3
"""
Parity: Zig FSOT neuron step vs Python (scientific reproducibility gate).

Runs embodiment/zig host binary, parses TRACE_*, recomputes same protocol
in Python (scalar + neuron_batch single unit), checks max |dS| and spike match.

Also optional bio lock summary when Allen CSV is present.
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIG_DIR = ROOT / "embodiment" / "zig"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def find_zig() -> str | None:
    import shutil

    z = shutil.which("zig")
    if z:
        return z
    pkgs = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    if pkgs.is_dir():
        for p in pkgs.rglob("zig.exe"):
            return str(p)
    return None


def python_trace(n_steps: int = 200):
    import torch
    from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
    from fsot_nuron.scalar import compute_scalar_float

    s0 = compute_scalar_float(
        N=4.0, P=3.0, D_eff=13.0, recent_hits=0.0, delta_psi=0.1, delta_theta=1.0, rho=1.0, observed=True
    )

    cfg = NeuronConfig(n_units=1)
    net = FSOTNeuronBatch(cfg, device="cpu", dtype=torch.float64)
    net.reset()
    rows = []
    for t in range(n_steps):
        stim = 0.65 if (t % 80) < 20 else 0.05
        S, fired, phase, tern = net.step(torch.tensor([stim], dtype=torch.float64))
        rows.append(
            {
                "t": t,
                "S": float(S[0].item()),
                "fired": int(fired[0].item()),
                "ternary": int(tern[0].item()),
            }
        )
    return s0, rows


def run_zig_host() -> str:
    zig = find_zig()
    if not zig:
        raise RuntimeError("zig not found")
    # Ensure install + run; capture both streams (zig may print on either)
    r = subprocess.run(
        [zig, "build", "host"],
        cwd=str(ZIG_DIR),
        capture_output=True,
        text=True,
        timeout=300,
    )
    blob = (r.stdout or "") + "\n" + (r.stderr or "")
    if r.returncode != 0 and "FSOT_STAGE_ZIG_NEURON_OK" not in blob:
        raise RuntimeError(f"zig build host failed:\n{blob[-3000:]}")
    # Prefer direct re-run of installed binary for clean parse
    for name in ("fsot_trit_host.exe", "fsot_trit_host"):
        exe = ZIG_DIR / "zig-out" / "bin" / name
        if exe.is_file():
            r2 = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
            return (r2.stdout or "") + (r2.stderr or "")
    # Fallback: parse build log
    if "TRACE_BEGIN" in blob:
        return blob
    raise RuntimeError("host binary missing and no TRACE in build log")


def parse_zig_trace(text: str):
    m = re.search(r"SCALAR_NEURO_DPI0\.1=([^\s]+)", text)
    s0 = float(m.group(1)) if m else float("nan")
    rows = []
    if "TRACE_BEGIN" in text and "TRACE_END" in text:
        block = text.split("TRACE_BEGIN", 1)[1].split("TRACE_END", 1)[0].strip()
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) >= 4:
                rows.append(
                    {
                        "t": int(parts[0]),
                        "S": float(parts[1]),
                        "fired": int(parts[2]),
                        "ternary": int(parts[3]),
                    }
                )
    return s0, rows


def bio_crosscheck() -> dict:
    """Allen-facing bio validation if ephys CSV present; never invents accuracy."""
    try:
        from fsot_nuron.allen_data import load_ephys_csv, data_status
        from fsot_nuron.validate import run_validation

        st = data_status()
        rows = load_ephys_csv()
        if not rows:
            return {"ok": False, "reason": "no Allen ephys CSV on this machine", "status": st}
        report = run_validation(
            n_units=32,
            steps=1000,
            device="cpu",
            use_api=False,
            mode="bio_match",
            both_modes=False,
            calibrate=True,
        )
        ev = (report.get("evoked") or {}).get("population") or {}
        gaps = report.get("gaps") or report.get("gap_ledger") or {}
        card = {
            "mean_isi_ms": ev.get("mean_isi_ms"),
            "mean_adaptation_index": ev.get("mean_adaptation_index"),
            "mean_firing_rate_Hz": ev.get("mean_firing_rate_Hz"),
            "primary_mode": report.get("primary_mode"),
            "data_source": (report.get("data_status") or {}).get("ephys_csv"),
            "n_cells": (report.get("data_status") or {}).get("n_ephys_rows"),
            "gaps_summary": gaps if isinstance(gaps, dict) else str(gaps)[:500],
        }
        # relative ISI error if targets present
        pop = (report.get("data_status") or {}).get("population") or {}
        tgt_isi = pop.get("mean_avg_isi_ms")
        if tgt_isi and card.get("mean_isi_ms") == card.get("mean_isi_ms"):
            card["target_isi_ms"] = tgt_isi
            card["isi_rel_err"] = abs(card["mean_isi_ms"] - tgt_isi) / max(tgt_isi, 1e-9)
        return {"ok": True, "card": card, "honest": "computational Allen match under stated protocol"}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def main() -> int:
    print("=== FSOT Zig↔Python neuron parity ===")
    py_s0, py_rows = python_trace(200)
    print(f"python scalar_neuro dpsi0.1 = {py_s0:.17e}")

    out = run_zig_host()
    if "FSOT_STAGE_ZIG_NEURON_OK" not in out and "FSOT_NEURON PASS" not in out:
        print("zig host did not report PASS")
        print(out[-2000:])
        return 1
    zig_s0, zig_rows = parse_zig_trace(out)
    print(f"zig    scalar_neuro dpsi0.1 = {zig_s0:.17e}")

    if len(zig_rows) != len(py_rows):
        print(f"FAIL trace length zig={len(zig_rows)} py={len(py_rows)}")
        return 1

    max_ds = 0.0
    spike_mismatch = 0
    tern_mismatch = 0
    for a, b in zip(py_rows, zig_rows):
        ds = abs(a["S"] - b["S"])
        max_ds = max(max_ds, ds)
        if a["fired"] != b["fired"]:
            spike_mismatch += 1
        if a["ternary"] != b["ternary"]:
            tern_mismatch += 1

    # f64 vs f32 torch path: neuron_batch defaults float32 — use loose but scientific bound
    # Host Zig is f64; Python step used float64 above → expect tight agreement
    scalar_err = abs(py_s0 - zig_s0)
    print(f"max |dS| over 200 steps = {max_ds:.3e}")
    print(f"|dS| scalar probe        = {scalar_err:.3e}")
    print(f"spike mismatches         = {spike_mismatch}")
    print(f"ternary mismatches       = {tern_mismatch}")

    # Gates (documented in STAGE md)
    ok_scalar = scalar_err < 1e-9 or scalar_err / max(abs(py_s0), 1e-12) < 1e-8
    ok_trace = max_ds < 1e-5  # allow tiny libm differences
    ok_spikes = spike_mismatch == 0
    # ternary may differ on boundary; allow few
    ok_tern = tern_mismatch <= 2

    print(f"gate_scalar: {ok_scalar}")
    print(f"gate_trace:  {ok_trace}")
    print(f"gate_spikes: {ok_spikes}")
    print(f"gate_tern:   {ok_tern}")

    bio = bio_crosscheck()
    print(f"bio_crosscheck: {bio.get('ok')} {bio.get('reason', bio.get('card'))}")

    from fsot_nuron.thesis_ledger import record_run

    record_run(
        "zig_neuron_parity",
        profile="zig_f64",
        gates={
            "scalar": ok_scalar,
            "trace": ok_trace,
            "spikes": ok_spikes,
            "ternary": ok_tern,
            "bio_data_present": bool(bio.get("ok")),
        },
        metrics={
            "max_abs_dS": max_ds,
            "scalar_abs_err": scalar_err,
            "spike_mismatch": spike_mismatch,
            "tern_mismatch": tern_mismatch,
            "bio": bio.get("card"),
        },
        notes="Zig freestanding neuron step parity vs Python; stage STAGE_ZIG_NEURON_STEP.md",
        formulas_ref="docs/FORMULAS.md",
        extra={"stage_doc": "docs/STAGE_ZIG_NEURON_STEP.md"},
    )

    if ok_scalar and ok_trace and ok_spikes and ok_tern:
        print("PARITY PASS")
        return 0
    print("PARITY FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
