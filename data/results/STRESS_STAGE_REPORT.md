# Stress suite report — stage break map

Generated: `2026-07-28T15:50:03.621928+00:00`  
Duration: **13.8s**  ·  tests **25/25** pass  
Mode: `quick`

## Doctrine

- Archive pin **D1D38A** + codon map
- Allen wet-lab class rates (scalpel)
- Intelligence via **FSOT machine** items (not Morse)
- Biology accuracy before performance

## Critical breaks (must fix before next climb)

_None — critical path held._

## Soft breaks (known stretch / scale)

_None._

## Full results

| Stage | Name | OK | Critical | t(s) |
|-------|------|:--:|:--------:|-----:|
| A | seeds_vs_archive | Y | Y | 1.26 |
| A | archive_pin | Y | Y | 1.27 |
| A | codon_64_map | Y | Y | 1.27 |
| A | atlas_domain_S | Y | Y | 1.29 |
| A | fsot_bridge | Y | Y | 1.3 |
| B | machine_verify | Y | Y | 1.3 |
| B | payload_1B | Y | Y | 1.3 |
| B | payload_16B | Y | Y | 1.3 |
| B | payload_256B | Y | Y | 1.3 |
| B | payload_4096B | Y | Y | 1.33 |
| B | morse_secondary | Y |  | 1.33 |
| B | inject_50_packets | Y |  | 1.37 |
| B | bridge_large_text | Y |  | 1.37 |
| C | genetic_net_n32 | Y | Y | 1.44 |
| C | genetic_net_n64 | Y | Y | 1.48 |
| C | multi_region_brain | Y | Y | 1.54 |
| D | allen_targets_loaded | Y | Y | 1.57 |
| D | scalpel_tol_2% | Y | Y | 4.7 |
| E | scalpel_brain_build | Y |  | 9.5 |
| E | intel_items4_delay50 | Y |  | 10.4 |
| E | intel_items6_delay100 | Y |  | 11.91 |
| E | ladder_summary | Y |  | 11.91 |
| F | zig_host_present | Y |  | 11.91 |
| F | zig_host_run | Y | Y | 11.98 |
| G | console_displays | Y | Y | 13.8 |

## Where to go next

1. Fix any **critical** breaks first (pin, codon, scalpel 2%, zig host).
2. Soft breaks at 1% scalpel or high item counts define the accuracy frontier.
3. After green critical path: Zig machine-frame inject + live brain meters in UI.

JSON: `artifacts/stress_suite_report.json`
