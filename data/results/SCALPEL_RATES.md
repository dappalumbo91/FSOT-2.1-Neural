# Scalpel class-rate targeting

Generated: `2026-07-28T15:00:56.577937+00:00`  
Tolerance: **1%** relative rate error vs Allen wet-lab means.

## Focus order

`['Pyr', 'PV', 'SST', 'VIP']` — close large margin first, then tight.

## Results

| Class | Target Hz | Measured Hz | Rel err | R (ms) | fi |
|-------|-----------|-------------|---------|--------|-----|
| PV | 83.35 | 83.33 | 0.0% | 11 | 1.400 |
| Pyr | 16.35 | 16.34 | 0.1% | 61 | 0.570 |
| SST | 29.54 | 29.33 | 0.7% | 33 | 1.071 |
| VIP | 34.82 | 34.67 | 0.4% | 28 | 1.262 |

## Gates

- `pv_faster_than_pyr`: **True**
- `scalpel_ok`: **True**
- `pyr_within_tol`: **True**
- `pv_within_tol`: **True**
- `sst_within_tol`: **True**
- `vip_within_tol`: **True**

Biological model-Hz only; silicon wall-clock is separate.
