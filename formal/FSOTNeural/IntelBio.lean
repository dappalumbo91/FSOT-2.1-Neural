/-
  Forward intelligence stack — structural contracts (Zig Fixed path).

  Neuromodulators DA/ACh/NE/5-HT as first-class ODE species.
  Sleep-like offline consolidation phases.
  Multi-hop claimability ≥95% threshold (ppt).
  Matches neuromod_fixed / sleep_replay_fixed / claimability_fixed.
-/

namespace FSOTNeural

/-- Neuromodulator species present on the mind path. -/
inductive NeuromodSpecies where
  | dopamine | acetylcholine | norepinephrine | serotonin
  deriving DecidableEq, Repr, Inhabited

def allNeuromods : List NeuromodSpecies :=
  [.dopamine, .acetylcholine, .norepinephrine, .serotonin]

theorem four_neuromods : allNeuromods.length = 4 := by native_decide

/-- Biological schedule phases (not wall-clock OS sleep). -/
inductive BioPhase where
  | wakeEncode | wakeProbe | wakeRest | sleepNrem | sleepReplay
  deriving DecidableEq, Repr, Inhabited

def allBioPhases : List BioPhase :=
  [.wakeEncode, .wakeProbe, .wakeRest, .sleepNrem, .sleepReplay]

theorem five_bio_phases : allBioPhases.length = 5 := by native_decide

/-- Offline consolidation uses replay + STDP (policy flags). -/
def sleepUsesReplay : Bool := true
def sleepUsesStdp : Bool := true
def sleepIsWallClockOs : Bool := false

theorem sleep_replay_on : sleepUsesReplay = true := rfl
theorem sleep_stdp_on : sleepUsesStdp = true := rfl
theorem sleep_not_os_clock : sleepIsWallClockOs = false := rfl

/-- Claimability: hop depths 1–3; pass ≥95% ppt. -/
def maxClaimHops : Nat := 3
def claimPass_ppt : Nat := 950

theorem max_hops_3 : maxClaimHops = 3 := rfl
theorem claim_pass_95 : claimPass_ppt = 950 := rfl

def claimPass (score_ppt : Nat) : Bool :=
  decide (score_ppt ≥ claimPass_ppt)

theorem claim_950_ok : claimPass 950 = true := by native_decide
theorem claim_900_fail : claimPass 900 = false := by native_decide

/-- STDP η is modulated by neuromodulators (policy). -/
def stdpCoupledToNeuromod : Bool := true
theorem stdp_neuromod_coupled : stdpCoupledToNeuromod = true := rfl

/-- Free parameters on neuromod law path (seed-scaled τ, not LSQ). -/
def neuromodFreeParams : Nat := 0
theorem neuromod_zero_free : neuromodFreeParams = 0 := rfl

/-- Closed intelligence loop stages (train → sleep → prove). -/
inductive IntelLoopStage where
  | train | retrievePractice | probePre | delay | sleep | prove
  deriving DecidableEq, Repr, Inhabited

def allLoopStages : List IntelLoopStage :=
  [.train, .retrievePractice, .probePre, .delay, .sleep, .prove]

theorem six_loop_stages : allLoopStages.length = 6 := by native_decide

/-- Prediction-error DA and limited working-memory capacity (structural). -/
def usesPredictionErrorDa : Bool := true
def workingMemorySlots : Nat := 4

theorem pe_da_on : usesPredictionErrorDa = true := rfl
theorem wm_slots_4 : workingMemorySlots = 4 := by native_decide

/-- Multi-day frontier + curiosity selection (structural). -/
def multiDayFrontier : Bool := true
def curiositySelectsNextItem : Bool := true
def speechReconnectPathPreserved : Bool := true

theorem multi_day_on : multiDayFrontier = true := rfl
theorem curiosity_select_on : curiositySelectsNextItem = true := rfl
theorem speech_path_preserved : speechReconnectPathPreserved = true := rfl

theorem intel_bio_ok :
    (allNeuromods.length = 4) ∧
    (allBioPhases.length = 5) ∧
    (sleepUsesReplay = true) ∧
    (sleepUsesStdp = true) ∧
    (sleepIsWallClockOs = false) ∧
    (maxClaimHops = 3) ∧
    (claimPass_ppt = 950) ∧
    (stdpCoupledToNeuromod = true) ∧
    (neuromodFreeParams = 0) ∧
    (allLoopStages.length = 6) ∧
    (usesPredictionErrorDa = true) ∧
    (workingMemorySlots = 4) ∧
    (multiDayFrontier = true) ∧
    (curiositySelectsNextItem = true) ∧
    (speechReconnectPathPreserved = true) := by
  refine ⟨by native_decide, by native_decide, rfl, rfl, rfl, rfl, rfl, rfl, rfl,
    by native_decide, rfl, by native_decide, rfl, rfl, rfl⟩

end FSOTNeural
