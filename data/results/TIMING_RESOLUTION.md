# Timing resolution study

Generated: `2026-07-28T17:04:28.016081+00:00`

Continuous-ms refractory (`ref_timer_ms`) vs Allen rates at several `dt_ms`.

**Recommended dt_ms: 0.25** (1% hits=2/4, 2% hits=4/4)

| dt_ms | steps | ≤1% | ≤2% | Pyr err | PV err | SST err | VIP err |
|------:|------:|----:|----:|--------:|-------:|--------:|--------:|
| 1.0 | 1400 | 2 | 4 | 1.21% | 0.33% | 1.04% | 0.57% |
| 0.25 | 5600 | 2 | 4 | 1.21% | 0.59% | 1.04% | 0.57% |

Policy: **fix time resolution before pushing accuracy further.**
