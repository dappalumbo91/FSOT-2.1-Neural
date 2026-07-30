/-
  FSOT-2.1-Neural — formal panel (Lean 4)

  Scope:
    • DNA base / codon finite model (64, A,G=+1; C,T=−1, fiber round-trip)
    • Neuroscience domain fold (D_eff=13, N=4, P=3, observed)
    • Cell-type synaptic signs (Pyr +; PV/SST/VIP −); cortical fractions
    • Gene-expression positivity
    • Authority: free_parameters = 0; machine primary; Morse not primary
    • Wet-lab structural gates (Allen 4 classes, 2% floor, SME/top-1 shapes)
    • Full spine duals (POOF/SUCTION, observer, consciousness on path)
    • Fixed lattice SCALE=1e12; MD lab not cognition
    • Wet stack: 48 AMPA / 16 NMDA / 12 quantal / 50µs Markov
    • Pair-weight zero free params; curriculum ≥95%; no history
    • Master theorem: scientific_panel_ok (Certificate.lean)

  Continuous scalar S = K(T1+T2+T3): FSOT-2.1-Lean / physical archive (D1D38A).
  Math solidification: docs/FSOT_MATH_SYSTEM_SOLIDIFIED.md
  Empirical wet-lab floats: data/results/wetlab_accuracy_battery.json
  Cross-reference: docs/LEAN_WETLAB_CROSSREF.md

  Build:
    cd formal
    lake build
    python ../scripts/verify_formal.py
    python ../scripts/export_lean_wetlab_certificate.py
-/

import FSOTNeural.Codon
import FSOTNeural.NeuroFold
import FSOTNeural.CellTypes
import FSOTNeural.Expression
import FSOTNeural.Authority
import FSOTNeural.WetLabGates
import FSOTNeural.FullSpine
import FSOTNeural.FixedLattice
import FSOTNeural.WetStack
import FSOTNeural.PairWeight
import FSOTNeural.CurriculumGates
import FSOTNeural.Certificate

namespace FSOTNeural

/-- Legacy aggregate (still holds). -/
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

/--
  Stage scientific verification: force all master theorems to elaborate.
  (Theorems are proofs of `Prop`; we inhabit `True` after citing each.)
-/
theorem stage_scientific_verification : True := by
  have := formal_panel_ok
  have := wetlab_structural_ok
  have := free_parameters_zero
  have := fixed_lattice_ok
  have := wet_stack_ok
  have := pair_weight_ok
  have := curriculum_gates_ok
  have := full_spine_structural_ok
  have := scientific_panel_ok
  trivial

end FSOTNeural
