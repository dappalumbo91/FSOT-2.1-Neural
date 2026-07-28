"""
Drosophila / fly-connectome motif targets for computer-centric FSOT design.

Authority is **public literature** (FlyWire whole-brain mapping and related work).
We do not ship multi-GB synapse tables in the transplant package.

Use:
  - Compare FSOT multi-region W motif stats to fly-scale targets
  - Optional future: import edge lists from data/species/fly/
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch

from ..paths import DATA

# Literature-scale targets (order-of-magnitude; refine as we import data)
FLY_LITERATURE_TARGETS: Dict[str, Any] = {
    "species": "Drosophila melanogaster",
    "common_name": "fruit fly",
    "resources": [
        {
            "name": "FlyWire / whole-brain connectome",
            "era": "2023-2024",
            "note": "Adult brain synaptic reconstruction; ~1e5 neurons scale",
            "url_hint": "https://flywire.ai / related Nature/Science publications",
        },
    ],
    "n_neurons_order": 1.4e5,  # whole brain order of magnitude
    "properties": {
        "connectome_completeness": "near-complete adult brain (literature)",
        "sensory": ["vision", "olfaction", "mechanosensation"],
        "learning_structure": "mushroom body (associative)",
    },
    # Motif targets for *comparison*, not identity
    "motif_targets": {
        "mean_out_degree_norm": 0.02,  # sparse-ish relative connectivity proxy
        "reciprocity_lo": 0.05,
        "reciprocity_hi": 0.35,
        "hub_fraction": 0.05,  # top hubs carry disproportionate edges
        "feedforward_depth_hint": 4,  # sensory→central layers order
    },
    "computer_centric_lesson": (
        "Prefer compact N + known motifs over human neuron census; "
        "keep human wet-lab for rate/learning band gates."
    ),
}


@dataclass
class GraphMotifScore:
    n_units: int
    n_edges: int
    density: float
    mean_abs_w: float
    reciprocity: float
    hub_edge_fraction: float
    vs_fly: Dict[str, Any]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def score_graph_motifs(
    W: torch.Tensor,
    *,
    thr: float = 0.02,
) -> GraphMotifScore:
    """
    Motif statistics on FSOT weight matrix W[post, pre].
    Compare lightly to fly literature targets (not a claim of fly identity).
    """
    Wc = W.detach().cpu().float()
    n = int(Wc.shape[0])
    mask = Wc.abs() > thr
    n_edges = int(mask.sum().item())
    density = n_edges / max(1, n * (n - 1))
    mean_abs = float(Wc[mask].abs().mean().item()) if n_edges else 0.0
    # reciprocity: fraction of edges that have reverse edge
    both = mask & mask.T
    recip = float(both.sum().item()) / max(1, n_edges)
    # hub fraction: top 5% nodes by out-degree share of edges
    out_deg = mask.float().sum(dim=0)  # pre → 
    k = max(1, int(0.05 * n))
    topk = torch.topk(out_deg, k=k).indices
    hub_edges = int(mask[:, topk].sum().item())
    hub_frac = hub_edges / max(1, n_edges)

    tgt = FLY_LITERATURE_TARGETS["motif_targets"]
    notes = [
        "Comparison is motif-level only — FSOT N≪ fly whole brain.",
        FLY_LITERATURE_TARGETS["computer_centric_lesson"],
    ]
    vs = {
        "density_vs_fly_mean_out_norm": {
            "ours": density,
            "fly_target_norm": tgt["mean_out_degree_norm"],
            "ratio": density / max(1e-9, tgt["mean_out_degree_norm"]),
        },
        "reciprocity_in_fly_band": bool(
            tgt["reciprocity_lo"] <= recip <= tgt["reciprocity_hi"]
        ),
        "hub_fraction": {
            "ours": hub_frac,
            "fly_target": tgt["hub_fraction"],
        },
    }
    return GraphMotifScore(
        n_units=n,
        n_edges=n_edges,
        density=density,
        mean_abs_w=mean_abs,
        reciprocity=recip,
        hub_edge_fraction=hub_frac,
        vs_fly=vs,
        notes=notes,
    )


def fly_motif_report(brain_or_W) -> Dict[str, Any]:
    """Accept FSOTBrainDesign or raw W tensor."""
    if hasattr(brain_or_W, "W"):
        W = brain_or_W.W
        extra = {
            "regions": list(getattr(brain_or_W, "region_index", {}).keys()),
            "n_units": getattr(brain_or_W, "n_units", None),
        }
    else:
        W = brain_or_W
        extra = {}
    score = score_graph_motifs(W)
    return {
        "literature": FLY_LITERATURE_TARGETS,
        "score": score.to_dict(),
        "brain": extra,
        "optional_data_dir": str(DATA / "species" / "fly"),
        "import_note": "Place edge-list CSV here later for denser comparisons; not required to boot.",
    }


def optional_import_edge_list(path: Path) -> Optional[torch.Tensor]:
    """
    Optional: load NxN or edge-list for experiments.
    Formats: .pt tensor, or CSV i,j,w
    """
    path = Path(path)
    if not path.is_file():
        return None
    if path.suffix == ".pt":
        return torch.load(path, map_location="cpu")
    # CSV edges
    import csv

    edges: List[Tuple[int, int, float]] = []
    nmax = 0
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        for row in r:
            if not row or row[0].startswith("#"):
                continue
            i, j = int(row[0]), int(row[1])
            w = float(row[2]) if len(row) > 2 else 1.0
            edges.append((i, j, w))
            nmax = max(nmax, i, j)
    n = nmax + 1
    W = torch.zeros(n, n)
    for i, j, w in edges:
        W[j, i] = w  # post, pre convention optional
    return W
