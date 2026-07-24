import Lake
open Lake DSL

package «fsot-neural-formal» where
  -- Standalone Lean 4 formal panel for FSOT-2.1-Neural.
  -- No mathlib dependency: finite genetics + domain fold definitions.
  -- Full analytic Scalar spine remains in FSOT-2.1-Lean / physical archive.

@[default_target]
lean_lib FSOTNeural where
  roots := #[`FSOTNeural]
