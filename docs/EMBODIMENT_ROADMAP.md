# Embodiment roadmap — from Python host to silicon-depth brain

**Thesis companion.** Python is the **prototype laboratory**, not the permanent body.

---

## 1. Why leave Python later

| Python host (now) | Silicon body (goal) |
|-------------------|---------------------|
| Fast iteration, torch, data locks | Lives in OS / firmware / bare metal |
| High-level tensors | Binary / **trinary** native kernels |
| Research accuracy first | Same math, lower stack, system loops |

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
 Body / silicon                   │ Zig|Rust|Ada process or kernel
                                  │ FSOT step + trinary W + state
```

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

### Phase E2 — Kernel port

Port hot path only:

1. scalar step (seed floats or fixed-point)  
2. genetic W apply  
3. region drive  

Python remains oracle for parity tests (`assert close(python, zig)`).

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

## 5. Trinary vs binary

- **Storage / ISA:** binary hardware underneath.  
- **Information topology:** FSOT trinary \(\{-1,0,+1\}\) remains the **logical** neural code (codons, spikes classes, spins).  
- Embodiment languages encode trits as `i8` / packed bits; they do not need ternary silicon.

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
python run_brain_design.py --profile ai_efficient
python scripts/verify_formal.py
```
