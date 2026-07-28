# Stress suite report — stage break map

**Full run** (2026-07-28): 90s · **30/32** pass · **0 critical** · **2 soft** (one fixed post-run)  
**Quick re-check** after ABI fix: **25/25** pass · 0 breaks  

## Doctrine

- Archive pin **D1D38A** + 64-codon map  
- Allen wet-lab class rates (scalpel)  
- Intelligence via **FSOT machine** items (not Morse)  
- Biology accuracy before performance  

## Critical path — GREEN

| Stage | Result |
|-------|--------|
| A Foundation (pin, seeds, codon 64/64, atlas S) | PASS |
| B Machine ABI (through 4KB + inject + bridge) | PASS (16KB overflow **fixed** → u32 `n_trits`) |
| C Genetic scale n=32…256 + multi-region brain | PASS |
| D Allen targets loaded; scalpel **2%** all four classes | PASS |
| E Intel ladder FSOT items 4→24 | PASS (above chance; ≥0.5 through 16 items) |
| F Zig host `FSOT_TRIT PASS` | PASS |
| G Console display review 15/15 | PASS |

## Soft breaks (accuracy frontier — not show-stoppers)

### 1. Scalpel **1%** (stretch)

| Class | Target Hz | Rel err @ 1% run |
|-------|-----------|------------------|
| Pyr | ~16.35 | **~1.21%** (just over 1%) |
| PV | ~83.35 | ~0.59% |
| SST | ~29.54 | ~0.001% |
| VIP | ~34.82 | ~0.57% |

- **1% gate:** 3/4 classes (Pyr slips ~0.2% over)  
- **2% gate:** **4/4 PASS** — wet-lab floor holds  

**Break interpretation:** Stage is **Allen-accurate at 2%**; 1% is a stretch target for Pyr only.

### 2. Machine frame `n_trits` u16 overflow (FIXED)

- Payload ≥ ~8KB UTF-8 → trit count > 65535  
- Header used **u16** → soft fail on 16KB round-trip  
- **Fix landed:** `MachineFrame` header uses **u32** `n_trits`  

### 3. Intelligence scale frontier (not a fail)

| Items | Delay | Top-1 | Chance | Note |
|------:|------:|------:|-------:|------|
| 4 | 0 | **1.00** | 0.25 | solid |
| 6 | 200 | **1.00** | 0.17 | solid |
| 12 | 400 | **0.58** | 0.08 | ≥0.5 hold |
| 16 | 600 | **0.56** | 0.06 | ≥0.5 hold |
| 24 | 800 | **0.42** | 0.04 | above chance; below 0.5 |

**Break interpretation:** Memory still beats chance at 24 items; **≥50% top-1 holds through 16** under delay. Harder ladder is the next climb, not a wet-lab failure.

## Allen wet-lab targets used

| Class | n cells | mean rate Hz |
|-------|--------:|-------------:|
| Pyr | 723 | 16.35 |
| PV | 222 | 83.35 |
| SST | 155 | 29.54 |
| VIP | 149 | 34.82 |

## How to re-run

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"
python run_stress_suite.py
python run_stress_suite.py --quick
python run_console.py   # Live/stress tab shows last report
```

JSON: `artifacts/stress_suite_report.json`

## Where to go next (after green critical path)

1. Tighten Pyr toward **1%** without free-parameter drift  
2. Intel ladder: more items + consolidation still ≥0.5  
3. Zig body: machine-frame inject into host + serial telemetry in UI  
4. Optional Dear PyGui polish — brain ABI unchanged  

---

*Stress is for finding breaks. Critical path green means the stage is honest and wet-lab–anchored.*
