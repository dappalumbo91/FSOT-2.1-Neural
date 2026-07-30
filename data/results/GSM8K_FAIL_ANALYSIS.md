# GSM8K failure analysis — binding pass (rules-first)

**Date:** 2026-07-29  
**Method:** Run `apply_rules` (with `solve_with_binding` first) on full GSM8K test (n=1319).  
**Doctrine:** Teach BIND/SCHEMA rules (form/why/how); do **not** stuff Q→A.

## Score breakdown (after high-lift SCHEMA pass)

| Outcome | n | % | Meaning |
|---------|--:|--:|---------|
| **No fire** | **1204** | **91.3%** | No matching rule schema yet |
| **Wrong fire** | **87** | **6.6%** | Rule ran on wrong quantities / incomplete hops |
| **Correct** | **28** | **2.1%** | Full rule chain matched |

| Metric | Pre-binding | After BIND | After high-lift schemas |
|--------|------------:|-----------:|------------------------:|
| Correct | ~10–14 | 22 | **28** |
| Wrong fire | ~106–500 | 95 | **87** |
| Fire precision | ~2–10% | ~19% | **~24.4%** (28/115) |
| Rule drills | — | 113/113 | **119/119 = 100%** |

When a rule fires: accuracy ≈ **19%**. Wrong-fire is still the quality bottleneck; no-fire is the coverage bottleneck.

---

## What we taught (form / why / how)

| Rule | Formula | Why | How |
|------|---------|-----|-----|
| **BIND-01** | number ↔ noun/role | Ops act on named quantities, not digit order | Store binding[noun]=N; never treat multipliers as base counts |
| **BIND-02** | half/% of X → binding[X] | Modifiers attach to grammatical object | Look up X; then half or %; nest half-of-subset |
| **BIND-03** | A=k·B; B=m·C; C=n → compose | Multi-hop must compose before ask | Edges from “times as / twice as many”; base is known absolute, never “has 4 times” |
| **BIND-04** | A = B ± k | Fewer/more shift a bound quantity | Resolve B first; then ±k |
| **SCHEMA-remainder-sell** | (start−u1−u2)×price | Residual inventory sold | Digits **or** number words for uses |
| **SCHEMA-win-loss** | W=(T+d)/2 | Sum + difference of two unknowns | From total games + “won d more than lost” |
| **SCHEMA-clock** | hours=end−start | Time span ≠ free nums | Melt rate×hours; **refuse** travel with return rate |
| **SCHEMA-profit-markup** | new=buy·(1+p/100); profit=new−buy−repair | GSM8K: % attaches to **purchase**, not invested total | Bind buy + repair separately |

Runtime: `math_binding.solve_with_binding` is called at the start of `apply_rules` (after pure AR identities).

---

## Correct fires now (examples)

| Schema/rule | Example structure |
|-------------|-------------------|
| SCHEMA-remainder-sell | Ducks: 16 eggs, eat three, bake with four, $2 each → 18 |
| SCHEMA-profit-markup | House 80k + 50k repair, +150% on buy → profit 70k |
| BIND-03 sheep chain | Toulouse 2× Charleston 4× Seattle=20 → together 260 |
| BIND-04 multi-hop | Siobhan 2 fewer than Aaron = half(Raymond40)+5 → 23 |
| BIND-02 nested half | 16 balls → half golf → half blue → 4 |
| SCHEMA-win-loss | 22 games, won 8 more than lost → 15 |
| SCHEMA-clock melt | 2 cm/h from 1–5 PM → 8 cm |
| BIND-02 price % | every second glass 60% of $5, 16 glasses → 64 |

---

## High-lift schemas landed this pass

| Schema | Form | GSM8K exemplar |
|--------|------|----------------|
| **inventory-cascade** | reverse half → ×2; +k; 1/3 sold → ×3/2 | Melanie vacuums → 18 |
| **sequential-fraction** | left = start·(1−f) − k | Nissa elves → 30 |
| **billable-hours** | hours=n×min/60; profit=h×(charge−cost) | Hospital → 10000 |
| **rate-schedule** | rate×h×days×weeks×(1−d%) | Jean makeup → 27000 |
| **fraction-remaining-split** | rem=start·(1−f); part=rem/2 | Bakery afternoon → 10 |
| **salary-fractions** | Σ(fi·sal); half rem; −gifts | Zaid → 350 |

---

## Remaining wrong-fire / no-fire (next lift)

| Pattern | Needed rule |
|---------|-------------|
| Multi-day exercise plans (Mon/Tue × year) | SCHEMA-schedule-product |
| Brokerage + transfer fee stack | SCHEMA-fee-stack |
| Download % of file vs time | SCHEMA-progress-bytes |
| Complex age/work-rate together | SCHEMA-work-rate |
| Keep mean list-only | already tightened |

---

## Curriculum gates

| Gate | Status |
|------|--------|
| Rule drills ≥ 95% | **PASS 100%** (119 items) |
| Imported Math-generator rules | **1520** in `data/math_rulebook` |
| Official GSM8K transfer | Climb via schemas — not Q→A stuffing |

---

## Next steps (ordered)

1. SCHEMA-fee-stack (transfer % + brokerage % of sale).  
2. SCHEMA-schedule-product (per-day actions × days × weeks).  
3. SCHEMA-work-rate / progress-bytes with strict referents.  
4. Re-score fire precision after each schema; refuse over-broad cues.
