# Stage: Intelligence on accurate FSOT neurons

| Field | Value |
|-------|--------|
| **Stage ID** | `INTELLIGENCE_PROBE` |
| **Date** | 2026-07-28 |
| **Depends on** | Scalpel Allen class rates · multi-region brain · Zig neuron parity |
| **Runner** | `python run_intelligence_probe.py` |
| **Accuracy bar** | [`ACCURACY_STANDARD.md`](ACCURACY_STANDARD.md) (AlphaFold-class rigor) |

---

## 1. Intent

Build **intelligence dynamics** (encode → retain → retrieve) on a substrate that is already **wet-lab-accurate at the cell-class level** — not a generic ANN, not an NLP climb.

```text
Allen wet-lab rates (scalpel ≤2%)
    → multi-region genetic brain (Pyr/PV/SST/VIP)
    → item patterns (trit-quantized features)
    → encode (thal + sens/assoc drive)
    → fingerprint memory
    → retrieve under partial cue
    → SME-style theta/gamma direction
```

---

## 2. Why this is the right next step

| Layer | Status |
|-------|--------|
| Neuron law \(S=K(T_1+T_2+T_3)\) | Ported + parity |
| Class rates vs Allen | Scalpel **≤2%** Pyr/PV/SST/VIP |
| Architecture | Multi-region + genetic \(W\) |
| **Intelligence primitive** | **This stage** |

Human learning literature (theta/gamma SME, consolidation, retrieval) is mapped in [`LEARNING_ALIGNMENT.md`](LEARNING_ALIGNMENT.md).

---

## 3. Reproduce

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"

python run_scalpel_rates.py --focus Pyr,PV,SST,VIP --tol 0.02
python run_intelligence_probe.py --tol 0.02 --items 6
```

---

## 4. Gates

| Gate | Meaning |
|------|---------|
| `pin_seed_ok` | FSOT authority |
| `scalpel_ok` | Class rates within tol on brain units |
| `retrieve_above_chance` | Top-1 > 1/N items |
| `correct_sim_gt_incorrect` | Fingerprints separate |
| SME theta/gamma direction | Encode power > rest (literature direction) |

---

## 5. Honesty

- Not a transformer; not medical.  
- Retrieval is **pattern completion on FSOT dynamics**, scored hard.  
- Climb accuracy (more items, longer retain, consolidation offline) under same wet-lab rails.
