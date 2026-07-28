# Full FSOT spine in Neural (do not drop)

**Authority:** `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full`  
**Code:** `fsot_nuron/fsot_full_spine.py` · `scalar.py` · Lean `FSOTNeural/FullSpine.lean`  
**Philosophy:** archive `docs/FSOT_PHILOSOPHY_AND_CONSCIOUSNESS_SPINE.md`

Earlier Neural docs under-weighted pieces that are **first-class in FSOT**. This file restores them.

---

## 1. Consciousness (fundamental + operational)

| Layer | Content |
|-------|---------|
| Ontology | Consciousness is a core ripple in the 25D fluid — not an afterthought |
| Math | `C_factor = C_eff · P_new` · `ψ_con = (e−1)/e` |
| Table (§20) | Gate φ/(1+φ), binding e/π, IIT-style weights from seeds only |
| Lean | `consciousnessOnLawPath = true` |

Hard problem remains definition-open *externally*; **inside FSOT** consciousness is on the law path via operational proxies.

---

## 2. Observer effect

```
quirk_mod(observed, δψ, P_var, C_factor) =
  if observed:  exp(C_factor · P_var) · cos(δψ + P_var)
  else:         1
```

When `observed=True`, **T1 is multiplied** by `quirk_mod`.  
Neural: `NeuronConfig.observed=True` by default; `compute_scalar_torch(..., observed=...)`.

```powershell
python -c "from fsot_nuron.fsot_full_spine import observer_effect_report; print(observer_effect_report())"
```

---

## 3. Yin–Yang duality (operational)

| Dual | Yang (+) | Yin (−) |
|------|----------|---------|
| Trinary | +1 emergent | −1 damped |
| Scalar | T1 coherence / observer | T3 valve / chaos |
| Acoustic | A_in cos² inflow | A_bleed sin² bleed |
| Fluid valves | **SUCTION** | **POOF** |
| Cells | Pyr E | PV/SST/VIP I |
| Observer | observed on | observed off |

Archive species panels also use `yin_yang_balance` / duality product metrics — Neural exposes `yin_yang_balance(S, e_rate, i_rate)`.

---

## 4. POOF effect (+ SUCTION dual)

**Layer-1 closed form:**

\[
\mathrm{POOF}=\exp\!\Big(\frac{-\ln\pi/e}{\eta_{\mathrm{eff}}\ln\varphi}\Big)
\approx 0.15348
\]

**Layer-2 dual:**

\[
\mathrm{SUCTION}=\mathrm{POOF}\cdot(-\cos(\theta_s-\pi))
\]

**In T3 valve:**

\[
1 + \mathrm{POOF}\cdot\cos(\theta_s+\pi) + \mathrm{SUCTION}\cdot\sin(\theta_s)
\]

Roles: fluid **dispersal / emergence valves** (not free noise). Also appears in soliton width `1/(1+POOF)`, STDP learning rate `K·ψ_con`, etc. (archive §22).

Precision climb uses **POOF+SUCTION** amplitude for FI micro-steps near the 1% band (no free \(S\) fit).

---

## 5. Homeostasis / attention / STDP (seed table)

From archive §21–22, exposed in `full_spine_snapshot()`:

- Novelty threshold \(1/\varphi\)
- Consolidation rate \(\gamma/\pi\)
- Replay passes \(\lfloor 2\pi\rfloor\)
- STDP learning rate \(K\cdot\psi_{\mathrm{con}}\)
- Soliton width \(1/(1+\mathrm{POOF})\)

---

## 6. Commands

```powershell
python -c "from fsot_nuron.fsot_full_spine import full_spine_snapshot; import json; print(json.dumps(full_spine_snapshot(), indent=2)[:2500])"
python run_full_spine_check.py
python run_precision_climb.py --tol 0.01
cd formal; lake build
```
