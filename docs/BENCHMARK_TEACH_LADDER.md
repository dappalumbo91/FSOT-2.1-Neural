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

## How we teach (same spirit as grade school)

```text
source solutions
  → extract pathway atoms (<<expr=value>>)
  → bank.tsv calc hops + word Q→final + bridges
  → held-out exam.tsv
  → score: final numeric + hop coverage + full pathway
  → emergent log (observe only)
  → climb limit_train / re-teach weak hops
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

## Success culture

| Signal | Meaning |
|--------|---------|
| Hop accuracy ↑ | Pathway atoms landing (teach is working) |
| Final accuracy ↑ | Composition / word→answer improving |
| Full pathway ↑ | Multi-hop claimability on math |
| Emergent log | Lifts logged, never curbed |

Targets are **climb bars**, not LLM leaderboard cosplay. GSM8K papers report high numbers with huge models + CoT; we measure **substrate teach lift** from cold bank.

## After GSM8K moves

Repeat the same packer pattern for BBH → ARC-C → HellaSwag, always:

1. Worst/most beneficial remaining  
2. Pathway-friendly conversion  
3. One set at a time  
4. Observe emergence  
