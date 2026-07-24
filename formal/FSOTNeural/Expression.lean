/-
  Gene-expression positivity — discrete model of the seed-free clamp.
-/

namespace FSOTNeural

def expressionMilli (spinSign : Int) (absQ : Nat) (_n : Nat) (aromMilli : Nat) : Nat :=
  1000 + spinSign.natAbs + absQ + aromMilli / 10

theorem expressionMilli_ge_1000
    (spinSign : Int) (absQ n aromMilli : Nat) :
    expressionMilli spinSign absQ n aromMilli ≥ 1000 := by
  simp only [expressionMilli]
  calc
    1000 ≤ 1000 + spinSign.natAbs := Nat.le_add_right 1000 _
    _ ≤ 1000 + spinSign.natAbs + absQ := Nat.le_add_right _ _
    _ ≤ 1000 + spinSign.natAbs + absQ + aromMilli / 10 := Nat.le_add_right _ _

theorem expressionMilli_pos
    (spinSign : Int) (absQ n aromMilli : Nat) :
    expressionMilli spinSign absQ n aromMilli ≥ 1 :=
  Nat.le_trans (by decide : 1 ≤ 1000)
    (expressionMilli_ge_1000 spinSign absQ n aromMilli)

def expressionPos (spinSign : Int) (absQ aromMilli : Nat) : Bool :=
  decide (expressionMilli spinSign absQ 1 aromMilli ≥ 1)

theorem expressionPos_true (s : Int) (q a : Nat) :
    expressionPos s q a = true := by
  simp [expressionPos]
  exact expressionMilli_pos s q 1 a

end FSOTNeural
