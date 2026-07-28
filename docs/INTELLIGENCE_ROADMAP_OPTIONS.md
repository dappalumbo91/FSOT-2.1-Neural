# Intelligence roadmap options (post-checkpoint)

**After** `CHECKPOINT_v0.5.md`. These are directions for the **mind**, built on accurate neurons — pick order by product need.

---

## A. Memory & learning (cognitive)

| Option | What it is | What a “neuron network” calculates | Difficulty |
|--------|------------|--------------------------------------|------------|
| **A1 Longer delays** | Encode → wait 2–10 s model-time → retrieve | Retention curve; interference over time | Low |
| **A2 More items** | 24–100 item lists | Capacity / interference of fingerprint memory | Low–med |
| **A3 Partial cues** | Retrieve from 30–50% feature mask | Pattern completion strength | Low |
| **A4 Offline consolidate v2** | Stronger replay, tagged theta at encode | Sleep-like strengthening (Creery-style) | Med |
| **A5 SME scoring** | Correlate encode theta/gamma with later hit/miss | Encoding success prediction | Med |
| **A6 Continual learning** | Stream of items without full reset | Catastrophic forgetting vs FSOT solidify | High |
| **A7 Concept classes** | Distinct concept families (like lecture fMRI) | Separability of activity patterns | Med |
| **A8 Creative recombine** | Ask for novel pair from two learned items | Alpha/network-switch proxies + novelty metric | High |

---

## B. What the substrate can calculate (neuron / network physics)

| Option | Calculation | Biological link |
|--------|-------------|-----------------|
| **B1 Class dynamics** | Rate, ISI, adapt per Pyr/PV/SST/VIP | Allen wet-lab (done ≤1%) |
| **B2 Population spectra** | Theta/alpha/sigma/gamma power | iEEG/EEG literature |
| **B3 E/I balance** | Synaptic mass, stability under drive | Cortical microcircuit |
| **B4 Criticality / avalanches** | Size distribution of co-activations | Neural criticality papers |
| **B5 Phase–amplitude coupling** | Theta phase × gamma power | Encoding code |
| **B6 Effective connectivity** | Granger-like / transfer on trinary streams | Network science |
| **B7 Failure lesions** | Gene-knockout / PV drop | Disease boundary catalog |
| **B8 Multi-compartment / dendritic** | Extra spatial state per unit | Morphological Allen `nr__*` |

---

## C. Embodiment / bare metal

| Option | What it is |
|--------|------------|
| **C1 Zig sensory inject** | Trit streams for vision/audio/metrics into network |
| **C2 Shared-memory ABI** | Host UI ↔ Zig process without QEMU |
| **C3 QEMU disk LTM** | Persist fingerprints / brain state on virtual disk |
| **C4 VirtIO-GPU guest UI** | Draw inside the VM (harder “mini-OS” path) |
| **C5 Ada/SPARK contracts** | Prove step invariants on hot path |

---

## D. Product / usability (priority after freeze)

| Option | What it is |
|--------|------------|
| **D1 Local native control panel** | Run, lock rates, encode/retrieve, charts — **no web server** |
| **D2 Live network graph view** | Regions, spikes, fingerprints (Obsidian-like or GPU canvas) |
| **D3 Telemetry strip** | Serial/metrics from brain → local meters |
| **D4 Scenario library** | One-click: scalpel, probe, consolidate, QEMU check |

See **`docs/PRODUCT_UI_AND_DISPLAY.md`** for display architecture.

---

## Recommended sequence for “usable intelligence product”

1. **D1 + D2** — local UI so you can *use* the accurate brain daily  
2. **A1–A4** — deepen memory under the UI  
3. **C2** — Zig engine as local process (QEMU stays verifier)  
4. **A5–A8 / B\*** — research climbs with AlphaFold-class gates  

Checkpoint accuracy must not regress when UI is added.
