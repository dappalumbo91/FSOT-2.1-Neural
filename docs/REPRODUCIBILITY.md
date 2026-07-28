# FSOT-2.1-Neural — full reproducibility package

**Version focus:** multi-modal organism (standalone pin · AV co-stream · subtitles · document read · knowledge→trinary · episodic memory · autonomous learn)

**GitHub:** https://github.com/dappalumbo91/FSOT-2.1-Neural  

---

## 1. What you need

| Requirement | Notes |
|-------------|--------|
| **This repo only** | Clone is the brain — no `I:\FSOT-Physical-Archive` required |
| Python 3.10+ | Tested 3.11 |
| `pip install -r requirements.txt` | torch, numpy; optional: pypdf, faster-whisper, psutil, av, soundfile |
| OS | Windows / Linux / macOS (paths are portable) |

**Optional worlds (not identity):**

| Optional | Env / path |
|----------|------------|
| Movies / shows / music | `FSOT_MEDIA_ROOTS=G:\movies;G:\showes;G:\Debut` |
| Local STT | `faster-whisper` + `python run_episode_watch.py --stt` |
| Online lexicon expand | `FSOT_KNOWLEDGE_ONLINE=1` |

---

## 2. One-command boot (standalone)

```powershell
git clone https://github.com/dappalumbo91/FSOT-2.1-Neural.git
cd FSOT-2.1-Neural
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
$env:FSOT_STANDALONE = "1"

# Authority pin (in-repo D1D38A)
python run_archive_pin.py

# Critical path stress (quick)
python run_stress_suite.py --quick

# Console UI
python run_console.py
```

Expect: `connected: True`, `pin_mode: standalone`, sha prefix `D1D38A…`.

---

## 3. Multi-modal stack (what was accomplished)

```text
Stand-alone law: data/archive_snapshot/fsot_compute_authority.py (D1D38A)
        │
        ├─ Genetic multi-region brain (thal/sens/assoc/hipp)
        ├─ Host senses (CPU/mem/HID/log) — adaptive, not one PC
        ├─ Media: vision ⊗ audio co-stream + .srt/.vtt subtitles
        ├─ Documents: PDF/MD/TXT actual page text (not next-token LM)
        ├─ Knowledge lexicon → machine UTF-8→trits (body language)
        └─ Episodic memory + plain-English recall
```

| Capability | Entry point | Doc |
|------------|-------------|------|
| Standalone transplant | `docs/STANDALONE_TRANSPLANT.md` | required |
| Media sensory | `python run_media_chew.py` | `docs/MEDIA_SENSORY.md` |
| Subtitles + memory | `python run_episode_watch.py` | `docs/KNOWLEDGE_CROSSFEED.md` |
| Knowledge→trinary | `python run_knowledge_demo.py` | `docs/KNOWLEDGE_CROSSFEED.md` |
| **Autonomous learn** | `python run_autonomous_learn.py` | this file |
| Stress map | `python run_stress_suite.py` | `docs/STRESS_STAGE_REPORT.md` |
| Bio comparison | | `docs/BIO_STRESS_COMPARISON.md` |

---

## 4. Autonomous learn (minimal instruction)

Gives the brain **access** to in-repo literature/docs and optional media, then lets
neurological pathways (co-occurrence, association, compact memory) run **without
per-item human prompts**.

```powershell
# Documents only (fully offline / any machine)
python run_autonomous_learn.py --docs-only --max-docs 6

# Documents + optional media libraries
$env:FSOT_MEDIA_ROOTS = "G:\movies;G:\showes;G:\Debut"
python run_autonomous_learn.py --max-docs 5 --videos 1 --frames 10

# Recall what it stored
python run_episode_watch.py --list
python run_episode_watch.py --recall "thesis"
```

**Reading:** `fsot_nuron/knowledge/document_read.py` extracts real text from
markdown/txt/PDF pages, chunks it, encodes to **trinary**, binds lexicon knowledge,
drives assoc/hipp — **not** an autoregressive chat model.

---

## 5. Authority & verification pins

| Pin | Value / check |
|-----|----------------|
| Compute authority SHA | `D1D38A185487B452…` in `data/archive_snapshot/` |
| Seeds | Closed-form match (`check_local_seeds`) |
| Free S parameters | **0** (`verify_fsot_bridge`) |
| Allen class rates | ≤2% critical; ≤1% via precision climb |
| Codon map | `data/64_codon_trinary_map.txt` 64/64 |

```powershell
python run_archive_pin.py
python run_fsot_bridge.py
python run_full_spine_check.py
python run_precision_climb.py --tol 0.01
python run_wetlab_accuracy_battery.py
```

---

## 6. Bundled data layout (transplant)

```text
data/
  archive_snapshot/     # law (fsot_compute_authority.py + certificate)
  64_codon_trinary_map.txt
  knowledge/lexicon.json
  literature/           # thesis + shakespeare stream for reading
  eeg/allen_ephys/      # wet-lab features when present
  results/              # human-readable reports
artifacts/              # runtime: episode_memory, reports (gitignored mostly)
```

---

## 7. What this is / is not

| Is | Is not |
|----|--------|
| Genetic-codon FSOT neural organism | Transformer LLM pretrain |
| Pattern association + compact memory | Medical device |
| Readable multi-modal experience | Claim of full open-world AGI vision |
| Standalone GitHub clone | Tied to one developer’s drive letters |

### Tracked unclaimed gaps (capability frontier)

We **log and keep** these as we climb — see [`docs/CAPABILITY_FRONTIER.md`](CAPABILITY_FRONTIER.md):

1. **Open-world pixel identity** — “that is Jake” from pixels alone  
2. **Self-directed curriculum design** — full autonomous learning plan  
3. **LLM-style free monologue** — open generative language  

```powershell
python run_capability_frontier.py
python run_capability_frontier.py --history 10
```

Live status: `data/capability_frontier/STATUS.md`

---

## 8. Suggested first-hour path for reviewers

1. `run_archive_pin.py` → standalone green  
2. `run_stress_suite.py --quick` → critical path  
3. `run_autonomous_learn.py --docs-only` → read thesis/literature, store memories  
4. `run_episode_watch.py` on a local movie **with .srt** if available  
5. `run_episode_watch.py --recall "<title>"`  

License: Apache-2.0. Keep experimental outputs under `artifacts/` / `data/results/`.
