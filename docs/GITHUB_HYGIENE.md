# GitHub hygiene — reproducible without confusion

**Repo:** https://github.com/dappalumbo91/FSOT-2.1-Neural  
**Local master worktree:** `I:\fsot nuron`  
**Math authority:** `I:\FSOT-Physical-Archive` (not fully mirrored in this repo)

---

## What belongs on GitHub

| Include | Why |
|---------|-----|
| `fsot_nuron/` mission modules | Accurate neural + FSOT bridge |
| `product/console/` | Local UI |
| `embodiment/zig/src`, `build.zig`, `run_qemu.ps1` | Body source (not zig-out cache) |
| `formal/` Lean sources | Math panel |
| `docs/`, `MISSION.md`, checkpoints | Repro narrative |
| Thin data: codon map, archive_snapshot pin, failure boundaries | Authority stubs |
| Primary `run_*.py` + `scripts/ci_smoke.py` etc. | Entrypoints |

## What must stay local / gitignored

| Exclude | Why |
|---------|-----|
| `data/external/**` large NLP+EEG CSVs | Size; listed in DOWNLOAD_MANIFEST only |
| `data/kaggle_datasets/**/*.csv` | Size |
| `data/eeg/allen_ephys/*.nwb` | Size |
| `artifacts/*.json` | Ephemeral runs |
| `embodiment/zig/.zig-cache`, `zig-out` | Build products |
| `files-3ccbc49e/` | Legacy experiments — **never commit** |
| `__pycache__/`, `.venv/` | Noise |

## Repro on a clean machine

```powershell
git clone https://github.com/dappalumbo91/FSOT-2.1-Neural.git
cd FSOT-2.1-Neural
pip install -r requirements.txt
# Mount or clone Physical Archive:
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"
$env:PYTHONPATH = (Get-Location).Path
python run_archive_pin.py
python run_fsot_bridge.py
python scripts/ci_smoke.py
python run_stress_suite.py --quick
python run_console.py
```

Optional wet-lab bulk (not required for pin/bridge):

- Place `mental-state.csv` under `data/kaggle_datasets/eeg_mental_state/`  
- Then: `python run_learning_eeg_study.py`

## Audit commands

```powershell
python scripts/runtime_audit.py          # → docs/RUNTIME_INVENTORY.md
git ls-files | measure                  # tracked count
git status                              # no secrets / huge dumps
```

## Policy

- **Mission path** is genetic + Allen + study EEG + machine body.  
- **Keep** NLP externals (IMDB, etc.) and **Shakespeare** for future language/intelligence bridges — see `docs/LANGUAGE_AND_NLP_BRIDGE.md`.  
- **Do not restore** deleted Morse legacy dump (`files-3ccbc49e`, old Morse theses). Optional `morse_itu` remains secondary demos only.  
- Secondary runners must not be required for `ci_smoke` / stress / console boot.
