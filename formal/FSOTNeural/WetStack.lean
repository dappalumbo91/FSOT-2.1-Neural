/-
  Wet biophysics stack — structural counts and time base (Zig Fixed path).

  Not continuum P_open toys: multi-channel Markov + quantal release.
  Transition law shape: P = 1 - exp(-k·dt) (implemented in Fixed; form named here).
  Matches docs/WET_BIOPHYSICS.md · channel_stoch_fixed · molecular_fixed · glia_fixed.
-/

namespace FSOTNeural

/-- Network tick in microseconds. -/
def networkTick_us : Nat := 1000  -- 1 ms

/-- Channel Markov substep in microseconds. -/
def channelDt_us : Nat := 50

/-- Channel substeps per network tick. -/
def channelStepsPerTick : Nat := networkTick_us / channelDt_us

theorem channel_steps_20 : channelStepsPerTick = 20 := by native_decide

/-- Single-channel bank sizes (structural). -/
def nAmpaChannels : Nat := 48
def nNmdaChannels : Nat := 16
def nQuantalSites : Nat := 12

theorem ampa_48 : nAmpaChannels = 48 := rfl
theorem nmda_16 : nNmdaChannels = 16 := rfl
theorem quantal_12 : nQuantalSites = 12 := rfl

/-- Markov transition law named (not a float proof). -/
def markovTransitionLaw : String := "P = 1 - exp(-k*dt)"

theorem markov_law_named : markovTransitionLaw.length > 5 := by native_decide

/-- Glia roles present as first-class (astro / micro / oligo). -/
inductive GliaRole where
  | astrocyte | microglia | oligodendrocyte
  deriving DecidableEq, Repr, Inhabited

def allGliaRoles : List GliaRole := [.astrocyte, .microglia, .oligodendrocyte]

theorem three_glia : allGliaRoles.length = 3 := by native_decide

/-- STDP sign domain: +1 LTP, -1 LTD, 0 none. -/
def stdpSignValid (s : Int) : Bool :=
  decide (s = 1 ∨ s = -1 ∨ s = 0)

theorem stdp_signs_ok :
    stdpSignValid 1 = true ∧ stdpSignValid (-1) = true ∧ stdpSignValid 0 = true ∧
    stdpSignValid 2 = false := by native_decide

/-- All-atom MD is not the cognitive wet stack. -/
def wetStackUsesAllAtomMd : Bool := false

theorem wet_not_all_atom : wetStackUsesAllAtomMd = false := rfl

/-- Wet stack structural panel. -/
theorem wet_stack_ok :
    (channelStepsPerTick = 20) ∧
    (nAmpaChannels = 48) ∧
    (nNmdaChannels = 16) ∧
    (nQuantalSites = 12) ∧
    (allGliaRoles.length = 3) ∧
    (wetStackUsesAllAtomMd = false) := by
  refine ⟨by native_decide, rfl, rfl, rfl, by native_decide, rfl⟩

end FSOTNeural
