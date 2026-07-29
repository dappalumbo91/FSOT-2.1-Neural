# Grade-school depth & claimability

## Goal

Do **not** push grades higher until **understanding** of the foundation is claimable:

> Given natural STEM/literacy questions about what we taught, the mind answers correctly ≥95% — even when the wording is **not** the exact bank key.

**No history track.** Curriculum stays truth-oriented STEM + literacy (math, science, reading/writing mechanics). History is deferred on purpose.

## Architecture (biological process)

```text
natural question (English)
  → tokenize / stop-filter / role-aware cues   (lexicon codec)
  → math compose if operators present           (calculate)
  → unwrap wrappers ("what is the answer to: …")
  → exact bank match if any
  → bag-of-words / key-cover retrieval          (declarative memory)
  → bind answer token
  → (later) episodic hop + TTS plant
```

This is **not** an LLM. It is the Fixed lattice + taught bank + process steps already owned by the organism path (`inject → ticks → retrieve → bind`).

## Gates (straight-A)

| Gate | Command | Meaning |
|------|---------|---------|
| Ladder PK→G8 | `fsot_mind ladder` | Domain bars math/sci/lit + **MNIST ≥95%** |
| MNIST vision | `fsot_mind mnist` / `python run_mnist_gate.py` | Real held-out digit ID |
| **Depth understand** | `fsot_mind depth` | Held-out **paraphrases** of taught facts ≥95% |

Build exam (held-out natural Qs, never exact keys):

```powershell
python run_grade_depth.py
cd embodiment\zig
zig build -Doptimize=ReleaseFast
.\zig-out\bin\fsot_mind.exe depth
```

## What claimability means (honest)

**Claimable when all gates green:**

- On the **open curriculum we taught** (PK–G8 STEM/literacy), the mind can answer **reworded** questions, not only cue strings.
- Vision digits: real MNIST held-out ≥95%.
- Process is substrate-native (Zig Fixed / FSOT doctrine).

**Not yet claimable:**

- Arbitrary grade-school chat outside the bank (untought facts).
- Long free-form explanations without further generation/codec work.
- History / contested human narrative corpora (out of scope by design).

## Expansion order (do not invert)

1. **Depth** on current foundation (this doc) until paraphrase + multi-hop gates stay green.  
2. **Density** inside bands (more paraphrases, word problems, multi-hop science paths).  
3. Only then **higher grades / SOTA breadth**.

Genetic / biological accuracy of the lattice remains the root constraint: every new capability must still run as organism process, not a bolted-on LLM.
