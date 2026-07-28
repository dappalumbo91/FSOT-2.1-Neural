# OpenNeuro / public learning EEG–fMRI catalog

**Purpose:** deeper study/encoding wet-lab sources beyond Kaggle mental-state CSV.  
**Policy:** credential-free public data; download on demand (not forced into GitHub).

| ID | Modality | Learning-related focus | Notes |
|----|----------|------------------------|-------|
| **ds002778** | EEG | PD / motor (already mirrored metadata under `data/eeg/openneuro_pd/`) | Not pure classroom; keep as EEG pipeline test |
| **ds003800** / similar | EEG | Working memory / n-back (search OpenNeuro “working memory EEG”) | Encode load |
| **ds004148** class | EEG | Cognitive tasks | Verify license on OpenNeuro |
| **OpenNeuro search** | EEG/iEEG | “memory”, “encoding”, “subsequent memory”, “study” | Prefer BIDS |

## Local fetch pattern

```powershell
# Example — only when you want bulk data on I:
# Use openneuro-py or browser download into:
#   data/eeg/openneuro_learning/<dataset_id>/
```

Index stub: `catalog.json` (dataset ids + URLs, no bulk).

## Coupling to FSOT

Same as study EEG path:

1. Band power / condition labels → concentrate vs rest style contrast  
2. Bridge into Neuroscience fold  
3. SME gates on multi-region probe  

Runner: `python run_learning_eeg_study.py`  
Module: `fsot_nuron/learning_eeg_study.py`
