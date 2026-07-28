# Accuracy standard — “AlphaFold-class,” not “AlphaFold competitor”

**Yes, your goal makes sense** when stated carefully.

We are **not** building a CASP structure-prediction rival as the main product of FSOT-2.1-Neural.  
We **are** adopting the **same class of ambition** AlphaFold set for computational biology:

> Match **experimental / wet-lab truth** so tightly that the error is in the same league as (or better than) the best public computational systems on **named, hard, public metrics** — with **reproducible protocols** and **no hand-wavy free parameters on the FSOT law path**.

That is a **standard of excellence**, not a claim that “our neuron is AlphaFold.”

---

## 1. Apples and oranges (must stay honest)

| | **AlphaFold** | **FSOT-2.1-Neural (this repo)** |
|--|---------------|----------------------------------|
| Object | 3D protein structure | Genetic-codon neural substrate + multi-region brain dynamics |
| Gold truth | Crystal/NMR/cryo-EM structures | Allen ephys, OpenNeuro, iEEG/EEG bands, public APIs, … |
| Classic metrics | GDT-TS, lDDT, Å RMSD/MAE, CASP/CAMEO | Class rates/ISI, E/I, band powers, SME-style learning, codon 64/64, pin D1D38A |
| Method culture | Huge trained nets + MSA | Seed-derived FSOT scalar + preregistered folds + wet-lab locks |

**Wrong claim:** “We beat AlphaFold on CASP.” (Different task unless we explicitly enter structure prediction.)  
**Right claim:** “On our wet-lab-backed neural/biological tasks, we hold **AlphaFold-class error discipline** — experimental authority, tight gates, public reproducibility.”

Your archive genetics track already frames this vs AlphaFold/ESMFold philosophically (zero free params vs billion-parameter nets) in `04_Genetics-Longevity` fluid-to-solid / CAMEO work. Neural inherits that **culture**, not their leaderboard.

---

## 2. What “beat AlphaFold accuracy-wise” means operationally

AlphaFold’s cultural bar is roughly:

1. **Public experimental gold standard** (not self-graded vibes)  
2. **Hard quantitative error** (Å, lDDT — or for us, % rate error, Hz, ms, band power)  
3. **Blind / held-out style honesty** where possible  
4. **State-of-art or better** on the metrics that define *our* domain  
5. **Useful enough that wet-lab people care**

For FSOT-Neural, translate to **tiers**:

| Tier | Name | Example gates (neural / bio) |
|------|------|------------------------------|
| **T0** | Structure sound | Codon 64/64, Lean panel, pin D1D38A, Zig↔Python parity |
| **T1** | Wet-lab order | PV faster than Pyr; E/I cortical-like |
| **T2** | Tight class lock | Class rates **≤ 5%** rel err vs Allen Cre (scalpel) — *achieved for Pyr/PV/SST/VIP* |
| **T3** | AlphaFold-class discipline | **≤ 1–2%** on primary ephys locks; multi-seed CIs; held-out cells; layer/species splits |
| **T4** | Domain SOTA ambition | Learning-band SME direction + effect size vs literature; optional protein/CAMEO track if reopened |

“Beat AlphaFold” for **this project** ≈ push **T2 → T3 → T4** on **wet-lab neural metrics**, while archive protein track separately can chase structure MAE/GDT if you choose.

---

## 3. Current position (honest)

| Track | Status vs ambition |
|-------|--------------------|
| Class rates Pyr/PV/SST/VIP | **T2–T3**: scalpel **≤2%** on wet-lab FI rates (often &lt;1.5%) |
| Zig neuron parity | **T0–T1**: max \|ΔS\| ~1e-6 |
| Intelligence encode/retrieve | **Live**: fingerprint memory on scalpel brain; SME direction gates |
| Learning (theta/gamma SME) | Directional gates on; effect-size vs literature still to climb |
| Protein structure (archive) | Separate ladder (CAMEO MAE history) — not the neural scoreboard |

---

## 4. Why this is compatible with a computer body

AlphaFold-class accuracy is about **matching measured biology**, not about matching biological **wall-clock**.  
Bare-metal Zig can run an accurate `bio_match` protocol at silicon speed; accuracy is judged in **model-ms / model-Hz** against wet-lab tables.

---

## 5. Policy for agents and future work

1. Prefer **public experimental authorities** (Allen, OpenNeuro, NIST panels, literature iEEG).  
2. Never inflate accuracy by changing the metric after the fact.  
3. Scalpel / gates: **large errors first**, then tighten (5% → 2% → 1%).  
4. Do not claim AlphaFold CASP wins unless we run that task.  
5. **Do** claim AlphaFold-class **rigor** when our wet-lab rel errors and protocols justify it.

---

## 6. One-sentence version

**Yes:** we aim for **experimental-grade, SOTA-tight accuracy on our neurological and FSOT biological tasks**, with the same seriousness AlphaFold brought to structure — **without** pretending this repo is a structure-prediction competitor unless we explicitly build that track.
