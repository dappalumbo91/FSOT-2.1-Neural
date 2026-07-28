/-
  Wet-lab gate structure for FSOT-2.1-Neural.

  These are *formal definitions of the scientific contract* — thresholds,
  class labels, and order constraints that the Python runtime must satisfy
  against public Allen / EEG / literature data.

  Measured floats live in data/results/wetlab_accuracy_battery.json;
  this file proves the *shape of the gates*, not the empirical float values.
-/

namespace FSOTNeural

/-- Allen Cre focus classes (matches cell_types / scalpel). -/
inductive AllenClass where
  | Pyr | PV | SST | VIP
  deriving DecidableEq, Repr, Inhabited

def allAllenClasses : List AllenClass := [.Pyr, .PV, .SST, .VIP]

theorem four_allen_classes : allAllenClasses.length = 4 := by native_decide

/-- Relative error tolerance in per-mille (‰). 20‰ = 2%, 10‰ = 1%. -/
def tol2pct_per_mille : Nat := 20
def tol1pct_per_mille : Nat := 10

theorem tol2_gt_tol1 : tol2pct_per_mille > tol1pct_per_mille := by native_decide

/--
  Integer model of |measured - target| / target ≤ tol.
  Uses milli-Hz (×1000) to stay in Nat arithmetic.
  rel_err ≤ t/1000  ⇔  1000 * |m - t| ≤ tol_pm * target  (when target > 0).
-/
def withinTolPerMille (measuredMilli targetMilli tolPm : Nat) : Bool :=
  if targetMilli = 0 then false
  else
    let diff := if measuredMilli ≥ targetMilli then measuredMilli - targetMilli
                else targetMilli - measuredMilli
    decide (1000 * diff ≤ tolPm * targetMilli)

/-- Example concrete: 16.351 Hz vs 16.351 Hz within 2% (milli-Hz units). -/
theorem exact_match_within_2pct :
    withinTolPerMille 16351 16351 tol2pct_per_mille = true := by
  native_decide

/-- Near-match within 2%: |16153-16351|/16351 ≈ 1.21% < 2%. -/
theorem pyr_example_within_2pct :
    withinTolPerMille 16154 16351 tol2pct_per_mille = true := by
  native_decide

/-- Cortical order: PV mean rate must exceed Pyr (Allen wet-lab order). -/
def pvFasterThanPyr (pvMilli pyrMilli : Nat) : Bool :=
  decide (pvMilli > pyrMilli)

theorem pv_order_example :
    pvFasterThanPyr 83350 16351 = true := by native_decide

/-- SME direction gates (Sederberg-style): encode band > rest band. -/
def smeDirection (encodePower restPower : Nat) : Bool :=
  decide (encodePower > restPower)

theorem sme_direction_strict :
    smeDirection 5 3 = true ∧ smeDirection 2 2 = false := by native_decide

/-- Memory ladder: top-1 accuracy as parts-per-thousand (625 = 0.625). -/
def top1GeHalf (top1_ppt : Nat) : Bool :=
  decide (top1_ppt ≥ 500)

theorem top1_625_ge_half : top1GeHalf 625 = true := by native_decide
theorem top1_400_lt_half : top1GeHalf 400 = false := by native_decide

/-- Chance floor: top1_ppt > 1000 / n_items  (integer: top1 * n > 1000). -/
def aboveChance (top1_ppt nItems : Nat) : Bool :=
  if nItems = 0 then false
  else decide (top1_ppt * nItems > 1000)

theorem above_chance_8_625 : aboveChance 625 8 = true := by native_decide

/-- Study EEG: concentrate/rest ratio as milli-ratio (1573 = 1.573). -/
def studyElevated (ratioMilli : Nat) : Bool :=
  decide (ratioMilli > 1000)

theorem study_theta_1573 : studyElevated 1573 = true := by native_decide

/-- Aggregate wet-lab structural contract (definitions compile; values from battery). -/
structure WetLabContract where
  nAllenClasses : Nat
  tolFloor_per_mille : Nat
  freeParams : Nat
  deriving Repr

def neuralWetLabContract : WetLabContract :=
  { nAllenClasses := 4
    tolFloor_per_mille := tol2pct_per_mille
    freeParams := 0 }

theorem contract_four_classes : neuralWetLabContract.nAllenClasses = 4 := rfl
theorem contract_tol_2pct : neuralWetLabContract.tolFloor_per_mille = 20 := rfl
theorem contract_zero_free : neuralWetLabContract.freeParams = 0 := rfl

/--
  Full structural wet-lab panel: gates that *must* hold for a scientific claim.
  Empirical satisfaction is certified in Python battery + JSON cross-ref.
-/
theorem wetlab_structural_ok :
    (allAllenClasses.length = 4) ∧
    (tol2pct_per_mille = 20) ∧
    (tol1pct_per_mille = 10) ∧
    (neuralWetLabContract.freeParams = 0) ∧
    (top1GeHalf 500 = true) := by
  refine ⟨?_, ?_, ?_, ?_, ?_⟩
  · exact four_allen_classes
  · rfl
  · rfl
  · rfl
  · native_decide

end FSOTNeural
