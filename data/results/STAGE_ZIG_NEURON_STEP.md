# Results snapshot — stage ZIG_NEURON_STEP

See full science/engineering write-up: [`docs/STAGE_ZIG_NEURON_STEP.md`](../../docs/STAGE_ZIG_NEURON_STEP.md)

## Gates (2026-07-24)

- Zig↔Python scalar: **exact** on neuro probe  
- max \|ΔS\| 200-step periodic: **~1.5e-6**  
- spike mismatches: **0**  
- QEMU freestanding: **FSOT_STAGE_ZIG_NEURON_OK**  
- Allen bio gaps (local CSV): **6/6 closed** (ISI rel ~0.6% vs sample targets under bio_match)  

Reproduce: `python scripts/parity_zig_neuron.py` and `embodiment/zig/run_qemu.ps1`.
