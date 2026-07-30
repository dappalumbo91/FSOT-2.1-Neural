# Dual-track scorecard — bio + math

Generated: `2026-07-30T04:10:13.082416+00:00`

**Doctrine:** Biological wet-lab accuracy and math curriculum are **separate tracks**. GSM8K climb must never drop rule drills below 95%. Auto-templates that break drills are refused.

## Gates

| Track | Gate | Status |
|-------|------|--------|
| **BIO wetlab** | public battery (Allen/codon/pin) | **PASS** `37/37` |
| **BIO card** | Allen batch ISI/adapt (operational) | **PASS** gaps `6/6` |
| **BIO lean** | Lean × wetlab certificate | **PASS** |
| **MATH drills** | ≥95% hard gate | **PASS** |
| **MATH binding** | 100% BIND/SCHEMA drills | **PASS** |

## Biological accuracy (not forgotten)

- **Wetlab battery:** `37/37` pass=True critical_fails=[] · `2026-07-30T03:54:12.268532+00:00`
- **Bio report card:** operational=True strict=True gaps=`6/6`
- ISI rel error: `0.012556033995267429` (operational needs ≤2%) · adapt: `0.06742300911743665`
- Lean wetlab cert: True
- Bio card generated: `2026-07-30T03:56:24.917719+00:00`

Refresh: `python scripts/dual_track_scorecard.py --refresh-bio`

Intel/bio stack modes (Zig): `intel-loop`, neuromod, sleep_replay — see `docs/FORWARD_INTELLIGENCE_BIO.md`.

## Math curriculum (rules-first)

- Drills: **1.0** (n=127) · hard gate ≥0.95
- Binding drills: 37/37
- GSM8K sample n=300: correct=71 wrong_fire=12 no_fire=217
- Fire precision: **0.8554**

Hard rule: `drills≥95% never sacrificed for auto-templates`

## Note on the 76% drill fail

That was a **regression from ungated train-template auto-apply**. It is **not** the current gate. Current drills must stay **100% / ≥95%**. Loose auto that tanks drills is rejected.
