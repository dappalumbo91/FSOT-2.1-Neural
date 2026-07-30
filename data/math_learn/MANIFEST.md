# Math learn memory banks

| File | Role | Commit? |
|------|------|---------|
| `trace_bank.json` | **Primary learned capacity** — episodic multi-hop methods from experience school | yes (~6 MB) |
| `episode_bank.json` | Legacy/drill episodes (cue→answer + atomics) | yes if modest |
| `trace_bank.json.bak_exp` | Local backup from `--fresh` runs | **no** |

## Doctrine

Traces are **methods** (hop sequences over slots), not stuffed test answers.

See [`docs/LEARNED_CAPACITY.md`](../../docs/LEARNED_CAPACITY.md).

## Regenerate traces

```powershell
python scripts/run_multihop_experience_learn.py --fresh --train-limit 8000 --epochs 8
```
