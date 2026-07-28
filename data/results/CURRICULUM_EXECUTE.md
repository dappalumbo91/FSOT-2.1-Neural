# Curriculum execute (short-horizon units + fixed A/B)

Time: `2026-07-28T20:20:40.633958+00:00` → `2026-07-28T20:22:04.205842+00:00`
OK: **True**  gap_steps=**4**

## Held metrics (same budget)

| Arm | Recall after | Pixel after | Δ recall vs base |
|-----|-------------:|------------:|-----------------:|
| baseline | 0.900 | 1.000 | — |
| **gap** | **0.917** | **0.583** | +0.017 |
| fixed | 0.917 | 0.667 | +0.017 |

- gap beats fixed on recall: **True** (held Δ=+0.000)
- gap beats fixed on pixel (±0.05): **False**
- plan synthetic Δ_vs_fixed=0.4455

## Gap steps

- step 1 `dialogue`: recall=0.917 pixel=0.917 caption=1.000
- step 2 `explain`: recall=0.900 pixel=0.500 caption=1.000
- step 3 `face`: recall=0.917 pixel=0.583 caption=1.000
- step 4 `particularly`: recall=0.900 pixel=0.875 caption=1.000

## Fixed steps

- step 1 `action`: recall=0.917 pixel=0.833
- step 2 `animal`: recall=0.900 pixel=0.625
- step 3 `brain`: recall=0.900 pixel=0.875
- step 4 `dialogue`: recall=0.917 pixel=0.750

## Notes

- plan steps=4 path=I:\fsot nuron\artifacts\curriculum\latest_plan.json
- gap_order=['dialogue', 'explain', 'face', 'particularly', 'person', 'project', 'science', 'shakespeare', 'subscribe', 'sufficiently']
- fixed_order=['action', 'animal', 'brain', 'dialogue', 'dog', 'explain', 'face', 'happened', 'human', 'ian']
- baseline recall=0.900 pixel=1.000 caption=1.000
- gap step 1 dialogue: recall=0.917 pixel=0.917
- gap step 2 explain: recall=0.900 pixel=0.500
- gap step 3 face: recall=0.917 pixel=0.583
- gap step 4 particularly: recall=0.900 pixel=0.875
- gap final recall=0.917 pixel=0.583 caption=1.000
- fixed final recall=0.917 pixel=0.667
