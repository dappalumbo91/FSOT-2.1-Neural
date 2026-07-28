# Biologically equivalent sensory system (FSOT-lawful)

**Goal:** computer-native afferents that **map to mammalian sensory organization**  
and **inject through FSOT seeds only** — not free transfer functions, not an LLM.

**Honesty (from [`BIO_ACCURACY.md`](BIO_ACCURACY.md)):**  
We claim **biological fidelity under named mappings and gates**, not that silicon *is* living tissue.

---

## 1. Anatomical map (simplified)

```text
VISION file/stream  →  decode (luma/RGB/hue/grid/motion)
                    →  thal (LGN-like relay, lower gain)
                    →  sens (early visual cortex proxy)

AUDIO file/stream   →  spectrum / speech-band
                    →  thal (MGN-like)
                    →  sens (auditory cortex proxy)

CROSS-MODAL bind    →  assoc (binding / “what goes with what”)
SPEECH / subtitles  →  assoc + hipp (language + episodic)
DOCUMENTS (read)    →  assoc + hipp (same language/episodic path)
SYS_METRIC / plant  →  thal only (interoception / autonomic)
HID                 →  sens + thal (somatosensory proxy)
```

Multi-region brain (already genetic / motif-aware):

| Region | Role |
|--------|------|
| **thal** | Relay + homeostatic / attentional gate |
| **sens** | Early modality-specific cortex |
| **assoc** | Binding, language, cross-modal |
| **hipp** | Episodic tag / memory |

Long-range projections: `thal→sens→assoc↔hipp` (see `brain_architecture.py`).

---

## 2. FSOT appropriateness

| Rule | How we enforce it |
|------|-------------------|
| \(S=K(T_1+T_2+T_3)\) unchanged | Sensory never refits S; optional `couple_S` only *gates* strength |
| Zero free pathway gains | `pathway_gain` uses φ-gate, 1/φ relay, poof/suction intero, ψ_con hipp |
| Cell-type biology | Feedforward inject **prefers excitatory** units |
| Time | Model-ms still owns rates; wall-clock is separate ([`BIO_ACCURACY.md`](BIO_ACCURACY.md) §0) |
| Machine language | Text/subtitles/docs → UTF-8→trits (body code), not next-token LM |

Code: `fsot_nuron/sensory/bio_pathways.py` · `bus.py` (`bio_route=True` default).

---

## 3. Self-check

```powershell
python run_bio_sensory_check.py
```

Gates:

1. Free parameters on pathway law = **0**  
2. Consciousness gate = φ/(1+φ)  
3. All modalities have a route  
4. Relay gain < primary gain (thalamic filter)  
5. Interoception targets **thal**  
6. Vision/audio primary **sens**  
7. Optional: fold diagnostics pin OK  

---

## 4. Relation to wet-lab accuracy

Sensory **routing** is motif-level biology.  
**Spike timing / class rates** remain Allen-locked via scalpel / precision climb.  
Do not trade Allen gates for prettier vision demos.

---

## 5. Capability frontier (still unclaimed)

Pixel-only identity (“that is Jake”), full self-curriculum, free monologue:  
[`CAPABILITY_FRONTIER.md`](CAPABILITY_FRONTIER.md) — tracked separately.

---

## 6. Design intent (one sentence)

**Build the computer’s eyes, ears, body sense, and reading path so they land on the same kind of regional architecture evolution used for mammals — driven by FSOT seeds, scored where wet-lab numbers exist.**
