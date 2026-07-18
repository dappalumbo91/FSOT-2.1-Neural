# FSOT-2.1-Neural bio report card

Generated: `2026-07-18T18:49:59.075509+00:00`  
Mode: **bio_match** · units=64 · steps=1200 · device=cpu

**Pass (operational):** YES  
**Pass (strict all-gaps):** YES

## Allen comparison (evoked)

| Metric | Sim | Allen | Rel error |
|--------|-----|-------|-----------|
| Mean ISI (ms) | 70.6748 | 70.5986 | 0.11% |
| Adaptation index | 0.0524 | 0.0512 | 2.45% |
| Evoked rate (Hz) | 19.7917 | — | — |

Gaps closed: **6/6**

## Band pass rates

- Evoked: 1.0
- Spontaneous: 1.0
- Rest: 1.0

_Allen-facing computational match under stated tolerances. Not a wet-lab electrophysiology claim. 1 ms step grid floors residual ISI error. pass_strict requires all gaps closed; pass_operational requires ISI+bands closed and adaptation within 25% (sign/order still primary for AHP)._
