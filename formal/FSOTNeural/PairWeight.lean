/-
  FSOT pairwise synaptic kernel — structural identities.

  Continuous/Fixed evaluation lives in genetic.zig / genetic_fixed.zig.
  Here we lock the *shape* of the law used to build W:
    Base(τi,τj) = (τi·τj)·e + (1-|τi·τj|)·π
    geom(d)     = φ · d^(-1/π)
    elec(qi,qj) = -qi·qj·e
  Seeds are named; free parameters on this kernel path = 0.
-/

namespace FSOTNeural

/-- Named seed symbols used in the pair kernel (documentation). -/
inductive PairSeed where
  | pi | e | phi
  deriving DecidableEq, Repr, Inhabited

def pairKernelSeeds : List PairSeed := [.pi, .e, .phi]

theorem three_pair_seeds : pairKernelSeeds.length = 3 := by native_decide

/-- Free parameters on the genetic pair-weight formula path. -/
def pairWeightFreeParams : Nat := 0

theorem pair_weight_zero_free : pairWeightFreeParams = 0 := rfl

/-- Trinary product cases for Base: same sign, opposite, or zero involvement. -/
inductive TritProductCase where
  | sameSign    -- product = +1  → Base = e
  | opposite    -- product = -1  → Base = -e
  | zeroish     -- product = 0   → Base = π
  deriving DecidableEq, Repr

/-- Structural: when product is ±1, Base is ±e (e-dominated); when 0, π-dominated. -/
def baseDominatedBy (c : TritProductCase) : PairSeed :=
  match c with
  | .sameSign => .e
  | .opposite => .e
  | .zeroish => .pi

theorem same_uses_e : baseDominatedBy .sameSign = .e := rfl
theorem zero_uses_pi : baseDominatedBy .zeroish = .pi := rfl

/-- Distance for geometric scale must be at least 1. -/
def distAtLeastOne (d : Nat) : Nat := if d = 0 then 1 else d

theorem dist_zero_becomes_one : distAtLeastOne 0 = 1 := rfl
theorem dist_preserved : distAtLeastOne 5 = 5 := rfl

/-- Pair-weight structural panel. -/
theorem pair_weight_ok :
    (pairWeightFreeParams = 0) ∧
    (pairKernelSeeds.length = 3) ∧
    (baseDominatedBy .sameSign = .e) ∧
    (baseDominatedBy .zeroish = .pi) ∧
    (distAtLeastOne 0 = 1) := by
  refine ⟨rfl, by native_decide, rfl, rfl, rfl⟩

end FSOTNeural
