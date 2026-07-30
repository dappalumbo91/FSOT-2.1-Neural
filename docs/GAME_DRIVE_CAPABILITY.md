# Game-drive data → capability apparatus

**Roots**

| Path | Role |
|------|------|
| `D:\fsot_training` | Local pack: `curriculum/pk_to_g8`, MNIST gate, climb logs |
| `D:\training data` | Full holdings: GSM8K, MMLU, HellaSwag, ARC, BBH, SQuAD, HumanEval, arXiv, genetics, … |

Env overrides: `FSOT_TRAINING_ROOT`, `FSOT_GAME_DATA`.

## What we built

| Piece | Path |
|-------|------|
| Catalog + convert + score | `fsot_nuron/game_drive_bench.py` |
| Runner | `scripts/run_game_drive_bench.py` |
| Scoreboard (on game drive) | `D:\fsot_training\capability\CAPABILITY_SCOREBOARD.md` |
| Converted bank | `D:\fsot_training\capability\bench_bank.tsv` |
| Emergent log (observe only) | `D:\fsot_training\logs\emergent_behavior.jsonl` |

## Convert apparatus

Public benchmarks → mind **bank.tsv** schema:

```text
domain \t grade \t kind \t question \t answer
```

| Dataset | Conversion |
|---------|------------|
| GSM8K | final `####` answer |
| MMLU | MCQ → correct choice text |
| HellaSwag | context → labeled ending |
| Winogrande | sentence → option1/2 |
| TruthfulQA | best_answer |
| BBH | input → target |
| MATH | problem → `\boxed{}` or tail |
| ARC Easy/Challenge CSV | question → answerKey text |
| pk_to_g8 | already native bank |

Code gen (HumanEval) / IFEval flagged **not** auto-converted yet (need code/instruction runtime).

## Scoring doctrine

Scores are **bank-token overlap retrieve** after conversion — the same *kind* of claim path as grade depth, **not** LLM fine-tune SOTA.

- Above chance on MCQ is meaningful progress signal  
- Open math (GSM8K) near zero is expected until multi-hop numeric reason is curriculum-backed  
- Curriculum `pk_to_g8` remains the straight-A path  

## Emergent behavior (monitor only)

```text
policy: observe_only_no_curb
```

We **log** strong transfer candidates, curriculum mastery, unexpected open-math lexical hits.  
We do **not** damp, prune, or “fix” for emergence. See append-only JSONL.

## Run

```powershell
cd "I:\fsot nuron"
python scripts/run_game_drive_bench.py --catalog
python scripts/run_game_drive_bench.py --convert --bench --limit 80
python scripts/run_game_drive_bench.py --emergent-summary
```

Then feed bank into Zig:

```powershell
# bank already at D:\fsot_training\capability\bench_bank.tsv
# depth/ladder load paths include D:/fsot_training/curriculum/...
fsot_mind depth
fsot_mind frontier
```

## Speech reconnect (still next product)

After capability map is honest: `docs/SPEECH_RECONNECT.md` — live mic/TTS was fluent before; path intact.
