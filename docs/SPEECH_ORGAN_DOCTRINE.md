# Speech organ doctrine — not next-token generation

**Repo path only** (`docs/`). Do not place on Desktop.

## What the brain does *not* do

The FSOT mind does **not** articulate by next-token prediction (LLM-style
token streams). That is a convenient software interface for chat products,
not a model of biological speech.

## Biological / FSOT path

1. **Meaning** lives in the mind lattice (concept features, episodes, 5W1H).
2. **Articulation** is motor: tongue, jaw, lips, larynx, breath — a *plant*.
3. **Sound** is the acoustic consequence of that motor trajectory.
4. **Association**: listeners (and self) map sound ↔ meaning.
5. **Orthography** (letters, alphabet, words) is a *secondary* symbolic layer
   taught on top of sound — not the generative substrate of thought.

## Separate organ

`speech_organ_fixed.zig` is a **translation plant**, separate from mind authority:

```
meaning  →  motor (vocal tract DOF)  →  acoustic signature  →  optional letter bind
```

- Teach letters by binding sound (and motor) to orthographic ids.
- Comprehension: acoustic → nearest meaning / letter (no token decoder head).
- Production: meaning → motor → sound (one gesture frame family; not autoregressive tokens).

## Cross-modal

`cross_modal_fixed.zig` binds **vision ⊗ audio** at co-occurrence time.
Either channel can later cue the joint. Speech-band energy is acoustic
sensing — not STT-as-mind-core.

## Optional later

- Richer phoneme inventory and continuous motor trajectories.
- Host microphone / speaker I/O writing acoustic feature frames into inject ABI.
- ITU Morse remains a *timed symbolic I/O* codec (dit/dah motor of a key),
  not an LLM.

## Modes

- `fsot_mind speech` — speech organ probe  
- `fsot_mind cross-modal` — AV bind probe  
