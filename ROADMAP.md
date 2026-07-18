# FSOT-2.1-Neural — roadmap

Public repo: https://github.com/dappalumbo91/FSOT-2.1-Neural  
Theory authority: https://github.com/dappalumbo91/FSOT-2.1-Lean (`vendor/fsot_compute.py` **D1D38A**)

## Done

| Item | Status |
|------|--------|
| Batched FSOT micro-neuron (CPU/CUDA) | Done |
| Dual modes `bio_match` / `efficient` | Done |
| Allen-facing bio lock + report card | Done (`data/results/bio_report_card.*`) |
| Failure boundaries + auto wire-around | Done |
| ITU Morse + 64-codon chemical path | Done |
| GPU consensus + quarantine | Done |
| Kaggle emotions notebook path | Done |
| Multi-dataset hard scoreboard | Done |
| Archive pin + certificate snapshot | Done |
| Public GitHub + CI smoke | Done |
| Train/test FSOT-gated readout | Done (`data/results/train_test_readout.json`) |
| Scale sweep + lesion consensus | Done |
| PD EEG depth report | Done (`data/results/pd_eeg_depth.json`) |
| One-shot `run_forward_stack.py` | Done |

## Next (deeper)

- [ ] Close strict adapt gap (≤10% vs Allen) without breaking ISI lock
- [ ] Held-out multi-seed readout averages + bootstrap CIs
- [ ] Full OpenNeuro ds002778 EDF continuous segments (when licensed download complete)
- [ ] Multi-dataset Kaggle notebook (code only; user attaches data)
- [ ] Couple Neural → published FSOT-GPU repo as submodule/path pin
- [ ] Bare metal / Zig hot path (archive stacks)

## How we pick work

1. **Reproducible** on public GitHub first  
2. **Honest metrics** over headline accuracy  
3. **Theory pin** (D1D38A / certificate) never silently drifts  
4. Biology is **reference**, not a speed limit (`efficient` mode)  
