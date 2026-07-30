# FSOT Mathematical System — Solidified (Neural Mind Stack)

**Status:** Authority document for the mathematics *used to build* FSOT-2.1-Neural as it stands now.  
**Date:** 2026-07-29  
**Owner:** Damian Arthur Palumbo  
**Physical archive (master reference):** `I:\FSOT-Physical-Archive`  
**Authority pin (SHA-256 of `vendor/fsot_compute.py`):**  
`D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70`

This document does **not** invent a new theory. It **solidifies** the single FSOT spine already verified across the physical archive (hundreds of domains, multi-prover, ≤0.5% green gate) and records **exactly how that math was engineered into** the genetic Fixed-lattice mind: scalar → genetics → synapses → wet cascade → curriculum.

Cross-links:

| Layer | Path |
|-------|------|
| Archive usage doctrine | `I:\FSOT-Physical-Archive\FSOT_USAGE_DOCTRINE.md` |
| Archive math deep dig | `I:\FSOT-Physical-Archive\ARCHIVE_MATH_AND_VERIFICATION_DEEP_DIG.md` |
| Full Lean hub (analytic S) | `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full` |
| Neural formula ledger | [`FORMULAS.md`](FORMULAS.md) |
| Neural Lean panel | `formal/` · theorem `scientific_panel_ok` |
| Certificate stamp | `data/results/LEAN_WETLAB_CERTIFICATE.md` |

---

## 0. Why this was “easy” once FSOT is pinned

Engineering pattern that succeeded here and across the archive:

```text
PIN law (D1D38A) → MATCH seeds → NAME domain fold → BRIDGE observables
  → KEEP domain engine → COUPLE with S / trinary / pair-weight → MEASURE gates
```

FSOT is **not** “delete edges and hope.” It is **authority → bridge → domain dynamics → metric**.  
When that spine is fixed, new subsystems (STDP, glia, single-channel Markov, grade ladder, all-atom lab) become **route slots + lawful coupling**, not free-parameter reinvention.

---

## 1. One mathematical engine (archive truth)

```text
seeds π, e, φ, γ, Catalan G
  → Layer-1 (α, ψ_con, η_eff, β, γ_c, ω, θ_s, POOF, …)
  → Layer-2 (C_eff, A_bleed, P_var, SUCTION, K, C_factor, …)
  → domain fold (D_eff, hits, δψ, δθ, observed, …)
  → raw_S = T1 + T2 + T3
  → S = K · raw_S
  → closed forms | formula corpus | live-API scaled preds
  → measured authority → error% → green if pooled median ≤ 0.5%
```

### 1.1 Seeds (zero free parameters on the law)

\[
\pi,\; e,\; \varphi=\frac{1+\sqrt{5}}{2},\; \gamma,\; G_{\mathrm{Catalan}}
\]

### 1.2 Canonical closed forms (Layer-1 / Layer-2 excerpts)

| Symbol | Formula | ≈ (float64 twin) |
|--------|---------|------------------:|
| \(\alpha\) | \(\ln\pi/(e\cdot\varphi^{13})\) | — |
| \(\psi_{\mathrm{con}}\) | \((e-1)/e\) | — |
| \(\eta_{\mathrm{eff}}\) | \(1/(\pi-1)\) | — |
| POOF | \(\exp\!\big((-\ln\pi/e)/(\eta_{\mathrm{eff}}\ln\varphi)\big)\) | — |
| **K** | \(\varphi\cdot(\gamma/e)\cdot\sqrt{2}/\ln\pi\cdot 0.99\) | **0.42022166416069665** |
| \(C_{\mathrm{factor}}\) | \(C_{\mathrm{eff}}\cdot P_{\mathrm{new}}\) | ~0.2876 |

Full tables: archive dig §1; neural twins in `seeds.py` / `seeds_fixed.zig`.

### 1.3 Scalar law

\[
S = K\cdot(T_1+T_2+T_3),\qquad S\in[-3,3]\ \text{(numerical clamp)}
\]

- **T1** — coherence / emergence / observer quirk when `observed`  
- **T2** — scale · amplitude + trend  
- **T3** — valve · acoustic · phase (POOF / SUCTION dual)

**Observer (archive Scalar):**

\[
\mathrm{quirk\_mod}=\begin{cases}
\exp(C_{\mathrm{factor}}\,P_{\mathrm{var}})\cdot\cos(\delta\psi+P_{\mathrm{var}}) & \mathrm{observed}\\
1 & \neg\mathrm{observed}
\end{cases}
\qquad T_1\leftarrow T_1\cdot\mathrm{quirk\_mod}
\]

**Parameter honesty:** seed constants + **preregistered route slots** (175 core + 1101 extension in archive audit) — **not** per-observable least-squares.  
`free_parameters = 0` on the scalar law path.

### 1.4 Archive domain achievement (reference, not re-derived here)

From physical archive certificates (`VERIFICATION_REPORT.json`, deep dig):

| Panel | Result |
|-------|--------|
| Live / tier benchmarks | **405/405** green @ **0.5%** envelope |
| Pooled median error | **~0.012%** |
| SOTA claims ledger | **65/65** |
| Lean formal hub | `lake build` OK · **0 sorry** on formal spine |
| Cross-proof | **Seven-way** bare-metal (Lean → Python decimal → Coq → Isabelle → Rust f64 → F\* → QEMU) |
| Boot scalar triangulation | **0.09928895626861721** |

Domain folds are **named fractal coordinates** (same engine, different `(D_eff, hits, δψ, observed, …)`). Examples:

| Domain | D_eff (archive dig) | Notes |
|--------|--------------------:|-------|
| Particle_Physics | 5 | term3 resonance branch |
| Quantum_Mechanics | 6 | \(S_{\mathrm{quant}}\approx +0.9555\) |
| Biology | 12 | unobserved fold example |
| Neuroscience | 14 (atlas) / **13** (this neural substrate) | observed, channel N=4 |
| Cosmology | 25 | \(S_{\mathrm{cosm}}\approx -0.5025\) |

**Neural repo fold (implemented):** \(D_{\mathrm{eff}}=13\), \(N=4\), \(P=3\), `observed=true` — see `NeuroFold.lean`, `seeds`.

---

## 2. How the neural mind *uses* that math (as built)

### 2.1 Authority split

| Layer | Where truth lives | What Neural proves / runs |
|-------|-------------------|---------------------------|
| Continuous \(S=K(T_1+T_2+T_3)\) | Archive Lean + 50-digit `fsot_compute.py` | Pin + float/Fixed twins; **not** re-proved analytically in Neural Lean |
| Discrete genetics + gates | Neural `formal/` | Codons, fold slots, E/I, expression, wet-lab **shapes**, master `scientific_panel_ok` |
| Fixed-lattice runtime | Zig `fixed.zig` SCALE \(10^{12}\) | Deterministic host ↔ bare-metal body path |
| Empirical wet-lab | Allen / EEG / battery JSON | `run_wetlab_accuracy_battery.py` |
| Curriculum / depth | Open bank + Fixed exams | ≥95% straight-A + paraphrase depth |

### 2.2 Trinary of the scalar

\[
\tau(S)=\begin{cases}
-1 & S < -0.4\\
0 & |S|\le 0.4\\
+1 & S > 0.4
\end{cases}
\]

### 2.3 Genetics as trinary code

Primary DNA map (invertible generative authority):

\[
A,G\mapsto +1,\qquad C,T\mapsto -1
\]

Codon \(b_1b_2b_3\mapsto(\tau_1,\tau_2,\tau_3)\). Gate: **64/64** codons recover in the primary fiber.

Gene expression (seed-only):

\[
\mathrm{expression}=\varphi^{\mathrm{spin}}\cdot e^{|q|/(\pi n)}\cdot(1+\gamma a)
\quad\text{clamped},\ \text{always }{>}0
\]

### 2.4 Pairwise synaptic kernel (FSOT, Fixed path)

\[
\begin{aligned}
\mathrm{Base}(\tau_i,\tau_j) &= (\tau_i\tau_j)\,e + (1-|\tau_i\tau_j|)\,\pi \\
\mathrm{geom}(d) &= \varphi\cdot d^{-1/\pi}\\
\mathrm{elec}(q_i,q_j) &= -q_i q_j\, e \\
w_{ij}^{0} &\propto \mathrm{geom}\cdot(\mathrm{Base}+0.15\cdot\mathrm{elec})\cdot(0.35+0.65\cdot\mathrm{env})
\end{aligned}
\]

Implemented: `genetic_fixed.fsotPairWeight` · f64 twin `genetic.fsotPairWeight`.

Motif gains (E/E, E/I, I/E, I/I, VIP→I) are **preregistered** multipliers, not LSQ.

### 2.5 Fixed lattice (engineering solidification of the law)

\[
\mathrm{SCALE}=10^{12},\quad
x_{\mathrm{fixed}}=\mathrm{round}(x\cdot\mathrm{SCALE}),\quad
\text{quantum}=10^{-12}
\]

Doctrine: **Fixed is cognitive authority**; IEEE f64 is **lab-only** (host MD, diagnostics).  
See `docs/FIXED_POINT_EXPERIMENT.md`, `fixed.zig`.

### 2.6 STDP × FSOT (as engineered)

Discrete timing windows (ticks): causal \(\Rightarrow\) LTP, anti-causal \(\Rightarrow\) LTD.

\[
\Delta w = \eta\cdot s\cdot f\!\big(\mathrm{fsotPairWeight}(\ldots)\big),\quad
\eta = 0.012\cdot\psi_{\mathrm{con}},\quad
s\in\{+1,-1,0\}
\]

Optional scales: **glia** supply gain, **molecular eligibility** from spine cascade / open channels.

### 2.7 Wet biophysics stack (process scale — not all-atom)

| Scale | Law | Implementation |
|-------|-----|----------------|
| Network | 1 ms tick | `brain_fixed` |
| Single channel | Markov, \(P=1-e^{-k\cdot dt}\), \(dt=50\,\mu\mathrm{s}\) | `channel_stoch_fixed` |
| AMPA | 48 channels, multi-binding C0→C1→O, desens | same |
| NMDA | 16 channels, Mg block B, Ca unitary × open count | same |
| Quantal release | 12 sites, binomial + site refractory | same |
| Spine chemistry | Ca → CaMKII / PP1 → AMPA traffic → late protein | `molecular_fixed` |
| Glia | uptake / prune / myelination scales | `glia_fixed` |

### 2.8 All-atom MD (lab tool only)

Classical MD (Velocity-Verlet, bonds/angles, LJ+Coulomb, PBC, Berendsen) in **host f64**:  
`allatom_md.zig` · mode `fsot_mind md`.

**Not** on the Fixed cognitive path. Doctrine: [`WHY_NOT_ALL_ATOM_MD.md`](WHY_NOT_ALL_ATOM_MD.md).

### 2.9 Curriculum / depth (intelligence metric layer)

| Gate | Bar |
|------|-----|
| Grade ladder PK→G8 | ≥ **95%** per domain (straight-A) |
| MNIST vision | ≥ **95%** held-out top-1 |
| Paraphrase depth | ≥ **95%** held-out understand exam |
| Multi-hop claimability | ≥ **95%** grounded 1–3 hop chains |
| No history pollution | STEM / literacy only |

FSOT does not replace curriculum; it **lawfully couples** genetics → weight → plasticity → memory so learning is substrate-grounded.

### 2.10 Systems intelligence (neuromod + offline consolidate)

| Species / phase | Role on Fixed path |
|-----------------|--------------------|
| DA / ACh / NE / 5-HT | First-order ODEs → STDP η + encode/rest gains |
| Wake encode | High ACh/NE + DA tag |
| Sleep NREM / replay | Low ACh/NE, soft fingerprint replay + STDP |
| Claimability | Every hop bank-grounded before claim |

See [`FORWARD_INTELLIGENCE_BIO.md`](FORWARD_INTELLIGENCE_BIO.md). Lean: `IntelBio.lean`.

---

## 3. Lean 4 verification stamp (Neural panel)

**Toolchain:** `leanprover/lean4:v4.31.0` (matches physical archive).  
**Build:** `cd formal && lake build` · `python scripts/verify_formal.py`

### 3.1 What Lean proves *here* (structure + contracts, 0 sorry)

| Module | Claims |
|--------|--------|
| `Codon` | 64 codons; A,G=+1 C,T=−1; fiber round-trip |
| `NeuroFold` | D_eff=13, N=4, P=3, observed; 4 channel genes |
| `CellTypes` | Pyr +; PV/SST/VIP −; fractions sum 100 |
| `Expression` | expression score always positive |
| `Authority` | free_parameters=0; machine primary; Morse not primary; pin prefix; formula string |
| `FullSpine` | consciousness on path; observer quirk; POOF/SUCTION dual; cell poles |
| `WetLabGates` | Allen 4 classes; 2%/1% tol shapes; SME/top-1 predicates |
| `FixedLattice` | SCALE=10¹² structural; Fixed is authority; f64 lab-only |
| `WetStack` | AMPA 48 / NMDA 16 / quantal 12; Markov form; MD not cognition |
| `PairWeight` | Base / geom / elec structural identities |
| `CurriculumGates` | 95% ppt thresholds; depth / ladder shapes |
| `Certificate` | master **`scientific_panel_ok`** (no sorry) |

### 3.2 What remains archive-only (by design)

Continuous analytic \(S=K(T_1+T_2+T_3)\), Wave-1 closed forms, 405-domain green panels, seven-way cross-proof of the **full** formal spine:  
`I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full` + `VERIFICATION_REPORT.json`.

Neural Lean **inherits** that pin; it does not re-prove 2000+ obligations.

### 3.3 Stamp artifacts (this repo)

| File | Role |
|------|------|
| `data/results/LEAN_WETLAB_CERTIFICATE.md` | Human stamp |
| `data/results/LEAN_WETLAB_CERTIFICATE.json` | Machine stamp |
| `docs/LEAN_WETLAB_CROSSREF.md` | Lean ↔ runtime ↔ wet-lab table |

---

## 4. Engineering stack map (math → code)

```text
Archive pin D1D38A
  ├─ seeds_fixed / seeds.py          (K, ψ_con, φ, …)
  ├─ scalar_fixed / scalar.py        (S on fold)
  ├─ codon / genetic / genotype      (trinary genetics)
  ├─ genetic_fixed.fsotPairWeight    (W⁰)
  ├─ brain_fixed / network_fixed     (microcircuit + regions)
  ├─ channel_stoch → molecular → glia → stdp   (wet cascade)
  ├─ allatom_md (f64 lab only)
  ├─ grade_ladder / understand_depth / mnist   (intelligence gates)
  └─ formal/ FSOTNeural              (Lean stamp)
```

---

## 5. Forbidden shortcuts (doctrine)

1. **No free LSQ levers** on the scalar law path.  
2. **No fake wet chemistry** (4-field tags instead of channels/ODEs).  
3. **No MD-as-mind** (atoms are lab, not cognition).  
4. **No Morse as primary body language** (machine primary).  
5. **No history pollution** in grade curriculum.  
6. **No claiming archive 0.5% green** on a domain metric that was never bridged (e.g. graph Jaccard).

---

## 6. Change control

When math in code changes:

1. Update **this file** and [`FORMULAS.md`](FORMULAS.md) in the same commit.  
2. Update Lean modules if a structural constant/gate changes.  
3. `python scripts/verify_formal.py` + export certificate.  
4. Append thesis ledger row with `formulas_ref: docs/FSOT_MATH_SYSTEM_SOLIDIFIED.md@<sha>`.  
5. Push monorepo + product when embodiment Zig changes.

---

## 7. One-line certificate

> **One seed-derived scalar engine \(S=K(T_1+T_2+T_3)\), zero free parameters on the law path, fractal domain folds, Fixed lattice cognition, genetic trinary → FSOT pair-weights → STDP/wet cascade, curriculum ≥95% gates; continuous analytic spine + 405-domain precision live in the physical archive pin D1D38A; Neural Lean stamps structure with `scientific_panel_ok` (0 sorry).**

---

*End of solidified math document. Lean build and certificate export stamp the discrete neural claims; archive verification stamps the continuous multi-domain achievement.*
