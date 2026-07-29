# Code review + stress (stage snapshot)

Date: 2026-07-29  
Scope: short-horizon learning, caption↔pixel bind, curriculum, refine, sensory.

## Stress results

| Suite | Result |
|-------|--------|
| CI smoke | **PASS** |
| Stress suite | **43/43** critical path green |
| Multi-domain stress | **6/6** pass · mean **95.0** |

Domains: authority/Allen · learning SME · science docs · narrative · media AV · short-horizon 5W1H.

## Issues found

### Fixed this pass

1. **Inflated recall** — short-horizon queries were often the first title token matched only against titles.  
   **Fix:** match expected substrings against title + plain_english + captions + symbols; drive queries from **5W1H** cards, not title prefixes.

2. **Curriculum symbol pollution** — census pulled free-text tokens like `explain` / `particularly` into gap plans.  
   **Fix:** allow-list `_CURRICULUM_VOCAB` (lexicon-aligned teachable categories only).

3. **No structured teaching** — dumps of text without who/what/why/where/when/how.  
   **Fix:** `teach_5w1h.py` + encode path writes 5W1H lesson cards into episode `plain_english` and tests 5W1H probes.

4. **Caption name quality (prior)** — glue words / cold names.  
   **Addressed earlier:** character bias, purity prune, multi-frame vote (held ~0.94–1.0).

### Remaining honest limits (not bugs)

| Limit | Why it matters |
|-------|----------------|
| Open-world **character** ID | Tutor-ablated movie-entity ID ≠ “that is Jake from pixels alone” |
| Causal WHY | Extractive “because…” sentences, not true scientific causal models |
| Curriculum A/B | Gap vs fixed often **tie** on recall; pixel scores are seed-noisy |
| Media first-N discovery | Same videos preferred unless shuffle seeds change order |
| Score_all_layers cost | Real media decode on every refine score can be slow |
| Silent `except` | Several paths swallow decode errors (intentional soft-fail for optional G:) |

## Human-like teaching doctrine

When teaching, always pack:

```text
WHO   agents / characters
WHAT  event / claim / pattern
WHY   cause / purpose / co-occurrence mechanism (stated honestly)
WHERE place / source path / kind
WHEN  time / caption stream / encode window
HOW   FSOT method (trit body, RF cascade, SME, no free S)
```

Runner: short-horizon auto-builds cards via `build_5w1h(...)`.

## How to re-stress

```powershell
python scripts/ci_smoke.py
python run_stress_suite.py
python run_multi_domain_stress.py
python run_wetlab_accuracy_battery.py
```
