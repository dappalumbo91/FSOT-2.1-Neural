# Thesis: FSOT Genetic Neural Architecture for Computer-Native Intelligence

| Field | Value |
|-------|--------|
| **Title** | Fluid Spacetime Omni-Theory (FSOT) 2.1 — Genetic-Codon Neural Substrate and Efficient Multi-Region Brain Design for Artificial Intelligence |
| **Author** | Damian Arthur Palumbo |
| **Document type** | Living research thesis (methods + formulas + measured results) |
| **Theory authority** | [FSOT-2.1-Lean](https://github.com/dappalumbo91/FSOT-2.1-Lean) · pin **D1D38A…** |
| **Code repository** | [FSOT-2.1-Neural](https://github.com/dappalumbo91/FSOT-2.1-Neural) |
| **Physical archive** | `I:\FSOT-Physical-Archive` |
| **Companion formulas** | [`docs/FORMULAS.md`](FORMULAS.md) |
| **Formal verification choice** | [`docs/FORMAL_VERIFICATION_CHOICE.md`](FORMAL_VERIFICATION_CHOICE.md) |
| **Efficiency doctrine** | [`docs/EFFICIENCY_DOCTRINE.md`](EFFICIENCY_DOCTRINE.md) |
| **Path / phases** | [`BRAIN_PATH.md`](../BRAIN_PATH.md) |
| **Last revised** | 2026-07-24 |
| **Status** | Active research — revised with each architecture run |

---

## Abstract

We construct an artificial neural substrate whose **structure** is derived from the **64-codon trinary genetic map** and ion-channel gene programs, whose **dynamics** are driven by the **zero-free-parameter FSOT scalar** \(S = K(T_1+T_2+T_3)\), and whose **wiring** follows preregistered biological microcircuit motifs and multi-region projections. Real public ephys statistics (e.g. Allen Cell Types) constrain timing and class behavior where data exist.

A central design claim separates **biological fidelity of mechanism** from **biological parity of scale**:

1. Human cortex processes interoception, homeostasis, and motor plant feedback that a **computer-native** agent does not require.  
2. Digital hardware can advance discrete state at wall-clock rates far above wetware milliseconds.  
3. Therefore an **FSOT neurological AI** can target **functional equivalence** (same architectural motifs, same genetic law, same measured gates) with **orders-of-magnitude fewer units** than human neuron counts — validated against **real data bands**, not against “86 billion” as a size goal.

This thesis is **living**: every claim is tied to formulas in `docs/FORMULAS.md`, code paths in this repository, and ledger rows under `data/thesis_ledger/`.

---

## 1. Research questions

**Q1.** Can a zero-free-parameter FSOT scalar, folded at neuroscience domain priors, produce spike-like dynamics whose population ISI/adaptation match Allen ephys envelopes?

**Q2.** Can the 64-codon trinary map define ion-channel gene programs (SCN/KCN/CACNA/LEAK) that yield class-typed neurons (Pyr/PV/SST/VIP) with E/I polarity without least-squares synaptic fits?

**Q3.** Can preregistered cortical motifs plus named long-range projections form a multi-region “mini-brain” whose E/I ratio and drive propagation are measurable and reproducible?

**Q4.** Under the **efficiency doctrine**, what is the smallest FSOT network (by unit count) that still satisfies the same structural gates as a larger wetware-reference layout?

**Q5.** How do local second-brain graphs (Obsidian Markdown wikilinks) make connective patterns inspectable without servers or cloud?

---

## 2. Background and prior FSOT stack

FSOT derives constants from seeds \(\{\pi, e, \varphi, \gamma, G\}\) and routes domains through preregistered folds \((D_{\mathrm{eff}}, \text{hits}, \delta\psi, \delta\theta, \text{observed})\). Multi-prover verification and public-data panels live in the physical archive and FSOT-2.1-Lean (see `FSOT_REPRODUCIBLE_METHODOLOGY.md` / archive methodology).

This repository **does not re-derive** the multi-domain certificate. It **pins** authority (SHA-256 `D1D38A…`) and **applies** the scalar to a genetic neural domain engine.

---

## 3. Methods (reproducible pipeline)

### 3.1 Authority pin

```text
resolve I:\FSOT-Physical-Archive → vendor/fsot_compute.py
hash == certificate authority (D1D38A…)
local seeds match closed forms (float64, max rel err ~1e-14)
```

Entry: `python run_archive_pin.py` · module `fsot_nuron.archive_pin`.

### 3.2 Genetic genotype

```text
DNA codon (64) → primary trinary (A,G=+1; C,T=−1)
  → AA / process → gene ORF expression (seed-only)
  → phenotype: d_eff, threshold, refractory, AHP, FI
```

Modules: `genetic_genotype.py`, `chemical_codon.py`, map `data/64_codon_trinary_map.txt`.

### 3.3 Cell types

| Class | Tx | Role |
|-------|-----|------|
| Pyr | glutamate (+) | principal excitatory |
| PV | GABA (−) | fast-spiking inhibition |
| SST | GABA (−) | adapting inhibition |
| VIP | GABA (−) | disinhibition of other I |

Module: `cell_types.py`. Cortical mix ~80/8/7/5% (preregistered fractions).

### 3.4 Synaptic law

Pair interaction (FSOT protein / fluid-to-solid lineage) + geometric falloff + electrostatic term; motif gains for E→E, E→I, I→E, I→I, VIP→I. Long-range E→E projections named feedforward/feedback.

See **FORMULAS §4–5**.

### 3.5 Multi-region layout

Default: thalamus → sensory cortex ↔ association ↔ hippocampus, with feedback loops.  
**Profiles:**

| Profile | Intent |
|---------|--------|
| `wetware_ref` | Literature-like timing; larger column for bio comparison |
| `ai_efficient` | Computer-native: fewer units, efficient refractory scale, no vegetative load |

Module: `brain_architecture.py` · runner `run_brain_design.py`.

### 3.6 Validation against real data

- Allen Cell Types ephys CSV (local / credential-free paths) for ISI & adaptation envelopes.  
- Codon map 64/64 invertibility.  
- Structural gates: E present, I present, multi-region, projections, synapses, finite E/I mass.  
- **Not claimed:** medical diagnosis, full human connectome, consciousness proof.

### 3.7 Local inspectability

Obsidian vaults under `artifacts/obsidian_vaults/` — Markdown + wikilinks only; no HTTP server; Sync/Publish disabled.

### 3.8 Thesis ledger

Each scientific run may append a JSONL row:

`data/thesis_ledger/runs.jsonl`

via `fsot_nuron.thesis_ledger.record_run(...)`.

---

## 4. Efficiency doctrine (summary)

Full text: [`EFFICIENCY_DOCTRINE.md`](EFFICIENCY_DOCTRINE.md).

- **Mechanism fidelity** (genetic structure, FSOT dynamics, E/I motifs) is mandatory.  
- **Scale parity** with human neuron counts is **not** a goal.  
- Omit systems load (immune, gut, endocrine, full sensorimotor plant) unless the application requires it.  
- Use **wall-clock** and **unit-steps/s** as efficiency metrics alongside bio-reference ISI locks.

---

## 5. Results (living)

Results are regenerated; do not treat this section as frozen. Point to:

| Artifact | Content |
|----------|---------|
| `data/results/BRAIN_DESIGN.md` | Multi-region structure + dynamics |
| `data/results/GENETIC_NETWORK.md` | Genetic population gates |
| `data/results/bio_report_card.md` | Allen-facing bio lock (batch path) |
| `data/thesis_ledger/runs.jsonl` | Append-only experiment log |
| `docs/FORMULAS.md` | Math spine used in code |

### 5.1 Snapshot (2026-07-24, ai path)

- Genetic codon map: **64/64** perfect  
- Mini-brain wetware_ref scale 1.0: E/I count ratio ≈ **3.9**, multi-region PASS  
- Archive pin: **seed_match_ok**, authority **D1D38A**  
- Obsidian brain vault: local export PASS  

*Update this subsection when ledger rows supersede it.*

---

## 6. Discussion

### 6.1 Why fewer units can still be “neurological”

The architectural claim is **isomorphism of organization** (genetic ion-channel programs, E/I motifs, region loops), not **isomorphism of census**. A CPU updating \(N=64\) FSOT units at \(>10^5\) unit-steps/s can explore more discrete cognitive steps per second than a wetware column of the same \(N\) at ~ms ISI — see efficiency doctrine.

### 6.2 What accuracy means here

Accuracy is **to measured public data and closed-form FSOT law**, not to marketing SOTA NLP. Wrong path: free-parameter transformers as the product KPI. Right path: pin → genetics → motifs → gates on real ephys/structure.

### 6.3 Limitations

- Discrete 1 ms step grid floors residual ISI error.  
- Gene ORFs are structural templates, not full SCN/KCN genomics.  
- Long-range projections are preregistered sparse motifs, not tractography.  
- Rhythm/knockout Phase A items still open (`BRAIN_PATH.md`).

---

## 7. Related work on this machine

| Resource | Role |
|----------|------|
| `I:\FSOT-Physical-Archive` | Master proofs, genetics, public data |
| FSOT-2.1-Lean | Formal / certificate authority |
| Archive methodology | Multi-prover + 0.5% green gate on science panels |

---

## 8. How to reproduce this thesis’s claims

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"

python run_archive_pin.py
python run_genetic_bio.py --units 64 --steps 1200
python run_brain_design.py --profile ai_efficient --obsidian
python run_brain_design.py --profile wetware_ref --steps 800
python scripts/ci_smoke.py
```

Ledger append is automatic when runners call `thesis_ledger.record_run`.

---

## 9. Versioning and GitHub

- Code + thesis markdown ship on **https://github.com/dappalumbo91/FSOT-2.1-Neural**  
- Theory pin remains **FSOT-2.1-Lean**  
- Large third-party CSVs and local vaults stay off git (see `.gitignore`)  
- Thesis `Last revised` date bumps on material method changes  

---

## 10. Ethics / non-claims

Not a medical device. Not a claim of human-equivalent consciousness. Computational research artifact under Apache-2.0.
