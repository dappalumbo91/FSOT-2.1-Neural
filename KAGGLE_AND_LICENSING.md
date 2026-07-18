# Kaggle emotions EEG + licensing / publishing

## What you have

| Item | Value |
|------|--------|
| Path | `D:\training data\archive\emotions.csv` (also staged under `data/eeg/kaggle_emotions/`) |
| Origin | Kaggle EEG emotion feature set |
| Shape | **2132 × 2549** (2548 numeric + `label`) |
| Labels | `NEGATIVE` (708), `NEUTRAL` (716), `POSITIVE` (708) |
| Features | Pre-engineered `mean_*`, `fft_*`, etc. (not raw multi-channel EDF) |

This is **useful real EEG-derived data** for emotion-conditioned drive and irregularity priors. It complements Allen NWB (single-cell voltage) rather than replacing it.

## Would publishing on Kaggle help?

**Yes — as a Notebook (kernel), carefully.**  
**Usually no — as a re-upload of the same CSV.**

| Publish | Benefit | Risk |
|---------|---------|------|
| **Kaggle Notebook** demo of FSOT-2.1-Neural + emotions.csv **as input** | Visibility, one-click runs, Kaggle audience for “EEG + novel substrate” | Low if you don’t redistribute the CSV |
| **New Kaggle Dataset = copy of emotions.csv** | Almost none (duplicate) | License conflict, takedown, looks like mirror spam |
| **New Kaggle Dataset = derived FSOT artifacts** (stats JSON, chew reports, Morse outputs) | Shows original work | Fine if you generated them |
| **GitHub `FSOT-2.1-Neural`** | Theory pin to FSOT-2.1-Lean, versioning, Apache-2.0 stack | Primary home of the project |

### Recommended stack

1. **GitHub** — code + notebook + `VERIFICATION.md` → [FSOT-2.1-Lean](https://github.com/dappalumbo91/FSOT-2.1-Lean)  
2. **Kaggle Notebook** — “FSOT-2.1-Neural: emotion EEG features → Morse chew/query” that attaches the **existing** public emotions dataset  
3. Optional **Kaggle Dataset** of *your* derived outputs only  

## MIT vs Apache-2.0

| | MIT | Apache-2.0 |
|--|-----|------------|
| Simple | Yes | Slightly longer |
| Patent grant | No | **Yes** (better for systems / GPU / “neural substrate” claims) |
| Match your FSOT Lean/GPU repos | Often Apache | **Preferred** |

**Recommendation: Apache-2.0** for the FSOT-2.1-Neural repo and notebooks. Use MIT only if you deliberately want a smaller license for a tiny helper script.

## Commands

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"

# Stats from Kaggle emotions.csv
python -c "from fsot_nuron.emotions_eeg import compute_emotions_stats, integrate_with_eeg_bundle; print(compute_emotions_stats()['labels']); integrate_with_eeg_bundle()"

# Full demo
python run_chew_query.py --demo
```

Notebook: `notebooks/FSOT_2_1_Neural_Emotions_Chew_Query.ipynb`

## Kaggle CLI (more data later)

```powershell
kaggle datasets list -s "eeg emotion"
# only download what you need; check each dataset's license
# kaggle datasets download -d <owner/dataset> -p "D:\training data"
```
