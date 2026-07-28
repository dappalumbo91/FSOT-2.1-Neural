# Capability frontier — what we do **not** claim (yet)

These are **tracked gaps**, not failures. We log them on every major climb
so progress is honest and comparable.

**Live status file:** [`data/capability_frontier/STATUS.md`](../data/capability_frontier/STATUS.md)  
**Append-only ledger:** `data/capability_frontier/frontier_runs.jsonl`  
**Last snapshot:** `2026-07-28T19:04:20.716861+00:00` · git `88c1c6592f74`

## Status vocabulary

| Status | Meaning |
|--------|---------|
| `unclaimed` | Not asserted; no green gate |
| `probing` | Experiment exists; not claimable |
| `partial` | Real capability, wrong shape for the full claim |
| `claimed` | Gate passed (explicit) |

---

## Open-world pixel identity

**ID:** `open_world_pixel_identity`  
**One-liner:** Recognize a specific entity (e.g. Jake) from pixels alone  
**Current status:** `unclaimed`  
**Note:** AV clusters + tutors exist; pixel-only identity not measured/green

### We do **not** claim

We do not claim the system can identify Jake (or any character) from pixels alone without path/title/subtitle/lexicon tutors.

### What counts as progress

- Recurring visual clusters co-occur with caption names across episodes
- Held-out clip (no path hints, no subtitles) retrieves correct name above chance
- Confusion matrix over ≥3 characters with top-1 > chance by clear margin

### Claim gate (when we may flip to `claimed`)

Held-out silent clips of ≥3 characters: top-1 name accuracy ≥ 0.70 with no path/title/subtitle/lexicon injection at test time; multi-seed.

### Metrics keys

`pixel_id_top1`, `pixel_id_chance`, `n_characters`, `n_heldout_clips`, `tutor_ablated`

### Latest metrics

```json
{
  "pixel_id_top1": null,
  "pixel_id_chance": null,
  "n_characters": 0,
  "n_heldout_clips": 0,
  "tutor_ablated": null
}
```

---

## Self-directed curriculum design

**ID:** `self_directed_curriculum`  
**One-liner:** Choose its own learning sequence without human ordering  
**Current status:** `probing`  
**Note:** run_autonomous_learn.py chews discovered docs/media with fixed heuristics; not self-authored curriculum

### We do **not** claim

We do not claim full self-directed curriculum design. Autonomous learn currently chews what it finds under fixed discovery heuristics, not a self-authored multi-step curriculum.

### What counts as progress

- System proposes next media/doc targets from memory gaps
- Revisits weak symbols preferentially
- Curriculum plan logged before execution and improves a held metric

### Claim gate (when we may flip to `claimed`)

Without human file lists: agent writes a multi-step plan, executes it, and improves a pre-registered metric (e.g. recall@k or pixel_id_top1) vs fixed-order baseline on the same budget.

### Metrics keys

`curriculum_steps_planned`, `curriculum_self_authored`, `gap_driven_fraction`, `metric_delta_vs_fixed_order`

### Latest metrics

```json
{
  "curriculum_steps_planned": 0,
  "curriculum_self_authored": false,
  "gap_driven_fraction": 0.0,
  "metric_delta_vs_fixed_order": null
}
```

---

## LLM-style free monologue

**ID:** `free_monologue`  
**One-liner:** Open-ended generative language like a large language model  
**Current status:** `partial`  
**Note:** plain_english / recall_plain_english are compositional expansions, not free generative monologue

### We do **not** claim

We do not claim LLM-style free monologue. Output is compositional regurgitation from lexicon + stream stats + stored episodes (compact trinary/machine codes re-expanded to English).

### What counts as progress

- Longer multi-sentence recall grounded in stored episodes
- Novel but source-faithful paraphrases of chewed material
- Chat-like multi-turn grounded in organism memory (not external LLM)

### Claim gate (when we may flip to `claimed`)

Multi-turn dialogue (≥5 turns) answering open questions about chewed media/docs using only organism memory + FSOT pathways; human rating groundedness ≥ 0.8 and zero external LLM dependency.

### Metrics keys

`monologue_mode`, `max_coherent_sentences`, `groundedness_score`, `external_llm_used`, `n_turns`

### Latest metrics

```json
{
  "monologue_mode": "compositional_regurgitation",
  "max_coherent_sentences": null,
  "groundedness_score": null,
  "external_llm_used": false,
  "n_turns": 0
}
```

---

## Related (claimed or green elsewhere)

These are **not** the three gaps above; they *are* things we already track:

- Standalone pin D1D38A · Allen class rates · AV co-stream bind · subtitle dialogue
- Document reading (page text → trinary) · compositional plain-English recall
- Autonomous chew of discovered files (fixed heuristics, not full curriculum design)

## How to log

```powershell
python run_capability_frontier.py              # snapshot + print
python run_capability_frontier.py --history 10
```

Call from runners:

```python
from fsot_nuron.capability_frontier import log_frontier
log_frontier(experiment='autonomous_learn', related_metrics={...}, notes='...')
```
