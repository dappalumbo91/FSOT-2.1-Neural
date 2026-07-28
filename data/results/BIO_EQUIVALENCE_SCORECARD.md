# Biological equivalence scorecard

Generated: `2026-07-28T19:52:17.573416+00:00`

Functional fidelity under named mapping — implements what sensory systems *do*,
not a claim that silicon *is* living retina/tissue.

## Layer bands (honest)

| Layer | ~fidelity band | note |
|-------|----------------|------|
| cell_class_rates | 95-99% | Allen scalpel/precision (wetlab 37/37) |
| ei_microcircuit | ~99% | sparse directed E→E + dense E↔I mass band |
| fly_connectome_motifs | ~78% | same-sign recip in FlyWire band |
| sensory_routing | 70-100% | thalamic gate + retina/cochlea soft ceilings ~72 |
| learning_dynamics | 85-88% | SME + harder 12-item information accuracy |
| film_semantics | 15-35% | association+subtitles early; not human comprehension |
| open_world_pixel_id | ~55% | synthetic retina entities; real crops unclaimed |

Live refine: `python run_refine_cycle.py --domain bio --score-only`

## Learning gates: **7/7** pass · ok=True

- top1=1.000 (chance=0.125)
- SME θ/γ encode>rest: True / True

## Fly motif snapshot

- density=0.1593 reciprocity=0.257 hub_frac=0.070
- reciprocity_in_fly_band=True

JSON: `I:\fsot nuron\artifacts\bio_equivalence_scorecard.json`

See docs/BIO_EQUIVALENCE_DISTANCE.md
