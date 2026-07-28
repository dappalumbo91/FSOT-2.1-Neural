/-
  Authority pin and zero free parameters (structural claims).

  Continuous S = K(T1+T2+T3) lives in archive FSOT-2.1-Lean / vendor/fsot_compute.py
  with SHA-256 D1D38A… — not re-proved analytically here.
  This module records the *policy* the Neural panel inherits.
-/

namespace FSOTNeural

/-- Free parameters on the FSOT scalar law path: zero. -/
def freeParametersOnScalar : Nat := 0

theorem free_parameters_zero : freeParametersOnScalar = 0 := rfl

/--
  Authority pin prefix (certificate). Full hash is 64 hex chars in Python pin;
  we keep the known prefix as a decidable string for documentation in Lean.
-/
def authorityPinPrefix : String := "D1D38A185487B452E470AC68ECE2EB45"

theorem authority_pin_prefix_len : authorityPinPrefix.length = 32 := by native_decide

/-- Formula string (structural identity of the law). -/
def scalarFormula : String := "S = K * (T1 + T2 + T3)"

theorem formula_nonempty : scalarFormula.length > 0 := by native_decide

/-- Encode path doctrine: machine is primary body I/O. -/
inductive EncodePath where
  | machine | chemical | morse
  deriving DecidableEq, Repr, Inhabited

def isPrimaryBodyPath : EncodePath → Bool
  | .machine => true
  | .chemical => true  -- genetics spine
  | .morse => false

theorem machine_primary : isPrimaryBodyPath .machine = true := rfl
theorem morse_not_primary : isPrimaryBodyPath .morse = false := rfl

end FSOTNeural
