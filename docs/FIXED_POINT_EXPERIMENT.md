# FSOT fixed-precision experiment (non-IEEE float)

## Checkpoint

Working float/`f64` genetic mind is saved on `main` as commit **Zig genetic mind authority before non-float experiment**.

This branch experiments with **replacing IEEE float** for continuous dynamics.

## Your idea (clarified)

You are making sense. Restated cleanly:

1. **FSOT already gives extreme numerical constants** (seeds: π, e, φ, γ, K, …) with **zero free fits**.
2. Continuous mind quantities live in **known extremes** (e.g. scalar \(S\) clamped to \([-3, 3]\), rates in cortical bands, gains in \([0, 2]\), etc.).
3. Therefore the machine does **not** need IEEE float’s open-ended “approximate reals.”  
   It needs a **deterministic lattice** fine enough to express:
   - the **constants** (seeds), and  
   - the **variables** only **between the extremes of the system**.

That is **fixed-point (or scaled integer) arithmetic**:  
value = integer / SCALE, with SCALE chosen so the entire dynamic range fits with controllable resolution.

**Genetic structure stays exact trinary** (already integer).  
**Continuous layer** (\(S\), expression scales, \(|W|\)) moves to **seed-scaled fixed integers**.

## Why float feels wrong here

| IEEE `f64` | Fixed / scaled integer |
|------------|-------------------------|
| Rounding mode is hardware/libm dependent | Same integer ops on host and bare metal |
| Soft-FPU vs hard-FPU can disagree (syn counts) | Bit-identical if same SCALE |
| “Almost reals” with quiet error | Explicit quantum \(1/\mathrm{SCALE}\) |
| Not the FSOT story | Matches “constants + bounded variables” |

## What we are *not* claiming

- That biology is fixed-point. Biology is hybrid discrete + continuous + noise.  
- That fixed-point removes *all* approximation — it makes the quantum **chosen and lawful**, not accidental.

## SCALE choice (this experiment)

- Type: `i64` storage, `i128` for multiply intermediate  
- **SCALE = 10¹²** (1_000_000_000_000)  
- Resolution ≈ \(10^{-12}\) per unit of “1.0”  
- \(S \in [-3,3]\) uses at most ~\(6\cdot 10^{12}\) raw units ≪ \(2^{63}\)  
- Room for products before rescaling  

Seeds are stored as pre-rounded fixed integers (same decimal authority as `seeds.zig`, once).

## Experiment goals

1. `computeNeuro` / scalar probe in **pure fixed** (no `f64` ops on the path).  
2. Compare to host `f64` scalar (report abs error, relative).  
3. Keep codon/genotype path **unchanged** (already integer trits).  
4. **Do not** switch the live mind to fixed until scalar + neuron step parity gates pass.

## Run

```powershell
cd embodiment\zig
zig build -Doptimize=ReleaseSafe
.\zig-out\bin\fsot_mind.exe fixed
```

## Later options (if fixed wins)

| Option | Use |
|--------|-----|
| **A. Fixed `i64` SCALE=1e12** | Default experiment |
| **B. Fixed binary Q48 (2⁴⁸)** | Faster shift-based mul |
| **C. Pure trit dynamics** | Only if dynamics rewritten fully in \(T\) (bigger theory step) |
| **D. Keep f64 host-only lab** | Lab parity with Python forever; fixed for bare metal |

## Doctrine

- Genetics / codon = **exact trinary**  
- Continuous FSOT fold = **fixed lattice between extremes**, constants from seeds  
- Never let libm soft-float rewrite structure  
