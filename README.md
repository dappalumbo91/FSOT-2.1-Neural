# FSOT-2.1-Neural

**Fluid Spacetime Omni-Theory 2.1 — micro-neuron / neural substrate**

Small, batched **FSOT active neurons** on CPU or CUDA — cortical-style dynamics, neurological **failure boundaries**, ITU Morse + **chemical codon** readout, and **FSOT consensus** (no softmax). Not a free-parameter giant net.

| | |
|--|--|
| **Theory authority** | [FSOT-2.1-Lean](https://github.com/dappalumbo91/FSOT-2.1-Lean) + local master `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full` |
| **Archive pin** | `python run_archive_pin.py` (must report `connected: True` on this machine) |
| **Scalar spine** | \(S = K(T_1+T_2+T_3)\) zero free parameters on theory path |
| **License** | Apache-2.0 |
| **Suggested GitHub name** | `FSOT-2.1-Neural` (see `GITHUB_PUBLISH.md`) |
| **Kaggle** | Notebook already run — see `KAGGLE_RUNBOOK.md` |
| **CI** | GitHub Actions smoke on every push (`scripts/ci_smoke.py`) |
| **Results** | See **`RESULTS.md`** and `data/results/` (hard metrics) |
| **Roadmap** | See `ROADMAP.md` |
| **Hardware** | NVIDIA GPU (RTX 5070 class validated) + vectorized CPU |

> Neurological failure modes are **substrate engineering boundaries**. This is **not** a medical device, diagnosis, or treatment.

## Results (latest forward stack)

Re-run the full stack anytime:

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
python run_forward_stack.py
```

| Track | Headline (honest) |
|-------|-------------------|
| **CI smoke** | Seeds / Morse / codon / neuron / failure catalog |
| **Scoreboard** | SMS hard top-1 ~0.80 · mental-state fit ~0.81 · emotions fit ~0.65 · sentiment hard ~0.48 |
| **Bio card** | ISI ~1.8% vs Allen; adapt ~20% (operational pass; strict 5/6 gaps) |
| **Train/test readout** | SMS test ~0.60 · sentiment test ~0.27 (linear probe on FSOT fingerprints — not LOO retrieval) |
| **Scale** | CPU efficient at small-N; CUDA wins as N→4k+ |
| **PD + consensus** | EEG-informed lesion + wire-around + unit quarantine path |

Full tables and JSON: **`RESULTS.md`**, `data/results/`.

## Why small

Edge systems (e.g. vehicle perception stacks) already run on compact nets. The claim here is not “bigger is better” — it is that **FSOT structure** (phase, refractory, trinary emergence, fluid bleed/poof terms) is a deeper substrate than shallow parameter counts, even at **Tesla-scale** sizes (tens–hundreds of units).

## Layout

```
fsot_nuron/           package
  scalar.py           vectorized FSOT scalar (CPU+CUDA)
  neuron_batch.py     batched FSOTActiveNeuron
  reservoir.py        small FluidLink U-Net reservoir
  bio_metrics.py      firing / ISI / adaptation / Vm proxy
  allen_data.py       local CSV + optional Allen/NeuroElectro API
  validate.py         cross-check vs Allen population
run_gpu_neuron.py     main substrate runner + bench
run_bio_validate.py   biological validation
files-3ccbc49e/       original v1–v4 prototypes (reference)
artifacts/            reports, benches
```

## Quick start

```powershell
cd "I:\fsot nuron"
pip install -r requirements.txt
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"

# 0) Connect substrate to FSOT 2.1 archive / Lean verification
python run_archive_pin.py

# Auto device: CPU for small nets (launch-bound), CUDA for large populations
python run_gpu_neuron.py --device auto --units 64 --steps 1000 --reservoir
python run_gpu_neuron.py --device cuda --units 4096 --steps 400 --bench

# Allen-mapped bio validation (closes ISI / adaptation gaps in bio_match)
python run_bio_validate.py --device auto --units 64 --steps 1000 --mode bio_match

# Intelligence throughput mode (faster trains, same structure)
python run_bio_validate.py --mode efficient

# Optional live Allen Brain Atlas API spot-check
python run_bio_validate.py --api
python run_bio_validate.py --status-only
```

### Modes (biology is reference, not speed limit)

| Mode | Intent |
|------|--------|
| **bio_match** | Refractory ≈ 0.78× Allen `avg_isi`; mild AHP → close ISI & adaptation gaps |
| **efficient** | Same FSOT dynamics, ~3× shorter ISI for more cognitive steps / second |

Dual-mode runs print an **efficiency ledger** (`isi_speedup`, `rate_speedup`). Structure stays; wetware latency is not a ceiling.

### FSOT-grade calibration

Analytical lock + population snap (SMILES Lab–style precision ledger):

| Metric | Budget | Typical after lock |
|--------|--------|--------------------|
| Pop mean ISI | ≤ **2%** (1 ms grid floor ~1.4% at 70 ms) | ~**1.8%** |
| Pop mean adaptation | ≤ **10%** | ~**0.1%** |
| Codon map | **64/64** round-trip | perfect |
| ITU Morse symbolic | **exact** charset | 100% char acc |
| SMILES Lab chemistry bar | median err **0.058%** (your archive) | referenced |

```powershell
python run_bio_validate.py --mode bio_match
```

### Language loop (Morse + chemical generative)

```powershell
python run_language_loop.py --verify-only          # authority gates only
python run_language_loop.py --mode efficient        # full Hamlet probe
python run_language_loop.py --text "FSOT 2.1" --mode efficient
```

Layers: **ITU Morse** (lossless interpretation) → **fluid reservoir** → **64-codon chemical generative** (your trinary map) + reconstruction head.

### Neurological failure boundaries

Known neurodegenerative / neurological break modes → FSOT lesions → envelope breach + wire-around.  
**Not a medical product** — boundary knowledge for substrate design (side benefit: failure maps that medicine already studies).

```powershell
python run_failure_probe.py --list
python run_failure_probe.py --mode all
python run_failure_probe.py --mode AD_synaptic_fatigue
```

Catalog: `data/neuro_failure_boundaries.json` (AD, PD, ALS, MS, epilepsy, ischemia, synuclein-like).

### Sub-ms timing + FSOT-GPU consensus

- Sub-ms refractory residual on each unit (finer than 1 ms grid for efficient mode).
- Consensus attention (no softmax) under Morse/chem readout:

```powershell
python run_gpu_consensus.py --text "TO BE OR NOT TO BE"
```

### Real neural signals + literature chew / Morse query

```powershell
# Allen NWB + OpenNeuro PD priors + Kaggle emotions.csv (staged under data/eeg/)
python -c "from fsot_nuron.emotions_eeg import integrate_with_eeg_bundle; print(integrate_with_eeg_bundle()['ok'])"

# Chew FSOT literature then ask questions (Morse + fluid retrieval articulation)
python run_chew_query.py --demo
python run_chew_query.py --query "What is the FSOT scalar?"
python run_chew_query.py --chew --max-chunks 50
```

Kaggle emotions EEG: `data/eeg/kaggle_emotions/emotions.csv` (from `D:\training data\archive\`).  
See **`KAGGLE_AND_LICENSING.md`** and notebook `notebooks/kaggle/FSOT_2_1_Neural_Kaggle_Emotions.ipynb`.

### Multi-dataset scoreboard (EEG + NLP)

```powershell
# download more with kaggle CLI into data/kaggle_datasets/<name>/
python run_multi_dataset.py
# → artifacts/multi_dataset_scoreboard.json
```

Fits **tabular EEG features** (class energy / separability → FSOT drive) and **NLP** (chew labeled text → Morse/fluid retrieval accuracy).

This is **not** a transformer LLM: Morse-exact query decode + reservoir fingerprint memory + extractive articulation from chewed literature.

### Later: bare metal (not yet)

When refined enough: port hot path to **C / Rust / Zig** on your existing FSOT **QEMU bootable** stacks — physical body / bare-metal emergence.

### Substrate policy (CPU + GPU)

Recurrent neuron steps are **serial in time**. For small populations (Tesla-scale tens–hundreds of units), **vectorized CPU** wins on unit-steps/s. The **GPU remains the correct substrate** for large populations and for coupling into the FSOT-GPU attention stack. `--device auto` picks by workload; `--bench` prints the crossover curve.

### Data paths

Default Allen features (already on this machine if present):

- `C:\Users\damia\Desktop\nuron\cell data\allen_cell_types\ephys_features.csv`

Override:

```powershell
$env:FSOT_ALLEN_EPHYS = "D:\path\to\ephys_features.csv"
$env:FSOT_NURON_ARTIFACTS = "I:\fsot nuron\artifacts"
```

## Bio metrics (what we compare)

| FSOT signal | Biological equivalent |
|-------------|------------------------|
| Spike events | Action potential count / rate (Hz) |
| Early vs late ISI | Adaptation index |
| ISI CV | Spike irregularity |
| \(S\) → linear map | \(V_m\) proxy (mV) |
| Min stim for spikes | Rheobase proxy |
| Trinary +1 fraction | Emergent / active duty |

Allen CSV supplies population targets (\(V_{rest}\), \(\tau\), \(R_{in}\), adaptation, avg ISI, \(f\)–\(I\) slope). Per-cell maps set \(D_{eff}\), fire threshold, \(V_{rest}\) readout — **scalar remains zero free parameters**.

## Related work on this machine

| Path | Role |
|------|------|
| `...\gpu exparment for lean coq isabell andf star` | CUDA consensus / FSOT-GPU ops |
| `...\Desktop\nuron` | Allen hybrid model, character LM |
| `I:\FSOT-Physical-Archive` | Lean authority + SR-ITE + public data |
| `I:\fsot in mathmatica` | Formula microscope / living mind |
| `...\Desktop\pflt` | Proto-fluid language translator |

## License lineage

Apache-2.0 aligned with your public FSOT repos. Keep experimental reports under `artifacts/`.
