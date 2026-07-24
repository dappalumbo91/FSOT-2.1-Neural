/-
  Cortical cell types and excitatory / inhibitory polarity.

  Matches fsot_nuron/cell_types.py:
    Pyr = glutamate = +1
    PV, SST, VIP = GABA = −1
-/

namespace FSOTNeural

inductive CellType where
  | Pyr | PV | SST | VIP
  deriving DecidableEq, Repr, Inhabited

/-- Synaptic polarity into postsynaptic current (pre-synaptic sign). -/
def synapseSign : CellType → Int
  | .Pyr => 1
  | .PV => -1
  | .SST => -1
  | .VIP => -1

def isExcitatory (c : CellType) : Bool := synapseSign c > 0
def isInhibitory (c : CellType) : Bool := synapseSign c < 0

theorem pyr_exc : isExcitatory .Pyr = true := by native_decide
theorem pv_inh : isInhibitory .PV = true := by native_decide
theorem sst_inh : isInhibitory .SST = true := by native_decide
theorem vip_inh : isInhibitory .VIP = true := by native_decide

theorem only_pyr_exc (c : CellType) :
    isExcitatory c = true ↔ c = .Pyr := by
  cases c <;> native_decide

/-- Cortical fraction numerators over 100 (80/8/7/5). -/
def corticalFractionNum : CellType → Nat
  | .Pyr => 80
  | .PV => 8
  | .SST => 7
  | .VIP => 5

theorem fractions_sum_100 :
    corticalFractionNum .Pyr + corticalFractionNum .PV +
      corticalFractionNum .SST + corticalFractionNum .VIP = 100 := by
  native_decide

end FSOTNeural
