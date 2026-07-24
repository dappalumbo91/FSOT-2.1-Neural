# FSOT Brain Design — report

Generated: `2026-07-24T17:38:44.031336+00:00`

## Mission

FSOT multi-region brain design — mechanism fidelity, computer-native scale, trinary bare-metal destination

**Profile:** `ai_efficient` — Computer-native AI: fewer units, faster trains, same motifs
**Units:** 32 (not a human neuron-count target)
**Formulas:** docs/FORMULAS.md · **Thesis:** docs/THESIS.md

## Regions

- **thal**: 4 units · {'Pyr': 3, 'PV': 1}
- **sens**: 12 units · {'Pyr': 10, 'PV': 1, 'SST': 1}
- **assoc**: 10 units · {'Pyr': 8, 'PV': 1, 'SST': 1}
- **hipp**: 6 units · {'Pyr': 5, 'PV': 1}

- E/I count ratio: **4.33**
- E/I synaptic mass: **3.479**
- Mean rate (thal drive): **3.36 Hz**

## Gates

- has_excitatory: **True**
- has_inhibitory: **True**
- multi_region: **True**
- has_projections: **True**
- has_synapses: **True**
- ei_mass_finite: **True**
- thal_drive_active: **True**
- efficiency_profile_ok: **True**
- sensory_path_ok: **True**

## Path forward

See `BRAIN_PATH.md`.
