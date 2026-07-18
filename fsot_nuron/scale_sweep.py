"""Population scale sweep + lesion-aware consensus quarantine test."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import torch

from .gpu_consensus import consensus_morse_chem_loop
from .neuron_batch import FSOTNeuronBatch, NeuronConfig
from .paths import ARTIFACTS, ROOT

RESULTS_DIR = ROOT / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


@torch.no_grad()
def population_scale_sweep(
    sizes: Optional[List[int]] = None,
    steps: int = 200,
    devices: Optional[List[str]] = None,
) -> Dict[str, Any]:
    sizes = sizes or [64, 256, 1024, 4096]
    if devices is None:
        devices = ["cpu"]
        if torch.cuda.is_available():
            devices.append("cuda")

    rows = []
    for device in devices:
        for n in sizes:
            # skip huge on cpu to keep CI/local sane
            if device == "cpu" and n > 1024:
                continue
            cfg = NeuronConfig(n_units=n)
            net = FSOTNeuronBatch(cfg, device=device)
            stim = torch.full((n,), 0.55, device=net.device, dtype=net.dtype)
            # warmup
            for _ in range(3):
                net.step(stim)
            net.reset()
            t0 = time.perf_counter()
            fires = 0
            for _ in range(steps):
                _, fired, _, _ = net.step(stim)
                fires += int(fired.sum().item())
            if device == "cuda":
                torch.cuda.synchronize()
            elapsed = time.perf_counter() - t0
            unit_steps = n * steps
            rows.append(
                {
                    "device": device,
                    "n_units": n,
                    "steps": steps,
                    "elapsed_s": elapsed,
                    "unit_steps_per_s": unit_steps / max(elapsed, 1e-9),
                    "mean_fire_frac": fires / max(unit_steps, 1),
                }
            )
            print(
                f"  {device:4s} n={n:5d}  {rows[-1]['unit_steps_per_s']:.0f} unit-steps/s  "
                f"fire_frac={rows[-1]['mean_fire_frac']:.3f}"
            )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "note": "Vectorized FSOTActiveNeuron step throughput; small-N often CPU-bound by launch overhead.",
    }


def lesion_consensus_test(
    text: str = "FSOT 2.1 NEURAL CONSENSUS",
    failure_mode: str = "PD_rate_irregularity",
    n_units: int = 32,
) -> Dict[str, Any]:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    healthy = consensus_morse_chem_loop(
        text, n_units=n_units, device=device, failure_mode=None
    )
    lesioned = consensus_morse_chem_loop(
        text,
        n_units=n_units,
        device=device,
        failure_mode=failure_mode,
        auto_wire=True,
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "text": text,
        "failure_mode": failure_mode,
        "device": device,
        "healthy": {
            "backend": healthy.get("backend"),
            "morse_exact": healthy.get("morse", {}).get("exact")
            if isinstance(healthy.get("morse"), dict)
            else healthy.get("morse_exact"),
            "keys": list(healthy.keys())[:20],
            "summary": {k: healthy.get(k) for k in ("backend", "n_units", "ok") if k in healthy},
        },
        "lesioned": {
            "backend": lesioned.get("backend"),
            "lesion": lesioned.get("lesion_info") or lesioned.get("lesion"),
            "quarantine": lesioned.get("quarantine"),
            "keys": list(lesioned.keys())[:24],
            "ok": lesioned.get("ok", True),
        },
        "full_lesioned_path": str(ARTIFACTS / "gpu_consensus_morse_chem_report.json"),
    }


def run_scale_and_consensus(write: bool = True) -> Dict[str, Any]:
    print("--- population scale sweep ---")
    sweep = population_scale_sweep()
    print("--- lesion-aware consensus ---")
    cons = lesion_consensus_test()
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scale_sweep": sweep,
        "lesion_consensus": cons,
    }
    if write:
        p = RESULTS_DIR / "scale_and_consensus.json"
        p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "scale_and_consensus.json").write_text(
            json.dumps(out, indent=2, default=str), encoding="utf-8"
        )
        out["path"] = str(p)
    return out
