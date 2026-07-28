# Bio-fidelity refine cycle

## Discipline

```text
score all layers
  → among scores < threshold, pick HIGHEST (closest under the bar)
  → run tests
  → log
  → apply FSOT-lawful fix
  → retest
  → log
  → repeat
```

Default **threshold = 70%**.

## Run

```powershell
python run_refine_cycle.py --score-only
python run_refine_cycle.py --threshold 70
python run_refine_cycle.py --domain bio --threshold 70    # wet-lab / sensory / learning first
python run_refine_cycle.py --domain capability            # frontier gaps only
python run_refine_cycle.py --layer retina_like_decode
```

**`--domain bio`** climbs Allen rates, E/I, thalamic gate, retina/cochlea, fly motifs,
EEG/SME, episodic memory, information accuracy, cross-modal, language — **before**
capability frontier items (pixel-ID / curriculum / monologue).

## Artifacts

| Path | Role |
|------|------|
| `data/refine_cycles/cycles.jsonl` | append-only history |
| `data/refine_cycles/LATEST.md` | last cycle human summary |
| `artifacts/refine_cycle_last.json` | machine snapshot |
| `data/results/REFINE_CYCLE.md` | last report |

## Layers scored

Cell-class rates · E/I motifs · thalamic gate · retina-like decode · episodic/SME · cross-modal · language · free monologue · self-curriculum · open-world pixel-ID.

## Selection rule (user discipline)

Among scores **below** threshold, pick the **highest** (closest under the bar first). Then:

```text
test → log → fix → retest → log → next target
```

## Soft ceilings (honesty)

| Layer | Typical ceiling until… |
|-------|------------------------|
| retina_like_decode | 78 — RF cascade (local ON/OFF, fine orient, DoG) |
| language_dialogue | 72 — SRT bind + trit + lexicon; open-vocab VL unclaimed |
| free_monologue | 72 — multi-turn memory monologue; free LLM monologue unclaimed |
| self_curriculum | 78 — gap plan + **short-horizon unit chain** (`run_curriculum_execute.py`) |
| open_world_pixel_id | **~70+** real-media entity ID; caption↔pixel co-occurrence stored; **named-character claim** still unclaimed |

## Snowball path

```text
short_horizon  (atom: encode docs+media → recall in minutes)
      ↓
vision_caption_bind  (subtitle midpoints ↔ RF features → name clusters)
      ↓
curriculum_execute  (gap plan → chain of short_horizon units → Δ metrics)
```

```powershell
python run_short_horizon_learn.py --docs 4 --videos 5 --frames 12
python run_curriculum_execute.py --steps 3 --docs 2 --videos 2
python run_wetlab_accuracy_battery.py
```

## FSOT rule

Fixes may only use **seeds / structure** — never free-fit \(S\) or silent constants for wet-lab match.
