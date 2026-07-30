# Lean 4 × Wet-lab scientific certificate

Generated: `2026-07-30T05:17:47.018912+00:00`

## Verdict

| Gate | Status |
|------|--------|
| Lean `lake build` (scientific_panel_ok) | **PASS** |
| Archive pin D1D38A / seeds | **PASS** |
| Wet-lab battery critical | **PASS** |
| Free parameters on scalar | **0** |

**Overall scientific stage:** **PASS**

## What is proved in Lean (structure)

The Lean panel proves *definitions and contracts* of the neurological substrate + mind stack:

- 64-codon finite set and primary trinary fiber round-trip
- Neuroscience fold slots (D_eff, N, P, observed)
- Cell-type E/I polarity and cortical fraction sum
- Expression positivity
- Fixed lattice SCALE=1e12; all-atom MD lab-only (not cognition)
- Wet stack: 48 AMPA / 16 NMDA / 12 quantal sites; 50µs×20 Markov
- FSOT pair-weight zero free params; curriculum ≥95%; no history
- Math solidification: docs/FSOT_MATH_SYSTEM_SOLIDIFIED.md
- Zero free parameters on the scalar *path*
- Machine primary / Morse not primary
- Wet-lab gate *shapes* (4 Allen classes, 2% floor, SME/top-1 predicates)

Continuous analytic \(S=K(T_1+T_2+T_3)\) remains in **FSOT-2.1-Lean / physical archive**
(pin `D1D38A185487B452E470…`, seven_way=True).

## What is measured against wet-lab (empirical)

- Battery: **37/37** pass
- Critical fails: **0**
- Soft fails: **0** (1% stretch allowed)
- Battery timestamp: `2026-07-30T03:54:12.268532+00:00`

## Cross-reference table (Lean ↔ runtime ↔ wet-lab)

| Lean theorem / def | Scientific claim | Runtime | Wet-lab check |
|--------------------|------------------|---------|---------------|
| `FSOTNeural.allCodons_card` | Exactly 64 DNA codons | codon_path_verify perfect 64/64 | T0/codon_map_64_roundtrip |
| `FSOTNeural.codon_in_own_fiber` | Every codon ∈ fiber of primary(trinary) map | A,G=+1; C,T=-1 primary map | T0/codon_map_64_roundtrip |
| `FSOTNeural.purine_pos / pyrimidine_neg` | A,G → +; C,T → − | chemical_codon / trinary_substrate | T4 gene ORFs |
| `FSOTNeural.neuroFold` | D_eff=13, N=4, P=3, observed | seeds.NEURO_* / neuron_batch | T0 structure |
| `FSOTNeural.synapseSign / only_pyr_exc` | Pyr +; PV/SST/VIP − | cell_types / scalpel population | T1/pv_faster_than_pyr + class rates |
| `FSOTNeural.fractions_sum_100` | Cortical fractions 80+8+7+5=100 | cell type mix design | structural |
| `FSOTNeural.expressionPos_true` | Expression score always positive | genetic_genotype expression | T4/gene_ORF_* |
| `FSOTNeural.free_parameters_zero` | 0 free parameters on scalar path | fsot_bridge free_parameters=0 | T0/fsot_bridge_zero_free |
| `FSOTNeural.machine_primary / morse_not_primary` | Machine body primary; Morse secondary | machine_encode EncodePath | T0/machine_abi_roundtrip |
| `FSOTNeural.wetlab_structural_ok` | 4 Allen classes; tol floor 2%; freeParams=0 | run_wetlab_accuracy_battery | T1–T2 Allen rates |
| `FSOTNeural.fixed_lattice_ok` | SCALE=1e12 Fixed authority; MD not on mind path | fixed.zig SCALE; allatom_md host f64 lab | structural (lab separation) |
| `FSOTNeural.wet_stack_ok` | 48 AMPA / 16 NMDA / 12 quantal / 20×50µs Markov | channel_stoch_fixed / molecular_fixed / glia_fixed | pathways wet cascade gate |
| `FSOTNeural.pair_weight_ok` | FSOT pair kernel zero free params (π,e,φ) | genetic_fixed.fsotPairWeight | genetic network / STDP coupling |
| `FSOTNeural.curriculum_gates_ok` | ≥95% ppt; PK–G8 bands; no history pollution | grade_ladder_fixed / understand_depth_fixed | curriculum intelligence gates |
| `FSOTNeural.intel_bio_ok` | 4 neuromods; sleep replay+STDP; claim hops≥95%; 0 free | neuromod_fixed / sleep_replay_fixed / claimability_fixed | intel-bio stack gate |
| `FSOTNeural.scientific_panel_ok` | Master structural certificate mind stack (no sorry) | lake build formal/ | full battery critical path |
| `FSOTNeural.stage_scientific_verification` | formal_panel ∧ wetlab ∧ fixed ∧ wet_stack ∧ pair ∧ curriculum ∧ scientific_panel | export_lean_wetlab_certificate.py | this document |
| `FSOTNeural.leanStampLabel` | LEAN4_STAMP:scientific_panel_ok:v4.31.0:0_sorry:mind_stack | formal Certificate.lean | GitHub stamp artifact |

## Atlas scalars (runtime pin)

- S_Biology ≈ `0.4447250077038458` (archive Biology fold ≈ +0.445)
- S_Neuroscience ≈ `0.5143619629083619` (archive ≈ +0.514)

## How to reproduce

```powershell
cd "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"
$env:PYTHONPATH = "I:\fsot nuron"
python run_archive_pin.py
python run_wetlab_accuracy_battery.py
cd formal; lake build; cd ..
python scripts/verify_formal.py
python scripts/export_lean_wetlab_certificate.py
```

## Authority split (honest)

| Layer | Prover / engine | Role |
|-------|-----------------|------|
| Continuous FSOT scalar | Archive Lean + multi-prover | S = K(T1+T2+T3), D1D38A |
| Neural discrete structure | This repo `formal/` Lean 4 | Codon, fold, E/I, gates |
| Empirical wet-lab | Python battery | Allen rates, SME, study EEG |
| Body | Zig host | Trit step + MachineFrame |

No claim that Lean re-derives Allen FI rates as theorems of analysis.
Claim: **structure is proved; measurements match public wet-lab within published gates.**
