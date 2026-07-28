# Self-modulation & extended host senses (v0.7)

The computer is the organism’s **body**. Senses and homeostasis must adapt at
runtime — not be hard-coded to one machine.

## Afferent map (scientific routing)

| Sense | Module | Target region | Role |
|-------|--------|---------------|------|
| CPU / RAM / disk / temp / GPU | `hardware_body.sample_metrics` | **thal** (`SYS_METRIC`) | Autonomic plant |
| Network I/O rate | `host_senses.sample_net_util` | **thal** (`NETWORK`) | Circulatory traffic |
| Keyboard / mouse | `note_hid_*` (console events) | **sens** (`HID`) | Exteroception |
| Engine log stream | `note_log_line` | **assoc** (`LOG`) | Structured language stream |
| Audio peak (optional) | `sample_audio_peak` | **sens** (`AUDIO`) | Off by default |

Missing backends → strength 0 / omit. **Same mind, different bodies.**

## Self-modulation (POOF / SUCTION)

`fsot_nuron/self_modulation.py` maps plant load + own firing into scales:

| Mode | Condition | Effect |
|------|-----------|--------|
| **dampen** (POOF) | high CPU/mem or high fire | lower `stim_scale`, optional `n_units_cap` |
| **explore** (SUCTION) | spare capacity + quiet | raise stim slightly, finer `dt` preference |
| **balanced** | mid-range | homeostatic 1.0 |

Gains use **archive seeds only** (`SEEDS.poof`, `SEEDS.suction`, φ-gate) — no free-fit PID.

## Multi-region visual

Console Visual tab builds `FSOTBrainDesign`:

- `ai_efficient` — ~32 units (default portable UI)
- `wetware_ref` — ~64 units when host recommends large `n_units`

Layout hubs: **thal · sens · assoc · hipp** with long-range projections as edges.

Live loop:

1. Host senses → `SensoryBus` packets  
2. Thalamic burst + cortical base drive  
3. Bus overlay into regional units  
4. `modulate_from_metrics` scales stim  
5. Every N steps → `append_live_tick` → Obsidian `05_Dynamics/LIVE.md`

## Live second brain

```text
artifacts/obsidian_vaults/FSOT_Neural_Live/
  00_Home.md
  05_Dynamics/LIVE.md          # markdown table of ticks
  05_Dynamics/live_ticks.jsonl # machine-readable
```

Open the folder as an **Obsidian desktop vault** (offline graph / note stream).

## API sketch

```python
from fsot_nuron.hardware_body import discover_hardware, sample_metrics
from fsot_nuron.sensory.host_senses import sample_host_senses
from fsot_nuron.self_modulation import modulate_from_metrics
from fsot_nuron.sensory.bus import SensoryBus

hw = discover_hardware()
m = sample_metrics(hw)
snap = sample_host_senses(metric=m)
mod = modulate_from_metrics(m, hw, fire_frac=0.1)
bus = SensoryBus()
for p in snap.packets:
    bus.push(p)
```
