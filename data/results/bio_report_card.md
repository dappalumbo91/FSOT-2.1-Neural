# FSOT-2.1-Neural bio report card

Generated: `2026-07-30T03:56:24.917719+00:00`  
Mode: **bio_match** · units=64 · steps=1200 · device=cpu

**Pass (operational):** YES  
**Pass (strict all-gaps):** YES

## Allen comparison (evoked)

| Metric | Sim | Allen | Rel error |
|--------|-----|-------|-----------|
| Mean ISI (ms) | 69.7121 | 70.5986 | 1.26% |
| Adaptation index | 0.0546 | 0.0512 | 6.74% |
| Evoked rate (Hz) | 19.6484 | — | — |

Gaps closed: **6/6**

## Band pass rates

- Evoked: 1.0
- Spontaneous: 1.0
- Rest: 1.0

_Allen-facing computational match under stated tolerances. Not a wet-lab electrophysiology claim. 1 ms step grid floors residual ISI error. pass_strict requires all gaps closed; pass_operational requires ISI+bands closed and adaptation within 25% (sign/order still primary for AHP)._
