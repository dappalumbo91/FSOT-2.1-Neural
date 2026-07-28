# Scalpel class-rate targeting

Generated: `2026-07-28T14:46:27.571567+00:00`  
Tolerance: **5%** relative rate error vs Allen wet-lab means.

## Focus order

`['Pyr', 'PV', 'SST', 'VIP']` — close large margin first, then tight.

## Results

| Class | Target Hz | Measured Hz | Rel err | R (ms) | fi |
|-------|-----------|-------------|---------|--------|-----|
| PV | 83.35 | 83.64 | 0.3% | 11 | 1.400 |
| Pyr | 16.35 | 16.36 | 0.1% | 51 | 0.602 |
| SST | 29.54 | 29.09 | 1.5% | 32 | 1.036 |
| VIP | 34.82 | 33.64 | 3.4% | 23 | 1.212 |

## Gates

- `pv_faster_than_pyr`: **True**
- `scalpel_ok`: **True**
- `pyr_within_tol`: **True**
- `pv_within_tol`: **True**
- `sst_within_tol`: **True**
- `vip_within_tol`: **True**

Biological model-Hz only; silicon wall-clock is separate.
