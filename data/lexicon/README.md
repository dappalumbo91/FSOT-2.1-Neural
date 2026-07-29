# English lexicon for FSOT machine language (teacher → student)

## Doctrine

- **Student (mind):** trinary / TritWord / FSOT frames + this lexicon as *codec*.
- **Teacher (optional LLM):** proposes English words and role tags offline or in batch.
- The LLM is **never** part of the runtime organism.

Grammar can wait. **Coverage first:** grow `en_roles.tsv`, then refine.

## File format (`en_roles.tsv`)

```text
# word<TAB>role
# roles: who verb what where when how adj link
I	who
see	verb
light	what
```

ASCII words only for TTS plant. Duplicates ignored on load.

## Commands

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"

# Free offline expand (no network) — seeded role lists
python run_lexicon_teacher.py --offline --target 500

# Local Ollama teacher (default LLM path — free, on your PC)
python run_lexicon_teacher.py --list-models
python run_lexicon_teacher.py --llm --target 800
python run_lexicon_teacher.py --llm --model qwen3.5:4b --target 1000

# Optional: OLLAMA_HOST / OLLAMA_MODEL env overrides
# $env:OLLAMA_MODEL = "fsot-gemma:latest"

# Mind loads TSV at boot of english / mind modes (if present)
```

**Do not** pay for cloud APIs for this. Teacher = Ollama (or offline lists).  
Remote provider flags exist only as an escape hatch; default is local.

## How big a lexicon for “fluid”?

| Goal | Productive words (rough) | Notes |
|------|--------------------------|--------|
| Survival chat | **~500** | who/verb/what core — we are here (~450 roles) |
| Everyday fluid | **~2,000** | most daily life without rare topics |
| Strong productive | **~5,000** | comfortable general speech |
| Adult *receptive* | **20,000+** | understanding more than speaking |

Grammar is separate. Grow **coverage first**, polish grammar later.  
Human child path: concrete words → social → abstract; practice by speaking and hearing self.

## Distill (definition + usage) via Ollama

```powershell
python run_lexicon_distill.py --report
python run_lexicon_distill.py --limit 30 --model gemma:7b
```

Writes `en_distill.jsonl` (word, role, definition, usage, related, hint).

## Practice (student learns by doing)

```text
fsot_mind practice
```

Utter → TTS → re-ingest own phrase (self-hear) → encode episode. Fluency score from recovery + frame RT + TTS.
