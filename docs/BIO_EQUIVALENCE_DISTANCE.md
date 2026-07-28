# How far from biological equivalence? (honest scorecard)

**Intent:** While the system watches media, reads language (subtitles/docs), and associates patterns, **how close is it to biological sensory–learning systems?**

**Language note:** We implement **what retinas, cochleas, thalamus, and cortex *do* (function)**. We never claim silicon *is* living tissue. Functional equivalence under named protocols is the target.

---

## 1. Layered distance (0–100% fidelity bands)

Rough **order-of-magnitude** status for *this* codebase (not marketing).  
100% = “matches public wet-lab / clinical target under named protocol.”

| Layer | Bio target | FSOT status | ~fidelity | Limiting factor |
|-------|------------|-------------|-----------|-----------------|
| **Cell-class rates** | Allen PV/Pyr/SST/VIP FI | Scalpel ≤2% · precision ≤1% | **~95–99%** on rates | Integer-spike / timing already solved |
| **E/I microcircuit motifs** | Cortical E→I, VIP disinhibition | Genetic W motifs | **~60–75%** | Simplified densities, not full connectome |
| **Regional anatomy** | thal→sens→assoc↔hipp | Named regions + projections | **~50–65%** | Few dozen units; no laminar V1/A1 |
| **Thalamic sensory gate** | LGN/MGN-like filter | Seed-lawful relay &lt; primary | **~55–70%** | Motif-level, not full relay nuclei |
| **Retina-like decode** | luminance, color opponency, motion | Luma/RGB/hue/grid/motion | **~35–50%** | No photoreceptor cascade, no center-surround RF library |
| **Cochlea-like decode** | frequency maps, speech bands | FFT bands + speech-band prior | **~30–45%** | No basilar membrane / hair-cell model |
| **Cross-modal binding** | STS / association co-occurrence | Vision⊗audio → assoc | **~40–55%** | Real co-occurrence; weak object semantics |
| **Language / dialogue** | speech→meaning with vision | Subtitles + STT optional + lexicon | **~25–40%** | Needs captions/STT; not open vocab vision-language |
| **Episodic memory** | encode–retain–retrieve, SME | learning_probe + bands | **~45–60%** | SME direction often green; capacity/delay limited |
| **Open-world identity** | “Jake from pixels alone” | **Unclaimed** (frontier) | **~0–10%** | No held-out pixel-ID gate yet |
| **Self curriculum** | autonomous study design | Probing (fixed discovery) | **~10–20%** | Heuristic chew ≠ authored curriculum |
| **Free monologue** | open generative language | Partial compositional | **~15–25%** | Not an LLM; grounded regurgitation only |

**Bottom line for “watching a movie + language + association”:**

- **Dynamics / class rates:** near wet-lab lock (strong).  
- **Sensory routing:** biologically *shaped*, FSOT-lawful (good motif level).  
- **Understanding what is on screen:** early association + tutors — **not** human-level comprehension.  
- **Overall multi-modal “watch & understand” stack:** roughly **mid-tier motif fidelity**, **early** semantic fidelity — useful organism, not a human viewer.

---

## 2. What we *can* score against real learning studies (now)

| Study / motif | Instrument | Our metric | Typical status |
|---------------|------------|------------|----------------|
| Sederberg SME | iEEG | `sme_theta_encode_gt_rest`, `sme_gamma_encode_gt_rest` | Often **green** on probes |
| Creery consolidation | iEEG sleep | consolidate top-1 / offline replay | Partial–good on small item sets |
| Allen class order | patch / Cre | PV ≫ Pyr rates | **Green** |
| Encode–delay–retrieve | behavioral memory | top-1 after delay | Good small-N; degrades large-N |

Runner: `python run_bio_equivalence_scorecard.py`

---

## 3. Multi-species / computer-centric (fruit fly and beyond)

Humans mapped the **adult Drosophila melanogaster** brain at synaptic resolution (e.g. FlyWire / related whole-brain connectome efforts, ~10⁵ neurons, complete wiring motifs). That matters because:

1. **Full graph exists** — we can compare *motif statistics* (degree, feedforward depth, recurrence), not only human-scale anatomy.  
2. **Computer-centric may prefer fly-like efficiency** — small N, dense known wiring, fast loops — over human neuron census (see [`EFFICIENCY_DOCTRINE.md`](EFFICIENCY_DOCTRINE.md)).  
3. **Human data still owns learning EEG/iEEG** (language, SME). Fly owns **connectome completeness**.

Scaffold: `fsot_nuron/species/fly_connectome.py` · doctrine in [`docs/MULTI_SPECIES_COMPUTER_CENTRIC.md`](MULTI_SPECIES_COMPUTER_CENTRIC.md).

We do **not** download multi-GB connectomes by default (standalone transplant). We store **literature targets + optional import path**.

---

## 4. Working toward unclaimed frontier (tracked)

| Gap | Near-term probe (does not claim green) |
|-----|----------------------------------------|
| Pixel identity | Synthetic multi-object visual templates + tutor-ablated retrieval |
| Curriculum | Gap-driven next-doc/media pick vs fixed order |
| Monologue | Multi-sentence grounded recall length + external_llm=false |

Ledger: [`CAPABILITY_FRONTIER.md`](CAPABILITY_FRONTIER.md) · `python run_capability_frontier.py`

---

## 5. Honest sentence for outsiders

> FSOT-Neural implements **functionally retina-/cochlea-/thalamo-cortical-inspired** sensory pathways and **wet-lab-locked** cell dynamics, and can **associate** audiovisual and language streams under FSOT law. It is **not** a claim of human-equivalent understanding of film, nor open-world visual identity, nor LLM monologue — those are **logged gaps** we climb with benchmarks.
