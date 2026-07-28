# Learning / study EEG wet-lab path

**Goal:** Use **public instrumental EEG** from people under cognitive load / study-like states to ground the **memory** side of FSOT-2.1-Neural — same spirit as Allen ephys for cell rates.

**Doctrine:** pin archive → Neuroscience fold → bridge study-band drivers → keep encode/retrieve engine → SME gates. Zero free parameters on \(S\).

---

## 1. Data we use

| Source | Local path (when present) | Role | GitHub? |
|--------|---------------------------|------|---------|
| **Mental state EEG** (concentrate / neutral / relax) | `data/kaggle_datasets/eeg_mental_state/mental-state.csv` | Study vs rest **condition contrast** | **No** (large CSV gitignored) |
| **Emotions EEG** (Birdy et al. style features) | `data/kaggle_datasets/eeg_emotions/emotions.csv` or `data/external/eeg/…` | Optional band feature matrix | **No** (gitignored) |
| **Literature SME / consolidation** | coded in `learning_eeg_study.LITERATURE_PRIORS` | Directional theta/gamma gates | Yes (code only) |
| **Allen cell rates** | `class_ephys` / scalpel | Separate wet-lab for **firing rates** | targets via code |

Place CSVs yourself (Kaggle / mirror). Repro **does not require** Git LFS for full CSVs; literature + FSOT SME path still runs.

### Mental-state labels (common public encoding)

| Label | Meaning | FSOT use |
|------:|---------|----------|
| 0 | relaxed | rest / baseline |
| 1 | neutral | intermediate |
| 2 | concentrating | **study / encoding** condition |

---

## 2. What we measure

1. **Concentrate vs relax** band-energy ratios from feature columns (theta/alpha/beta/gamma proxies).  
2. **FSOT couple:** ratios → mild Neuroscience-fold `P` / amplitude (seed-folded).  
3. **Memory probe:** FSOT machine items + SME (`theta_encode > rest`, `gamma_encode > rest`) from spike-train proxies — same as `LEARNING_ALIGNMENT.md`.  
4. **Gates:** data loaded (optional), SME direction, top-1 above chance.

---

## 3. Commands

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"

python run_learning_eeg_study.py
python run_learning_eeg_study.py --items 8 --delay-steps 300
```

Artifacts: `data/results/LEARNING_EEG_STUDY.md`, `artifacts/learning_eeg_study.json`.

---

## 4. Relation to other wet-lab layers

```text
Allen Cre rates     →  scalpel (Pyr/PV/SST/VIP Hz)
Study EEG / SME     →  learning_eeg_study + learning_memory bands
Codon / archive S   →  genotype + fsot_bridge
```

Do **not** mix NLP sentiment CSVs into this path — those are secondary demos only (`MISSION.md`).

---

## 5. Public literature anchors

- Sederberg et al., 2003 — successful encoding ↑ theta + gamma (iEEG)  
- Creery et al., 2022 — consolidation / offline reactivation bands  
- Classroom / concept fMRI (Zhang et al., 2025) — future concept fingerprints  

Full mapping table: [`LEARNING_ALIGNMENT.md`](LEARNING_ALIGNMENT.md).
