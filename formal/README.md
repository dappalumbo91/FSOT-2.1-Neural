# FSOT-2.1-Neural — Lean 4 formal panel

Phase V1 formalization of **discrete neurological structure** (not the full archive Scalar analytic spine).

## Build

```powershell
cd "I:\fsot nuron\formal"
lake build
# or from repo root:
python scripts/verify_formal.py
```

Toolchain: `leanprover/lean4:v4.31.0` (matches physical archive).

## Modules

| Module | Claims |
|--------|--------|
| `FSOTNeural/Codon.lean` | 64 codons; primary A,G=+1 C,T=−1; round-trip fiber membership |
| `FSOTNeural/NeuroFold.lean` | D_eff=13, N=4, P=3, observed |
| `FSOTNeural/CellTypes.lean` | Pyr +; PV/SST/VIP −; fractions sum 100 |
| `FSOTNeural/Expression.lean` | expression score always ≥ 1 (positivity gate) |
| `FSOTNeural.lean` | aggregate `formal_panel_ok` |

## Authority split

- **This panel:** genetics + fold + polarity + positivity  
- **FSOT-2.1-Lean / archive:** continuous \(S=K(T_1+T_2+T_3)\), multi-prover obligations  

## Embodiment

Python hosts the runnable brain today. Body languages: Zig / Rust / Ada — see `docs/EMBODIMENT_ROADMAP.md`.
