# FSOT intelligence probe — retention & consolidation

Generated: `2026-07-28T15:00:17.659441+00:00`

- Items: **12** (chance 0.083)
- Delay: **600** model-ms
- Consolidate: **True**
- Scalpel tol used: **0.02** ok=True

## Accuracy ladder

| Condition | Top-1 |
|-----------|------:|
| Immediate | 0.750 |
| After delay | 0.750 |
| After consolidate | 0.750 |

## Gates

- `pin_seed_ok`: **True**
- `scalpel_ok`: **True**
- `scalpel_tol_1pct_or_fallback`: **True**
- `immediate_above_chance`: **True**
- `delay_above_chance`: **True**
- `delay_ge_half`: **True**
- `correct_sim_gt_incorrect`: **True**
- `sme_theta_direction`: **True**
- `sme_gamma_direction`: **True**
- `consolidate_above_chance`: **True**
- `consolidate_ge_half`: **True**

See `docs/STAGE_INTELLIGENCE_PROBE.md`, `docs/LEARNING_ALIGNMENT.md`.
