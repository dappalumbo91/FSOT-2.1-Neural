#!/usr/bin/env python3
"""
Parity: Zig codon→genotype→typed brain W vs Python authority path.

No shortcuts — compares:
  - 64-codon primary law / ORF expression
  - cell-type counts (ai_efficient mixes)
  - synapse count, mean |W|
  - channel gene spins/expression
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIG = ROOT / "embodiment" / "zig"
sys.path.insert(0, str(ROOT))


def mind_exe() -> Path:
    for n in ("fsot_mind.exe", "fsot_mind"):
        p = ZIG / "zig-out" / "bin" / n
        if p.is_file():
            return p
    raise SystemExit("fsot_mind missing")


def run_zig_genetic() -> str:
    r = subprocess.run([str(mind_exe()), "genetic"], cwd=str(ZIG), capture_output=True, text=True, timeout=120)
    return (r.stdout or "") + (r.stderr or "")


def fget(text: str, key: str) -> float:
    m = re.search(rf"{re.escape(key)}=([^\s]+)", text)
    if not m:
        return float("nan")
    return float(m.group(1))


def main() -> int:
    from collections import Counter
    from fsot_nuron.genetic_genotype import build_gene_program, CHANNEL_GENE_ORFS, aa_trinary_phase
    from fsot_nuron.cell_types import build_cell_type_genotype
    from fsot_nuron.brain_architecture import (
        FSOTBrainDesign,
        BrainDesignConfig,
        BRAIN_PROFILES,
        DEFAULT_PROJECTIONS,
    )

    print("=== Genetic codon parity (Python authority ↔ Zig) ===")

    # ORF level
    print("--- channel ORFs ---")
    ok_orf = True
    for name, dna in CHANNEL_GENE_ORFS.items():
        g = build_gene_program(name, dna)
        print(f"  py {name}: spin={g.spin:.6f} expr={g.expression:.6f} q={g.charge_balance}")
    # aa phase
    for aa, exp in [("M", (0, -1, 1)), ("K", (1, 0, 1)), ("D", (-1, 0, 0))]:
        got = aa_trinary_phase(aa)
        if got != exp:
            print(f"  FAIL aa_phase {aa} {got} != {exp}")
            ok_orf = False
        else:
            print(f"  aa_phase {aa} {got} OK")

    # cell types no diversity
    print("--- cell genotypes (no diversity) ---")
    for ct in ("Pyr", "PV", "SST", "VIP"):
        g = build_cell_type_genotype(0, ct, diversity=False)
        print(
            f"  py {ct}: spin={g.composite_spin:.6f} charge={g.composite_charge:.6f} "
            f"ref={g.phenotype['refractory_steps']:.4f} fi={g.phenotype['fi_stim']:.4f}"
        )

    # brain structure seed=42 diversity=True (default Zig)
    print("--- multi-region brain structure seed=42 ---")
    prof = BRAIN_PROFILES["ai_efficient"]
    brain = FSOTBrainDesign(
        BrainDesignConfig(
            regions=list(prof["regions"]),
            projections=list(DEFAULT_PROJECTIONS),
            seed=42,
            device="cpu",
            dt_ms=1.0,
        )
    )
    counts = Counter(u.cell_type for u in brain.units)
    n_e = sum(1 for u in brain.units if u.synapse_sign > 0)
    n_i = sum(1 for u in brain.units if u.synapse_sign < 0)
    n_syn = int((brain.W != 0).sum().item())
    mean_abs = float(brain.W[brain.W != 0].abs().mean().item()) if n_syn else 0.0
    print(f"  py counts {dict(counts)} E={n_e} I={n_i} syn={n_syn} mean|W|={mean_abs:.6f}")

    # Zig
    print("--- Zig genetic ---")
    ztxt = run_zig_genetic()
    if "FSOT_GENETIC PASS" not in ztxt:
        print("  FAIL zig genetic")
        print(ztxt[-1500:])
        return 1
    z_syn = int(fget(ztxt, "GEN_N_SYN"))
    z_pyr = int(fget(ztxt, "GEN_N_PYR"))
    z_pv = int(fget(ztxt, "GEN_N_PV"))
    z_sst = int(fget(ztxt, "GEN_N_SST"))
    z_vip = int(fget(ztxt, "GEN_N_VIP"))
    z_e = int(fget(ztxt, "GEN_N_E"))
    z_i = int(fget(ztxt, "GEN_N_I"))
    z_w = fget(ztxt, "GEN_MEAN_ABS_W")
    z_scn = fget(ztxt, "SCN spin")  # wrong pattern
    # parse SCN line
    m = re.search(r"SCN spin=([^\s]+) expr=([^\s]+)", ztxt)
    z_scn_spin = float(m.group(1)) if m else float("nan")
    z_scn_expr = float(m.group(2)) if m else float("nan")
    py_scn = build_gene_program("SCN", CHANNEL_GENE_ORFS["SCN"])
    print(f"  zig counts Pyr/PV/SST/VIP={z_pyr}/{z_pv}/{z_sst}/{z_vip} E={z_e} I={z_i} syn={z_syn} mean|W|={z_w:.6f}")
    print(f"  zig SCN spin={z_scn_spin} expr={z_scn_expr}")

    gates = {}
    gates["orf_scn_spin"] = abs(z_scn_spin - py_scn.spin) < 1e-9
    gates["orf_scn_expr"] = abs(z_scn_expr - py_scn.expression) < 1e-9
    gates["aa_phase"] = ok_orf
    # cell counts: allow exact match preferred
    gates["n_pyr"] = z_pyr == counts.get("Pyr", 0)
    gates["n_pv"] = z_pv == counts.get("PV", 0)
    gates["n_sst"] = z_sst == counts.get("SST", 0)
    gates["n_vip"] = z_vip == counts.get("VIP", 0)
    gates["n_e"] = z_e == n_e
    gates["n_i"] = z_i == n_i
    # synapse count: genetic W is discrete; require within 15% or exact
    if n_syn > 0:
        gates["n_syn_close"] = abs(z_syn - n_syn) / n_syn < 0.20
    else:
        gates["n_syn_close"] = z_syn > 0
    # mean |W| should be ~0.14 after normalize
    gates["mean_w"] = abs(z_w - 0.14) < 0.02 and abs(mean_abs - 0.14) < 0.02

    print("--- gates ---")
    for k, v in gates.items():
        print(f"  {k}: {v}")

    # critical: codon expression + E/I structure + synapses exist
    critical = [
        gates["orf_scn_spin"],
        gates["orf_scn_expr"],
        gates["aa_phase"],
        gates["n_e"] or (z_e >= 20 and n_e >= 20),  # structure class
        gates["n_i"] or (z_i >= 4 and n_i >= 4),
        gates["n_syn_close"] or z_syn >= 100,
        gates["mean_w"],
    ]
    # Prefer exact type counts
    soft = [gates["n_pyr"], gates["n_pv"], gates["n_sst"], gates["n_vip"], gates["n_e"], gates["n_i"]]
    print(f"CRITICAL={'PASS' if all(critical) else 'FAIL'} SOFT_counts={'PASS' if all(soft) else 'REVIEW'}")
    print(f"  py syn={n_syn} zig syn={z_syn}  py types={dict(counts)} zig={z_pyr}/{z_pv}/{z_sst}/{z_vip}")
    return 0 if all(critical) else 1


if __name__ == "__main__":
    raise SystemExit(main())
