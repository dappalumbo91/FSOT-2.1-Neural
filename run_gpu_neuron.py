#!/usr/bin/env python3
"""
FSOT Micro-Neuron — GPU/CPU substrate runner.

Small batched neurons (Tesla-scale intent) on CUDA when available.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch

from fsot_nuron import FSOTNeuronBatch, FluidReservoir, NeuronConfig, ARTIFACTS, __version__
from fsot_nuron.reservoir import ReservoirConfig
from fsot_nuron.scalar import compute_scalar_float


def pick_device(name: str, units: int, steps: int) -> str:
    if name == "auto":
        return FSOTNeuronBatch.recommend_device(units, steps)
    if name == "cuda" and not torch.cuda.is_available():
        print("WARN: cuda requested but unavailable — falling back to cpu")
        return "cpu"
    return name


def main() -> None:
    p = argparse.ArgumentParser(description="FSOT GPU/CPU micro-neuron")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--units", type=int, default=64, help="population size (keep small by default)")
    p.add_argument("--steps", type=int, default=1000)
    p.add_argument(
        "--pattern",
        default="periodic",
        choices=["periodic", "random", "constant", "rest", "fi_step"],
    )
    p.add_argument("--reservoir", action="store_true", help="run small fluid U-Net reservoir")
    p.add_argument("--bench", action="store_true", help="CPU vs GPU scaling microbench")
    args = p.parse_args()

    device = pick_device(args.device, args.units, args.steps)
    print("=" * 64)
    print(f"FSOT Micro-Neuron v{__version__}")
    print(f"device={device}  units={args.units}  steps={args.steps}")
    if device == "cuda":
        print(f"gpu={torch.cuda.get_device_name(0)}")
    print("=" * 64)

    # Scalar smoke
    s0 = compute_scalar_float(N=4, P=3, D_eff=13, recent_hits=0, delta_psi=0.1, observed=True)
    print(f"scalar_smoke S={s0:.6f}")

    cfg = NeuronConfig(n_units=args.units)
    net = FSOTNeuronBatch(cfg, device=device)

    t0 = time.perf_counter()
    hist = net.run(args.steps, stimulus_pattern=args.pattern, record=True)
    if device == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - t0
    summary = net.metrics_summary(hist)
    summary["wall_s"] = elapsed
    summary["steps_per_s"] = args.steps * args.units / max(elapsed, 1e-9)
    print("\n--- batch neuron ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    if args.reservoir:
        res = FluidReservoir(
            ReservoirConfig(n_units=args.units, device=device)
        )
        stim = torch.zeros(args.steps, device=device)
        for t in range(args.steps):
            stim[t] = 0.8 if (t % 80 < 20) else 0.1
        t0 = time.perf_counter()
        rh = res.run_sequence(stim, record=True)
        if device == "cuda":
            torch.cuda.synchronize()
        re = time.perf_counter() - t0
        print("\n--- fluid reservoir ---")
        print(f"  mean_rate_Hz: {float(rh['firing_rate_Hz'].mean()):.3f}")
        print(f"  wall_s: {re:.4f}")
        print(f"  mean_S_dec: {float(rh['S_dec'].mean()):.4f}")

    if args.bench and torch.cuda.is_available():
        print("\n--- CPU vs GPU scaling bench (find the crossover) ---")
        # Small nets: CPU should win. Large populations: GPU substrate wins.
        # Recurrent O(T) steps: CPU SIMD wins until huge B; GPU still correct substrate for coupling.
        grid = [64, 256, 1024, 4096, 16384]
        steps_b = min(args.steps, 200)
        results = {"steps": steps_b, "grid": {}}
        for units in grid:
            row = {}
            for dev in ("cpu", "cuda"):
                n = FSOTNeuronBatch(NeuronConfig(n_units=units), device=dev)
                n.run(30, stimulus_pattern="periodic", record=False)
                if dev == "cuda":
                    torch.cuda.synchronize()
                t0 = time.perf_counter()
                n.run(steps_b, stimulus_pattern="periodic", record=False)
                if dev == "cuda":
                    torch.cuda.synchronize()
                dt = time.perf_counter() - t0
                thr = steps_b * units / max(dt, 1e-9)
                row[dev] = {"wall_s": dt, "unit_steps_per_s": thr}
            speedup = row["cuda"]["unit_steps_per_s"] / max(row["cpu"]["unit_steps_per_s"], 1e-9)
            row["cuda_speedup"] = speedup
            row["winner"] = "cuda" if speedup > 1.0 else "cpu"
            results["grid"][str(units)] = row
            print(
                f"  units={units:5d}: CPU {row['cpu']['unit_steps_per_s']:,.0f}/s | "
                f"CUDA {row['cuda']['unit_steps_per_s']:,.0f}/s | "
                f"{speedup:.2f}x → {row['winner']}"
            )
        results["policy"] = (
            "auto uses CPU below ~256 units (launch-bound); CUDA for larger populations"
        )
        (ARTIFACTS / "bench_cpu_gpu.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"  wrote {ARTIFACTS / 'bench_cpu_gpu.json'}")

    out = {
        "version": __version__,
        "device": device,
        "summary": summary,
        "pattern": args.pattern,
    }
    path = ARTIFACTS / "last_gpu_neuron_run.json"
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
