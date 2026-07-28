# Product checkpoint — FSOT-2.1-Neural v0.5

**Freeze date:** 2026-07-28  
**Git tag:** `v0.5.0-bio-intel` (see `git tag`)  
**Commit:** `bb3c261` (climb: retention, consolidation, Zig FP@QEMU, scalpel 1%) and successors on `main`  
**Repo:** https://github.com/dappalumbo91/FSOT-2.1-Neural  

This file **saves the project where accuracy is strong** before product-UI and further intelligence climbs. Treat this as the **known-good scientific floor**.

---

## 1. What this is

A **biologically structured neural substrate** (not a transformer product):

- FSOT scalar \(S = K(T_1+T_2+T_3)\), zero free parameters on the theory path  
- 64-codon trinary genetics → ion-channel programs → Pyr/PV/SST/VIP  
- Multi-region brain + genetic synapses  
- Wet-lab **Allen Cre-line** rate locks (scalpel)  
- Encode → delay → consolidate → retrieve memory probe  
- Zig freestanding body under QEMU (serial + trinary + fingerprints)  
- Lean formal panel for discrete structure  

**North star:** accurate neurons → intelligence on that substrate → silicon-depth body.  
**Accuracy culture:** AlphaFold-**class rigor** on wet-lab metrics — not a CASP competitor (`docs/ACCURACY_STANDARD.md`).

---

## 2. Frozen accuracy numbers (do not regress without reason)

### Cell-class rates vs Allen wet-lab (scalpel, 1% tol, FI drive window)

| Class | Target Hz | Measured Hz | Rel err |
|-------|-----------|-------------|---------|
| Pyr | 16.35 | ~16.34 | **~0.1%** |
| PV | 83.35 | ~83.33 | **~0.0%** |
| SST | 29.54 | ~29.33 | **~0.7%** |
| VIP | 34.82 | ~34.67 | **~0.4%** |

Reproduce: `python run_scalpel_rates.py --focus Pyr,PV,SST,VIP --tol 0.01`

### Intelligence / memory (12 items, chance ≈ 8.3%)

| Condition | Top-1 |
|-----------|------:|
| Immediate | **0.75** |
| After 600 ms model delay | **0.75** |
| After offline consolidate | **0.75** |

Reproduce: `python run_intelligence_probe.py --suite --items 12 --delay-steps 600 --tol 0.01`

### Zig @ QEMU

- Trit / scalar / neuron / network / **FP PASS** on serial  
- Reproduce: `cd embodiment/zig; powershell -File .\run_qemu.ps1`

### Theory pin

- Authority **D1D38A…** · `python run_archive_pin.py`

---

## 3. Reproduce full checkpoint suite

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"

python run_archive_pin.py
python run_scalpel_rates.py --focus Pyr,PV,SST,VIP --tol 0.01
python run_intelligence_probe.py --suite --items 12 --delay-steps 600 --tol 0.01
python scripts/parity_zig_neuron.py
cd embodiment\zig
powershell -File .\run_qemu.ps1
```

---

## 4. Key docs at freeze

| Doc | Role |
|-----|------|
| `MISSION.md` | Product mission |
| `docs/ACCURACY_STANDARD.md` | Accuracy bar |
| `docs/BIO_ACCURACY.md` | Wet-lab data doctrine |
| `docs/SCALPEL_RATE_SYSTEM.md` | Class rate lock |
| `docs/LEARNING_ALIGNMENT.md` | Human learning instrumental targets |
| `docs/STAGE_INTELLIGENCE_PROBE.md` | Encode/retrieve stage |
| `docs/STAGE_RETENTION_CONSOLIDATION.md` | Delay + sleep-like replay |
| `docs/STAGE_ZIG_NEURON_STEP.md` | Zig neuron parity |
| `docs/PRODUCT_UI_AND_DISPLAY.md` | **Local UI / display options (next product phase)** |
| `docs/INTELLIGENCE_ROADMAP_OPTIONS.md` | **Where intelligence can go next** |

---

## 5. What we deliberately pause here

- Further technical climbs (longer delays, more items, Zig sensory, 0.5% scalpel, etc.) are listed in the roadmap options doc.  
- **Product phase next:** local usable UI + visual system **without web dependency** as the primary interface.  
- Bare-metal QEMU remains the **body / verification plane**; UI can sit **beside** it (recommended) or **inside** the guest later.

---

## 6. Restore policy

If later work regresses wet-lab rates or intelligence gates:

1. `git checkout v0.5.0-bio-intel` (or this commit)  
2. Re-run §3 suite  
3. Diff only intentional changes  

Do **not** free-fit FSOT seeds to chase UI demos.
