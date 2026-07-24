/-
  Neuroscience domain fold — preregistered FSOT route slots.

  Matches fsot_nuron/seeds.py and docs/FORMULAS.md:
    D_eff = 13, N_channels = 4, P = 3, observed = true
  Continuous scalar S lives in archive FSOT/Scalar.lean (authority).
-/

namespace FSOTNeural

/-- Preregistered neuroscience fold (not free parameters). -/
structure NeuroFold where
  D_eff : Nat
  N_channels : Nat
  P_props : Nat
  observed : Bool
  deriving Repr, DecidableEq

/-- Canonical fold used by FSOT-2.1-Neural substrate. -/
def neuroFold : NeuroFold :=
  { D_eff := 13
    N_channels := 4
    P_props := 3
    observed := true }

theorem neuro_D_eff : neuroFold.D_eff = 13 := rfl
theorem neuro_N : neuroFold.N_channels = 4 := rfl
theorem neuro_P : neuroFold.P_props = 3 := rfl
theorem neuro_observed : neuroFold.observed = true := rfl

/-- Ion-channel gene names (structural identifiers). -/
inductive ChannelGene where
  | SCN | KCN | CACNA | LEAK
  deriving DecidableEq, Repr, Inhabited

def allChannelGenes : List ChannelGene := [.SCN, .KCN, .CACNA, .LEAK]

theorem four_channel_genes : allChannelGenes.length = 4 := by native_decide

/-- Resting S proxy documented in seeds (×1000 as milli-units to stay Nat-friendly). -/
def restingS_milli : Nat := 460  -- 0.46

theorem resting_in_band : restingS_milli ≥ 300 ∧ restingS_milli ≤ 650 := by
  native_decide

end FSOTNeural
