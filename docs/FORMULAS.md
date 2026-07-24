# FSOT-2.1-Neural — Formula ledger

**Living appendix to the thesis.** Every formula here is implemented in code and must stay consistent with the archive authority pin **D1D38A…** for seed-derived constants.

| Symbol source | Location |
|---------------|----------|
| Seeds / K / Layer-1 | `fsot_nuron/seeds.py` · archive `vendor/fsot_compute.py` |
| Scalar | `fsot_nuron/scalar.py` |
| Codon map | `data/64_codon_trinary_map.txt` |
| Gene expression | `fsot_nuron/genetic_genotype.py` |
| Synapses / motifs | `fsot_nuron/genetic_network.py`, `brain_architecture.py` |
| Protein interaction lineage | Archive `04_Genetics-Longevity` |

---

## 1. Seeds (zero free parameters)

\[
\pi,\; e,\; \varphi=\frac{1+\sqrt{5}}{2},\; \gamma,\; G_{\mathrm{Catalan}}
\]

Canonical floats (float64 twins of archive closed forms) include:

| Symbol | ≈ value | Role |
|--------|--------:|------|
| \(K\) | 0.42022166416069665 | Master scale |
| \(\psi_{\mathrm{con}}\) | \((e-1)/e\) | Coherence |
| \(\eta_{\mathrm{eff}}\) | \(1/(\pi-1)\) | Effective viscosity-like scale |
| \(\alpha\) | \(\ln\pi/(e\cdot\varphi^{13})\) | Growth micro-rate |
| POOF / suction / bleed | seed composites | Term-3 fluid valves |

Full Layer-1 table: archive methodology / `fsot_compute.py`.

---

## 2. Domain scalar

\[
\begin{aligned}
T_1 &= \text{coherence / emergence (channels }N\text{, props }P\text{, }D_{\mathrm{eff}},\delta\psi,\rho,\ldots)\\
T_2 &= \text{scale}\cdot\text{amplitude} + \text{trend}\\
T_3 &= \text{valve}\cdot\text{acoustic}\cdot\text{phase (POOF / suction / bleed)}\\
S &= K\cdot(T_1+T_2+T_3),\quad S\in[-3,3]\ \text{(numerical clamp)}
\end{aligned}
\]

**Neuroscience fold priors (this repo):**

| Slot | Default |
|------|--------:|
| \(D_{\mathrm{eff}}\) | 13 |
| \(N\) (channels) | 4 (Na, K, Ca, leak proxy) |
| \(P\) | 3 |
| observed | true |

Implementation: `compute_scalar_torch` in `scalar.py`.

---

## 3. Trinary state

\[
\tau(S)=\begin{cases}
-1 & S < \ell \\
0 & \ell \le S \le h \\
+1 & S > h
\end{cases}
\quad \ell=-0.4,\; h=+0.4
\]

---

## 4. Codon → primary trinary

Primary map (authority file):

\[
\text{base}\mapsto\begin{cases}+1 & \in\{A,G\}\\ -1 & \in\{C,T\}\end{cases}
\]

Codon \(b_1b_2b_3\) → \((\tau_1,\tau_2,\tau_3)\). Secondary map uses \(\{A=+1,T=-1,G/C=0\}\) (recorded in map file; primary used for generative invertibility).

**Gate:** 64/64 codon ∈ inverse(primary(codon)).

---

## 5. Gene expression (seed-only)

For residues in an ORF:

\[
\begin{aligned}
\mathrm{spin} &= \mathrm{mean}(\text{all primary trits})\\
q &= \#\{R,H,K\}-\#\{D,E\}\\
a &= \text{aromatic fraction }\{F,Y,W\}\\
\mathrm{expression} &= \varphi^{\mathrm{spin}}\cdot e^{|q|/(\pi n)}\cdot(1+\gamma a)
\end{aligned}
\]

clamped to \([0.05, 3]\) (or class-biased range). Neutral pivot ≈ 1 when spin\(=0\), \(q=0\), \(a=0\).

Cell-type biases multiply expression (Pyr/PV/SST/VIP) — preregistered, not LSQ.

---

## 6. Phenotype map (channel programs → neuron knobs)

Qualitative law (see `phenotype_from_genes`):

| Gene ↑ | Effect |
|--------|--------|
| SCN | ↓ fire threshold, ↑ FI drive |
| KCN | ↑ refractory floor |
| CACNA | ↑ adapt_step / AHP |
| LEAK | rest / \(V_{\mathrm{rest}}\) proxy |

\(D_{\mathrm{eff}}\) modulated mildly by Ca and SCN−KCN contrast with \(\varphi,\gamma\).

---

## 7. Pairwise synaptic kernel (genetic)

\[
\begin{aligned}
\mathrm{Base}(\tau_i,\tau_j) &= (\tau_i\tau_j)\,e + \bigl(1-|\tau_i\tau_j|\bigr)\,\pi \\
\mathrm{geom}(i,j) &= \varphi\cdot |i-j|^{-1/\pi}\quad(i\neq j)\\
\mathrm{elec}(q_i,q_j) &= -q_i q_j\, e \\
\mathrm{env}(s) &= s/(s+\pi e)\\
w_{ij}^{0} &\propto \mathrm{geom}\cdot(\mathrm{Base}+0.15\cdot\mathrm{elec})\cdot(0.35+0.65\cdot\mathrm{env})
\end{aligned}
\]

Normalize mean absolute nonzero weight, then scale by `syn_scale`.

---

## 8. Microcircuit motif gains

Presynaptic sign \(s_{\mathrm{pre}}\in\{+1,-1\}\):

| Pre → Post | Gain symbol (defaults) |
|------------|------------------------|
| E → E | `gain_ee` ≈ 0.35 |
| E → I | `gain_ei` ≈ 0.85 |
| I → E | `gain_ie` ≈ 0.75 |
| I → I | `gain_ii` ≈ 0.40 |
| VIP → I | `gain_vip_i` ≈ 0.55 |

\[
W_{\mathrm{post,pre}} = w^{0}\cdot\mathrm{gain}(\mathrm{types})\cdot s_{\mathrm{pre}}
\]

Long-range: add E→E terms with projection strength × density schedule.

---

## 9. Spike rule (discrete ms proxy)

At each step \(t\):

1. Decay adaptation; advance refractory (incl. sub-ms residual).  
2. Map stimulus + AHP → \(\delta\psi,\rho,\mathrm{recent\_hits}\).  
3. Compute \(S\).  
4. Fire if not refractory and \(S > \theta_{\mathrm{fire}} + c_1\mathrm{adapt} - c_2\mathrm{stim}_+\).  
5. On fire: set refractory ≈ \(R + k\cdot\delta_{\mathrm{adapt}}\); update AHP.

**Allen lock (optional):** solve \(R,\delta\) so mean ISI and adaptation index track targets; genetic modulation multiplies relative diversity (KCN/Ca/SCN).

---

## 10. Efficiency scaling (computer-native)

Wetware reference ISI \(I_{\mathrm{bio}}\). Efficient mode:

\[
I_{\mathrm{eff}} = I_{\mathrm{bio}} / \kappa,\quad \kappa=3\ \text{(default)}
\]

Same structure; more cognitive steps per wall-clock second. Unit count \(N_{\mathrm{AI}} \ll N_{\mathrm{human}}\) under efficiency doctrine — see thesis §4 and `EFFICIENCY_DOCTRINE.md`.

**Equivalence is functional (gates + motifs), not census.**

---

## 11. Structural gates (brain design)

Boolean claims used in CI / thesis ledger:

- has_excitatory ∧ has_inhibitory  
- multi_region (≥3)  
- has_projections (≥3 named)  
- has_synapses  
- ei_mass_finite  
- thal_drive_active (or mean rate > ε under drive)  

---

## 12. Formal verification (which prover)

Full comparison: [`FORMAL_VERIFICATION_CHOICE.md`](FORMAL_VERIFICATION_CHOICE.md).

| Role | System |
|------|--------|
| **Primary math home** | **Lean 4** (FSOT-2.1-Lean / archive hub) |
| Optional numeric cross-check | Coq **or** Isabelle (export obligations) |
| Boot scalar kernel | F\* (+ Rust/QEMU triangulation) |
| Step-kernel contracts (when Ada) | SPARK/GNATprove |

Do **not** re-prove the full spine in every system for neural work.

## 13. Change control

When code changes a formula:

1. Update this file in the **same commit**.  
2. Bump thesis `Last revised`.  
3. Append ledger row with `formulas_ref: docs/FORMULAS.md@<git sha>`.  
4. Re-run pin + `run_brain_design.py` / `run_genetic_bio.py`.  
5. If formalized, update Lean neural panel / obligations in the same release train.  
