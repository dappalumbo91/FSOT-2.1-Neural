/-
  64-codon trinary map — finite formalization.
-/

namespace FSOTNeural

inductive Base where
  | A | C | G | T
  deriving DecidableEq, Repr, Inhabited

inductive Trit where
  | pos | neg
  deriving DecidableEq, Repr, Inhabited

def baseTrit : Base → Trit
  | .A => .pos
  | .G => .pos
  | .C => .neg
  | .T => .neg

structure Codon where
  b1 : Base
  b2 : Base
  b3 : Base
  deriving DecidableEq, Repr, Inhabited

def primary (c : Codon) : Trit × Trit × Trit :=
  (baseTrit c.b1, baseTrit c.b2, baseTrit c.b3)

def allBases : List Base := [.A, .C, .G, .T]

def codonsFrom (bs : List Base) : List Codon :=
  bs.flatMap fun x =>
    bs.flatMap fun y =>
      bs.map fun z => ⟨x, y, z⟩

def allCodons : List Codon := codonsFrom allBases

theorem allCodons_card : allCodons.length = 64 := by
  native_decide

def primaryFiber (t : Trit × Trit × Trit) : List Codon :=
  allCodons.filter (fun c => decide (primary c = t))

/-- Round-trip: every codon is in the fiber of its own primary image. -/
theorem codon_in_own_fiber (c : Codon) : c ∈ primaryFiber (primary c) := by
  cases c with
  | mk b1 b2 b3 =>
    cases b1 <;> cases b2 <;> cases b3 <;> native_decide

theorem primary_total (c : Codon) : ∃ t, primary c = t := ⟨primary c, rfl⟩

def tritToInt : Trit → Int
  | .pos => 1
  | .neg => -1

def primaryInts (c : Codon) : Int × Int × Int :=
  let t := primary c
  (tritToInt t.1, tritToInt t.2.1, tritToInt t.2.2)

theorem purine_pos : baseTrit .A = .pos ∧ baseTrit .G = .pos := ⟨rfl, rfl⟩
theorem pyrimidine_neg : baseTrit .C = .neg ∧ baseTrit .T = .neg := ⟨rfl, rfl⟩

end FSOTNeural
