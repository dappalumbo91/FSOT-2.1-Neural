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

# Free offline expand (no API) — frequency / role seeds
python run_lexicon_teacher.py --offline --target 500

# Optional teacher LLM (xAI / SpaceXAI) — proposes new words into TSV
# $env:XAI_API_KEY = "..."
python run_lexicon_teacher.py --llm --target 800

# Mind loads TSV at boot of english / mind modes (if present)
```

## Fluency later

Score: known-word rate, encode/retrieve of machine frames, TTS self-loop — not “chat like GPT.”
