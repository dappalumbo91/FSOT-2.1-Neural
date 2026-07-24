# Scalpel rate targeting system

**Purpose:** Drive FSOT class firing rates to **Allen wet-lab means** with tight relative error — not “good enough order only.”

| | |
|--|--|
| **Runner** | `python run_scalpel_rates.py --focus Pyr,PV --tol 0.05` |
| **Module** | `fsot_nuron/scalpel_rate.py` |
| **Authority** | Allen Cell Types Cre-line rates (`class_ephys.build_class_targets`) |
| **Results** | `data/results/SCALPEL_RATES.md` |

---

## 1. Why “scalpel”

| Blunt lock | Scalpel |
|------------|---------|
| One-shot analytical R from ISI | Measure → adjust R / fi / thr → re-measure |
| Full-trace rate (includes FI rest head) | Rate **only in sustained FI window** (skip 100 ms onset) |
| 35% “order-ish” bands | **5%** hard tol on named classes |
| All classes at once | **Priority order:** large error first (**Pyr**), then **PV** |

User requirement: **~24% Pyr error is not acceptable**; close it, then the ~8% PV band.

---

## 2. Two clocks (unchanged)

- **Model-Hz** (what Allen targets): locked here.  
- **Silicon wall-clock**: irrelevant to this gate.

---

## 3. Algorithm

1. Build typed population (Pyr/PV/SST/VIP genotypes).  
2. Seed knobs from `apply_class_targets_to_genotype_phenotype`.  
3. **Measure** class mean rate on FI drive epoch only:
   \[
   r = \frac{N_{\mathrm{spikes}}[t \ge 100\,\mathrm{ms}]}{(T-100)\,\mathrm{ms}/1000}
   \]
4. For each focus class in order:
   - \(\mathrm{err} = (r - r^\star)/r^\star\)
   - if \(|\mathrm{err}| \le \mathrm{tol}\): done for class  
   - if too slow: lower `refractory_steps` toward \(1000/r^\star\), raise `fi_stim`, lower `fire_threshold`, zero `adapt_step` if needed  
   - if too fast: raise R, ease FI  
5. Optional global polish.  
6. **PASS** iff every `--focus` class has \(|\mathrm{err}| \le \mathrm{tol}\) and PV rate > Pyr rate.

**Does not** free-fit \(S = K(T_1+T_2+T_3)\) seeds.

---

## 4. Measured (this machine, 2026-07-24)

| Class | Allen target | Scalpel measured | Rel err |
|-------|--------------|------------------|---------|
| **Pyr** | 16.35 Hz | **16.36 Hz** | **0.1%** |
| **PV** | 83.35 Hz | **83.64 Hz** | **0.3%** |

Both within **5%**. Order preserved.

SST/VIP not in default focus — next scalpel pass after Pyr/PV locked.

---

## 5. Reproduce

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
python run_scalpel_rates.py --focus Pyr,PV --tol 0.05
# later:
python run_scalpel_rates.py --focus Pyr,PV,SST,VIP --tol 0.05
```

---

## 6. Relation to learning alignment

Once class rates sit on wet-lab rails, theta/gamma **learning-band** proxies (`LEARNING_ALIGNMENT.md`) are meaningful in **model-Hz**. Scalpel is the cell-physiology foundation under those cognitive targets.
