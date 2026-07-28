# Capability frontier — live status

Updated: `2026-07-28T19:15:51.771084+00:00`  
Git: `c606a7a8065a`  
Experiment: `frontier_probes`

| Claim | Status | Note |
|-------|--------|------|
| **Open-world pixel identity** (`open_world_pixel_identity`) | `probing` | synthetic tutor-ablated top1=0.938 chance=0.250 (not real Jake pixels) |
| **Self-directed curriculum design** (`self_directed_curriculum`) | `probing` | gap-driven order heuristic measured; not self-authored curriculum |
| **LLM-style free monologue** (`free_monologue`) | `partial` | compositional grounded expansion scored; not free monologue |

See [`docs/CAPABILITY_FRONTIER.md`](../../docs/CAPABILITY_FRONTIER.md) for gates.

```json
{
  "pixel_id_top1": 0.9375,
  "curriculum_gap_driven_fraction": 1.0,
  "monologue_groundedness": 0.5,
  "monologue_sentences": 2
}
```
