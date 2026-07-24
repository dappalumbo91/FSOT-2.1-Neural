# FSOT Brain Design — report

Generated: `2026-07-24T17:20:07.087867+00:00`

## Mission

FSOT multi-region brain design — mechanism fidelity, computer-native scale (efficiency doctrine)

**Profile:** `wetware_ref` — Biological comparison layout; Allen-style timing when locked
**Units:** 64 (not a human neuron-count target)
**Formulas:** docs/FORMULAS.md · **Thesis:** docs/THESIS.md

## Regions

- **thal**: 8 units · {'Pyr': 7, 'PV': 1}
- **sens**: 24 units · {'Pyr': 19, 'PV': 2, 'SST': 2, 'VIP': 1}
- **assoc**: 20 units · {'Pyr': 16, 'PV': 2, 'SST': 1, 'VIP': 1}
- **hipp**: 12 units · {'Pyr': 9, 'PV': 1, 'SST': 1, 'VIP': 1}

- E/I count ratio: **3.92**
- E/I synaptic mass: **3.079**
- Mean rate (thal drive): **4.69 Hz**

## Gates

- has_excitatory: **True**
- has_inhibitory: **True**
- multi_region: **True**
- has_projections: **True**
- has_synapses: **True**
- ei_mass_finite: **True**
- thal_drive_active: **True**
- efficiency_profile_ok: **True**

## Path forward

See `BRAIN_PATH.md`.
