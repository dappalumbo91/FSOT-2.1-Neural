"""
FSOT Micro-Neuron — GPU/CPU batched substrate.

Small, bio-mirroring reservoir neurons on Fluid Spacetime Omni-Theory.
Theory authority: FSOT-2.1-Lean / physical archive (I:/FSOT-Physical-Archive).
"""

__version__ = "0.3.0"

from .neuron_batch import FSOTNeuronBatch, NeuronConfig
from .reservoir import FluidReservoir
from .paths import ROOT, ARTIFACTS, ARCHIVE_ROOT, LEAN_HUB
from .modes import OperatingMode

__all__ = [
    "FSOTNeuronBatch",
    "NeuronConfig",
    "FluidReservoir",
    "OperatingMode",
    "ROOT",
    "ARTIFACTS",
    "ARCHIVE_ROOT",
    "LEAN_HUB",
    "__version__",
]
