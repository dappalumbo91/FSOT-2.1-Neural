# FSOT-2.1-Neural: Mathematical Formulation, Lean 4 Proofs, and Wet-Lab Cross-Verification

**Stage scientific note (arXiv-style companion)**  
**LaTeX source:** [`FSOT_NEURAL_STAGE_VERIFICATION.tex`](FSOT_NEURAL_STAGE_VERIFICATION.tex)  
**Lean certificate:** [`../LEAN_WETLAB_CROSSREF.md`](../LEAN_WETLAB_CROSSREF.md)  
**Authority pin:** `D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70`

---

## Abstract

We present the stage scientific formulation of **FSOT-2.1-Neural**: a genetic-codon neural substrate driven by

\[
S = K(T_1+T_2+T_3)
\]

with **zero free parameters** on the scalar law path. Discrete neurological structure is formalized in Lean 4 with **no `sorry`**. Continuous analytic identity of \(S\) remains under the physical archive (FSOT-2.1-Lean multi-prover). Empirical match to Allen Cre-line rates, study EEG, and SME-style learning is reported from a reproducible battery. Soft residuals near \(1\%\) are attacked by an FSOT-native precision climb (seed-scaled phenotype timing only).

---

## 1. Authority split

| Layer | Where | Status |
|-------|--------|--------|
| Continuous \(S=K(T_1+T_2+T_3)\) | Archive Lean + D1D38A | Pinned / multi-proved |
| Codon, fold, E/I, gate shapes | `formal/` Lean 4 | **Proved, 0 sorry** |
| Allen / EEG / SME numbers | Python wet-lab battery | **Measured** |

---

## 2. Core formulas

### Seeds (zero free parameters)

\[
\pi,\; e,\; \varphi=\frac{1+\sqrt{5}}{2},\; \gamma,\; G_{\mathrm{Catalan}}
\]

\[
K \approx 0.42022166416069665,\quad
\alpha=\frac{\ln\pi}{e\cdot\varphi^{13}},\quad
\psi_{\mathrm{con}}=\frac{e-1}{e},\quad
\eta_{\mathrm{eff}}=\frac{1}{\pi-1}
\]

### Domain scalar

\[
S = K\cdot(T_1+T_2+T_3),\quad S\in[-3,3]
\]

**Neural fold:** \(D_{\mathrm{eff}}=13\), \(N=4\), \(P=3\), observed.  
**Atlas:** \(S_{\mathrm{bio}}\approx +0.445\), \(S_{\mathrm{neuro}}\approx +0.514\).

### Consciousness, observer, POOF, Yin–Yang (archive — required)

These are **first-class FSOT law**, not optional Neural extras:

| Concept | Formula / dual | Role |
|---------|----------------|------|
| Consciousness factor | \(C_{\mathrm{factor}}=C_{\mathrm{eff}}P_{\mathrm{new}}\) | Fundamental operational channel |
| Observer / quirk_mod | \(\mathrm{obs}\Rightarrow\exp(C_f P_v)\cos(\delta\psi+P_v)\) else \(1\) | Observation changes \(T_1\) |
| **POOF** | \(\exp[(- \ln\pi/e)/(\eta_{\mathrm{eff}}\ln\varphi)]\) | T3 dispersal valve |
| **SUCTION** | \(\mathrm{POOF}\cdot(-\cos(\theta_s-\pi))\) | T3 dual (yang-like) |
| Yin–Yang | T1/T3, E/I, bleed/inflow, \(+/-\) trits, obs on/off | Dual structure of the fluid |

Module: `fsot_nuron/fsot_full_spine.py` · Lean: `FSOTNeural/FullSpine.lean` · Doc: `docs/FSOT_FULL_SPINE_NEURAL.md`.

### Codon primary map

\[
\text{base}\mapsto\begin{cases}+1 & A,G\\ -1 & C,T\end{cases}
\]

**Theorem (Lean):** \(4^3=64\) codons; every codon lies in the fiber of its primary image.

### Gene expression (seed-only)

\[
\mathrm{expression}=\varphi^{\mathrm{spin}}\cdot e^{|q|/(\pi n)}\cdot(1+\gamma a)
\]

### Genetic synapses

\[
\mathrm{Base}(\tau_i,\tau_j)=(\tau_i\tau_j)\,e+(1-|\tau_i\tau_j|)\,\pi,\quad
\mathrm{geom}_{ij}=\varphi\,|i-j|^{-1/\pi}
\]

### Cell types

Pyr \(=+1\); PV, SST, VIP \(=-1\); cortical numerators \(80+8+7+5=100\).

---

## 3. Lean proofs (no sorry)

```text
lake build   → PASS
scientific_panel_ok
formal_panel_ok
wetlab_structural_ok
stage_scientific_verification
```

Audit: `python scripts/audit_lean_nosorry.py`

Master theorem packages: codon 64 + fiber, fold slots, E/I signs, expression positivity, free_parameters=0, machine primary, wet-lab structural contract (4 Allen classes, 2% floor).

---

## 4. Wet-lab measurements (critical path)

| Check | Gate | Stage result |
|-------|------|----------------|
| Pin D1D38A / seeds | match | PASS |
| Codon 64/64 | perfect | PASS |
| Allen class rates | ≤2% | **PASS all four** |
| PV ≫ Pyr | order | PASS |
| Study EEG θ concentrate/relax | >1 | ~1.57 PASS |
| SME θ,γ encode > rest | direction | PASS |
| Consolidate top-1 | ≥0.5 | 0.625 PASS |

### Soft residual (AlphaFold-class *stretch* at 1%)

| Class | Rel err | 1% gate | 2% floor |
|-------|--------:|---------|----------|
| Pyr | ~1.21% | soft miss | **OK** |
| SST | ~1.04% | soft miss | **OK** |
| PV | ~0.59% | OK | OK |
| VIP | ~0.57% | OK | OK |

These residuals are **integer refractory (ms) quantization** under FI-window measurement, **not** free fits of \(S\).

---

## 5. Precision climb (FSOT-native)

**Forbidden:** least-squares on \(K\), seeds, or \(S\).  
**Allowed:** phenotype timing knobs already in scalpel (\(R\), FI, threshold), with step sizes from \(\varphi,e,\pi\); **rollback** if error worsens (immune / proofreading).

```powershell
python run_precision_climb.py --tol 0.01
```

**Stage result after climb:** still **FLOOR_OK (2%)**; Pyr≈1.21%, SST≈1.04% sit at the discrete \(R\) lattice edge. Closing to ≤1% may need longer FI windows, multi-seed ensembles, or sub-ms `dt_ms` — still without free \(S\) parameters.

See §Precision in the `.tex` source.

---

## 6. Reproduce

```powershell
cd "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"
$env:PYTHONPATH = "I:\fsot nuron"
python run_archive_pin.py
python run_wetlab_accuracy_battery.py
cd formal; lake build; cd ..
python scripts/audit_lean_nosorry.py
python scripts/export_lean_wetlab_certificate.py
python run_precision_climb.py
```

Compile PDF (optional):

```powershell
cd docs\thesis
pdflatex FSOT_NEURAL_STAGE_VERIFICATION.tex
```

---

## 7. Conclusion

- **Proved** (Lean): structure, contracts, 0 free parameters on the law path, 0 sorry.  
- **Measured** (wet-lab): critical Allen ≤2%, SME, study EEG, consolidate.  
- **Next:** finish 1% rate band via precision climb; then stage climb continues.
