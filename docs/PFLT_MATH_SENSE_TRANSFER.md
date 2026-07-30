# PFLT → math: sense-identity bindings (not drip schemas)

**Date:** 2026-07-29  
**Authority twin:** `I:\pflt` Protofluid Language Translator  
**Pin doctrine:** form → SENSE → form/formula · densify offline · no free LLM core

---

## What you pointed at (and what we had been doing wrong)

| PFLT actually is | What we were doing on GSM8K |
|------------------|-----------------------------|
| **~15.8k senses · ~103k form bindings** | Hand-coding ~6 schemas per chat turn |
| `aqua → SENSE_water → water` | Regex island per problem family |
| Mass densify packs (`densify_lexicon` 17k+) | “Next steps” drip that burns budget |
| `chew_climb` mines misses → **binds**, not cloud NMT | Paying for multi-hop analysis every round |

Vision lock (`I:\pflt\docs\VISION_SENSE_IDENTITY.md`):

> Surface forms are labels. **Sense is identity.**  
> Bind once; resolve instantly forever under law.

That is the climb. Not another six schemas per session.

---

## PFLT translation process (the real product path)

```
surface form  →  SENSE_id  →  surface form (target language)
     aqua     →  SENSE_water →  water / Wasser / eau / 水
```

Modules:

| Piece | Path | Role |
|-------|------|------|
| Sense spine | `sense_interlingua.py` | form↔sense index + `translate()` |
| CLI | `pflt_sense_translate.py` | seconds, not hours |
| Mass lexicon | `PFLT_FSOT_2_1_aligned.pul_terms` (~15k) | form → gloss |
| Densify | `data/chew_climb/densify_lexicon.json` (~17k) | miss → bind |
| Gold mass | `expanded_gold.jsonl` / Ada `train_mass.tsv` | hundreds of MB of **pairs** |
| Climb | `chew_climb.py` / `fast_climb` | score → mine → densify → repeat **local** |

Live probe on this machine:

```
n_senses:           15 801
n_form_bindings:   103 208
n_index_keys:      102 498
langs:             100+
```

Example:

```
aqua manus lingua (la→en)
  aqua  → SENSE_water    → water
  manus → SENSE_hand     → hand
  lingua→ SENSE_language → language
```

**Not NMT. Not Q→A stuffing.** Unresolved forms stay unresolved (honest).

---

## Math twin (now in nuron)

Same spine, math domain:

```
language cue  →  OP_SENSE / SCHEMA_SENSE  →  formula + strategy
"altogether"  →  OP_add                   → total = a+b+…
"half of X"   →  OP_half + BIND_referent  → half(binding[X])
```

| Piece | Path |
|-------|------|
| Interlingua | `fsot_nuron/math_sense_interlingua.py` |
| Densify CLI | `scripts/densify_math_sense_bindings.py` |
| Pack | `data/math_sense/binding_pack.json` |
| Densify | `data/math_sense/densify_bindings.json` |
| Wired into | `math_rules.detect_strategies()` |

Sources bulk-loaded (PFLT `_build` order):

1. Core OP / SCHEMA sense tables (multi-form labels)  
2. Extra explicit form↔sense pairs  
3. Live `ARITH_RULES` + `LANGUAGE_MAPS`  
4. `BINDING_RULES` (BIND-*/SCHEMA-*)  
5. **Math-generator MASTER rulebook (~1520 RB_* senses)**  
6. densify pack on disk  
7. Optional **PFLT** number/quantity forms (`I:\pflt` SenseInterlingua)

### First densify stats (this machine)

| Metric | Value |
|--------|------:|
| Senses | **~1790** |
| Form bindings | **~14 480** |
| Index keys | **~6100** |
| RB (rulebook) senses | **1520** |
| PFLT-imported forms | **~180+** (filtered) |

Rank on collision (so dumps do not clobber school ops):

`OP > SCHEMA > BIND > RULE > DEN > PFLT > RB`

Stop-forms (`what`, `with`, `many`, …) never claimed by RB/PFLT.

---

## How this expedites the GSM8K climb (budget)

| Old path | New path |
|----------|----------|
| Chat: invent 3–6 schemas | One local densify: **thousands of form→sense binds** |
| Re-analyze fails every turn | `densify_from_gsm8k_cues` + sense scan |
| Pay for reasoning each drip | Pay once for wiring; climb loop is local Python |

**Still required for full accuracy:** executable SCHEMA solvers (state machines) for multi-hop.  
Bindings alone do not invent arithmetic — they **route language to the right law**, exactly as PFLT routes `aqua` to water without generating prose.

Executor path stays:

1. Pure AR identities  
2. `solve_with_binding` (referent multi-hop)  
3. Keyword templates  
4. Strategy detect now **reads mass sense index** (PFLT-style)

---

## Commands (local, no API)

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH="I:\fsot nuron"
$env:FSOT_STANDALONE="1"

# Build / refresh thousands of math sense bindings
python scripts/densify_math_sense_bindings.py --smoke

# Existing rule drills (still ≥95% gate)
python scripts/run_math_rules_teach.py --gsm8k-practice 300 --test 300
```

PFLT itself (reference):

```powershell
cd I:\pflt
python pflt_sense_translate.py --smoke
python pflt_sense_translate.py "aqua manus lingua" --src la --tgt en
```

---

## Honesty

- **Bindings** = teachable form↔sense tables (observer densify).  
- **Law** = fixed formulas / schemas (not rewritten by densify).  
- **No** stuffing GSM8K answers into a retrieval index.  
- **No** cloud NMT/LLM as the math core.

This is the same product philosophy that got PFLT to ~99.99% form→gloss on inventory: **bind meaning at scale**, then resolve.
