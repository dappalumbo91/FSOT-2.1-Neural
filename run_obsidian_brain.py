#!/usr/bin/env python3
"""
Export the FSOT genetic neural network as a **local** Obsidian second-brain vault.

Offline only:
  - Writes Markdown + wikilinks under artifacts/obsidian_vaults/...
  - Does NOT start a server
  - Does NOT call the web
  - Open the folder in Obsidian desktop (Open folder as vault) for local Graph view

Usage:
  cd "I:\\fsot nuron"
  $env:PYTHONPATH = "I:\\fsot nuron"
  python run_obsidian_brain.py
  python run_obsidian_brain.py --units 64 --top-k 8 --sparse
  python run_obsidian_brain.py --vault "D:\\MyVaults\\FSOT_Brain" --no-dynamics
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Local Obsidian vault export of FSOT genetic network (no server/web)"
    )
    ap.add_argument("--units", type=int, default=48, help="Number of neuron notes")
    ap.add_argument("--top-k", type=int, default=6, help="Strongest outgoing synapses per neuron")
    ap.add_argument("--min-w", type=float, default=0.05, help="Min |weight| to keep as link")
    ap.add_argument(
        "--connectivity",
        type=str,
        default="genetic_sparse",
        choices=["genetic_dense", "genetic_sparse", "local"],
        help="Genetic W topology before top-k pruning for display",
    )
    ap.add_argument("--sparse-keep", type=float, default=0.12)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--device", type=str, default="cpu")
    ap.add_argument("--steps", type=int, default=400, help="Local FI steps for rate tags")
    ap.add_argument("--no-dynamics", action="store_true", help="Skip FI run (faster export)")
    ap.add_argument(
        "--synapse-notes",
        action="store_true",
        help="Also write individual synapse notes (heavier vault)",
    )
    ap.add_argument(
        "--vault",
        type=str,
        default="",
        help="Vault folder path (default: artifacts/obsidian_vaults/FSOT_Neural_Second_Brain)",
    )
    ap.add_argument(
        "--name",
        type=str,
        default="FSOT_Neural_Second_Brain",
        help="Vault folder name when using default artifacts path",
    )
    ap.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not delete existing vault (fails if unmarked folder exists)",
    )
    args = ap.parse_args()

    from fsot_nuron.obsidian_brain import (
        ObsidianExportConfig,
        build_obsidian_vault,
        default_vault_root,
    )

    vault = Path(args.vault) if args.vault else default_vault_root(args.name)
    cfg = ObsidianExportConfig(
        n_units=args.units,
        top_k_out=args.top_k,
        min_abs_w=args.min_w,
        connectivity=args.connectivity,
        sparse_keep=args.sparse_keep,
        seed=args.seed,
        device=args.device,
        dynamics_steps=args.steps,
        run_dynamics=not args.no_dynamics,
        write_synapse_notes=args.synapse_notes,
        vault_name=args.name,
    )

    print("=== FSOT Neural Second Brain — local vault export ===")
    print("offline: true | server: none | web: none")
    print(f"vault:  {vault}")

    try:
        manifest = build_obsidian_vault(
            vault_root=vault,
            cfg=cfg,
            clean=not args.no_clean,
        )
    except FileExistsError as e:
        print(f"ERROR: {e}")
        return 2

    print(f"neurons:     {manifest['n_units']}")
    print(f"edges kept:  {manifest['n_edges_export']}")
    print(f"syn notes:   {manifest['n_synapse_notes']}")
    print(f"generated:   {manifest['generated_at']}")
    print()
    print("Open locally in Obsidian desktop:")
    print("  1. Obsidian → Open folder as vault")
    print(f"  2. Select: {manifest['vault_root']}")
    print("  3. Open Graph view (core plugin, offline)")
    print("  4. Start at note: 00_Home")
    print()
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
