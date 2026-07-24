# Stage document: Zig FSOT neuron step + Python parity + bio cross-check

| Field | Value |
|-------|--------|
| **Stage ID** | `ZIG_NEURON_STEP` |
| **Date** | 2026-07-24 |
| **Repo** | [FSOT-2.1-Neural](https://github.com/dappalumbo91/FSOT-2.1-Neural) |
| **Authority pin** | `D1D38A…` (`vendor/fsot_compute.py` / local seeds twin) |
| **Host lab** | Python + PyTorch (`fsot_nuron/`) |
| **Body kernel** | Zig freestanding Multiboot + host (`embodiment/zig/`) |
| **I/O** | Serial UART (QEMU); parallel TritWord datapath |
| **Formal math** | Lean panel `formal/` (codon / fold / signs) |
| **Ledger** | `data/thesis_ledger/runs.jsonl` experiment `zig_neuron_parity` |

This document freezes **how this stage was built**, **why it works**, **the mathematics**, and **how to reproduce** it. It is the scientific / engineering record for the project at the Zig neuron-step stage.

---

## 1. Purpose of this stage

**Goal:** Port the **FSOT active-neuron step** from the Python laboratory into **Zig**, prove **numerical parity** on a fixed protocol, boot the same logic under **QEMU serial**, and **cross-check biological timing** against Allen Cell Types ephys when local public data exist.

**Non-goals (this stage):** full multi-region brain in Zig; true multi-level silicon RAM; medical claims; NLP benchmarks.

---

## 2. Scientific framing (FSOT)

Fluid Spacetime Omni-Theory supplies a **single seed-derived scalar**

\[
S = K \cdot (T_1 + T_2 + T_3)
\]

with **zero free parameters** on the theory path. Seeds \(\{\pi,e,\varphi,\gamma,G\}\) generate Layer-1/2 constants (see `docs/FORMULAS.md`, archive methodology). Neuroscience uses a **preregistered domain fold**:

| Slot | Value | Meaning |
|------|------:|---------|
| \(D_{\mathrm{eff}}\) | 13 | cellular / neural effective dimension |
| \(N\) | 4 | channel classes (Na, K, Ca, leak proxy) |
| \(P\) | 3 | state properties |
| observed | true | quirk_mod / observer channel on |

The **neuron** is a discrete-time dynamical system (1 ms proxy steps) that:

1. Maps stimulus + adaptation + refractory → fold inputs \((\delta\psi,\delta\theta,\rho,\mathrm{hits})\).  
2. Evaluates \(S\).  
3. Emits **trinary** membrane class \(\tau(S)\in\{-1,0,+1\}\).  
4. Fires if not refractory and \(S > \theta_{\mathrm{fire}}\).  
5. On fire: sets refractory / AHP (adaptation), resets phase.

**Why this is “neurological” under FSOT:** structure comes from genetic codon law + channel gene programs (earlier stages); dynamics come from the **same scalar** as the multi-domain theory, not a free-fit Hodgkin–Huxley parameter soup. **Accuracy** here means agreement with **public ephys statistics** (Allen) and **internal parity** across languages—not a claim of a full human brain.

**Efficiency doctrine:** computer-native scale (fewer units, optional faster ISI) is allowed; mechanism fidelity is not optional (`docs/EFFICIENCY_DOCTRINE.md`).

**Trinary bare metal:** \(\mathbb{T}=\{-1,0,+1\}\) is the target machine ontology; Zig implements trit ops + packing; integer carriers are transport during development (`docs/TRINARY_BARE_METAL.md`).

---

## 3. Mathematics implemented at this stage

### 3.1 Scalar (Zig `scalar.zig` ≡ Python `scalar.py` f64)

\[
\begin{aligned}
\mathrm{growth} &= \exp\bigl(\alpha(1-\mathrm{hits}/N)\gamma/\varphi\bigr) \\
T_1 &= \frac{NP}{\sqrt{D}}\cos\frac{\psi_{\mathrm{con}}+\delta\psi}{\eta_{\mathrm{eff}}}
       \exp(-\alpha\cdot\mathrm{hits}/N+\rho+B_{\mathrm{in}}\delta\psi)\,(1+\mathrm{growth}\,C_{\mathrm{eff}}) \\
       &\quad\times\bigl(1+P_{\mathrm{new}}\ln(D/25)\bigr) \\
       &\quad\times \underbrace{\exp(C_{\mathrm{factor}}P_{\mathrm{var}})\cos(\delta\psi+P_{\mathrm{var}})}_{\text{if observed}} \\
T_2 &= \mathrm{scale}\cdot\mathrm{amplitude}+\mathrm{trend} \\
T_3 &= \underbrace{\beta\cos\delta\psi\frac{NP}{\sqrt{D}}(\cdots)}_{\mathrm{valve}}
       \cdot\underbrace{\bigl(1+\tfrac{A_{\mathrm{bleed}}\sin^2\delta\theta}{\varphi}+\tfrac{A_{\mathrm{in}}\cos^2\delta\theta}{\varphi}\bigr)}_{\mathrm{acoustic}}
       \cdot(1+B_{\mathrm{in}}P_{\mathrm{var}}) \\
S &= \mathrm{clamp}\bigl(K(T_1+T_2+T_3),\,-3,\,3\bigr)
\end{aligned}
\]

Constants: `embodiment/zig/src/seeds.zig` = `fsot_nuron/seeds.py`.

### 3.2 Neuron step (Zig `neuron.zig` ≡ Python `neuron_batch.step` one unit)

Each step \(t\) (dt = 1 ms):

1. **Refractory:** tick integer counter; optional sub-ms residual.  
2. **AHP:** \(\mathrm{adapt}\leftarrow\mathrm{adapt}\cdot\mathrm{decay}\).  
3. \(\mathrm{stim}_{\mathrm{eff}}=\mathrm{clamp}(\mathrm{stim}-\mathrm{adapt},-0.5,1.5)\).  
4. Map to fold inputs (refractory raises hits, lowers \(\delta\psi\)).  
5. \(S\leftarrow\mathrm{computeScalar}(\ldots)\).  
6. \(\tau\leftarrow\mathrm{from\_S}(S)\) with thresholds \(\ell=-0.4,h=+0.4\).  
7. Advance phase; fire if \(\neg\mathrm{in\_ref}\land S>\theta+0.35\cdot\mathrm{adapt}-0.5\cdot\mathrm{stim}_+\).  
8. On fire: extend refractory from \(\mathrm{ref\_steps}+\mathrm{train\_count}\cdot\mathrm{adapt\_step}\); bump adapt gain.

### 3.3 Trinary ops (Zig `trit.zig`)

`neg`, `pair`, `sum_sat`, `consensus`, codon primary A,G→+1 C,T→−1, T1 packing, parallel `TritWord`.

### 3.4 Formal (Lean, prior stage)

64-codon fiber membership, neuro fold constants, E/I signs, expression positivity — `formal/`, `lake build`.

---

## 4. Engineering architecture

```text
                    ┌─────────────────────────────┐
                    │  docs/FORMULAS.md + thesis  │
                    │  Lean formal/ (structure)   │
                    └─────────────┬───────────────┘
                                  │ pin D1D38A
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
  Python lab              Zig host oracle           Zig freestanding
  neuron_batch.py         scalar+neuron f64         Multiboot i386
  Allen lock              TRACE dump                COM1 serial
         │                        │                        │
         └──────── parity ────────┘                        │
                    scripts/parity_zig_neuron.py            │
                                                           ▼
                                                    QEMU -kernel
                                                    FSOT_STAGE_*_OK
```

| Plane | Channel | Role |
|-------|---------|------|
| Bring-up | **Serial UART** | QEMU PASS lines |
| Mind bus | **Parallel TritWord** | trit algebra |
| Lab accuracy | **Python + Allen** | bio gates |
| Math structure | **Lean** | codon / fold proofs |

---

## 5. How it was made (process)

1. **Authority:** seeds copied from Python / archive (no hand-fit).  
2. **Scalar port:** closed-form \(T_1,T_2,T_3\) in Zig f64.  
3. **Neuron port:** single-unit state machine mirrored from `neuron_batch.step`.  
4. **Protocol:** 200 steps, period 80, burst 20 of stim 0.65 (matches Python `periodic`).  
5. **Parity harness:** Python recomputes same protocol in float64; max \|ΔS\|, spike identity.  
6. **Kernel:** same self-tests on freestanding + serial.  
7. **Bio:** `run_validation` against local Allen ephys CSV when present (credential-free public data lineage).  
8. **Record:** thesis ledger + this stage doc.

---

## 6. Reproduction (commands)

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"

# Pin theory
python run_archive_pin.py

# Lean structure (optional if lake installed)
python scripts/verify_formal.py

# Zig host + Python parity (core of this stage)
python scripts/parity_zig_neuron.py

# QEMU bare-metal serial gate
cd embodiment\zig
powershell -File .\run_qemu.ps1

# Biological cross-check (Allen local CSV)
cd "I:\fsot nuron"
python run_bio_validate.py --mode bio_match --primary-only --units 64 --steps 1000
```

**Expected parity gates (host):**

| Gate | Criterion (this stage) | Measured (2026-07-24) |
|------|------------------------|------------------------|
| Scalar probe | \|ΔS\| ≈ 0 or rel &lt; 1e-8 | **0** (exact match on probe) |
| Trace | max \|ΔS\| &lt; 1e-5 over 200 steps | **~1.5e-6** |
| Spikes | 0 mismatches | **0** |
| Ternary | ≤2 mismatches | **0** |
| Zig host | `FSOT_STAGE_ZIG_NEURON_OK` | **PASS** |
| QEMU serial | `FSOT_STAGE_ZIG_NEURON_OK` | **PASS** (FPU enabled at bare metal) |

**Bio cross-check (Allen ephys CSV local, 2333 cells, protocol `bio_match`):**

| Metric | Sim (32-unit sample) | Target / band | Closed |
|--------|---------------------|---------------|--------|
| Mean ISI | ~74.8 ms | ~75.3 ms Allen | **yes** (rel ~0.6% under 2% tol) |
| Adaptation index | ~0.056 | ~0.057 | **yes** |
| Evoked rate | ~18.7 Hz | band 5–80 Hz | **yes** |
| Gaps | 6/6 closed | — | **yes** |

Honesty: computational population match under stated protocol—not a wet-lab electrophysiology claim. Credential-free public Allen-style features on disk.

---

## 7. Why it works (claim structure)

| Claim | Support |
|-------|---------|
| Same law as theory | Seeds + scalar formula shared with archive / Lean Scalar lineage |
| Language port is faithful | f64 parity max error ~1e-6 on 200-step protocol |
| Trinary is structural | Codon map + \(\tau(S)\) + trit ops; Lean 64/64 |
| Bare metal lives | Multiboot kernel + COM1 under QEMU |
| Bio-facing | Allen ephys lock path in Python lab (population ISI/adapt) |
| Not overclaimed | Stage does not claim full cortex or clinical accuracy |

---

## 8. File map (this stage)

| Path | Role |
|------|------|
| `embodiment/zig/src/seeds.zig` | Seed constants |
| `embodiment/zig/src/scalar.zig` | \(S=K(T_1+T_2+T_3)\) |
| `embodiment/zig/src/neuron.zig` | Active neuron step |
| `embodiment/zig/src/trit.zig` | Trinary substrate |
| `embodiment/zig/src/serial.zig` | COM1 |
| `embodiment/zig/src/main_host.zig` | Host TRACE dump |
| `embodiment/zig/src/main_kernel.zig` | QEMU kernel |
| `scripts/parity_zig_neuron.py` | Parity + bio card + ledger |
| `docs/FORMULAS.md` | Math ledger |
| `docs/TRINARY_BARE_METAL.md` | Trit ISA doctrine |
| `docs/BARE_METAL_IO.md` | Serial / parallel / display |
| `docs/STAGE_ZIG_NEURON_STEP.md` | **This document** |

---

## 9. Next stage (preview)

- Multi-unit Zig batch + genetic \(W\) apply in trit/fixed-point  
- Sensory trit inject into Zig kernel  
- Tighter Allen class separation (PV vs Pyr) under shared step  
- Optional obligation export of scalar sample points to archive Coq path  

---

## 10. Ethics / honesty

Not a medical device. We **calibrate and score against public wet-lab datasets** (Allen Cell Types, OpenNeuro, …). That *is* biological accuracy for a computational neurological system. We do **not** claim the computer *is* a living preparation — we claim **fidelity to wet-lab measurements under named protocols**. See **`docs/BIO_ACCURACY.md`**. Missing pieces → import more public wet-lab data and close gates.

---

## 11. Changelog entry

- **2026-07-24:** Stage opened. Zig scalar+neuron step; Python parity PASS; stage documentation; bio harness wired to Allen when CSV present.  
- **2026-07-24 (follow-on):** Allen Cre-line class lock (PV/Pyr/SST/VIP); `run_class_ephys.py` PASS (PV faster than Pyr); Zig multi-unit network + W under QEMU; BIO_ACCURACY.md clarifies wet-lab data vs “identity.”
