"""
FSOT-2.1-Neural — genetic-codon neural substrate.

Primary mission: biologically accurate neural networks whose structure comes
from 64-codon trinary genetics (ion-channel gene programs + FSOT synapses),
driven by the zero-free-parameter FSOT scalar.

Theory authority: FSOT-2.1-Lean / physical archive (I:/FSOT-Physical-Archive).
"""

__version__ = "0.4.0"

from .neuron_batch import FSOTNeuronBatch, NeuronConfig
from .reservoir import FluidReservoir
from .paths import ROOT, ARTIFACTS, ARCHIVE_ROOT, LEAN_HUB
from .modes import OperatingMode
from .genetic_genotype import NeuronGenotype, build_population_genotypes
from .genetic_network import GeneticNeuralNetwork, GeneticNetworkConfig
from .obsidian_brain import ObsidianExportConfig, build_obsidian_vault

__all__ = [
    "FSOTNeuronBatch",
    "NeuronConfig",
    "FluidReservoir",
    "OperatingMode",
    "NeuronGenotype",
    "build_population_genotypes",
    "GeneticNeuralNetwork",
    "GeneticNetworkConfig",
    "ObsidianExportConfig",
    "build_obsidian_vault",
    "ROOT",
    "ARTIFACTS",
    "ARCHIVE_ROOT",
    "LEAN_HUB",
    "__version__",
]
