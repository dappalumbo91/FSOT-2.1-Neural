/-
  Scientific certificate: Lean structural panel + wet-lab contract bundle.

  This is the formal side of the Neural stage verification.
  Empirical numbers are attached by scripts/export_lean_wetlab_certificate.py
  into data/results/LEAN_WETLAB_CERTIFICATE.json / .md
-/

import FSOTNeural.Codon
import FSOTNeural.NeuroFold
import FSOTNeural.CellTypes
import FSOTNeural.Expression
import FSOTNeural.Authority
import FSOTNeural.WetLabGates

namespace FSOTNeural

/--
  Master structural theorem for the Neural formal panel + wet-lab contract.
  No `sorry`. Builds with `lake build`.
-/
theorem scientific_panel_ok :
    -- Genetics
    (allCodons.length = 64) ∧
    (∀ c : Codon, c ∈ primaryFiber (primary c)) ∧
    (baseTrit .A = .pos ∧ baseTrit .G = .pos) ∧
    (baseTrit .C = .neg ∧ baseTrit .T = .neg) ∧
    -- Domain fold
    (neuroFold.D_eff = 13) ∧
    (neuroFold.N_channels = 4) ∧
    (neuroFold.P_props = 3) ∧
    (neuroFold.observed = true) ∧
    (allChannelGenes.length = 4) ∧
    -- Cell types
    (synapseSign .Pyr = 1) ∧
    (synapseSign .PV = -1) ∧
    (synapseSign .SST = -1) ∧
    (synapseSign .VIP = -1) ∧
    (corticalFractionNum .Pyr + corticalFractionNum .PV +
      corticalFractionNum .SST + corticalFractionNum .VIP = 100) ∧
    -- Expression positivity
    (∀ s : Int, ∀ q a : Nat, expressionPos s q a = true) ∧
    -- Authority
    (freeParametersOnScalar = 0) ∧
    (isPrimaryBodyPath .machine = true) ∧
    (isPrimaryBodyPath .morse = false) ∧
    -- Wet-lab structural contract
    (allAllenClasses.length = 4) ∧
    (neuralWetLabContract.tolFloor_per_mille = 20) ∧
    (neuralWetLabContract.freeParams = 0) := by
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · exact allCodons_card
  · intro c; exact codon_in_own_fiber c
  · exact purine_pos
  · exact pyrimidine_neg
  · rfl
  · rfl
  · rfl
  · rfl
  · exact four_channel_genes
  · rfl
  · rfl
  · rfl
  · rfl
  · exact fractions_sum_100
  · intro s q a; exact expressionPos_true s q a
  · exact free_parameters_zero
  · exact machine_primary
  · exact morse_not_primary
  · exact four_allen_classes
  · rfl
  · rfl

/-- Named export for documentation / certificate. -/
def certificateName : String :=
  "FSOT-2.1-Neural scientific_panel_ok (Lean 4 formal + wet-lab structural contract)"

theorem certificate_name_ok : certificateName.length > 10 := by native_decide

end FSOTNeural
