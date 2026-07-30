# Game-drive capability scoreboard

Generated: `2026-07-30T01:54:26.365927+00:00`

**Game data:** `D:\training data`  
**Training pack:** `D:\fsot_training`  
**Bank:** `D:\fsot_training\capability\bench_bank.tsv`

Scores are bank-retrieval / overlap capability of the FSOT mind stack after conversion — not LLM fine-tune SOTA. Curriculum pk_to_g8 is the straight-A path; external benches map progress toward broader claimability.

## Scores (bank retrieval)

| Dataset | n | correct | acc | chance | above_chance |
|---------|--:|--------:|----:|-------:|:------------:|
| gsm8k | 21 | 1 | 0.048 | 0.000 | N |
| mmlu | 12 | 3 | 0.250 | 0.250 | N |
| hellaswag | 13 | 5 | 0.385 | 0.250 | Y |
| winogrande | 14 | 3 | 0.214 | 0.500 | N |
| truthfulqa | 13 | 0 | 0.000 | 0.250 | N |
| bbh | 11 | 4 | 0.364 | 0.250 | Y |
| math | 8 | 2 | 0.250 | 0.000 | Y |
| arc_easy | 12 | 1 | 0.083 | 0.250 | N |
| arc_challenge | 7 | 3 | 0.429 | 0.250 | Y |
| pk_to_g8 | 13 | 0 | 0.000 | 0.050 | N |
| pk_to_g8_self | 60 | 51 | 0.850 | 0.250 | Y |

**Mean acc:** 0.2611 · **Above chance:** 5/11

## Loaded counts

```json
{
  "gsm8k": 60,
  "mmlu": 60,
  "hellaswag": 60,
  "winogrande": 60,
  "truthfulqa": 60,
  "bbh": 60,
  "math": 60,
  "arc_easy": 60,
  "arc_challenge": 60,
  "pk_to_g8": 60
}
```

## Next

- Ingest high-scoring convertible rows into open curriculum climb
- Zig Fixed path: teach bank.tsv → depth/claim/frontier
- Emergent monitor: `logs/emergent_behavior.jsonl` (observe only)
