# Which formal system for FSOT neurological math?

**Question:** We do **not** need to re-prove every formula in Coq + Isabelle + Lean + F\* + SPARK. Which system is best for the **neurological substrate** math in FSOT-2.1-Neural?

**Answer (short):**  
**Primary = Lean 4** (extend the existing FSOT-2.1-Lean authority).  
**Optional second = Coq** (or Isabelle) for numeric-obligation cross-check only.  
**F\*** = boot / kernel layer, not the main neuro formula home.  
**Ada/SPARK** = implementation contracts on the *step kernel*, not pure math library proofs.

Authority pin remains `D1D38A…` / archive certificate. Living formulas: [`FORMULAS.md`](FORMULAS.md).

---

## 1. What you already have (archive)

From `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full`:

| Layer | Role today |
|-------|------------|
| **Lean 4** (`FSOT/Scalar.lean`, `FSOT/Formal/*`) | Authority twin of the scalar; domain priors; **0 sorry** formal spine; certificate claims |
| **Coq** (`verification/coq/`) | Re-proves **exported numeric obligations** (full formal spine chunks, transcendentals) |
| **Isabelle** (`verification/isabelle/`) | Same export spine re-proof (parallel to Coq) |
| **F\*** (`verification/fstar/`) | **Boot scalar kernel** shell — runtime/kernel triangulation, not full mathlib-style domain theory |
| **Rust f64 + QEMU** | Bare-metal numeric triangulation |
| **Ada (SR-ITE)** | Fluid topology / optical gates; SPARK-style contracts appear in soul lineage docs |

Cross-proof report (on disk): `seven_way_bare_metal: true`, `overall_ok: true`.  
Honest ceiling (archive README): triangulation of **exported numeric obligations**, not every deep Lean construction re-derived from axioms in every prover.

---

## 2. What the neurological system actually needs to prove

Split claims by *kind* — different tools excel at different kinds.

### A. Continuous FSOT law (shared with whole theory)

- Seeds → Layer-1/2 composites → \(S = K(T_1+T_2+T_3)\)  
- Neuroscience fold: \(D_{\mathrm{eff}}\approx 13\text{–}14\), observed, \(N,P\)  
- Sign / positivity / clamp lemmas; domain prior tables  

**Best home: Lean 4** (already exists; Mathlib `Real`).

### B. Discrete genetics (neurological structure)

- 64-codon primary map invertibility (round-trip)  
- Trit algebra \(\{-1,+1\}^3\)  
- Gene expression bounds (strictly positive, clamped)  
- Cell-type → synapse sign \(\pm 1\) consistency  
- Motif gain tables as preregistered finite maps  

**Best home: Lean 4** (finite types, `Finset`, decidable equality — fast, natural).  
Coq is equally fine for this class; you already invest in Lean for FSOT.

### C. Synaptic / graph structure

- \(W_{ij}\) built from trinary pair + geometry + charge  
- No self-loops; polarity of I cells; projection endpoints in region index sets  
- E/I mass finite; density bounds  

**Best home: Lean 4** (definitions + lemmas).  
Optional **Isabelle** if you want locale-style structured development of “network as locale.”

### D. Discrete-time neuron step (implementation invariants)

- Refractory non-negative; spike only if not refractory  
- `adapt` decay in \([0,1]\) factors; fire threshold finite  
- Stimulus clamp bounds preserved  

**Best home: Ada/SPARK (GNATprove)** *or* Lean executable specs.  
SPARK shines when the **hot path is production Ada** (avionics-style contracts). Your runtime today is **Python/PyTorch** — SPARK does not prove that Python. SPARK becomes first-class when/if you port the step kernel to Ada (or keep Zig + separate contracts).

### E. Boot scalar / bare-metal constant

- Single triangulated float (archive boot value)  

**Best home: F\* kernel + Rust/QEMU** (already the archive pattern). Not where you should formalize codon maps or E/I motifs.

---

## 3. Head-to-head for *this* project

| System | Strength for neuro + FSOT math | Weakness here | Recommendation |
|--------|--------------------------------|---------------|----------------|
| **Lean 4** | Already the **theory authority**; Mathlib; Scalar + Formal; GitHub FSOT-2.1-Lean; good for reals *and* finite codon combinatorics; modern workflow | Heavier for low-level memory-safety of C/Ada kernels | **PRIMARY** |
| **Coq** | Mature; excellent for obligation re-proof; extraction; archive already has FullFormalSpine | Duplicates Lean if you rebuild whole theory; slower “second home” cost | **Secondary cross-check** of exported neural obligations |
| **Isabelle/HOL** | Strong for structured theories, sledgehammer; archive spine exists | Same duplication cost as Coq; less “default” for your public FSOT brand | Alternate secondary (pick **one** of Coq/Isabelle, not both for new work) |
| **F\*** | Executable refinement, effectful/kernel reasoning; archive boot scalar | Constrained for large Mathlib-style analytic spines; archive uses it as **kernel**, not full theory | Keep for **boot / runtime kernel only** |
| **Ada/SPARK** | Best-in-class for **contracts on imperative steps**, ranges, absence of run-time errors | Does not replace a mathlib proof of \(S=K(T_1+T_2+T_3)\); weak fit while logic lives in Python | Use when **porting neuron step** to Ada for safety-critical body |

---

## 4. Recommended strategy (minimal, scientific)

### Phase V1 — Lean only (neurological module)

Add under Lean hub (or vendored `formal/` in this repo later):

1. **Pin lemmas:** seeds / \(K\) match certificate decimals (or rational bounds).  
2. **Scalar:** reuse `FSOT.Scalar` / formal raw_S; fix neuroscience fold constants as `def`.  
3. **Codon:** inductive or `Fin 64` map; prove primary round-trip (matches Python `codon_path_verify`).  
4. **Expression:** prove `expression > 0` and clamp idempotence on the closed-form.  
5. **Sign:** `Pyr.sign = +1`, `PV/SST/VIP.sign = -1`.  
6. **Export obligations JSON** for any numeric literals (same pipeline as archive).

### Phase V2 — One cross-prover (optional)

- Export neural numeric obligations → **Coq** *or* **Isabelle** using existing `verification/` harness.  
- Do **not** maintain three full rewrites of codon theory.

### Phase V3 — SPARK (when embodied)

- When neuron `step` lands in Ada (or you wrap a SPARK-proven core): Pre/Post on refractory, fire, clamps.  
- Complements Lean; does not replace it.

### Explicit non-goals

- Re-verify all 400 science API panels inside the neural repo.  
- Claim “human brain proven.”  
- F\* as primary home for codon combinatorics.

---

## 5. Why Lean wins for neurological systems specifically

1. **Single source of truth** — your archive policy is “I: Lean hub is master; GitHub syncs from there.” Neural formulas should pin *to that*, not fork a Coq-only theory.  
2. **Mix of continuous + discrete** — FSOT reals (Mathlib) + 64-codon finite math + graph-shaped wiring lemmas in one development.  
3. **Already green** — certificate, 0 sorry Formal, seven-way numeric triangulation; neurological work is *extension panels*, not a greenfield prover choice.  
4. **Research publishing path** — Lean 4 + mathlib is currently the default language of formalized pure math communities; aligns with thesis posture.  
5. **Your own prior art** — SR-ITE soul formulas already dual-tracked Lean+Coq; for *new* neural work, lean into the hub that owns Scalar.

Coq remains excellent if you need a **second opinion** on exported numbers (as the archive already does). Isabelle is peer-quality for that same secondary role. F\* and SPARK answer different questions (kernel / implementation safety).

---

## 6. Mapping `docs/FORMULAS.md` → prover

| FORMULAS § | Content | Lean | Coq/Isa export | SPARK | F\* |
|------------|---------|:----:|:--------------:|:-----:|:--:|
| §1–2 Seeds + scalar | Continuous law | **yes** | numeric bounds | — | boot const |
| §3 Trinary of \(S\) | Piecewise | **yes** | — | step guard | — |
| §4 Codon map | Finite | **yes** | optional | — | — |
| §5 Gene expression | Algebraic + clamp | **yes** | bounds | — | — |
| §6 Phenotype map | Definitions | **yes** | — | contracts if Ada | — |
| §7 Synaptic kernel | Algebra + geometry | **yes** | sample points | — | — |
| §8 Motif gains | Finite table | **yes** | — | — | — |
| §9 Spike rule | Discrete dynamics | defs + invariants | — | **yes** | — |
| §10 Efficiency scale | Definitions | **yes** | — | — | — |
| §11 Structural gates | Predicates | **yes** | — | runtime assert | — |

---

## 7. Practical next step

1. Keep Python/PyTorch as **executable domain engine** + real-data gates.  
2. Start **Lean neural panel**: codon round-trip + neuroscience fold + expression positivity (smallest end-to-end formal slice).  
3. Hook obligations into existing `run_cross_proof_verification` only if you want Coq/Isabelle numbers.  
4. Defer SPARK until Ada (or proven-kernel) step exists.  
5. Record formal claims in thesis ledger with `formulas_ref` + Lean module path.

---

## 8. One-sentence recommendation

**Use Lean 4 as the home of neurological FSOT mathematics (building on the physical archive hub); use Coq or Isabelle only as optional export cross-checks; use F\* for boot scalar; use Ada/SPARK for step-kernel contracts when the implementation is in Ada — not as the primary math prover.**
