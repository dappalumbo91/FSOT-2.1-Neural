# FSOT-2.1-Neural — Results

**Mission metrics** live in `data/results/GENETIC_NETWORK.md` (genetic-codon network).  
Legacy NLP/EEG climb numbers are retained below for history only.

Repo: https://github.com/dappalumbo91/FSOT-2.1-Neural  
Theory: https://github.com/dappalumbo91/FSOT-2.1-Lean (`D1D38A` authority)

---

## 0. Primary mission — genetic-codon network

Re-run:

```powershell
python run_genetic_bio.py --units 64 --steps 1200
```

Latest gates (see `data/results/genetic_network_report.json`):

| Gate | Status |
|------|--------|
| Codon map 64/64 | **PASS** |
| Channel genes SCN/KCN/CACNA/LEAK | **PASS** |
| Genetic synapses | **PASS** (dense density 1.0 on off-diagonal) |
| Archive seed pin | **PASS** |
| Mean ISI (FI, Allen-locked) | ~77 ms (Allen target ~71 ms) |
| Mean adaptation | ~0.027 (Allen target ~0.051) |
| Mean rate | ~19 Hz |
| Rate↔SCN expression corr | positive (weak; genetic diversity preserved under lock) |

Honesty: Allen lock sets population timing scale; gene expression multiplies relative refractory / adapt / FI. Not a wet-lab claim.

---

## 1. Quality gates (CI)

- CI smoke: **PASS** (seeds, codon, channel genes, genetic net, failure catalog)
- Morse: secondary only

## 2–7. Legacy NLP / EEG scoreboard (demoted)

These tracks were an exploration climb and are **not** the product KPI.

- SMS hard top-1 ~0.80 · train/test probe ~0.94  
- Mental-state EEG fit ~0.81 · emotions ~0.65  
- Sentiment / IMDB hierarchical climb — see `SOTA_FRONTS.md` / `CLIMB.md`  
- Bio card (non-genetic batch path): ISI ~0.11%, adapt ~2.45%, 6/6 gaps — `data/results/bio_report_card.md`

Full legacy JSON remains under `data/results/`.
