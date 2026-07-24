# Learning alignment — instrumental human data → FSOT neural targets

**Status:** living roadmap (not yet fully implemented as closed gates).  
**Purpose:** Keep human **encoding / retention / retrieval / creative use** of information as measurable alignment targets while we stay biologically accurate on cell-class ephys and port to bare metal.

These targets come from **instrumental wet-lab / clinical recordings** (iEEG, EEG, fMRI, MEG) — public literature your project can treat the same way as Allen ephys: **authority for dynamics**, not metaphors.

---

## 1. Two clocks (your Hz question)

| Clock | What it is | Controls |
|-------|------------|----------|
| **Biological / protocol time** | `dt = 1 ms` steps; ISI in ms; rates in Hz **inside the model** | Wet-lab match (Allen PV ~80 Hz *in sim time*) |
| **Silicon wall-clock** | How fast the PC/QEMU executes those steps | Throughput only |

**Bare metal does not automatically “make PV fire wrong.”**  
If we run 20 steps of 1 ms with refractory set for ~20 ms ISI, the **biological rate is ~50 Hz in model time**, whether Zig does that in 1 µs or 1 ms of wall time.

Rate gaps we saw (PV sim ~30 Hz vs Allen ~83 Hz) were from **phenotype lock not tight enough**, not from “computers are too fast.”  

**Policy (your preference):**  
1. **First** close wet-lab fidelity in `bio_match` (class rates, ISI, order).  
2. **Then** use `efficient` / bare-metal wall-clock speed for performance — **same structure**, shorter wall time per cognitive step.

Documented also in `docs/BIO_ACCURACY.md` and `docs/EFFICIENCY_DOCTRINE.md`.

---

## 2. Learning phases → measurable neural signatures

### 2.1 Encoding / ingestion (subsequent memory effect)

| Finding | Instrument | FSOT mapping (planned) |
|---------|------------|-------------------------|
| Successful encoding ↑ **theta (4–8 Hz)** + **gamma (28–64 Hz)** power | iEEG (Sederberg et al., 2003, *J Neurosci*) | Population spike / S spectrogram in `hipp` + `assoc` during “study” inject; SME = later retrieval success |
| Theta–gamma coupling as multi-item code | Reviews / replications | Phase-amplitude coupling proxy between slow S oscillation and fast trinary bursts |
| MTL / hippocampus central; neocortex distributed | iEEG spatial | Region tags: `hipp`, `sens`, `assoc` already in brain design |

### 2.2 Retention / consolidation

| Finding | Instrument | FSOT mapping (planned) |
|---------|------------|-------------------------|
| Sleep reactivation: ↑ theta, sigma (~12–16 Hz), gamma; gamma ↔ improvement | iEEG MTL (Creery et al., 2022, *PNAS*) | Offline “rest” protocol: low external drive, spontaneous reactivation of prior patterns; consolidation score vs retention probe |
| Encoding theta tags items for sleep consolidation | iEEG / EEG | Encoding-time theta power → priority weight for offline replay |

### 2.3 Retrieval

| Finding | Instrument | FSOT mapping (planned) |
|---------|------------|-------------------------|
| Overlapping theta/gamma; hippocampal–neocortical dialogue | iEEG | Query inject → pattern completion along genetic \(W\); match encoding bands |

### 2.4 Creative / flexible application

| Finding | Instrument | FSOT mapping (planned) |
|---------|------------|-------------------------|
| ↑ **alpha (8–12 Hz)** (frontal / right temporal) in ideation | EEG | “Reconfigure” mode: alpha-band power on association population |
| DMN ↔ executive network switching | fMRI networks | Dual-mode coupling between assoc loops and control-like thalamic drive |
| Hippocampus + MTG for novel combinations | fMRI | Cross-region bridges `hipp`↔`assoc` already in projection list |

### 2.5 Classroom / concept-specific learning

| Finding | Instrument | FSOT mapping (planned) |
|---------|------------|-------------------------|
| Distinct BOLD / hippocampal patterns per CS concept; classifiers ~94% | fMRI (Zhang et al., 2025, *Front. Neurosci.*) | Concept tokens as distinct sensory trit fingerprints; decode concept id from regional activity |

---

## 3. Practical constraints for FSOT-2.1-Neural (implementation order)

1. **Cell-class wet-lab lock** (Allen Cre) — in progress / climbing absolute rates.  
2. **Population band proxies** from spike trains / S (theta, alpha, gamma power) under study vs rest protocols.  
3. **Encode → retain → retrieve** task loop with SME-style success metric.  
4. **Offline consolidation** schedule (low drive + replay).  
5. **Creative reconfigure** probe (novel combination accuracy + alpha proxy).  
6. Map same metrics onto **Zig multi-unit network** under QEMU (serial log of band scores).

---

## 4. Frequency bands as FSOT observables

Given spike trains or \(S(t)\) at 1 ms:

| Band | Hz | Proxy |
|------|-----|--------|
| Theta | 4–8 | Spectral power of population rate or mean \(S\) |
| Alpha | 8–12 | Same |
| Sigma | 12–16 | Same (consolidation) |
| Gamma | 28–64 | Fast power / burst fraction / trinary +1 rate |

Implementation sketch: `fsot_nuron/learning_bands.py` (Welch or simple FFT on rate bins).

---

## 5. Citations (starting set)

- Sederberg et al. (2003). Theta and gamma oscillations during encoding predict subsequent recall. *J Neurosci*.  
- Creery et al. (2022). Electrophysiological markers of memory consolidation in human sleep. *PNAS*.  
- Zhang et al. (2025). fMRI decoding of CS lecture concepts. *Frontiers in Neuroscience*.  
- Broader: theta–gamma coupling reviews; alpha–creativity EEG literature; DMN–ECN flexibility fMRI.

*(Expand with DOIs as we implement each gate.)*

---

## 6. Relation to bare metal / QEMU

- **Biological Hz** (theta 6 Hz) = cycles **per second of model time**.  
- **CPU GHz** = how fast we simulate those seconds.  
- Serial console reports both: e.g. `theta_power=…` in model time; wall-clock only for engineering.

---

## 7. Next concrete tickets

- [ ] `learning_bands.py` — theta/alpha/gamma proxies from FSOT population runs  
- [ ] Encode/retrieve toy list task with SME-style success  
- [ ] Close PV/Pyr **absolute** Allen rates (≤20% rel err goal after 35% gate)  
- [ ] Zig network log of band proxies over serial  
