# Speech / self-articulation reconnect path

**Status:** Intact in tree — **not removed** by wet stack / intel-loop / frontier work.  
**When:** Reconnect as first product focus **after** intelligence frontiers land (multi-day, curiosity, ladder-in-loop).

## What you had that worked

The connected organism already closed the **speaker → mic → self-hear → retune** loop:

| Piece | File / mode |
|-------|-------------|
| Live mind | `mind_live_fixed.zig` · `fsot_mind mind` |
| Self-audio loop | `self_audio_loop.zig` |
| Host mic / display | `host_senses_windows.zig` |
| TTS plant | `host_tts_fixed.zig` · English lexicon |
| Formant organ | `speech_organ_fixed.zig` |
| Language practice | `language_practice_fixed.zig` · `fsot_mind practice` |
| Speakers smoke | `fsot_mind speakers` |

`LiveConfig` defaults (still in code):

- `speakers = true`
- `self_hear = true`
- `english_tts = true`
- `speak_every` / settle after DAC for room echo

Metrics already reported by live mind: `n_speaks`, `n_self_hear`, `n_self_air`, `n_english_say`, `n_tts_spoken`, `last_self_match`.

## Why we parked it briefly

Recent work locked **substrate intelligence** (channels, neuromod, sleep, claimability, multi-day curiosity) without free parameters. Speech was already fluent enough that it did not need re-proving during that climb — but it remains the **body interface** for a chatting organism.

## Reconnect plan (do not invent a new stack)

1. Run `fsot_mind mind` (or `BOOT_MIND.cmd`) with speakers + mic on Windows host.  
2. Confirm self-hear match rate and EN_SAY / TTS counts.  
3. Couple **intel-loop / frontier** teach tags → **speech organ meaning** (say what was just claimably learned).  
4. After sleep cycle: verbal re-probe (speak answer → self-hear → bank check).  
5. Keep machine language as native tongue; English as codec (doctrine unchanged).

## Modes that must stay green

```text
fsot_mind practice     # utter → TTS → self-hear → encode
fsot_mind english      # lexicon + TTS
fsot_mind mind         # full connected plant
fsot_mind speakers     # DAC smoke
```

If any of these regress, fix **before** adding new speech features.

## Doctrine

Fluid self-articulation is **embodiment**, not the FSOT scalar law.  
Intelligence frontiers (this doc’s sibling work) make **what** is sayable claimable; speech makes it **hearable and self-correcting**.
