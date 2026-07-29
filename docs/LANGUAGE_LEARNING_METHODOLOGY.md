# Language learning methodology (reproducible)

**Branch:** `experiment/fsot-fixed-precision` (monorepo) · public Zig: `fsot-neuron-zig`  
**Authority:** Fixed lattice mind + machine language (TritWord / FSOT frames).  
**Teacher (Ollama or offline lists):** builds capability only — **not** part of the runtime organism.

---

## 1. Doctrine (do not invert)

| Layer | Owns | Does not own |
|-------|------|----------------|
| **Student mind (Zig)** | Encode / retrieve / choose / speak / self-hear / apply facts | Live LLM calls |
| **Machine language** | Native tongue (frames, tokens, trits) | English phonetics |
| **Lexicon codec** | Word ↔ role ↔ machine token | Free chat |
| **Teacher** | Grow TSV/JSONL offline | Runtime intelligence |
| **TTS plant** | Human-hearable English | Mind authority |

LLM / Ollama = **lab scalpel** to fill dictionaries and fact cards faster.  
If the teacher vanishes, the mind still runs on committed artifacts under `data/`.

---

## 2. Reproducible pipeline (order)

```text
[A] Lexicon roles     → data/lexicon/en_roles.tsv
[B] Optional distill  → data/lexicon/en_distill.jsonl  (definition, usage, hint)
[C] Curriculum facts  → data/curriculum/pk_k_g1/facts.jsonl
[D] Curriculum problems → data/curriculum/pk_k_g1/problems.jsonl
[E] Student practice  → fsot_mind practice | grade | mind
```

### A — Lexicon (productive words)

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"

# Free offline (bulk TSV seeds)
python run_lexicon_teacher.py --offline --target 2000

# Local Ollama only (no paid API) — optional accelerator
python run_lexicon_teacher.py --list-models
python run_lexicon_teacher.py --llm --model gemma:7b --target 2000
```

**Seeds (committed, free):**

- `data/lexicon/preschool_bulk.tsv`
- `data/lexicon/g1_productive_bulk.tsv`
- embedded list in `embodiment/zig/src/lexicon_en_fixed.zig`

**Runtime load:** Zig `tryLoadDefaultRoles()` reads `data/lexicon/en_roles.tsv` (paths tried relative to cwd + fixed monorepo path).

### B — Distill usage (optional depth)

```powershell
python run_lexicon_distill.py --report
python run_lexicon_distill.py --limit 50 --model gemma:7b
```

Artifact: `data/lexicon/en_distill.jsonl`  
Fields: `word`, `role`, `definition`, `usage`, `related`, `hint`, `teacher`.

### C/D — PK → K → Grade 1 knowledge (not ugga-dugga)

```powershell
python run_curriculum_pk.py --ensure-lexicon --target 2000 --report
python run_curriculum_pk.py --expand-facts 15 --model gemma:7b   # optional Ollama
python run_curriculum_pk.py --report
```

Committed seeds:

- `data/curriculum/pk_k_g1/facts.jsonl`
- `data/curriculum/pk_k_g1/problems.jsonl`

### E — Student gates (Zig, no teacher online)

```powershell
cd "I:\fsot nuron\embodiment\zig"
# build (example)
zig build-exe -OReleaseFast "-femit-bin=$env:TEMP\fsot_mind_live.exe" --cache-dir "$env:TEMP\fsot_zig_cache_live" --name fsot_mind_live src/main_mind.zig -lgdi32 -luser32 -lwinmm

$m = "$env:TEMP\fsot_mind_live.exe"
& $m machine-lang          # native tongue round-trip
& $m machine-lang-stress   # 1000-frame stress
& $m english               # lexicon + TTS
& $m practice              # utter → TTS → self-hear → encode
& $m grade                 # teach facts → quiz → solve problems
& $m mind                  # full live organism
```

| Mode | What it proves |
|------|----------------|
| `machine-lang` | Generate = understand machine frames |
| `practice` | Self-hear own English phrases |
| `grade` | Apply facts/problems (knowledge, not labels) |
| `mind` | Connected organism + EN_SAY + TTS |

---

## 3. Size targets (honest)

| Milestone | Productive lexicon | Knowledge |
|-----------|-------------------|-----------|
| Survival | ~500 | preschool facts |
| Everyday fluid | **~2,000** | K–G1 facts + problems |
| Strong | ~5,000 | later grades |
| Receptive adult | 20k+ | not required for fluid *use* |

**Fluency test = use language on facts and problems**, not “word means word.”

Shallow is OK early: deepen curriculum + distill usage while growing toward 2000+.

---

## 4. Git / reproducibility rules

1. **Commit artifacts that the student needs:** `en_roles.tsv`, bulk TSVs, curriculum JSONL, distill JSONL when stable.  
2. **Do not commit:** `$out`, `zig-out` locks, `__pycache__`, huge EEG dumps unless already tracked policy.  
3. **Teacher is disposable:** regenerable from Ollama + scripts; student must run from committed files alone.  
4. **Record methodology here** and in `data/lexicon/README.md` when the pipeline changes.  
5. **Push** monorepo branch `experiment/fsot-fixed-precision` and public `fsot-neuron-zig` `main` after green gates.

### Remotes

- Monorepo: `https://github.com/dappalumbo91/FSOT-2.1-Neural.git`  
- Product Zig: `https://github.com/dappalumbo91/fsot-neuron-zig.git`

---

## 5. What “success” looks like (gates)

- `FSOT_MACHINE_LANG PASS` / stress PASS  
- `FSOT_ENGLISH PASS` / `FSOT_TTS_SPOKEN_OK`  
- `FSOT_LANGUAGE_PRACTICE PASS` / `FSOT_SELF_HEAR_LANGUAGE_OK`  
- `FSOT_GRADE_PRACTICE PASS` / `FSOT_KNOWLEDGE_APPLY_OK`  
- `FSOT_LIVE_MIND PASS` when full plant available  

---

## 6. Next expansions (same methodology)

1. Lexicon → 2000 with repeated `--llm --target 2000` (local Ollama).  
2. Distill definitions for all role words (`--limit` batches).  
3. Expand `facts.jsonl` / `problems.jsonl` (hand + optional Ollama).  
4. Deeper apply: multi-step problems, still Fixed mind + codec.  
5. Grammar templates last.

**Point:** capability is built into **committed data + Zig student**, not into keeping a teacher online.
