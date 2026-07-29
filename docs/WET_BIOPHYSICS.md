# Wet biophysics synapse cascade (Zig Fixed)

## No shortcuts

Each excitatory connection carries a **spine micro-compartment** with multi-species ODEs
(forward Euler, `CHEM_SUBSTEPS` per lattice tick), not a 4-field tag toy.

## State per E→E synapse

| Species | Role |
|---------|------|
| `glu` | Cleft glutamate (release on pre-spike) |
| `nmda_open` | NMDA open (glu × Mg²⁺ relief from post V) |
| `ca` / `ca_buf` | Free / buffered postsynaptic Ca²⁺ |
| `camk_c` / `camk_p` | Ca-bound / autophosphorylated CaMKII |
| `pp1` | Phosphatase (LTD branch, moderate Ca) |
| `ampa_surf` / `ampa_phos` | Surface AMPA density + phosphorylation |
| `protein` | Late-LTP products → structural W update |

## Coupling

- **Glia EAAT** (`glia.eaatUptakeScale`) scales glutamate clearance.
- **STDP** Δw scaled by `eligibility(spine)` (AMPA/CaMKII/protein vs PP1).
- **consolidateToW** bakes late LTP / LTD into genetic `W`.
- **FSOT** still defines pair-weight at wiring/plasticity boundary.

## Run

```powershell
cd embodiment\zig
zig build -Doptimize=ReleaseFast
.\zig-out\bin\fsot_mind.exe glia
# pathways | molecular | cascade
```

Expect `FSOT_GLIA_MOLECULAR_OK` and wet counters: releases, nmda, ca_peaks, chem_steps.
