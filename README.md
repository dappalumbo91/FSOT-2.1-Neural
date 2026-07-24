# FSOT-2.1-Neural

**Fluid Spacetime Omni-Theory 2.1 — genetic-codon neural network**

Biologically structured **FSOT neurons** whose identity and wiring come from the **64-codon trinary genetic map** and ion-channel gene programs (SCN / KCN / CACNA / LEAK). Dynamics use the zero-free-parameter scalar \(S = K(T_1+T_2+T_3)\). Multi-region brain design for **computer-native AI**: mechanism fidelity to neurological systems, **not** human neuron census (see efficiency doctrine). Optional Allen ephys lock. **Not** a free-parameter transformer NLP project.

| Science docs | |
|--------------|--|
| **Thesis (living)** | [`docs/THESIS.md`](docs/THESIS.md) |
| **Formulas** | [`docs/FORMULAS.md`](docs/FORMULAS.md) |
| **Efficiency** | [`docs/EFFICIENCY_DOCTRINE.md`](docs/EFFICIENCY_DOCTRINE.md) |
| **Path** | [`BRAIN_PATH.md`](BRAIN_PATH.md) |

| | |
|--|--|
| **Mission** | See **`MISSION.md`** (read this first) |
| **Primary runner** | `python run_genetic_bio.py` |
| **Theory authority** | [FSOT-2.1-Lean](https://github.com/dappalumbo91/FSOT-2.1-Lean) + `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full` |
| **Archive pin** | `python run_archive_pin.py` → must report `connected: True` on this machine |
| **Codon authority** | `data/64_codon_trinary_map.txt` (A,G=+1 · C,T=−1) |
| **License** | Apache-2.0 |
| **GitHub** | [FSOT-2.1-Neural](https://github.com/dappalumbo91/FSOT-2.1-Neural) |
| **Results** | `data/results/GENETIC_NETWORK.md` · legacy NLP demos under `RESULTS.md` |
| **Hardware** | CPU (small nets) · NVIDIA CUDA (large populations) |

> Neurological failure modes are **substrate engineering boundaries**. This is **not** a medical device, diagnosis, or treatment.

---

## Intended architecture

```text
64-codon trinary map
    ↓
Ion-channel gene ORFs (SCN Na · KCN K · CACNA Ca · LEAK)
    ↓
Per-unit phenotype (d_eff, threshold, refractory, AHP, FI drive)
    ↓
Synaptic W_ij = FSOT trinary interaction (e, π, φ) + charge term
    ↓
FSOTNeuronBatch dynamics + recurrent genetic synapses
    ↓
Allen timing lock (bio_match) + hard bio metrics
```

**Codon structure is the genotype of the network**, not a post-hoc language decoder.

---

## Quick start (primary path)

```powershell
cd "I:\fsot nuron"
pip install -r requirements.txt
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"

# 0) Pin theory authority
python run_archive_pin.py

# 1) Genetic-codon network (mission)
python run_genetic_bio.py --units 64 --steps 1200
python run_genetic_bio.py --connectivity genetic_sparse

# 2) Multi-region brain design (default: ai_efficient — fewer units, computer-native)
python run_brain_design.py --profile ai_efficient --obsidian
python run_brain_design.py --profile wetware_ref   # larger bio-comparison layout
# Open artifacts/obsidian_vaults/FSOT_Brain_Design in Obsidian (local graph)
# Thesis ledger appends to data/thesis_ledger/runs.jsonl

# 3) Population genetic vault (single-region view)
python run_obsidian_brain.py

# 4) Lean formal panel (codon · neuro fold · cell types)
python scripts/verify_formal.py

# 5) Zig neuron step parity vs Python + Allen bio card
python scripts/parity_zig_neuron.py
cd embodiment\zig; powershell -File .\run_qemu.ps1

# 6) CI smoke
python scripts/ci_smoke.py
```

**Current stage doc:** [`docs/STAGE_ZIG_NEURON_STEP.md`](docs/STAGE_ZIG_NEURON_STEP.md)  
**Road to a full brain design:** [`BRAIN_PATH.md`](BRAIN_PATH.md)  
**Python → Zig body:** [`docs/EMBODIMENT_ROADMAP.md`](docs/EMBODIMENT_ROADMAP.md)

### Local second brain (offline)

| | |
|--|--|
| **Exporter** | `python run_obsidian_brain.py` |
| **Output** | `artifacts/obsidian_vaults/FSOT_Neural_Second_Brain/` |
| **Network** | None — pure local Markdown + wikilinks |
| **View** | Obsidian desktop → Open folder as vault → Graph view |

Neuron notes link to each other by strongest genetic synapses; gene + atlas notes organize the pattern. Sync/Publish plugins are disabled in the vault config.


### What `run_genetic_bio.py` reports

| Gate | Meaning |
|------|---------|
| Codon 64/64 | Map invertibility |
| Channel genes | SCN/KCN/CACNA/LEAK ORFs decode |
| Synapses | Non-empty \(W\) from trinary spins |
| Dynamics | FI rates, ISI, adaptation |
| Allen lock | Optional refractory snap to ephys targets |
| Rate↔SCN corr | Genetic expression couples to firing diversity |

---

## Package layout

```
fsot_nuron/
  genetic_genotype.py   # codon → gene programs → phenotype  (PRIMARY)
  genetic_network.py    # genetic W + FSOT dynamics           (PRIMARY)
  scalar.py             # vectorized S = K(T1+T2+T3)
  neuron_batch.py       # batched active neurons
  chemical_codon.py     # 64-codon map parse / verify
  calibrate.py          # Allen ISI / adapt analytical lock
  allen_data.py         # ephys CSV / API
  bio_metrics.py        # ISI, adaptation, bands
  failure_boundaries.py # lesion catalog (engineering)
  # --- secondary / demos ---
  morse_itu.py          # optional symbolic readout
  language_loop.py      # Morse + codon demo loop
  multi_dataset.py      # NLP/EEG scoreboard (non-mission)
run_genetic_bio.py      # primary entrypoint
run_bio_validate.py     # Allen-facing batch (non-genetic legacy path)
run_archive_pin.py
```

---

## Modes

| Mode | Intent |
|------|--------|
| **bio_match** | Refractory / AHP sized to Allen ISI & adaptation (validation) |
| **efficient** | Same structure, shorter trains (throughput) |

Biology is the **reference**, not a hard ceiling on simulation speed.

---

## Genetic structure (detail)

### Ion-channel gene programs

| Gene | Role | Phenotype levers |
|------|------|------------------|
| **SCN** | Voltage-gated Na | Lower fire threshold, stronger FI |
| **KCN** | Voltage-gated K | Longer refractory |
| **CACNA** | Voltage-gated Ca | Adaptation / AHP strength |
| **LEAK** | Leak | Resting \(S\) / \(V_{rest}\) proxy |

Expression scales are **seed-only** (\(\varphi, e, \pi, \gamma\)) from codon trinary + AA charge/aromatic stats — no least-squares channel fits.

### Synapses

\[
W_{ij} \propto \underbrace{\bigl((\tau_i\tau_j)\,e + (1-|\tau_i\tau_j|)\,\pi\bigr)}_{\text{trinary pair}}
\cdot \varphi\,|i-j|^{-1/\pi}
\cdot \text{envelope}
+ \text{electrostatic}(q_i,q_j)
\]

Normalized; optional sparse / local topology masks.

---

## Secondary demos (not the product)

These remain for exploration; do **not** treat them as the mission KPI:

```powershell
python run_language_loop.py --verify-only   # Morse + codon readout demo
python run_failure_probe.py --mode all      # neurological lesion envelopes
python run_multi_dataset.py                 # NLP/EEG scoreboard (legacy climb)
python run_climb.py                         # hierarchical NLP climb (legacy)
```

See `RESULTS.md` / `SOTA_FRONTS.md` for legacy numbers. Mission metrics live in **`data/results/GENETIC_NETWORK.md`**.

---

## Failure boundaries

Known neurodegenerative break modes → FSOT lesions → wire-around.  
Catalog: `data/neuro_failure_boundaries.json`. Not a clinical tool.

```powershell
python run_failure_probe.py --list
```

---

## Data paths

```powershell
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"
$env:FSOT_ALLEN_EPHYS = "D:\path\to\ephys_features.csv"   # optional override
$env:FSOT_NURON_ARTIFACTS = "I:\fsot nuron\artifacts"
```

Default Allen features (if present on this machine): Desktop nuron cell data CSV.

---

## Related work on this machine

| Path | Role |
|------|------|
| `I:\FSOT-Physical-Archive` | Lean authority + genetics + SR-ITE |
| `I:\FSOT-Physical-Archive\04_Genetics-Longevity` | Codon map + protein formulas |
| [FSOT-2.1-Lean](https://github.com/dappalumbo91/FSOT-2.1-Lean) | Public theory |

---

## License

Apache-2.0. Keep experimental reports under `artifacts/` and `data/results/`.
