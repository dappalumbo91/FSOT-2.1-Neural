# Biological accuracy — what we mean (and what we still need)

**You already use wet-lab data.** Allen Cell Types ephys on this machine (~2333 cells, mouse + human), OpenNeuro PD priors, Kaggle EEG features, archive public science caches — those come from real laboratories and clinics, not from us inventing numbers.

---

## 0. Biological time vs computer GHz (important)

| | Biological / model time | Silicon wall-clock |
|--|-------------------------|---------------------|
| Unit | 1 step = 1 ms of *simulated* neuron time | real milliseconds on CPU/QEMU |
| Rate “80 Hz” | 80 spikes per **model** second | how fast we *simulate* that second |
| Bare metal | Does **not** rewrite biology | Runs the same protocol faster |

If PV is wrong vs Allen, fix **phenotype lock to wet-lab ms/Hz**, not “slow the computer down.”  
Performance tweaks (`efficient` mode, Zig speed) come **after** `bio_match` fidelity.

Learning-band targets (theta/gamma, etc.): **`docs/LEARNING_ALIGNMENT.md`**.

---

## 1. The confusing phrase (and the fix)

When docs said **“not wet-lab identity”**, that did **not** mean:

- we refuse wet-lab data, or  
- the brain should be “non-biological,” or  
- stay-at-home / no personal lab = cannot be accurate.

It meant only this technical distinction:

| Phrase | Meaning |
|--------|---------|
| **Wet-lab *data*** | Measurements from real tissue, animals, humans (Allen, OpenNeuro, NeuroElectro, papers). **We use these. We should use more.** |
| **Wet-lab *identity*** | Claiming “this simulation *is* the same physical neuron sitting in a dish right now” or “we ran the patch clamp.” That claim is false for *any* software model, including industry HH/Markov models. |

**Your goal is the right one:** a computer neurological system whose **structure and dynamics match biological neurological systems** as closely as public data and FSOT law allow — for humans and other species — without owning a wet lab.

**Correct honesty language going forward:**

> FSOT neural dynamics are **calibrated and scored against public wet-lab and clinical datasets** (Allen Cell Types, OpenNeuro, …). We claim **biological fidelity under named protocols and error gates**, not that the computer *is* a living preparation.

If a piece of biology is missing, the answer is **import more public wet-lab data and close the gate** — not lower the ambition.

---

## 2. What “biologically accurate” means here (operational)

A claim is allowed when **all** hold:

1. **Public wet-lab (or clinical) authority** for the target numbers (Allen, OpenNeuro, NeuroElectro, peer-reviewed tables, archive credential-free APIs).  
2. **Preregistered FSOT structure** (scalar, codon genetics, cell-type signs) — no silent free-fit of the law.  
3. **Named protocol** (stimulus, dt, mode `bio_match`, unit count, seed).  
4. **Hard metric** within a declared band (ISI, adaptation, rate, class order PV faster than Pyr, E/I ratio, …).  
5. **Reproducible** (`python run_…` + stage markdown).

That *is* scientific biological accuracy for a computational system. Full molecular identity of every channel protein is a **gap list**, not a reason to stop.

---

## 3. Wet-lab data we already hold (this machine)

| Source | Path / role | Species |
|--------|-------------|---------|
| Allen Cell Types ephys features | `data/eeg/allen_ephys/ephys_features.csv` | mouse + human |
| Allen cell metadata | `data/eeg/allen_ephys/cells.json` (Cre lines: Pvalb, Sst, Vip, Rorb, …) | mouse + human |
| Allen NWB sample | `data/eeg/allen_ephys/ephys.nwb` | — |
| OpenNeuro PD index/priors | `data/eeg/openneuro_pd/` | human clinical |
| Emotions EEG features | `data/eeg/kaggle_emotions/` | human (feature tables) |
| Archive public science | `I:\FSOT-Physical-Archive\03_FSOT-PublicData\` | multi-domain |

**Cre-line labels in `cells.json` are wet-lab genetic identity** — we use them to lock PV / SST / VIP / Pyr classes to real ephys.

---

## 4. Known gaps → data to grab next

| Gap | Why it matters | Public fill |
|-----|----------------|-------------|
| Class-specific ISI/rate (PV vs Pyr) | Fast-spiking vs regular-spiking biology | Allen `line_name` + ephys (in progress) |
| Layer-specific stats (L2/3, L4, L5) | Column architecture | Allen `structure__layer` |
| Full continuous PD EEG | Disease boundary realism | OpenNeuro ds002778 EDF (partial index exists) |
| Synaptic kinetics / PSP shapes | More than sign ±1 | NeuroElectro, published tables, Allen synaptic datasets |
| Human-only cortical panels | Species fidelity | Allen human cells subset already in cells.json |
| Ion channel densities | Gene→phenotype | Allen transcriptomics / Patch-seq public releases |
| Morphology | Wiring geometry | Allen reconstruction metrics in cells.json (`nr__*`) |

**Policy:** prefer **credential-free public** sources (same FSOT archive rule). Document every download in `data/external/DOWNLOAD_MANIFEST.json` or stage docs.

---

## 5. How class accuracy works (this update)

```text
Allen cells.json (Cre line, dendrite type, layer)
    + ephys_features.csv (ISI, adapt, rate, Vrest, …)
        → class targets for Pyr / PV / SST / VIP
        → FSOT cell-type genotypes + bio_match lock
        → gate: mean_rate(PV) > mean_rate(Pyr) under same FI
               mean_isi(PV) < mean_isi(Pyr)
```

Runner: `python run_class_ephys.py`

---

## 6. Relation to Zig body

Python lab = where wet-lab data **locks** phenotypes.  
Zig body = same step law, parity-tested, bare metal.  
Biological accuracy is **not abandoned** when we leave Python — the lock moves with the ABI.

---

## 7. Bottom line for this project

- You **do** have wet-lab data.  
- We will **keep pulling** public wet-lab data to fill gaps.  
- “Not wet-lab identity” only rejects the false claim that software *is* a dish experiment — it does **not** reject biological accuracy as the goal.  
- **Biological accuracy via public wet-lab authority is the goal.**  
