# FSOT-2.1-Neural — Lean 4 formal panel

Formalization of **discrete neurological structure** + **wet-lab gate contracts**.  
Continuous scalar \(S=K(T_1+T_2+T_3)\) remains in the physical archive / FSOT-2.1-Lean.

## Build

```powershell
cd "I:\fsot nuron\formal"
lake build
# or from repo root:
python scripts/verify_formal.py
python scripts/export_lean_wetlab_certificate.py
```

Toolchain: `leanprover/lean4:v4.31.0` (matches physical archive).

## Modules

| Module | Claims |
|--------|--------|
| `FSOTNeural/Codon.lean` | 64 codons; primary A,G=+1 C,T=−1; fiber round-trip |
| `FSOTNeural/NeuroFold.lean` | D_eff=13, N=4, P=3, observed; 4 channel genes |
| `FSOTNeural/CellTypes.lean` | Pyr +; PV/SST/VIP −; fractions sum 100 |
| `FSOTNeural/Expression.lean` | expression score always ≥ 1 |
| `FSOTNeural/Authority.lean` | free_parameters=0; machine primary; Morse not primary |
| `FSOTNeural/WetLabGates.lean` | Allen 4 classes; 2%/1% tol shapes; SME/top-1 predicates |
| `FSOTNeural/FullSpine.lean` | consciousness / observer / POOF–SUCTION duals |
| `FSOTNeural/FixedLattice.lean` | SCALE=1e12; Fixed authority; MD lab-only |
| `FSOTNeural/WetStack.lean` | 48 AMPA / 16 NMDA / 12 quantal / 50µs·20 steps; glia |
| `FSOTNeural/PairWeight.lean` | FSOT pair kernel shape; zero free params |
| `FSOTNeural/CurriculumGates.lean` | ≥95% ppt; PK–G8; no history |
| `FSOTNeural/Certificate.lean` | **`scientific_panel_ok`** master theorem (no sorry) |
| `FSOTNeural.lean` | `formal_panel_ok` + `stage_scientific_verification` |

Math solidification: `docs/FSOT_MATH_SYSTEM_SOLIDIFIED.md` (archive 405-domain bridge).

## Scientific certificate

Cross-reference Lean structure × wet-lab battery × archive pin:

- `docs/LEAN_WETLAB_CROSSREF.md`
- `data/results/LEAN_WETLAB_CERTIFICATE.md`

## Authority split

| Layer | Where |
|-------|--------|
| Continuous FSOT scalar | `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full` (D1D38A) |
| Neural discrete + gates | this `formal/` panel |
| Empirical wet-lab | `run_wetlab_accuracy_battery.py` |

## Embodiment

Python hosts the runnable brain today. Body: Zig — see `docs/EMBODIMENT_ROADMAP.md`.
