"""Multi-species connectome motifs for computer-centric design."""

from .fly_connectome import (
    FLY_LITERATURE_TARGETS,
    score_graph_motifs,
    fly_motif_report,
)

__all__ = [
    "FLY_LITERATURE_TARGETS",
    "score_graph_motifs",
    "fly_motif_report",
]
