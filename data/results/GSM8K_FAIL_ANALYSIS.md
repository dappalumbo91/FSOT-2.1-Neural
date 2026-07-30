# GSM8K failure analysis — binding pass (rules-first)

**Date:** 2026-07-29  
**Method:** Run `apply_rules` (with `solve_with_binding` first) on full GSM8K test (n=1319).  
**Doctrine:** Teach BIND/SCHEMA rules (form/why/how); do **not** stuff Q→A.

## Score breakdown (after BIND/SCHEMA wiring)

| Outcome | n | % | Meaning |
|---------|--:|--:|---------|
| **No fire** | **1202** | **91.1%** | No matching rule schema yet |
| **Wrong fire** | **95** | **7.2%** | Rule ran on wrong quantities / incomplete hops |
| **Correct** | **22** | **1.7%** | Full rule chain matched |

| Metric | Before binding fix | After BIND/SCHEMA |
|--------|-------------------:|------------------:|
| Correct | ~10–14 | **22** |
| Wrong fire | ~106–500 | **95** |
| Fire precision | ~2–10% | **~18.8%** (22/117) |
| Rule drills | — | **113/113 = 100%** (≥95% gate) |

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

## Remaining wrong-fire patterns (next schemas)

| Pattern | Example fail | Needed rule |
|---------|--------------|-------------|
| Fraction of remaining multi-hop | Melanie vacuum thirds/half of left | SCHEMA-inventory-cascade |
| Rate × people × time money | Hospital 500 × 24 min × $150/h | SCHEMA-billable-hours |
| “A third quit” then more quit | Nissa elves | SCHEMA-sequential-fraction |
| Multi-day exercise plans | Sue Mon/Tue cookies × year | SCHEMA-schedule-product |
| Brokerage + transfer fees stack | Mr. Tan house fees | SCHEMA-fee-stack |
| Partial “mean of duration” cue | still some mean over-fires | keep mean list-only |

---

## Curriculum gates

| Gate | Status |
|------|--------|
| Rule drills ≥ 95% | **PASS 100%** (113 items, includes 23 BIND/SCHEMA drills) |
| Imported Math-generator rules | **1520** in `data/math_rulebook` |
| Official GSM8K transfer | Climb via schemas — not Q→A stuffing |

---

## Next steps (ordered)

1. SCHEMA-inventory-cascade (sold a third, then 2 more, half of remaining).  
2. SCHEMA-billable-hours (patients × minutes → hours × rate).  
3. SCHEMA-sequential-fraction (⅓ quit, half of rest quit, …).  
4. Wire more AR-* forms from MASTER_RULEBOOK only when referent-safe.  
5. Re-score fire precision after each schema; refuse over-broad cues.
