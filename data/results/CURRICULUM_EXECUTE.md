# Curriculum execute (short-horizon units)

Time: `2026-07-28T20:13:14.377858+00:00` → `2026-07-28T20:14:01.725675+00:00`
OK: **True**  steps=**2**

- recall **0.900** → **0.917** (Δ=+0.017)
- pixel_id **1.000** → **0.583** (Δ=-0.417)
- caption→name **0.000** → **0.000**
- plan Δ_vs_fixed (synthetic)=0.3144

## Steps

- step 1 `dialogue`: recall=0.917 pixel=0.417 caption=0.000 ok=True
- step 2 `explain`: recall=0.900 pixel=0.750 caption=0.000 ok=True

## Notes

- plan steps=2 path=I:\fsot nuron\artifacts\curriculum\latest_plan.json
- gap_order=['dialogue', 'explain', 'face', 'particularly', 'person', 'project', 'science', 'shakespeare']
- baseline recall=0.900 pixel=1.000 caption=0.000 ok=True
- step 1 target=dialogue recall=0.917 pixel=0.417
- step 2 target=explain recall=0.900 pixel=0.750
- final recall=0.917 pixel=0.583 caption=0.000 ok=True
