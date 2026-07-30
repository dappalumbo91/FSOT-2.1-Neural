# GitHub repository connectivity audit

**Date:** 2026-07-30  
**Repos:** monorepo `FSOT-2.1-Neural` (`experiment/fsot-fixed-precision`) + product `fsot-neuron-zig` (`main`)  
**Reference math:** [`FSOT_MATH_SYSTEM_SOLIDIFIED.md`](FSOT_MATH_SYSTEM_SOLIDIFIED.md) · archive `I:\FSOT-Physical-Archive`

## Verdict

| Check | Status |
|-------|--------|
| Zig src monorepo ↔ product hash parity | **PASS** (0 content diffs, 0 missing files) |
| Lean `scientific_panel_ok` (mind stack) | **PASS** · 0 sorry · v4.31.0 |
| Lean × wet-lab certificate overall | **PASS** |
| Archive pin D1D38A / seeds | **PASS** |
| Wet-lab battery critical | **PASS** (37/37 on last battery) |
| Product stress: `fixed` | **PASS** (`FSOT_FIXED_STACK_OK`, bio accurate) |
| Product stress: `pathways` / wet | **PASS** (`FSOT_GLIA_MOLECULAR_OK`, STDP ok) |
| Product stress: `md` | **PASS** (`FSOT_ALLATOM_MD PASS`) |
| Product stress: `depth` | **PASS** (540 paraphrase exam) |

## What was stale / disconnected (and fixed this pass)

| Item | Issue | Fix |
|------|-------|-----|
| Product README | Still described PK/K/G1 only; no wet stack, ladder, depth, MD | Updated modes + architecture |
| Product doctrine set | Missing wet/depth/pathways/bio audit / genetics-as-code docs | Synced from monorepo |
| Math solidification | Math lived across archive dig + FORMULAS + code | New `FSOT_MATH_SYSTEM_SOLIDIFIED.md` + Lean modules |
| Lean stamp | Neural panel lacked Fixed / wet / curriculum structure | Extended `scientific_panel_ok`; certificate refreshed |
| MD path in product doc | Said `embodiment/zig/src/...` | Corrected to `src/allatom_md.zig` |

## Still monorepo-only (by design)

| Component | Why |
|-----------|-----|
| `formal/` Lean panel + certificate export | Product is Zig body; stamp lives with Python host + battery |
| `run_wetlab_accuracy_battery.py` | Allen/EEG empirical panel |
| Open curriculum download + `run_curriculum_open.py` | Host data pipeline |
| `run_grade_depth.py` / Python grade helpers | Optional host; Zig `depth`/`ladder` are authority |
| Character pixel-id experiment scripts | Uncommitted research side-path (not core mind) |

## Local dirty noise (not blocking)

Monorepo working tree still has result JSON churn (`stress_suite_report`, `precision_climb`, thesis ledger) and optional `character_pixel_id` untracked scripts — **not** part of the mind core stamp. Binary junk `$out` / `$out.pdb` under embodiment must stay untracked.

## Connectivity map (as of this audit)

```text
I:\FSOT-Physical-Archive  (405-domain pin D1D38A, full Lean hub)
        │ pin / seeds / doctrine
        ▼
FSOT-2.1-Neural monorepo
  docs/FSOT_MATH_SYSTEM_SOLIDIFIED.md
  formal/ scientific_panel_ok
  data/results/LEAN_WETLAB_CERTIFICATE.*
  embodiment/zig/*  ──hash-match──►  fsot-neuron-zig/src/*
  docs wet/depth/*  ──synced──►      fsot-neuron-zig/docs/*
```

## Stress evidence (product binary, 2026-07-30)

```text
FSOT_FIXED_STACK_OK
FSOT_FIXED_BIO_ACCURATE_OK
FSOT_SYNAPSE_PATH PASS / FSOT_GLIA_MOLECULAR_OK  (stdp_ok=true, wet cascade live)
FSOT_ALLATOM_MD PASS / FSOT_MD_LAB_OK
FSOT_DEPTH PASS / FSOT_GRADE_SCHOOL_UNDERSTAND_OK  (exam n=540)
```

## Remaining bio-accuracy / intelligence work (next)

Not “disconnected components” — **forward path**:

1. Any soft wetlab stretch history (prior 1% rate soft fails) — re-run full battery when Allen cache refreshed.  
2. Curriculum ladder full PK→G8 on training drive after depth (already depth-green).  
3. Deeper multi-hop / claimability still the intelligence frontier (not missing files).  
4. Optional: NVE energy tighter on MD lab (currently short Berendsen demo gate).  
5. Missing *process* bio pieces already present (channels, glia, STDP, quantal); longer-horizon multi-region systems (sleep replay, neuromodulators as first-class Fixed ODEs) can extend without breaking the stamp.

---

*Audit after Lean mind-stack stamp push `fb3a117` (monorepo) + product math/docs sync.*
