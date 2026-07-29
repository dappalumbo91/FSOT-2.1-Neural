# English lexicon for FSOT machine language (teacher → student)

**Full methodology:** [`docs/LANGUAGE_LEARNING_METHODOLOGY.md`](../../docs/LANGUAGE_LEARNING_METHODOLOGY.md)

## Doctrine

- **Student (mind):** trinary / TritWord / FSOT frames + this lexicon as *codec*.
- **Teacher (optional local Ollama):** proposes English words / roles / definitions offline.
- The LLM is **never** part of the runtime organism — only a capability builder.
- **Knowledge fluency** is tested via PK/K/G1 facts & problems (`data/curriculum/pk_k_g1/`), not “word means word.”

## Artifacts (commit these)

| File | Role |
|------|------|
| `en_roles.tsv` | Productive word → role (mind loads this) |
| `preschool_bulk.tsv` | Free seed list |
| `g1_productive_bulk.tsv` | Free seed list |
| `en_distill.jsonl` | Optional definition / usage cards |

## Commands

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"

python run_lexicon_teacher.py --offline --target 2000
python run_lexicon_teacher.py --llm --model gemma:7b --target 2000   # local Ollama only

python run_lexicon_distill.py --report
python run_lexicon_distill.py --limit 50 --model gemma:7b

python run_curriculum_pk.py --ensure-lexicon --target 2000 --report
```

## Size targets

| Goal | Words |
|------|------:|
| Survival | ~500 |
| Everyday fluid | **~2000** |
| Strong productive | ~5000 |

## Student gates (Zig)

```text
fsot_mind english
fsot_mind practice
fsot_mind grade
fsot_mind mind
```
