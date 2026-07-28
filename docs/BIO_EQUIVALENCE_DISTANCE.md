# How far from biological equivalence? (honest scorecard)

**Intent:** While the system watches media, reads language (subtitles/docs), and associates patterns, **how close is it to biological sensory–learning systems?**

**Language note:** We implement **what retinas, cochleas, thalamus, and cortex *do* (function)**. We never claim silicon *is* living tissue. Functional equivalence under named protocols is the target.

---

## 1. Layered distance (0–100% fidelity bands)

Rough **order-of-magnitude** status for *this* codebase (not marketing).  
100% = “matches public wet-lab / clinical target under named protocol.”

| Layer | Bio target | FSOT status | ~fidelity (refine `--domain bio`) | Limiting factor |
|-------|------------|-------------|-----------------------------------|-----------------|
| **Cell-class rates** | Allen PV/Pyr/SST/VIP FI | Scalpel ≤2% · precision ≤1% | **~96%** | Timing / integer spikes mostly solved |
| **E/I microcircuit motifs** | Cortical E→I, VIP disinhibition | Sparse directed E→E + dense E↔I | **~99%** (mass band) | Not full connectome densities |
| **Thalamic sensory gate** | LGN/MGN-like filter | Seed-lawful relay &lt; primary | **~100%** motif | Motif-level, not full nuclei |
| **Retina-like decode** | CS, opponency, orientation | Multi-scale CS / ON-OFF / orient | **~72%** soft ceiling | No full photoreceptor cascade |
| **Cochlea-like decode** | tonotopy, speech bands | φ-tilted log bands + formants | **~72%** soft ceiling | No basilar membrane / IHC |
| **Fly connectome motifs** | FlyWire density/reciprocity/hubs | Same-sign recip in band | **~78%** | N≪ fly brain; E↔I floor density |
| **EEG / learning bands** | mental-state θ + Sederberg SME | Public EEG + spike-band SME | **~85%** | Not clinical iEEG |
| **Information accuracy** | encode–delay–retrieve under load | 12-item / 280-step probe | **~88%** | Small-N machine items |
| **Episodic memory / SME** | SME θ/γ + consolidate | learning_bio gates | **~72%** soft ceiling | Capacity/delay limits |
| **Cross-modal binding** | STS co-occurrence | Sync/async bind separation | **~74%** | Weak object semantics |
| **Language / dialogue** | caption→trit→lexicon | Measured SRT/bind/cross-feed | **~72%** soft ceiling | Open-vocab VL unclaimed |
| **Open-world identity** | pixels alone | Synthetic retina entities | **~55%** ceiling | Real crops required |
| **Self curriculum** | self-authored plan | Gap plan + synthetic Δ | **~72%** | Real execute budget unclaimed |
| **Free monologue** | multi-turn grounded | Memory monologue (no LLM) | **~72%** | Free LLM monologue unclaimed |

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
