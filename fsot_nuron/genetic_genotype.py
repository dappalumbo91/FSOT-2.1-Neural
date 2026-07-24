"""
Genetic / codon genotype for FSOT neurons.

Mission spine (not a language readout):
  DNA codon (64) → primary trinary {-1,+1}³ → amino acid / process
  → ion-channel gene program → neuronal phenotype parameters

Authority:
  - data/64_codon_trinary_map.txt  (A,G=+1; C,T=-1)
  - Standard genetic code (IUPAC)
  - FSOT seeds (π,e,φ,γ) for zero-free-parameter phenotype scales
  - Protein trinary interaction structure (archive genetics formulas)

Ion-channel gene families (neurogenetics proxies):
  SCN   — voltage-gated Na  (threshold / rising)
  KCN   — voltage-gated K   (repolarization / refractory)
  CACNA — voltage-gated Ca  (adaptation / AHP / plasticity)
  LEAK  — leak conductance  (resting set-point)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .chemical_codon import (
    AA_PROCESS,
    DNA_TO_AA,
    codon_path_verify,
    parse_codon_trinary_map,
)
from .seeds import SEEDS, NEURO_D_EFF, NEURO_N_CHANNELS, NEURO_P, RESTING_S

# Canonical short ORFs for ion-channel gene programs (DNA, length multiple of 3).
# These are structural templates — expression strength is modulated by trinary
# statistics of the codon program, not by free-fit weights.
CHANNEL_GENE_ORFS: Dict[str, str] = {
    # Na: start + cationic (K/R) + aromatic (voltage-sensor-like) + stop
    "SCN": "ATGAAATTTCGTTATTGG",
    # K: start + hydrophobic packing + Ser/Thr hydroxyl (mod) + stop
    "KCN": "ATGCTGGTTTCATCTTAG",
    # Ca: start + acidic (D/E) + Cys bridge + aromatic + stop
    "CACNA": "ATGGATGAGTGTTATTGA",
    # Leak: start + Gly/Ala compact + polar + stop
    "LEAK": "ATGGGTGCAAGCTCTTAA",
}

CHANNEL_ROLES = {
    "SCN": "voltage_gated_sodium",
    "KCN": "voltage_gated_potassium",
    "CACNA": "voltage_gated_calcium",
    "LEAK": "leak_resting",
}


@dataclass(frozen=True)
class CodonResidue:
    codon: str
    trinary: Tuple[int, int, int]
    aa: str
    process: str


@dataclass
class GeneProgram:
    name: str
    role: str
    dna: str
    residues: List[CodonResidue]
    mean_trinary: Tuple[float, float, float]
    spin: float  # mean of all primary trits ∈ [-1, 1]
    charge_balance: int
    aromatic_fraction: float
    hydrophobic_fraction: float
    expression: float  # seed-scaled expression ∈ (0, ~2]


@dataclass
class NeuronGenotype:
    """Per-unit genetic program: four channel genes + composite phenotype."""

    unit_id: int
    genes: Dict[str, GeneProgram]
    composite_spin: float
    composite_charge: float
    phenotype: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "composite_spin": self.composite_spin,
            "composite_charge": self.composite_charge,
            "genes": {
                k: {
                    "name": g.name,
                    "role": g.role,
                    "dna": g.dna,
                    "spin": g.spin,
                    "expression": g.expression,
                    "charge_balance": g.charge_balance,
                    "n_codons": len(g.residues),
                    "aa_sequence": "".join(r.aa for r in g.residues),
                }
                for k, g in self.genes.items()
            },
            "phenotype": self.phenotype,
        }


def _aa_charge(aa: str) -> int:
    if aa in "RHK":
        return 1
    if aa in "DE":
        return -1
    return 0


def decode_orf(
    dna: str,
    primary_map: Optional[Dict[str, Tuple[int, int, int]]] = None,
) -> List[CodonResidue]:
    primary_map = primary_map or parse_codon_trinary_map()
    dna = dna.upper().replace("U", "T")
    out: List[CodonResidue] = []
    for i in range(0, len(dna) - 2, 3):
        codon = dna[i : i + 3]
        if len(codon) < 3 or any(b not in "ACGT" for b in codon):
            continue
        trip = primary_map.get(codon)
        if trip is None:
            trip = tuple(1 if b in "AG" else -1 for b in codon)  # type: ignore
        aa = DNA_TO_AA.get(codon, "?")
        out.append(
            CodonResidue(
                codon=codon,
                trinary=(int(trip[0]), int(trip[1]), int(trip[2])),
                aa=aa,
                process=AA_PROCESS.get(aa, "unknown"),
            )
        )
    return out


def gene_expression_from_residues(residues: Sequence[CodonResidue]) -> float:
    """
    Seed-only expression scale (no free parameters).

    expression = φ^{spin} · e^{|q|/(π·n)} · (1 + γ · aromatic)
    normalized so a balanced gene ≈ 1.
    """
    if not residues:
        return 1.0
    trits = [t for r in residues for t in r.trinary]
    spin = sum(trits) / len(trits)
    q = sum(_aa_charge(r.aa) for r in residues)
    n = max(1, len(residues))
    arom = sum(1 for r in residues if r.aa in "FYW") / n
    s = SEEDS
    raw = (s.phi**spin) * math.exp(abs(q) / (s.pi * n)) * (1.0 + s.gamma * arom)
    # Neutral pivot: spin=0, q=0, arom=0 → φ^0 * 1 * 1 = 1
    return float(max(0.05, min(3.0, raw)))


def build_gene_program(
    name: str,
    dna: str,
    primary_map: Optional[Dict[str, Tuple[int, int, int]]] = None,
) -> GeneProgram:
    residues = decode_orf(dna, primary_map)
    if not residues:
        raise ValueError(f"empty ORF for gene {name}")
    trits = [t for r in residues for t in r.trinary]
    spin = sum(trits) / len(trits)
    means = (
        sum(r.trinary[0] for r in residues) / len(residues),
        sum(r.trinary[1] for r in residues) / len(residues),
        sum(r.trinary[2] for r in residues) / len(residues),
    )
    n = len(residues)
    q = sum(_aa_charge(r.aa) for r in residues)
    arom = sum(1 for r in residues if r.aa in "FYW") / n
    hydro = sum(1 for r in residues if r.aa in "AILMFVW") / n
    return GeneProgram(
        name=name,
        role=CHANNEL_ROLES.get(name, name),
        dna=dna,
        residues=residues,
        mean_trinary=means,
        spin=float(spin),
        charge_balance=int(q),
        aromatic_fraction=float(arom),
        hydrophobic_fraction=float(hydro),
        expression=gene_expression_from_residues(residues),
    )


def phenotype_from_genes(genes: Dict[str, GeneProgram]) -> Dict[str, float]:
    """
    Map channel gene expression → FSOT neuron phenotype parameters.

    All scales use seeds only. Allen calibration may later snap refractory
    timing; genetic structure sets relative diversity and channel balance.
    """
    s = SEEDS
    scn = genes["SCN"].expression
    kcn = genes["KCN"].expression
    ca = genes["CACNA"].expression
    leak = genes["LEAK"].expression

    # Effective channel count (genetics N): base 4, modulated by mean expression
    mean_expr = (scn + kcn + ca + leak) / 4.0
    n_channels = NEURO_N_CHANNELS * (0.75 + 0.25 * mean_expr)

    # D_eff: neuroscience base 13, genetic charge / Ca complexity
    d_eff = NEURO_D_EFF + s.phi * (ca - 1.0) * 0.35 + s.gamma * (scn - kcn) * 0.2
    d_eff = float(max(8.0, min(20.0, d_eff)))

    # Fire threshold: more Na → lower threshold (easier spike)
    fire_threshold = 1.05 - 0.12 * (scn - 1.0) + 0.06 * (kcn - 1.0)
    fire_threshold = float(max(0.85, min(1.25, fire_threshold)))

    # Refractory floor (ms): K expression lengthens absolute refractory
    refractory_steps = 12.0 * (0.85 + 0.30 * kcn)
    refractory_steps = float(max(4.0, min(40.0, refractory_steps)))

    # Adaptation step (ms): Ca-driven AHP lengthening per spike
    adapt_step = 0.7 * (0.6 + 0.8 * ca)
    adapt_step = float(max(0.0, min(8.0, adapt_step)))

    adapt_gain = 0.02 * (0.7 + 0.6 * ca)
    adapt_decay = 0.988 - 0.004 * (ca - 1.0)
    adapt_decay = float(max(0.96, min(0.995, adapt_decay)))

    # Resting S: leak pulls toward RESTING_S; Na/Ca raise slightly
    resting_bias = RESTING_S + 0.02 * (scn - leak) * s.eta_eff
    resting_bias = float(max(0.30, min(0.65, resting_bias)))

    # FI stim amplitude: higher Na / lower K → stronger effective drive
    fi_stim = 0.50 * (0.85 + 0.25 * scn - 0.10 * kcn)
    fi_stim = float(max(0.25, min(0.95, fi_stim)))

    # vrest proxy: more leak → more negative rest
    vrest_mV = -70.0 - 3.0 * (leak - 1.0) + 1.5 * (scn - 1.0)
    vrest_mV = float(max(-80.0, min(-55.0, vrest_mV)))

    # Composite spins for synaptic genetics
    composite_spin = sum(g.spin * g.expression for g in genes.values()) / sum(
        g.expression for g in genes.values()
    )
    composite_charge = sum(g.charge_balance * g.expression for g in genes.values()) / 4.0

    return {
        "n_channels": float(n_channels),
        "p_props": float(NEURO_P),
        "d_eff": d_eff,
        "fire_threshold": fire_threshold,
        "refractory_steps": refractory_steps,
        "adapt_step": adapt_step,
        "adapt_gain": float(adapt_gain),
        "adapt_decay": adapt_decay,
        "resting_bias": resting_bias,
        "fi_stim": fi_stim,
        "vrest_mV": vrest_mV,
        "scn_expression": float(scn),
        "kcn_expression": float(kcn),
        "cacna_expression": float(ca),
        "leak_expression": float(leak),
        "composite_spin": float(composite_spin),
        "composite_charge": float(composite_charge),
    }


def mutate_orf(dna: str, unit_id: int, locus: int = 0) -> str:
    """
    Deterministic, seed-free diversity: permute synonymous bases at locus
    using unit_id (structural diversity, not learned weights).
    """
    dna = list(dna.upper())
    # Map of positions that are third-position wobble-ish for diversity
    if not dna:
        return ""
    # Flip purine/pyrimidine class at a deterministic index
    idx = (unit_id * 3 + locus * 5) % len(dna)
    b = dna[idx]
    # Stay in same primary trit class when possible (AG stay AG, CT stay CT)
    if b in "AG":
        dna[idx] = "G" if b == "A" else "A"
    elif b in "CT":
        dna[idx] = "T" if b == "C" else "C"
    return "".join(dna)


def build_neuron_genotype(
    unit_id: int,
    primary_map: Optional[Dict[str, Tuple[int, int, int]]] = None,
    diversity: bool = True,
) -> NeuronGenotype:
    primary_map = primary_map or parse_codon_trinary_map()
    genes: Dict[str, GeneProgram] = {}
    for i, (name, orf) in enumerate(CHANNEL_GENE_ORFS.items()):
        dna = mutate_orf(orf, unit_id, locus=i) if diversity else orf
        genes[name] = build_gene_program(name, dna, primary_map)
    ph = phenotype_from_genes(genes)
    return NeuronGenotype(
        unit_id=unit_id,
        genes=genes,
        composite_spin=float(ph["composite_spin"]),
        composite_charge=float(ph["composite_charge"]),
        phenotype=ph,
    )


def build_population_genotypes(
    n_units: int,
    seed: int = 42,
    diversity: bool = True,
) -> List[NeuronGenotype]:
    """
    Build n_units genotypes. `seed` only reorders unit_ids for sample
    assignment — phenotype math stays seed-derived from codon programs.
    """
    primary = parse_codon_trinary_map()
    # Deterministic shuffle of unit indices via LCG (no numpy dependency)
    ids = list(range(n_units))
    a, c, m = 1103515245, 12345, 2**31
    state = seed & 0x7FFFFFFF
    for i in range(n_units - 1, 0, -1):
        state = (a * state + c) % m
        j = state % (i + 1)
        ids[i], ids[j] = ids[j], ids[i]
    return [build_neuron_genotype(uid, primary, diversity=diversity) for uid in ids]


def aa_trinary_phase(aa: str) -> Tuple[int, int, int]:
    """
    F01-style (charge, polarity, volume) ∈ {-1,0,+1}³ from archive protein formulas.
    """
    charge = _aa_charge(aa)
    if charge > 0:
        c = 1
    elif charge < 0:
        c = -1
    else:
        c = 0
    polar = aa in "STNQYC"
    p = 1 if polar else (-1 if aa in "AILMFVW" else 0)
    large = aa in "ILMFWYRKQE"
    small = aa in "AGSTC"
    if large:
        v = 1
    elif small:
        v = -1
    else:
        v = 0
    return (c, p, v)


def genetic_authority_report() -> Dict[str, Any]:
    """Codon map + gene program invertibility / expression sanity."""
    cv = codon_path_verify()
    genes = {n: build_gene_program(n, dna) for n, dna in CHANNEL_GENE_ORFS.items()}
    ph = phenotype_from_genes(genes)
    return {
        "codon_map": cv,
        "channel_genes": {
            n: {
                "dna": g.dna,
                "role": g.role,
                "spin": g.spin,
                "expression": g.expression,
                "aa": "".join(r.aa for r in g.residues),
                "n_codons": len(g.residues),
            }
            for n, g in genes.items()
        },
        "canonical_phenotype": ph,
        "mission": (
            "Genetic codon structure defines ion-channel programs; "
            "FSOT scalar drives dynamics; phenotype is not free-fit."
        ),
    }
