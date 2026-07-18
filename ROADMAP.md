# FSOT-2.1-Neural — roadmap

Public repo: https://github.com/dappalumbo91/FSOT-2.1-Neural  
Theory authority: https://github.com/dappalumbo91/FSOT-2.1-Lean (`vendor/fsot_compute.py` **D1D38A**)

## Done (foundation)

| Item | Status |
|------|--------|
| Batched FSOT micro-neuron (CPU/CUDA) | Done |
| Dual modes `bio_match` / `efficient` | Done |
| Allen-facing bio lock (ISI ~2%, adapt ~0.1%) | Done |
| Failure boundaries + auto wire-around | Done |
| ITU Morse + 64-codon chemical path | Done |
| GPU consensus (no softmax) | Done |
| Kaggle emotions notebook path | Done |
| Multi-dataset scoreboard (EEG + NLP) | Done (metrics honesty hardening in progress) |
| Physical archive pin + certificate snapshot | Done |
| Public GitHub package | Done |

## Now (next engineering)

### 1. Versionable quality gates (this sprint)

- [x] GitHub Actions CI smoke (seeds, Morse, codon, tiny neuron, failure catalog)
- [x] Honest text metrics: **hard top-1**, confusion matrix, balanced accuracy
- [ ] Re-run multi-dataset scoreboard under hard metrics; commit summary artifact text (not huge CSVs)
- [ ] Badge + short “Results” section in README from latest hard numbers

### 2. Bio report card (wetware track)

- [ ] Single `artifacts/bio_report_card.json` + markdown table as release artifact
- [ ] Population ISI residual under 1 ms grid floor documented as floor, not failure
- [ ] Optional Allen API spot-check documented as optional

### 3. Real EEG depth (PD / OpenNeuro)

- [ ] Pull continuous OpenNeuro ds002778 EDF samples (licensed) into lesion path
- [ ] PD signature metrics from real signal stats, not priors only
- [ ] Keep clinical disclaimer hard

### 4. Learning on the substrate (not a transformer)

- [ ] Online reservoir readout training (linear / FSOT-gated) on Morse fingerprints
- [ ] SMS / sentiment with held-out **train vs test** split (current is LOO retrieval — honest but different)
- [ ] Multi-dataset notebook on Kaggle (code only; third-party data attached by user)

### 5. Scale + consensus

- [ ] Population sweep 64 → 4k → 16k with GPU crossover curve in CI artifact
- [ ] Lesion-aware consensus quarantine integration test
- [ ] Coupling demo: Neural substrate → FSOT-GPU attention stack

### 6. Later (not blocking)

- Bare metal / QEMU / Zig hot path (archive already has stacks)
- Medical claims of any kind — **out of scope forever** without clinical partners

## How we pick work

1. **Reproducible** on public GitHub first  
2. **Honest metrics** over headline accuracy  
3. **Theory pin** (D1D38A / certificate) never silently drifts  
4. Biology is **reference**, not a speed limit (`efficient` mode)  
