# Path to a biologically accurate FSOT brain design

**Goal:** a brain-like architecture built from genetic-codon neurons and connective patterns — **mechanism fidelity** to real neurological structure and FSOT law, **not** human neuron census parity.

**Living thesis:** [`docs/THESIS.md`](docs/THESIS.md) · **Formulas:** [`docs/FORMULAS.md`](docs/FORMULAS.md) · **Efficiency:** [`docs/EFFICIENCY_DOCTRINE.md`](docs/EFFICIENCY_DOCTRINE.md)

**Efficiency pivot:** computers run faster and need no vegetative plant → use **`ai_efficient`** profile (fewer units, faster trains) for AI; use **`wetware_ref`** when comparing to Allen/biology.

---

## Where we are now (foundation)

| Layer | Status | What it is |
|-------|--------|------------|
| 0. Theory pin | **Done** | FSOT scalar \(S=K(T_1+T_2+T_3)\), authority D1D38A |
| 1. Genetic codon neuron | **Done** | 64-codon → SCN/KCN/CACNA/LEAK phenotype |
| 2. Cell types | **Done** | Pyr / PV / SST / VIP gene programs + E/I sign |
| 3. Microcircuit motifs | **Done** | E→E, E→I, I→E, I→I, VIP disinhibition |
| 4. Multi-region layout | **Done** | thal → sens ↔ assoc ↔ hipp (+ feedback) |
| 5. Local graph view | **Done** | Obsidian vault (offline) of neurons/regions |
| 6. Population ephys lock | **Partial** | Allen ISI/adapt on batch path; region-typed lock next |

```text
YOU ARE HERE ──► multi-region mini-brain + living thesis + ai_efficient profile
                 python run_brain_design.py --profile ai_efficient --obsidian
```

---

## Where we go next (ordered)

### Phase A — Make the mini-brain *more biological* (near term)

1. **Cell-type ephys targets**  
   Lock Pyr / PV / SST to class-typical rate & ISI bands (PV fast, Pyr regular-spiking, SST adapting) using Allen cell-type labels when available.

2. **E/I balance gate**  
   Hard metric: cortical-like ~4:1 count ratio + synaptic mass band; fail closed if inhibition collapses.

3. **Oscillation / rhythm probes**  
   Under thalamic pulse drive, measure population spectral peaks (alpha/beta/gamma proxies) from spike trains — structure test, not EEG clinical claim.

4. **Gene-knockout lesions**  
   Silence SCN/KCN or drop PV population; wire-around on genetic \(W\) (ties to failure boundaries).

5. **Obsidian = design board**  
   Always export region-colored graph after architecture changes (local only).

**Command focus:**

```powershell
python run_brain_design.py --profile ai_efficient --obsidian
python run_brain_design.py --profile wetware_ref --steps 1000
python run_genetic_bio.py --units 64
python run_obsidian_brain.py
# thesis ledger: data/thesis_ledger/runs.jsonl
```

### Phase B — Scale the architecture (medium term)

| Step | Deliverable |
|------|-------------|
| B1 | Layered cortical column (L2/3, L4, L5) as sub-regions |
| B2 | Bilateral hemispheres + callosal E→E sparse projection |
| B3 | Basal ganglia / cerebellum *stubs* (same genetic neuron substrate) |
| B4 | Sensory input channels → thalamus → cortex (structured external drive) |
| B5 | Memory loop: sens → hipp → assoc replay schedule |

Still **zero free parameters** on the FSOT scalar; topology stays seed + genetics + preregistered motifs.

### Phase C — Validation stack (ongoing, parallel)

| Check | Against |
|-------|---------|
| Codon 64/64 | Map authority |
| Channel genes | ORF decode |
| Allen / cell-type rates | Public ephys |
| E/I stability | Motif literature bands |
| Failure modes | `neuro_failure_boundaries.json` |
| Archive pin | D1D38A green |

### Phase D — Embodiment (later)

- Couple brain design → archive **Zig / SR-ITE** bare-metal stacks  
- Physical or robotic I/O only after A–C metrics are honest and reproducible  

---

## Design rules (do not break)

1. **Genetics first** — structure from codon/cell-type programs, not random dense nets.  
2. **FSOT scalar only** for membrane dynamics — no ad-hoc LSQ on \(S\).  
3. **Motifs are preregistered** — E/I wiring rules named and versioned.  
4. **Local interfaces** — Obsidian/files on disk; no required server for design view.  
5. **Honest claims** — computational brain *design*, not a clinical human brain replica.  
6. **NLP demos stay demoted** — they do not steer architecture.

---

## Success snapshot (Phase A exit criteria)

- [x] Multi-region graph with E and I cell types  
- [x] Long-range projections named (FF/FB)  
- [x] Local vault shows region + cell-type connectivity  
- [ ] PV fires faster than Pyr under same drive (class separation)  
- [ ] E/I mass ratio in a declared healthy band under drive  
- [ ] Knockout PV → rate runaway or sync change (predicted signature)  
- [ ] Re-run on clean pin always reproduces structure hash  

---

## One-sentence north star

**A multi-region, cell-typed, genetically structured FSOT brain whose connective patterns you can *see* (Obsidian) and *measure* (ephys-style metrics) — built only from codon law + FSOT scalar + preregistered biological motifs.**
