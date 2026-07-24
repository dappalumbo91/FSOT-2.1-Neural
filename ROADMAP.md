# FSOT-2.1-Neural — roadmap

Public repo: https://github.com/dappalumbo91/FSOT-2.1-Neural  
Theory authority: https://github.com/dappalumbo91/FSOT-2.1-Lean (`vendor/fsot_compute.py` **D1D38A**)

**Mission:** biologically accurate neural network from **genetic codon trinary structure** + FSOT dynamics.  
See `MISSION.md`.

---

## Primary track (genetic-codon network)

| Item | Status |
|------|--------|
| 64-codon map load + 64/64 round-trip | Done |
| Ion-channel gene ORFs (SCN/KCN/CACNA/LEAK) | Done (`genetic_genotype.py`) |
| Phenotype from expression (seed-only) | Done |
| FSOT trinary synaptic \(W_{ij}\) | Done (`genetic_network.py`) |
| Recurrent genetic network dynamics | Done |
| Allen timing lock on genetic population | Done (optional) |
| Primary runner `run_genetic_bio.py` | Done |
| CI smoke on genetic path | Done |
| Mission docs (MISSION / README reframe) | Done |
| Local Obsidian second-brain vault (no server/web) | Done (`run_obsidian_brain.py`) |
| Cell types Pyr/PV/SST/VIP | Done (`cell_types.py`) |
| Multi-region brain + motifs + projections | Done (`brain_architecture.py`, `run_brain_design.py`) |
| Brain path document | Done (`BRAIN_PATH.md`) |

### Next (primary) — see BRAIN_PATH.md Phase A

- [ ] Cell-type-specific ephys bands (PV fast vs Pyr regular)
- [ ] Hard E/I balance gate under thalamic drive
- [ ] Population rhythm / coactivity spectrum probe
- [ ] PV / gene knockout lesions on brain \(W\)
- [ ] Layered cortical column (L2/3, L4, L5) sub-regions
- [ ] Richer multi-gene ORFs from archive consciousness-genetics panels
- [ ] Pair genotypes with Allen cell-type metadata labels
- [ ] Export green brain panels to Lean hub when claim-sensitive
- [ ] Bare-metal / Zig hot path (archive SR-ITE)

---

## Substrate foundation (keep)

| Item | Status |
|------|--------|
| Batched FSOT micro-neuron (CPU/CUDA) | Done |
| Dual modes `bio_match` / `efficient` | Done |
| Archive pin D1D38A | Done |
| Failure boundary catalog | Done |
| Public GitHub + CI | Done |

---

## Secondary / demoted (do not drive the product)

| Item | Status | Note |
|------|--------|------|
| ITU Morse readout | Kept | Demo / optional interface |
| NLP multi-dataset scoreboard | Kept | Not mission KPI |
| IMDB / sentiment climb | Kept | Legacy exploration |
| Kaggle emotions notebook | Kept | External demo path |
| Literature chew-query | Kept | Docs tool, not genotype |

---

## How we pick work

1. **Genetic structure first** — codon → channels → synapses → dynamics  
2. **Reproducible** on public GitHub + archive pin  
3. **Honest bio metrics** (ISI, adapt, rate diversity) over headline NLP accuracy  
4. **Theory pin** (D1D38A / certificate) never silently drifts  
5. Biology is **reference**, not a simulation speed limit (`efficient` mode)  
