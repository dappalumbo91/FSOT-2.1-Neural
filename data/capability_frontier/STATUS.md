# Capability frontier — live status

Updated: `2026-07-29T12:22:21.763093+00:00`  
Git: `560ca319d9c2`  
Experiment: `visual_individual_identity`

| Claim | Status | Note |
|-------|--------|------|
| **Open-world pixel identity** (`open_world_pixel_identity`) | `partial` | VIU-first: look→individual then name bind; re-id=0.689 chance≈0.152 unique_name=0.333 (name-bag franchise protocol retired as primary) |
| **Self-directed curriculum design** (`self_directed_curriculum`) | `probing` | run_autonomous_learn.py chews discovered docs/media with fixed heuristics; not self-authored curriculum |
| **LLM-style free monologue** (`free_monologue`) | `partial` | plain_english / recall_plain_english are compositional expansions, not free generative monologue |

See [`docs/CAPABILITY_FRONTIER.md`](../../docs/CAPABILITY_FRONTIER.md) for gates.

```json
{
  "pixel_id_top1": 0.6888888888888889,
  "pixel_id_chance": 0.15151515151515152,
  "n_characters": 26,
  "n_heldout_clips": 45,
  "tutor_ablated": true,
  "viu_reid_top1": 0.6888888888888889,
  "unique_name_top1": 0.3333333333333333,
  "n_viu": 33
}
```
