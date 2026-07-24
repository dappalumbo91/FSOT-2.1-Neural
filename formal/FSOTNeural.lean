/-
  FSOT-2.1-Neural — formal panel (Lean 4)

  Scope (Phase V1):
    • DNA base / codon finite model
    • Primary trinary map (A,G = +1; C,T = −1)
    • Round-trip property: every codon lies in the fiber of its primary image
    • Full codon set has cardinality 64
    • Neuroscience domain fold constants (preregistered)
    • Cell-type synaptic signs (Pyr +, PV/SST/VIP −)
    • Gene-expression positivity (integer model of the seed-free clamp)

  Authority for continuous scalar S = K(T1+T2+T3): FSOT-2.1-Lean / archive
  (not re-derived here). Python is the temporary host; embodiment targets
  Zig / Ada / Rust (see docs/EMBODIMENT_ROADMAP.md).

  Build:
    cd formal
    lake build
-/

import FSOTNeural.Codon
import FSOTNeural.NeuroFold
import FSOTNeural.CellTypes
import FSOTNeural.Expression

/-! # Top-level status theorems (re-export names for `lake env lean`) -/

namespace FSOTNeural

theorem formal_panel_ok :
    (∀ c : Codon, c ∈ primaryFiber (primary c)) ∧
    (allCodons.length = 64) ∧
    (neuroFold.D_eff = 13) ∧
    (synapseSign CellType.Pyr = 1) ∧
    (synapseSign CellType.PV = -1) ∧
    (expressionPos 0 0 0 = true) := by
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩
  · intro c; exact codon_in_own_fiber c
  · exact allCodons_card
  · rfl
  · rfl
  · rfl
  · exact expressionPos_true 0 0 0

end FSOTNeural
