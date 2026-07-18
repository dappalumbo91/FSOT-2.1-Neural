# Kaggle runbook — FSOT-2.1-Neural notebook

You are **not** re-uploading the emotions CSV. You attach Bird’s public dataset as **input data** and run **your** notebook/code under Apache-2.0.

## Dataset to attach (third-party)

| Kaggle ref | Title |
|------------|--------|
| **`birdy654/eeg-brainwave-dataset-feeling-emotions`** | EEG Brainwave Dataset: Feeling Emotions |

Credit that dataset in the notebook header (already done).

## One-time: package *your* code (optional, for full package path)

```powershell
cd "I:\fsot nuron"
python scripts\package_for_kaggle.py
# → dist\fsot-2-1-neural-kaggle.zip
```

Upload that zip as a **new Kaggle Dataset** owned by you, e.g. `yourname/fsot-2-1-neural-code`  
(Contents = code + literature snippets + Morse/codon tables — **no** emotions.csv.)

## Create the notebook on Kaggle

1. Kaggle → **Code** → **New Notebook**
2. **File → Import Notebook** →  
   `I:\fsot nuron\notebooks\kaggle\FSOT_2_1_Neural_Kaggle_Emotions.ipynb`  
   or copy-paste cells
3. **Add data**
   - Required: `birdy654/eeg-brainwave-dataset-feeling-emotions`
   - Optional: your `fsot-2-1-neural-code` package
4. **Save Version → Save & Run All**
5. Set notebook license / visibility as you prefer; keep **Apache-2.0** for code cells

## Local dry-run (same logic as Kaggle)

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
python scripts\kaggle_local_smoke.py
```

## Next industry datasets (attach same way)

```text
birdy654/eeg-brainwave-dataset-mental-state
wanghaohan/confused-eeg
```

Pattern: Add Data → discover CSV → energy/label stats → FSOT templates → Morse chew/query.

## CLI download (optional, local only)

```powershell
kaggle datasets download -d birdy654/eeg-brainwave-dataset-feeling-emotions -p "D:\training data\kaggle_emotions" --unzip
```
