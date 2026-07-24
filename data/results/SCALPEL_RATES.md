# Scalpel class-rate targeting

Generated: `2026-07-24T18:20:11.374827+00:00`  
Tolerance: **5%** relative rate error vs Allen wet-lab means.

## Focus order

`['Pyr', 'PV']` — close large margin first, then tight.

## Results

| Class | Target Hz | Measured Hz | Rel err | R (ms) | fi |
|-------|-----------|-------------|---------|--------|-----|
| PV | 83.35 | 83.64 | 0.3% | 11 | 1.400 |
| Pyr | 16.35 | 16.36 | 0.1% | 51 | 0.602 |
| SST | 29.54 | 20.91 | 29.2% | 34 | 1.749 |
| VIP | 34.82 | 27.27 | 21.7% | 28 | 1.800 |

## Gates

- `pyr_within_tol`: **True**
- `pv_within_tol`: **True**
- `pv_faster_than_pyr`: **True**
- `scalpel_ok`: **True**

Biological model-Hz only; silicon wall-clock is separate.
