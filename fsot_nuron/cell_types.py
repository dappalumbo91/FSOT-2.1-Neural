"""
Cortical cell-type genotypes for FSOT brain design.

Maps biological classes onto ion-channel gene programs (codon ORFs) and
excitatory/inhibitory transmitter sign. No free-fit weights — expression
and ORF templates only; FSOT seeds scale phenotype as in genetic_genotype.

Canonical mammalian neocortex mix (simplified, literature-typical):
  ~80% excitatory pyramidal
  ~20% inhibitory (PV / SST / VIP split of interneurons)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .genetic_genotype import (
    CHANNEL_GENE_ORFS,
    NeuronGenotype,
    build_gene_program,
    mutate_orf,
    phenotype_from_genes,
    parse_codon_trinary_map,
)
from .seeds import SEEDS


@dataclass(frozen=True)
class CellTypeSpec:
    """One biologically named class."""

    id: str
    label: str
    transmitter: str  # glutamate | gaba
    sign: int  # +1 excitatory synapse polarity, -1 inhibitory
    # Relative channel ORF overrides (DNA); missing keys use CHANNEL_GENE_ORFS
    orf_overrides: Dict[str, str]
    # Multipliers on gene expression after decode (seed-scaled, not LSQ)
    expression_bias: Dict[str, float]
    # Target share among units in a generic cortical column
    cortical_fraction: float
    notes: str


# ORF templates emphasize class-typical channel balance (still codon-legal DNA).
CELL_TYPES: Dict[str, CellTypeSpec] = {
    "Pyr": CellTypeSpec(
        id="Pyr",
        label="pyramidal_excitatory",
        transmitter="glutamate",
        sign=1,
        orf_overrides={
            # Stronger Na / Ca flavor for regular-spiking excitatory
            "SCN": "ATGAAACGGTTCTATTGG",
            "CACNA": "ATGGATGAGTGCTACTGA",
            "KCN": "ATGCTGGTTTCCAGTTAG",
            "LEAK": "ATGGGTGCAAGCTCTTAA",
        },
        expression_bias={"SCN": 1.15, "KCN": 0.95, "CACNA": 1.10, "LEAK": 1.0},
        cortical_fraction=0.80,
        notes="Regular-spiking excitatory principal cell proxy.",
    ),
    "PV": CellTypeSpec(
        id="PV",
        label="parvalbumin_fast_spiking",
        transmitter="gaba",
        sign=-1,
        orf_overrides={
            # High K (fast repolarization), high Na, lower Ca adaptation
            "SCN": "ATGAAATTTAAGCGTTGG",
            "KCN": "ATGAAACGTGTTTCGTAG",
            "CACNA": "ATGGCTGCATCCTCTTAG",
            "LEAK": "ATGGGTGCTAACTCTTAA",
        },
        expression_bias={"SCN": 1.25, "KCN": 1.45, "CACNA": 0.70, "LEAK": 0.95},
        cortical_fraction=0.08,
        notes="Fast-spiking basket-like interneuron proxy (short ISI).",
    ),
    "SST": CellTypeSpec(
        id="SST",
        label="somatostatin_adapting",
        transmitter="gaba",
        sign=-1,
        orf_overrides={
            "SCN": "ATGAAATTCCGCTATTGA",
            "KCN": "ATGCTGGTTACATCTTAA",
            "CACNA": "ATGGATGACTGCTATTGA",
            "LEAK": "ATGGCAGCAAGCTCTTAA",
        },
        expression_bias={"SCN": 0.95, "KCN": 1.05, "CACNA": 1.35, "LEAK": 1.05},
        cortical_fraction=0.07,
        notes="Martinotti-like adapting inhibitory proxy.",
    ),
    "VIP": CellTypeSpec(
        id="VIP",
        label="vip_disinhibitory",
        transmitter="gaba",
        sign=-1,
        orf_overrides={
            "SCN": "ATGAAACAGTTCTATTAA",
            "KCN": "ATGTTGGTTTCTTCTTAA",
            "CACNA": "ATGGAGGAGTGTTCTTGA",
            "LEAK": "ATGGGTTCAAACTCTTAA",
        },
        expression_bias={"SCN": 1.05, "KCN": 0.90, "CACNA": 1.15, "LEAK": 1.10},
        cortical_fraction=0.05,
        notes="Disinhibitory interneuron proxy (targets other IN).",
    ),
}


def list_cell_types() -> List[str]:
    return list(CELL_TYPES.keys())


def build_cell_type_genotype(
    unit_id: int,
    cell_type: str,
    diversity: bool = True,
) -> NeuronGenotype:
    """Genotype for one unit of a named biological class."""
    if cell_type not in CELL_TYPES:
        raise ValueError(f"unknown cell type {cell_type!r}; use {list_cell_types()}")
    spec = CELL_TYPES[cell_type]
    primary = parse_codon_trinary_map()
    genes = {}
    for i, (name, base_orf) in enumerate(CHANNEL_GENE_ORFS.items()):
        orf = spec.orf_overrides.get(name, base_orf)
        if diversity:
            orf = mutate_orf(orf, unit_id, locus=i)
        genes[name] = build_gene_program(name, orf, primary)

    # Apply class expression bias (multiplicative on seed expression)
    from .genetic_genotype import GeneProgram

    biased = {}
    for name, g in genes.items():
        bias = float(spec.expression_bias.get(name, 1.0))
        # Rebuild with scaled expression — GeneProgram is a dataclass
        biased[name] = GeneProgram(
            name=g.name,
            role=g.role,
            dna=g.dna,
            residues=g.residues,
            mean_trinary=g.mean_trinary,
            spin=g.spin,
            charge_balance=g.charge_balance,
            aromatic_fraction=g.aromatic_fraction,
            hydrophobic_fraction=g.hydrophobic_fraction,
            expression=float(max(0.05, min(3.5, g.expression * bias))),
        )
    ph = phenotype_from_genes(biased)

    # Class-specific phenotype nudges (still seed-bounded, not free LSQ)
    s = SEEDS
    if cell_type == "PV":
        # Fast-spiking: shorter refractory, higher threshold recovery
        ph["refractory_steps"] = float(max(3.0, ph["refractory_steps"] * 0.45))
        ph["adapt_step"] = float(ph["adapt_step"] * 0.35)
        ph["fire_threshold"] = float(max(0.85, ph["fire_threshold"] - 0.04))
        ph["fi_stim"] = float(min(0.95, ph["fi_stim"] * 1.15))
    elif cell_type == "SST":
        ph["adapt_step"] = float(min(10.0, ph["adapt_step"] * 1.4))
        ph["refractory_steps"] = float(ph["refractory_steps"] * 1.05)
    elif cell_type == "VIP":
        ph["fi_stim"] = float(ph["fi_stim"] * 0.9)
        ph["d_eff"] = float(min(20.0, ph["d_eff"] + 0.3 * s.phi))
    elif cell_type == "Pyr":
        ph["adapt_step"] = float(ph["adapt_step"] * 1.05)

    ph["cell_type"] = float(hash(cell_type) % 1000)  # numeric tag only for tensors if needed
    ph["synapse_sign"] = float(spec.sign)
    ph["cell_type_id"] = cell_type  # type: ignore[assignment] — kept in dict for reports

    # Store string meta separately via genotype
    gt = NeuronGenotype(
        unit_id=unit_id,
        genes=biased,
        composite_spin=float(ph["composite_spin"]),
        composite_charge=float(ph["composite_charge"]),
        phenotype=ph,
    )
    # Attach non-float metadata on object
    gt.cell_type = cell_type  # type: ignore[attr-defined]
    gt.transmitter = spec.transmitter  # type: ignore[attr-defined]
    gt.synapse_sign = spec.sign  # type: ignore[attr-defined]
    return gt


def allocate_cell_types(n_units: int, mix: Optional[Dict[str, float]] = None) -> List[str]:
    """
    Allocate cell-type labels for n units from fractions (default cortical mix).
    Guarantees at least one Pyr and one inhibitory when n >= 4.
    """
    mix = dict(mix or {k: v.cortical_fraction for k, v in CELL_TYPES.items()})
    # normalize
    total = sum(mix.values()) or 1.0
    mix = {k: v / total for k, v in mix.items()}
    labels: List[str] = []
    # largest remainder method
    raw = {k: mix[k] * n_units for k in mix}
    base = {k: int(raw[k]) for k in raw}
    for k, c in base.items():
        labels.extend([k] * c)
    rem = n_units - len(labels)
    order = sorted(raw.keys(), key=lambda k: raw[k] - base[k], reverse=True)
    for i in range(rem):
        labels.append(order[i % len(order)])
    # safety for tiny nets
    if n_units >= 4 and "Pyr" not in labels:
        labels[0] = "Pyr"
    if n_units >= 4 and not any(x != "Pyr" for x in labels):
        labels[-1] = "PV"
    # stable order: group by type for readable regions
    order_ids = ["Pyr", "PV", "SST", "VIP"]
    labels.sort(key=lambda x: order_ids.index(x) if x in order_ids else 99)
    return labels[:n_units]


def build_typed_population(
    n_units: int,
    mix: Optional[Dict[str, float]] = None,
    seed: int = 42,
    diversity: bool = True,
) -> List[NeuronGenotype]:
    labels = allocate_cell_types(n_units, mix)
    # deterministic unit_id shuffle for diversity without changing counts
    ids = list(range(n_units))
    a, c, m = 1103515245, 12345, 2**31
    state = seed & 0x7FFFFFFF
    for i in range(n_units - 1, 0, -1):
        state = (a * state + c) % m
        j = state % (i + 1)
        ids[i], ids[j] = ids[j], ids[i]
    out: List[NeuronGenotype] = []
    for local_i, uid in enumerate(ids):
        ct = labels[local_i]
        out.append(build_cell_type_genotype(uid, ct, diversity=diversity))
    # re-index unit_id to 0..n-1 in list order for network matrix alignment
    for i, g in enumerate(out):
        g.unit_id = i
    return out


def population_type_report(genotypes: List[NeuronGenotype]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    signs = []
    for g in genotypes:
        ct = getattr(g, "cell_type", "unknown")
        counts[ct] = counts.get(ct, 0) + 1
        signs.append(int(getattr(g, "synapse_sign", 1)))
    n = max(1, len(genotypes))
    n_exc = sum(1 for s in signs if s > 0)
    n_inh = sum(1 for s in signs if s < 0)
    return {
        "n_units": len(genotypes),
        "counts": counts,
        "fractions": {k: v / n for k, v in counts.items()},
        "n_excitatory": n_exc,
        "n_inhibitory": n_inh,
        "ei_count_ratio": n_exc / max(1, n_inh),
        "target_cortical_pyr_fraction": CELL_TYPES["Pyr"].cortical_fraction,
    }
