# GSM8K failure analysis — what the rules do wrong

**Date:** 2026-07-30  
**Method:** Run `apply_rules` on full GSM8K test (n=1319).  
**Raw dump:** `GSM8K_FAIL_ANALYSIS.json`

## Score breakdown (not one blob of “low accuracy”)

| Outcome | n | % | Meaning |
|---------|--:|--:|---------|
| **No fire** | **809** | **61.3%** | Engine refused or found no matching rule schema |
| **Wrong fire** | **500** | **37.9%** | A rule *did* run — but on the **wrong quantities / incomplete multi-hop** |
| **Correct** | **10** | **0.8%** | Rule chain matched the problem structure |

When a rule fires at all: accuracy ≈ **2%** (10/510).  
So the problem is **not** “it never applies rules.” It’s:

1. **Most problems need schemas we have not taught yet** (no fire).  
2. **When language cues match, we often apply a *single* local rule to the *wrong* numbers** (wrong fire).

---

## What’s different about questions that work

Correct examples share:

| Property | Example |
|----------|---------|
| Short, **isomorphic to a drill** | “3 sprints × 3 times × 60 m” → pure product |
| Clear **relative chain with one base number last** | Sheep: twice / 4 times / Seattle=20 |
| **Half-of-first + add** with two quantities only | Robe: 2 bolts + half that much |
| Unit conversion + product we explicitly coded | Eggs → dozens / week |

These look like **worksheet items**: few numbers, one dominant structure, little distractor text.

---

## Wrong fire — the real damage

Top **rule steps** used on wrong answers:

| Rule step | Count (approx) | Failure mode |
|-----------|---------------:|--------------|
| **double** | ~152 | Sees “twice” and doubles the **first** number, ignores multi-hop chain |
| **percent** | ~143 | Pairs **wrong** base with **wrong** % (e.g. 60% of 16 glasses instead of 60% of $5) |
| **half** | ~130 | Sees “half” and halves **first digit**, ignores “half of what was left” / multi-step |
| mul_rate | ~31 | “Per hour” → multiplies first two nums, ignores overtime / two rates |
| add_combine | ~33 | Sums some numbers when problem is not a pure total |

### Pattern A — **Cue match, referent wrong**

Human rule: *“half” means ÷2 of the **referent quantity**.*  

Engine: *if “half” ∈ text, half(nums[0]).*

| Gold | Pred | What text said |
|-----:|-----:|----------------|
| 23 | 1 | “5 more than **half of Raymond’s 40**” — engine halved **2** (from “2 fewer”) |
| 18 | 1 | “**half of what was left**” — multi-hop inventory; engine halved first num |
| 10 | 30 | “runs 3 hours first day and **half as much** the other days” + speed — not half of 60 miles |

**Difference from drills:** drills say “What is half of 16?” (referent explicit). GSM8K hides the referent in discourse.

### Pattern B — **Percent of the wrong thing**

| Gold | Pred | What happened |
|-----:|-----:|---------------|
| 64 | 9.6 | “every second glass costs **60% of the price** ($5)” → used 60% of **16** (count) |
| 160 | 8 | “**40% of the way** through download” → 40% of **20 minutes** (time), not of 200 GB |
| 60 | 12 | Dance class multi-step % of remaining — almost right chain but asked **percentage of entire class** for last group, not headcount |

**Difference:** drills are “What is 25% of 200?” GSM8K embeds % inside **pricing / progress / remaining** schemas.

### Pattern C — **“Twice” ≠ “double the first number”**

| Gold | Pred | Text |
|-----:|-----:|------|
| 8 | 2 | “4× as old as … 2× as old as Suzy (1 year)” — needs **compose multiplies**, not double(1) |
| 800 | 100 | “twice as many red ties… red cost 50% more… $200 on blue at $40” — multi-hop money |

**Difference:** drills teach double(n). GSM8K uses “twice” inside **relative age / inventory / pricing** graphs.

### Pattern D — **Rate multiplies wrong pair**

“Per hour” present → `nums[0]*nums[1]` even when those are hours and $/hour in wrong order, or two different jobs.

---

## No fire — what’s missing (not “bad rules”)

809 items never match a **complete** schema. Samples need:

| Missing schema | Example need |
|----------------|--------------|
| **Number words** (“three”, “four”) not digits | Duck eggs remainder sell |
| **Profit / markup** | House flip +150% value |
| **Multi-item cart** | Bakery dozens × prices |
| **Break-even / net over years** | Lemon tree cost vs lemon revenue |
| **Distance compound** | Trains west then north (Pythagoras or path length) |
| **Age story** | Born X years before, son at age Y |
| **Time-of-day duration** | 1 PM–5 PM → 4 hours without “hours” as a number |
| **Mixture / fraction of water** | Two-thirds water + spill |
| **Win/loss constraints** | W = L + 8, W+L = 22 |

Language maps often **detect** mul/sub (`strats` non-empty) but **apply** refuses because we tightened “don’t guess” — correct humility, incomplete curriculum.

Number-count: failures often have **3–6+ quantities**; successes often **1–3** clean quantities.

---

## Root cause (one sentence)

**We taught atomic rules and apply them when a keyword appears, but GSM8K needs *schema selection + referent binding + multi-hop composition*; drills bind referents explicitly, test items bury them in narrative.**

```text
DRILL:  half of 40            → referent = 40 (clear)
GSM8K:  "2 fewer than Aaron. Aaron has 5 more than half of Raymond's 40"
        → must bind "half" to Raymond's jewels, then +5, then −2
```

---

## What to teach next (rules, not stuffing)

1. **Referent binding rule**  
   *How:* “half of X” / “twice as many as Y” attach to the **named quantity**, not nums[0].

2. **Relative chain rule**  
   *How:* “A is k times B; B is m times C; C = n” → compose multipliers before ask.

3. **Percent-of-price vs percent-of-count**  
   *Why:* % modifies the nearest rate/price noun, not any number nearby.

4. **Number-word lexicon**  
   *How:* three→3, four→4 (so remainder-sell schema can fire).

5. **Schema library** (each with why/how): profit, cart sum, age, clock duration, win/loss, unit path distance.

6. **Refuse more often** until schema matches — wrong fire (500) hurts more than silence (809).

---

## Metric to watch while climbing

| Metric | Goal |
|--------|------|
| wrong_fire / (correct+wrong_fire) | ↓ toward 0 (precision of apply) |
| correct / n | ↑ |
| no_fire with clear missing schema | shrink by adding **named** schemas |
| drills still ≥95% | must not regress |

Do **not** improve score by stuffing test answers. Improve by teaching **binding + multi-hop rule graphs**.
