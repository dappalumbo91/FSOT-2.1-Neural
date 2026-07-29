# Visual individual identity (doctrine)

## What we got stuck on

Earlier climbs treated **the name string** as the identity:

```text
caption "Alice" @ t  →  RF features  →  prototype[Alice]
test pixels → argmax_name
```

That fails the human problem in two ways:

1. **Name collisions** — different people can share "Alice". The system was forced to merge them into one bag of pixels.
2. **Name-first learning** — humans do **not** primarily learn "the word Alice means this average look." They learn **this look is an individual**, then attach a name when language co-occurs.

Franchise disambiguation and within-film hacks were **symptoms of the wrong unit of identity**.

## What humans roughly do (our mapping)

| Human motif | FSOT mapping |
|-------------|--------------|
| This face/body/motion is **one individual** | Visual identity unit (VIU) = RF-feature cluster over time |
| Another person looks different | Separate VIU (appearance distance) |
| Someone says their name | **Bind** string token → VIU (Hebbian co-occurrence) |
| Same name, different people | Same string on **two VIUs** — no forced merge |
| "Who is that?" from sight alone | Nearest VIU from pixels (tutor-ablated); name is a **label on the VIU**, not the key |

Identity is **individualism of pattern**, not uniqueness of the string.

## Correct two-stage pipeline

```text
STAGE 1 — visual individuals (no names required)
  frames → RF cascade features
        → cluster by appearance (cosine / φ-threshold)
        → VIU_1, VIU_2, … (stable IDs)

STAGE 2 — language bind (optional, train-time)
  caption tokens @ time t  co-occur with active VIU
        → attach name labels to that VIU
        → one VIU can have many names; one name can label many VIUs

STAGE 3 — query (tutor-ablated)
  held-out pixels → nearest VIU
        → report VIU id + any bound names
        → primary metric: re-identify the same VIU across time
        → secondary: name string if uniquely bound
```

## Primary vs secondary metrics

| Metric | Meaning | Claim relevance |
|--------|---------|-----------------|
| **VIU re-ID top-1** | Held-out frames land on the same visual individual | Core human-like memory of *who that is* visually |
| **Name bind purity** | When a name is unique to one VIU, pixels→name works | Language label on top of individual |
| **Global name bag accuracy** | Pixels → shared string across people | **Wrong primary metric** (what we over-optimized) |

Open-world claim (“that is Jake from pixels alone”) is **VIU re-ID + unique name bind for Jake**, not “average all Jake captions into one prototype.”

## Biological honesty

- RF cascade = early visual features (not a face network).
- Clustering = rough individuation motif (not IT / FFA).
- Caption co-occurrence = multimodal bind (not full person semantics).
- We still do **not** claim human face recognition or open-world character ID until gates pass on held-out silent clips with multi-seed VIU re-ID and unique name bind.

## Code

- `fsot_nuron/knowledge/visual_individual.py` — VIU cluster + name bind
- `run_visual_individual.py` — probe runner
- Legacy name-bag path remains for comparison only (`character_pixel_id.py`)

## Relation to 5W1H

- **WHO** = VIU (+ bound names), not a free string without a visual individual.
- **HOW** = RF → cluster → episodic bind; FSOT seeds only.
- **WHY** (media) = co-occurrence of look and name at time t, not “all Alices are one person.”
