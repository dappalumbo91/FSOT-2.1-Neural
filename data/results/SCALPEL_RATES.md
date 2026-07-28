# Scalpel class-rate targeting

Generated: `2026-07-28T14:50:53.709197+00:00`  
Tolerance: **2%** relative rate error vs Allen wet-lab means.

## Focus order

`['Pyr', 'PV', 'SST', 'VIP']` — close large margin first, then tight.

## Results

| Class | Target Hz | Measured Hz | Rel err | R (ms) | fi |
|-------|-----------|-------------|---------|--------|-----|
| PV | 83.35 | 83.85 | 0.6% | 11 | 1.400 |
| Pyr | 16.35 | 16.15 | 1.2% | 59 | 0.569 |
| SST | 29.54 | 29.23 | 1.0% | 32 | 1.039 |
| VIP | 34.82 | 34.62 | 0.6% | 28 | 1.286 |

## Gates

- `pv_faster_than_pyr`: **True**
- `scalpel_ok`: **True**
- `pyr_within_tol`: **True**
- `pv_within_tol`: **True**
- `sst_within_tol`: **True**
- `vip_within_tol`: **True**

Biological model-Hz only; silicon wall-clock is separate.
