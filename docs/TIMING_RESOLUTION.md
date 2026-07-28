# Timing resolution (before more accuracy)

**Policy:** Fix continuous-ms time base and FI window length **before** chasing tighter percent errors.

## Hard limit: integer spikes

Rate \(f = n/T\) with \(n\in\mathbb{Z}\). For relative gate \(\varepsilon\):

\[
T \gtrsim \frac{1}{2\varepsilon f}
\]

Pyr \(f\approx 16.35\,\mathrm{Hz}\), \(\varepsilon=0.01\) ⇒ **\(T\gtrsim 3\,\mathrm{s}\)**.  
Short FI windows (~1.3 s) **cannot** hit 1% even with perfect continuous \(R\).

Default: **~4.2 s** sim time for precision / timing studies.

## Implementation

| Piece | Behavior |
|-------|----------|
| `ref_timer_ms` | Continuous countdown each `dt_ms` |
| Scalpel | `refractory_ms` float |
| Precision | Fractional ΔR_ms (POOF·φ) + long window |
| Seeds | Full Layer-1/2 incl. POOF, SUCTION, \(C_{\mathrm{factor}}\), \(\omega\), \(\gamma_c\), \(C_{\mathrm{cosm}}\) |

```powershell
python scripts/audit_formula_completeness.py
python run_timing_resolution.py --sim-ms 4200
python run_precision_climb.py --dt-ms 0.5 --sim-ms 4200 --tol 0.01
```

## Formula completeness

See [`FORMULA_COMPLETENESS.md`](FORMULA_COMPLETENESS.md) — archive closed forms present on Neural `SEEDS`; archive-primary cosmology / E_con panels remain on Physical Archive by scope.
