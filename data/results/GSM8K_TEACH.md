# GSM8K teach pack — first external reasoning benchmark

Generated: `2026-07-30T02:00:01.585494+00:00`

**Why first:** Flagship LLM multi-hop math reasoning; grade-school domain; worst open-answer baseline; pathways in <<expr=val>> solutions

Train problems: **1500** · Test: **300**  
Bank rows: **13130** · Unique calc atoms: **3061**

## Scores (bank retrieval + pathways)

| Phase | Final acc | Hop acc | Full pathway acc |
|-------|----------:|--------:|-----------------:|
| Cold (no teach) | 0.000 | 0.000 | 0.000 |
| After teach | **0.317** | **0.395** | **0.003** |
| Δ lift | +0.317 | +0.395 | +0.003 |

Train self-check final: `{'n': 80, 'correct': 80, 'accuracy': 1.0, 'method': 'bank_retrieve_final'}`

## What was taught

1. **Calc atoms** — each `<<expr=value>>` hop as math fact (pathway)
2. **Word problems** — full question → final numeric answer
3. **Bridges** — last step → final (composition)

## Next benchmarks (after GSM8K climbs)

- bbh (hard multi-hop reasoning)
- arc_challenge (science reasoning)
- hellaswag (commonsense)
- mmlu (broad knowledge — later)

## Files

```
data/curriculum/gsm8k/bank.tsv
data/curriculum/gsm8k/exam.tsv
data/curriculum/gsm8k/pathways.jsonl
D:/fsot_training/curriculum/gsm8k/  (mirror)
```
