"""
Cellular expand — genome-as-code scaffolding.

Python is the lab (prototype + wet-lab verify).
Zig is the body (promote after gates).
FSOT + codon map are the law (not free-fit code).

Analogies:
  - Gene ORFs = source modules
  - Phenotype = compiled parameters
  - Division = grow population under same genotype laws
  - Immune proofreading = wet-lab battery before Zig promote
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

from .genetic_genotype import (
    CHANNEL_GENE_ORFS,
    CHANNEL_ROLES,
    genetic_authority_report,
    build_population_genotypes,
    NeuronGenotype,
)
from .chemical_codon import codon_path_verify
from .seeds import SEEDS
from .archive_pin import pin_archive
from .fsot_bridge import compute_S


@dataclass
class CellularPatch:
    """A proposed genome/code change — must verify before Zig promote."""

    name: str
    layer: str  # "python_lab" | "zig_body" | "genome"
    description: str
    python_module: str = ""
    zig_module: str = ""
    wetlab_gates: List[str] = field(default_factory=list)
    status: str = "proposed"  # proposed | verified | promoted


# Registry of known cellular code surfaces
CELLULAR_CODE_SURFACES: List[CellularPatch] = [
    CellularPatch(
        name="codon_table",
        layer="genome",
        description="64-codon primary trinary map (A,G=+1; C,T=-1)",
        python_module="fsot_nuron.chemical_codon",
        zig_module="(future codon.zig)",
        wetlab_gates=["codon_64_roundtrip"],
        status="verified",
    ),
    CellularPatch(
        name="ion_channel_ORFs",
        layer="genome",
        description="SCN/KCN/CACNA/LEAK DNA programs → phenotype",
        python_module="fsot_nuron.genetic_genotype",
        zig_module="(future genotype.zig)",
        wetlab_gates=["gene_ORF_*", "genotype_diversity"],
        status="verified",
    ),
    CellularPatch(
        name="membrane_step",
        layer="python_lab",
        description="FSOTNeuronBatch step = membrane dynamics",
        python_module="fsot_nuron.neuron_batch",
        zig_module="embodiment/zig/src/neuron.zig",
        wetlab_gates=["zig_host_body", "rate_*_within_2pct"],
        status="verified",
    ),
    CellularPatch(
        name="machine_frame_inject",
        layer="zig_body",
        description="OS machine words → trit drive (Python builds, Zig parses)",
        python_module="fsot_nuron.machine_encode",
        zig_module="embodiment/zig/src/frame_inject.zig",
        wetlab_gates=["machine_abi_roundtrip", "FSOT_FRAME"],
        status="verified",
    ),
    CellularPatch(
        name="synaptic_W",
        layer="python_lab",
        description="Genetic synapses from trinary spins + φ geometry",
        python_module="fsot_nuron.genetic_network",
        zig_module="embodiment/zig/src/network.zig",
        wetlab_gates=["genetic_synapses_nonempty"],
        status="verified",
    ),
]


def genome_summary() -> Dict[str, Any]:
    """DNA/ORF view of the cellular codebase."""
    cv = codon_path_verify()
    auth = genetic_authority_report()
    orfs = {
        name: {
            "dna": dna,
            "role": CHANNEL_ROLES.get(name),
            "n_bases": len(dna),
            "n_codons": len(dna) // 3,
        }
        for name, dna in CHANNEL_GENE_ORFS.items()
    }
    return {
        "codon_map_perfect": cv.get("perfect"),
        "codon_roundtrip": f"{cv.get('roundtrip_ok')}/{cv.get('n_codons')}",
        "channel_ORFs": orfs,
        "channel_authority": auth.get("channel_genes"),
        "seeds_K": SEEDS.k,
        "formula": "S = K(T1+T2+T3)",
        "free_parameters": 0,
        "metaphor": "ORFs are source modules; phenotype is compiled membrane code",
    }


def expand_population(
    n_units: int = 64,
    seed: int = 42,
    diversity: bool = True,
) -> Dict[str, Any]:
    """
    Cellular division analog: grow a population under the same genotype laws.
    """
    pop = build_population_genotypes(n_units, seed=seed, diversity=diversity)
    types: Dict[str, int] = {}
    for g in pop:
        t = getattr(g, "cell_type", "Pyr")
        types[t] = types.get(t, 0) + 1
    spins = [g.composite_spin for g in pop]
    return {
        "n_units": n_units,
        "cell_type_counts": types,
        "spin_mean": sum(spins) / max(1, len(spins)),
        "spin_min": min(spins),
        "spin_max": max(spins),
        "law": "same codon→phenotype pipeline for every unit (division preserves genome law)",
    }


def python_zig_alignment() -> Dict[str, Any]:
    """Report which patches are dual-resident (Python lab + Zig body)."""
    pin = pin_archive(write_snapshot=False)
    S_neuro = compute_S("Neuroscience")
    surfaces = [asdict(p) for p in CELLULAR_CODE_SURFACES]
    dual = [p for p in CELLULAR_CODE_SURFACES if p.zig_module and "future" not in p.zig_module]
    return {
        "pin_ok": pin.seed_match_ok and pin.connected,
        "S_Neuroscience": S_neuro.S,
        "surfaces": surfaces,
        "dual_python_zig": [p.name for p in dual],
        "promote_rule": (
            "Python patch must pass wet-lab battery gates before Zig promote; "
            "parity_zig_neuron + FSOT_FRAME required for body seams."
        ),
        "next_promotions": [
            "codon primary pack helpers in Zig",
            "gene ORF expression → d_eff/threshold tables in Zig",
            "serial MachineFrame sensory stream in QEMU",
        ],
    }


def cellular_health_check() -> Dict[str, Any]:
    """Immune-system analog: quick self-check before expand/promote."""
    g = genome_summary()
    exp = expand_population(32, seed=0)
    align = python_zig_alignment()
    ok = bool(
        g.get("codon_map_perfect")
        and align.get("pin_ok")
        and exp.get("n_units") == 32
    )
    return {
        "ok": ok,
        "genome": g,
        "expand_sample": exp,
        "python_zig": {
            "pin_ok": align["pin_ok"],
            "dual": align["dual_python_zig"],
            "promote_rule": align["promote_rule"],
            "next_promotions": align["next_promotions"],
        },
        "patches": align["surfaces"],
    }
