# Stage: Retention, consolidation, Zig fingerprints, 1% scalpel

| Field | Value |
|-------|--------|
| **Date** | 2026-07-28 |
| **Runners** | `run_intelligence_probe.py --suite` · `run_scalpel_rates.py --tol 0.01` · `embodiment/zig/run_qemu.ps1` |

---

## 1. More items + retention delay

- Default probe: **12 items** (chance ≈ 0.083)
- **Delay** = pure rest for `delay_steps` model-ms (default 500–600)
- Metrics: `top1_immediate` vs `top1_after_delay`

Biological time only — delay is not wall-clock sleep of the PC.

---

## 2. Offline consolidation

Inspired by instrumental sleep/reactivation literature (`LEARNING_ALIGNMENT.md`):

1. Quiet rest  
2. Soft **replay** of item patterns into hipp/assoc (+ sparse thalamic packets)  
3. Optional second rest  
4. Retrieve  

Reports `consolidate_sigma_rel` (sigma-band proxy during replay) and final top-1.

---

## 3. Zig multi-unit fingerprints @ QEMU

- `embodiment/zig/src/fingerprint.zig` — encode 4 items × 16 units, cosine retrieve  
- Serial: `FP_ENCODE` / `FP_RETRIEVE correct=k/n` / `FSOT_FP PASS`  
- Host + freestanding kernel

```powershell
cd embodiment\zig
zig build host
powershell -File .\run_qemu.ps1
```

---

## 4. Scalpel toward 1%

```powershell
python run_scalpel_rates.py --focus Pyr,PV,SST,VIP --tol 0.01
```

**Policy:** require 1% where stable; intelligence probe **falls back to 2%** if 1% fails, and records `tol_used`.

| Class | Typical at 1% attempt |
|-------|------------------------|
| PV / SST / VIP | Often **≤1%** |
| Pyr | May need **≤2%** band (discrete ms grid + FI duty) |

AlphaFold-class climb: keep pushing Pyr micro-pass / longer steps.

---

## 5. Suite

```powershell
python run_intelligence_probe.py --suite --items 12 --delay-steps 600 --tol 0.01
python run_climb_suite.py
```
