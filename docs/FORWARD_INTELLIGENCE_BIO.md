# Forward intelligence — biological direction

**Date:** 2026-07-30  
**Status:** Implemented on Zig Fixed lattice (not LLM chain-of-thought).

This is the path after wet stack + math stamp: **process-accurate intelligence mechanisms**.

## Stack

| Layer | File | Role |
|-------|------|------|
| Neuromodulators | `neuromod_fixed.zig` | DA / ACh / NE / 5-HT first-order ODEs |
| Offline consolidate | `sleep_replay_fixed.zig` | Wake encode → rest → NREM → replay+STDP |
| Multi-hop claimability | `claimability_fixed.zig` | 1–3 hop grounded chains ≥95% |
| Combined gate | `fsot_mind intel-bio` | All three |

## Biology (honest process scale)

| Mechanism | Biology | Our model |
|-----------|---------|-----------|
| ACh high at encode | Basal forebrain / attention | `wake_encode` tonic → encode gain |
| LC NE arousal | Locus coeruleus | External drive gain |
| DA tagging | VTA/SNc reward / salience | Pulses on encode + replay STDP η |
| 5-HT quiet | Raphe | Elevated in NREM; rest quiet gain |
| Sleep replay | Hippocampal–cortical reactivation | Soft fingerprint replay + STDP |
| Sigma proxy | Spindle-band association | `sigmaProxy(HT, low ACh, reactivate)` |
| Claimability | Premises must support claim | Every hop bank-grounded + taught answer |

**Not** wall-clock PC sleep. Schedule is **model-ms** (same doctrine as retention stage).

## FSOT coupling

- Time constants / scales: φ, ψ_con, η_eff (seed-derived)  
- STDP η: `1 + 0.8·DA + 0.4·ACh`  
- Encode gain: `(1+0.7·ACh)·(1+0.5·NE)`  
- Zero free LSQ parameters on the neuromod law path  
- Lean: `FSOTNeural.IntelBio` · folded into `scientific_panel_ok`

## Closed loop (train → sleep → prove)

Mode: **`intel-loop`** (`train-sleep-prove`, `loop`)

```text
TRAIN (wake_encode ACh/NE + DA tags)
  → SPACED RETRIEVAL (prediction-error DA on hit/miss)
  → PROBE_PRE (claimability + episodic top-1)
  → DELAY (wake_rest)
  → SLEEP (NREM + replay STDP)
  → PROVE (claim post + mem post + transfer chains)
```

Extras:

| Piece | Role |
|-------|------|
| Prediction-error DA | Correct retrieve → DA pulse; miss → NE reorient + re-encode |
| Working memory | 4 Fixed slots (limited capacity), decay over rest |
| Transfer probe | Cross-domain 2-cue items after sleep (≥80%) |

## Run

```powershell
cd embodiment\zig
# or product repo
$out = "$env:TEMP\fsot_mind_live.exe"
zig build-exe -OReleaseFast "-femit-bin=$out" --name fsot_mind_live src/main_mind.zig -lgdi32 -luser32 -lwinmm
& $out neuromod
& $out sleep          # consolidate / replay
& $out claim          # multi-hop claimability
& $out intel-bio      # full stack
& $out intel-loop     # closed train→sleep→prove organism cycle
```

Expect:

```text
FSOT_NEUROMOD PASS
FSOT_SLEEP_REPLAY PASS / FSOT_CONSOLIDATION_OK
FSOT_CLAIMABILITY PASS / FSOT_MULTI_HOP_INTEL_OK
FSOT_INTEL_BIO_STACK PASS
FSOT_INTEL_LOOP PASS / FSOT_TRAIN_SLEEP_PROVE_OK
```

## How this ties to curriculum depth

```text
teach STEM/literacy (ladder/depth bank)
  → encode under ACh/NE (+ DA tag)
  → multi-hop claim chains (claimability)
  → offline replay consolidates W + fingerprints
  → re-probe retention + understand paraphrases
```

Wet cascade (channels → molecular → glia → STDP) remains the **synaptic** substrate;  
neuromod + sleep are the **systems-level** intelligence schedule on top of it.

## Lean stamp

`formal/FSOTNeural/IntelBio.lean` — 4 neuromods, 5 phases, replay+STDP, claim ≥95%, 0 free params.
