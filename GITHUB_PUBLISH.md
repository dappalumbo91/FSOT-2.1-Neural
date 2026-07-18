# Publish as GitHub: **FSOT-2.1-Neural**

Suggested public name (matches theory pin):

| Candidate | Notes |
|-----------|--------|
| **FSOT-2.1-Neural** | Recommended — theory version + neural substrate |
| FSOT-2.1-Neuron | Singular neuron emphasis |
| FSOT-2.1-NeuralNet | Avoid “Neural Network” alone (implies industry MLP/Transformer) |

## Theory + archive pin (required)

This package **depends on** FSOT 2.1 verification authority:

- Physical: `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full`  
- Public: https://github.com/dappalumbo91/FSOT-2.1-Lean  
- Local pin: `python run_archive_pin.py` → `data/archive_snapshot/`

Kaggle notebooks are already a public run path; GitHub is the **code + pin** home.

## Create repo (when `gh auth login` is done)

```powershell
cd "I:\fsot nuron"

git init
git add LICENSE NOTICE VERIFICATION.md GITHUB_PUBLISH.md README.md pyproject.toml requirements.txt .gitignore
git add fsot_nuron run_*.py scripts notebooks
git add data/itu_morse.json data/64_codon_trinary_map.txt data/neuro_failure_boundaries.json
git add data/archive_snapshot data/literature data/eeg/openneuro_pd/pd_eeg_feature_priors.json
git add data/eeg/kaggle_emotions/README.txt
# Do NOT add large third-party CSVs / NWB unless license-clear and intentional
git status

git commit -m "FSOT-2.1-Neural: substrate + archive pin to FSOT-Physical-Archive / Lean hub"

# After: gh auth login
gh repo create dappalumbo91/FSOT-2.1-Neural --public --source=. --remote=origin --push
```

## README badge ideas

- Theory: [FSOT-2.1-Lean](https://github.com/dappalumbo91/FSOT-2.1-Lean)  
- License: Apache-2.0  
- Status: research substrate (not medical device)  
- Archive pin: `run_archive_pin.py`

## Do not publish

- Full Kaggle `emotions.csv` / large third-party EEG as *your* data  
- Full Allen NWB if license unclear (document path; user supplies)  
- Raw clinical EEG without consent/license  
- Desktop secrets / absolute-only machine dumps  

Ship: code, ITU Morse table, codon map text, failure catalog, archive pin snapshot, verification docs.
