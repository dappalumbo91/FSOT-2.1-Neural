#!/usr/bin/env python3
"""Lightweight CI smoke for FSOT-2.1-Neural (no GPU, no large third-party CSVs)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    errors: list[str] = []
    print("=== FSOT-2.1-Neural CI smoke ===")

    # 1) Seeds match archive closed-form
    from fsot_nuron.archive_pin import check_local_seeds, pin_archive

    ok, max_err, bad = check_local_seeds()
    print(f"seeds_match: {ok} max_rel_err={max_err:.3e}")
    if not ok:
        errors.append(f"seed mismatch: {bad}")

    # 2) Pin (uses snapshot if archive absent)
    pin = pin_archive(write_snapshot=False)
    print(f"seed_match_ok: {pin.seed_match_ok}")
    print(f"snapshot_authority: {(pin.cert_authority_sha256 or '')[:16]}")
    if not pin.seed_match_ok:
        errors.append("pin seed_match_ok false")

    snap = ROOT / "data" / "archive_snapshot" / "fsot_compute_AUTHORITY_PIN.json"
    if snap.is_file():
        d = json.loads(snap.read_text(encoding="utf-8"))
        auth = (d.get("authority_sha256") or "").upper()
        print(f"shipped_authority_pin: {auth[:16]}…")
        if not auth.startswith("D1D38A"):
            errors.append(f"unexpected authority pin {auth[:16]}")
    else:
        errors.append("missing data/archive_snapshot/fsot_compute_AUTHORITY_PIN.json")

    # 3) Codon map (genetic authority) — primary
    from fsot_nuron.chemical_codon import codon_path_verify
    from fsot_nuron.genetic_genotype import genetic_authority_report, build_population_genotypes

    cv = codon_path_verify()
    print(f"codon_ok: {cv.get('perfect')} {cv.get('roundtrip_ok')}/{cv.get('n_codons')}")
    if not cv.get("perfect"):
        errors.append("codon map fail")

    auth = genetic_authority_report()
    genes_ok = all(
        auth["channel_genes"][k]["n_codons"] >= 4
        for k in ("SCN", "KCN", "CACNA", "LEAK")
    )
    print(f"channel_genes_ok: {genes_ok}")
    if not genes_ok:
        errors.append("channel gene programs incomplete")

    # 4) Tiny genetic network step (primary substrate)
    import torch
    from fsot_nuron.genetic_network import GeneticNeuralNetwork, GeneticNetworkConfig

    gcfg = GeneticNetworkConfig(n_units=8, connectivity="genetic_dense", seed=0)
    gnet = GeneticNeuralNetwork(gcfg, device="cpu")
    S, fired, phase, ternary, syn = gnet.step(torch.ones(8) * 0.5)
    print(
        f"genetic_net_ok: fired={int(fired.sum())} S_mean={float(S.mean()):.4f} "
        f"synapses={int((gnet.W != 0).sum())}"
    )
    if S.shape[0] != 8:
        errors.append(f"unexpected S shape {tuple(S.shape)}")
    if int((gnet.W != 0).sum()) < 8:
        errors.append("genetic weight matrix too sparse/empty")

    # 5) Population genotype diversity
    pop = build_population_genotypes(16, seed=1, diversity=True)
    spins = {round(g.composite_spin, 4) for g in pop}
    print(f"genotype_diversity: n={len(pop)} unique_spins={len(spins)}")
    if len(spins) < 2:
        errors.append("genotype diversity collapsed")

    # 6) Failure catalog loads (engineering boundaries)
    from fsot_nuron.failure_boundaries import load_failure_catalog

    cat = load_failure_catalog()
    modes = cat.get("failure_modes") or cat.get("modes") or cat.get("boundaries") or []
    n = len(modes)
    print(f"failure_boundaries: {n}")
    if n < 5:
        errors.append(f"too few failure modes: {n}")

    # 7) Local Obsidian vault builder (tiny, no dynamics — filesystem only)
    from fsot_nuron.obsidian_brain import ObsidianExportConfig, build_obsidian_vault
    from fsot_nuron.paths import ARTIFACTS

    vroot = ARTIFACTS / "obsidian_vaults" / "_ci_smoke_vault"
    man = build_obsidian_vault(
        vault_root=vroot,
        cfg=ObsidianExportConfig(
            n_units=6,
            top_k_out=2,
            connectivity="genetic_sparse",
            sparse_keep=0.3,
            run_dynamics=False,
            device="cpu",
            seed=0,
        ),
        clean=True,
    )
    home = vroot / "00_Home.md"
    n0 = vroot / "02_Neurons" / "N000.md"
    print(
        f"obsidian_local_ok: edges={man['n_edges_export']} "
        f"home={home.is_file()} n0={n0.is_file()} offline={man.get('offline')}"
    )
    if not home.is_file() or not n0.is_file():
        errors.append("obsidian vault missing notes")
    if not man.get("offline", False):
        errors.append("obsidian vault not marked offline")

    # 8) Lean formal panel if lake is available (skip soft-fail if missing toolchain)
    import shutil
    import subprocess

    if shutil.which("lake"):
        r = subprocess.run(
            ["lake", "build"],
            cwd=str(ROOT / "formal"),
            capture_output=True,
            text=True,
            timeout=600,
        )
        print(f"formal_lean_ok: {r.returncode == 0}")
        if r.returncode != 0:
            errors.append("lake build failed")
            sys.stdout.write(r.stdout or "")
            sys.stderr.write(r.stderr or "")
    else:
        print("formal_lean_ok: skipped (lake not installed)")

    # 9) Morse remains optional secondary gate (do not fail CI if missing)
    try:
        from fsot_nuron.morse_itu import verify_morse_tables

        mv = verify_morse_tables()
        print(
            f"morse_secondary: {mv.get('letter_digit_ok')} "
            f"phrase={mv.get('phrase_test', {}).get('exact_morse_path')}"
        )
    except Exception as e:
        print(f"morse_secondary: skipped ({e})")

    if errors:
        print("FAIL:")
        for e in errors:
            print(" -", e)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
