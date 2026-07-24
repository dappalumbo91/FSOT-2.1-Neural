# Embodiment roadmap — from Python host to silicon-depth brain

**Thesis companion.** Python is the **prototype laboratory**, not the permanent body.

---

## 1. Why leave Python later

| Python host (now) | Silicon body (goal) |
|-------------------|---------------------|
| Fast iteration, torch, data locks | Lives in OS / firmware / bare metal |
| High-level tensors | **Native trinary** kernels + state |
| Research accuracy first | Same math, lower stack, system loops |
| Trits simulated in float/int | Trits as machine values all the way down |

A computer brain should sit where **software biology** lives: schedulers, interrupts, drivers, metrics — analogous to how a human brain coexists with heart/lung autonomic loops.

---

## 2. Target languages (ranked for *this* project)

| Language | Fit for neurological FSOT body | Notes |
|----------|--------------------------------|-------|
| **Zig** | **Strong default** | Explicit memory, cross-compile, already in SR-ITE (`fsot_continuous_flow.zig`, TUI). Great for “lives on the drive / process.” |
| **Rust** | **Strong co-equal** | Ownership safety; archive already has Rust scalar kernel + QEMU path. Good for sandbox + no_std. |
| **Ada/SPARK** | **Best for contracts** | GNATprove on step invariants; SR-ITE Ada topology exists. Heavier toolchain, excellent for safety-critical body. |
| C | Portable glue | Only if needed for drivers; prefer Zig/Rust wrappers. |
| Formal Lean | **Math**, not the body | Already primary prover (`formal/`). |

**Recommendation:**  
- **Math / consistency** → Lean (done Phase V1 panel).  
- **First embodiment kernel** → **Zig** (matches archive SR-ITE soul/body split) *or* **Rust** if you want stronger borrow-checked isolation.  
- **Second pass safety** → optional **Ada/SPARK** contracts on the same step API.

No need to pick forever today — keep a **thin C ABI / trinary packet API** so Zig and Rust can both host the same brain image.

---

## 3. Depth model (biological analogy)

```text
                    ┌─────────────────────────────┐
 Sensory cortex     │ vision U-Net · audio · text │  ← Phase S
                    │ + computer-native sensors   │
                    └─────────────┬───────────────┘
                                  │
 Association / hipp               │ genetic multi-region brain
                    └─────────────┬───────────────┘
                                  │
 Autonomic / subconscious         │ system metrics loop
  (heart/lungs analog)            │ CPU · mem · disk · net · temps
                    └─────────────┬───────────────┘
                                  │
 Body / trinary bare metal        │ Zig|Rust|Ada freestanding kernel
                                  │ FSOT step + native T={-1,0,+1} substrate
```

Full trinary machine model: **`docs/TRINARY_BARE_METAL.md`**.

---

## 4. Phases

### Now (host)

- Python genetic brain + Allen gates + thesis ledger  
- Lean formal panel (`formal/`, `lake build`)  
- Local Obsidian graph  

### Phase E1 — Stable ABI

Define `fsot_brain_abi` (header / flatbuffers / custom):

- state blob (S, phase, refractory, ternary, region ids)  
- `step(external[N])`  
- sensory inject packets  
- metric inject packets (subconscious)  

### Phase E2 — Trinary kernel port

Port hot path on the **trinary substrate** (not “binary NN with trit labels”):

1. trit ops + T1/T3 packing ABI (`trinary_substrate.py` oracle)  
2. scalar step (fixed-point twin → later discrete collapse)  
3. genetic W in trinary pair algebra  
4. region drive from quantized sensory trit streams  

Python remains oracle: `assert port_trits == python_trits`.

### Phase E3 — Subconscious loop

Background fiber/thread:

- sample host metrics → map into FSOT fold drives (δψ / stim)  
- never free-fit; preregistered metric→fold bridges  
- analogous to interoception without biological organs  

### Phase E4 — Sensory cortex

| Sense | Computer channel | FSOT entry |
|-------|------------------|------------|
| Vision | frames / U-Net features | region `sens` drive |
| Audition | spectrogram / embeddings | `sens` / association |
| Text | tokens / Morse-trinary optional | association |
| Computer-native | syscalls, logs, HID, GPU load | thalamic / autonomic |

Interfaces scaffolded under `fsot_nuron/sensory/` (Python first).

### Phase E5 — Persistence body

- brain state on disk (like LTM / virtual substrate in SR-ITE)  
- boot = restore genotype + W + last S  
- live as service or bootable component  

---

## 5. Trinary bare metal (architecture law)

**We are not settling for permanent binary hardware as the ontology of the brain.**

| Layer | Rule |
|-------|------|
| **Ontology** | \(\mathbb{T}=\{-1,0,+1\}\) is first-class at every depth we control |
| **Host contingency** | Today’s PCs may only *carry* packed trits on binary buses |
| **Port goal** | Zig/Rust/Ada implement trinary ALU + memory semantics at bare metal |
| **End goal** | Multi-level / trinary-capable substrate (custom, firmware-defined, or future silicon) |

See **`docs/TRINARY_BARE_METAL.md`** and `fsot_nuron/trinary_substrate.py`.

Binary is a **transport accident of current lab machines**, not the design endpoint.

---

## 6. Accuracy non-negotiables across ports

1. Authority pin D1D38A (or fixed-point twin certified against it)  
2. Codon 64 formal + Python parity  
3. E/I motifs unchanged  
4. Thesis ledger + FORMULAS.md updated on formula change  
5. Lean panel still builds  

---

## 7. Commands

```powershell
# Formal math panel
cd "I:\fsot nuron\formal"; lake build

# Host brain
cd "I:\fsot nuron"
$env:PYTHONPATH = "."
python run_brain_design.py --profile ai_efficient --sensory
python -c "from fsot_nuron.trinary_substrate import self_test; print(self_test())"
python scripts/verify_formal.py
```
