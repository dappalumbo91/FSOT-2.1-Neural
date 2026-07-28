/-
  Full FSOT spine — consciousness / observer / yin–yang / POOF (structural).

  Continuous closed forms live in archive Scalar.lean + fsot_compute.py.
  Here we fix *policy* and dual structure used by Neural, zero free params.
-/

import FSOTNeural.CellTypes

namespace FSOTNeural

/-- Consciousness is on the law path (operational flag for documentation). -/
def consciousnessOnLawPath : Bool := true

theorem consciousness_on_path : consciousnessOnLawPath = true := rfl

/-- Observer flag is a first-class ScalarInput (not optional decoration). -/
structure ObserverChannel where
  observed : Bool
  deriving DecidableEq, Repr

def quirkActive (o : ObserverChannel) : Bool := o.observed

theorem quirk_on_when_observed : quirkActive ⟨true⟩ = true := rfl
theorem quirk_off_when_unobserved : quirkActive ⟨false⟩ = false := rfl

/-- Yin–Yang dual labels for fluid / neural channels. -/
inductive DualPole where
  | yang  -- emergent / + / inflow / E
  | yin   -- dispersal / − / bleed / I
  deriving DecidableEq, Repr, Inhabited

def dualOf : DualPole → DualPole
  | .yang => .yin
  | .yin => .yang

theorem dual_involutive (p : DualPole) : dualOf (dualOf p) = p := by
  cases p <;> rfl

/-- Term-3 fluid valves named (POOF / SUCTION dual). -/
inductive FluidValve where
  | poof
  | suction
  deriving DecidableEq, Repr, Inhabited

def valvePole : FluidValve → DualPole
  | .poof => .yin      -- dispersal / cos channel in archive narrative
  | .suction => .yang  -- dual inflow-like

theorem poof_yin : valvePole .poof = .yin := rfl
theorem suction_yang : valvePole .suction = .yang := rfl

/-- Acoustic dual (bleed vs inflow). -/
inductive AcousticChannel where
  | bleed   -- A_bleed · sin²
  | inflow  -- A_in · cos²
  deriving DecidableEq, Repr

def acousticPole : AcousticChannel → DualPole
  | .bleed => .yin
  | .inflow => .yang

/-- Cell-type polarity already in CellTypes; dual map here. -/
def cellPole : CellType → DualPole
  | CellType.Pyr => DualPole.yang
  | CellType.PV => DualPole.yin
  | CellType.SST => DualPole.yin
  | CellType.VIP => DualPole.yin

theorem pyr_yang : cellPole CellType.Pyr = DualPole.yang := rfl
theorem pv_yin : cellPole CellType.PV = DualPole.yin := rfl

/-- Full-spine structural panel (no free parameters, duals closed under dualOf). -/
theorem full_spine_structural_ok :
    (consciousnessOnLawPath = true) ∧
    (quirkActive ⟨true⟩ = true) ∧
    (quirkActive ⟨false⟩ = false) ∧
    (dualOf (dualOf .yang) = .yang) ∧
    (valvePole .poof = .yin) ∧
    (valvePole .suction = .yang) ∧
    (cellPole CellType.Pyr = DualPole.yang) ∧
    (cellPole CellType.PV = DualPole.yin) := by
  refine ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩

end FSOTNeural
