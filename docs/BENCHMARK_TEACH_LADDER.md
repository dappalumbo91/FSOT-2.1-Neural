# External benchmark teach ladder

Grade-school curriculum (PK→G8) is the **home path**.  
External LLM benchmarks are taught **one at a time**, like another grade band — premises + pathways, not weight dumping.

## Order (impact × teachability for *this* substrate)

| # | Benchmark | Why this slot | Our cold baseline |
|---|-----------|---------------|-------------------|
| **1** | **GSM8K** | Flagship multi-hop *reasoning*; literally grade-school math; worst open-answer offender; solutions contain `<<step>>` pathways | ~0.05 final |
| 2 | BBH | Hard multi-hop / algorithmic reasoning | ~0.36 MC-ish |
| 3 | ARC-Challenge | Science reasoning (MCQ) | ~0.43 sample |
| 4 | HellaSwag | Commonsense completion | ~0.39 sample |
| 5 | MMLU | Broad knowledge (later — high school/college) | ~chance |
| 6 | TruthfulQA / Winogrande | Truth & coref (harder; after reasoning atoms) | weak |
| later | HumanEval | Needs code runtime | not converted |

**Not first:** MMLU (too broad, less pathway structure), TruthfulQA (knowledge/truth, not hop math), HumanEval (needs interpreter).

## How we teach (rule-first — not stuffing)

**Correction:** shoving Q→A and retrieving is *not* teaching. Humans learn:

```text
1. RULES / formulas   (a+b, left=total−used, half=n/2, …)
2. LANGUAGE MAPS      ("altogether"→add, "left"→subtract, …)
3. DECOMPOSITION      find quantities → pick rule → evaluate → compose hops
4. DRILLS             worksheet practice of rule application
5. WORD PROBLEMS      only as practice applying rules (not answer memorization)
```

```powershell
# 1) Pull full Math-generator corpus (Desktop) into monorepo
python scripts/import_math_generator_rules.py
#    → data/math_rulebook/MASTER_RULEBOOK.json  (~1520 atomic rules)
#    → data/math_rulebook/bank.tsv

# 2) Runtime apply + drills (school word-problem layer)
python scripts/run_math_rules_teach.py
# artifacts: data/curriculum/math_rules/{RULES.md,bank.tsv,REPORT.md}
```

**Authority rule source:** `C:\Users\damia\Desktop\Math generator`  
(`MATH_GENERATOR_ROOT` env override). Registry: `RULE_DOCUMENT_REGISTRY.json`.

Legacy GSM8K stuffing path remains as contrast only; **doctrine is math_rules + imported rulebook**.

## Linguistics (reading + writing) — same rule pedagogy

```powershell
python scripts/run_linguistics_rules_teach.py
# form + WHY + HOW + apply drills ≥95%
# data/curriculum/linguistics_rules/RULES.md
```

Domains: phonics · morphology · grammar · reading · writing · composition.

Combined:

```powershell
python scripts/run_rules_teach_all.py
# import math generator + math drills + linguistics drills
```

## Run GSM8K (active)

```powershell
cd "I:\fsot nuron"
python scripts/run_gsm8k_teach.py
python scripts/run_gsm8k_teach.py --limit-train 800 --limit-test 200
```

Artifacts:

- `data/curriculum/gsm8k/bank.tsv`
- `data/curriculum/gsm8k/exam.tsv`
- `data/curriculum/gsm8k/pathways.jsonl`
- `D:\fsot_training\curriculum\gsm8k\` (mirror)
- `data/results/GSM8K_TEACH.md`

## Success culture (same as grade school: ≥95%)

| Gate | Bar | Meaning |
|------|-----|---------|
| **Re-ask taught** | ≥**95%** | Exact taught questions |
| **Paraphrase taught** | ≥**95%** | Reworded taught (numbers kept) |
| **Pathway hops** | ≥**95%** | `<<expr>>` calc atoms + executor |
| **Official GSM8K test** | climb | Transfer / OOD; keep pushing |

Straight-A on GSM8K **curriculum** = first three gates (like PK→G8).  
Official test is the **hard transfer** climb (case-based pathway rewrite + heuristics), not a free pass.

Targets are climb bars with honest split metrics — not LLM leaderboard cosplay.

## After GSM8K moves

Repeat the same packer pattern for BBH → ARC-C → HellaSwag, always:

1. Worst/most beneficial remaining  
2. Pathway-friendly conversion  
3. One set at a time  
4. Observe emergence  
