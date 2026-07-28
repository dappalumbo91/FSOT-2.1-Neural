# Multi-species motifs → computer-centric brain

## Why leave “human-only” as the sole template?

Human wet-lab data (Allen Cre ephys, iEEG SME, EEG learning) is the **best authority for rates and learning bands**.  
But **human cortex is huge, incomplete as a connectome, and metabolically “wet.”**

A **computer-native** organism may better match:

| Property | Human neo-cortex | Fruit fly brain | Computer goal |
|----------|------------------|-----------------|---------------|
| Neuron count | ~10¹⁰ | ~10⁵ (whole brain) | **small–medium N**, scalable |
| Connectome | partial | **complete** (FlyWire-class maps) | known wiring motifs |
| Recurrence | massive | compact, mapped | controllable loops |
| Sensory | multi-modal rich | vision/olfaction specialized | **AV + text + plant** we already wire |
| Goal | survival body | survival body | **task + embodiment on silicon** |

**Doctrine:** use **human data for dynamics & learning metrics**; use **fly (and C. elegans, etc.) for graph motifs and efficiency** when refining computer-centric architecture. Not “become a fly” — **steal wiring lessons**.

---

## Public authorities (literature; optional bulk data)

| Species | Resource | Use |
|---------|----------|-----|
| *Drosophila* | FlyWire / whole-brain connectome papers (~2023–2024) | degree distributions, hub neurons, sensory→central depth |
| *C. elegans* | Complete hermaphrodite connectome (classic) | tiny closed graph baselines |
| Mouse | Allen Cell Types, MICrONS (optional) | cell class + partial cortex |
| Human | iEEG/EEG learning studies | SME, consolidation, language-adjacent bands |

Bulk connectome files are **optional downloads** (multi-GB). Standalone clone ships **targets + importers only**.

---

## What we store in-repo

`fsot_nuron/species/fly_connectome.py`:

- Literature-scale **targets** (order-of-magnitude N, sensory pathways)
- Motif checklist for FSOT multi-region graphs
- Optional CSV/edge-list import hook when user places files under `data/species/fly/`

---

## Mapping to FSOT multi-region (today)

| Fly-ish motif | FSOT analog |
|---------------|-------------|
| Sensory periphery → central brain | `sens` ← world inject |
| Hub / convergence | `thal` + `assoc` hubs |
| Mushroom body / learning | `hipp` episodic + genetic W |
| Compact recurrence | sparse genetic `W`, AI-efficient profiles |

Efficiency profiles already exist: `ai_efficient` vs `wetware_ref` in `brain_architecture.py`.

---

## Climb path

1. Score current FSOT graphs on **motif stats** vs fly literature targets (not full synapse import).  
2. Optional: import small FlyWire subsets for degree-matching experiments.  
3. Keep Allen + SME as **hard gates** so “computer-centric” never means “ignore wet-lab rates.”
