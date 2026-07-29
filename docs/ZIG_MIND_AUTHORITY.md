# Zig mind authority — where the neuron lives

## Genetic folding doctrine

Trinary is not a coding gimmick. The **64-codon PRIMARY map** (A,G=+1; C,T=−1)
is the same law as neural genetic structure in this project:

```
DNA codon → primary trinary → ORF (SCN/KCN/CACNA/LEAK)
  → expression (seed-only) → phenotype → genetic W → dynamics
```

Watching composite_spin / channel expression under operation is watching
**genetic structure fold during biological ops in code**. That is the foundation
for later cellular systems (other tissues): same codon spine, different ORFs.

## Correction

Earlier product runs used **Python as the live mind** (short-horizon, multi-region
`FSOTBrainDesign`, learning probes). That was a **lab convenience mistake** relative
to project doctrine:

| Layer | Authority |
|-------|-----------|
| **Neural step, multi-region brain, encode/retrieve** | **Zig** (`embodiment/zig`) |
| **Bare metal body** | **QEMU freestanding kernel** |
| **Python** | Lab parity, media decode, optional UI inject — **not** the mind owner |

## Executables

| Binary | Role |
|--------|------|
| `zig-out/bin/fsot_mind.exe` | **Primary mind host** — multi-region brain + learn + live |
| `zig-out/bin/fsot_trit_host.exe` | Parity / ABI self-test (legacy host) |
| `zig-out/bin/fsot_trit_kernel` | QEMU Multiboot kernel (serial) |

### Build & run mind

```powershell
cd "I:\fsot nuron\embodiment\zig"
zig build mind
# or with args:
zig build mind -- selftest
zig build mind -- learn
zig build mind -- live
zig build mind -- all

# direct:
.\zig-out\bin\fsot_mind.exe all
```

### QEMU bare metal

```powershell
zig build kernel
.\run_qemu.ps1
# serial should show FSOT_BRAIN PASS and FSOT_MIND_BAREMETAL_OK
```

## Zig mind modules

| Module | Replaces (Python) |
|--------|-------------------|
| `neuron.zig` | `neuron_batch` single unit |
| `network.zig` | multi-unit W @ spikes |
| `brain.zig` | `brain_architecture` multi-region step |
| `learning.zig` | encode–delay–retrieve probe |
| `memory.zig` | episodic FP store + retrieve |
| `slots.zig` | 5W1H card + curiosity fill |
| `pathways.zig` | `sensory/bio_pathways` gains/routes |
| `sensory.zig` | packets + bus `buildExternal` |
| `modulate.zig` | `self_modulation` POOF/SUCTION |
| `organism.zig` | continuous always-on mind loop |
| **`codon.zig`** | **64-codon PRIMARY map (A,G=+1; C,T=−1) + DNA→AA** |
| **`genotype.zig`** | **ORF → gene expression → phenotype (SCN/KCN/CACNA/LEAK)** |
| `cell_types.zig` | Pyr/PV/SST/VIP labels + fractions |
| `genetic.zig` | W_ij from codon spins/charges + motifs |
| `bands.zig` | theta/alpha/sigma/gamma + SME contrast |
| `inject_io.zig` | feature-file → sensory bus |
| `fingerprint.zig` | compact memory FP (kernel-scale) |
| `scalar.zig` / `seeds.zig` | `scalar.py` / `seeds.py` |
| `trit.zig` | trinary substrate |
| `frame_inject.zig` | machine frame ABI seam |
| `metric_inject.zig` | interoception plant ABI |

## Migration map (push order)

| Layer | Status | Notes |
|-------|--------|-------|
| Neural step + multi-region | **Zig** | host + QEMU |
| Encode / retrieve / Hebb | **Zig** | `learning.zig` |
| Episodic memory + 5W1H slots | **Zig** | token hashes (no heap) |
| Sensory bus + bio gains | **Zig** | floats in; no media decode |
| Self-modulation | **Zig** | seed POOF/SUCTION |
| Organism tick loop | **Zig** | `fsot_mind organism` |
| Media decode (video/audio) | Python optional | inject features only |
| Allen / wet-lab reports | Python lab | never mind authority |
| Flash boot image | **later** | not this stage |

## What Python still does (bridge only)

- Optional **media decode** (PyAV) → float feature vectors → inject into Zig via frame/metric ABI (in progress)
- Optional **tk console UI** that should call `fsot_mind.exe`, not own the step loop
- **Parity harness** (`scripts/parity_zig_neuron.py`) to keep Zig honest vs lab numbers
- **Allen / wet-lab analysis** reports (science lab, not mind runtime)

## Migration rule

1. New neural capability lands in **Zig first**.
2. Python may mirror for plots/parity — never as sole authority.
3. Product “boot” for the mind = `fsot_mind.exe all` and/or QEMU kernel.

## Status (this stage)

- [x] Multi-region `brain.zig` (thal/sens/assoc/hipp, 32 units)
- [x] `brain.injectFeatures` / sensory bus — float features → regional drive
- [x] `brain.structureReport` — E/I/synapse inventory
- [x] `learning.zig` encode–delay–retrieve + Hebbian E→E (6 items, unit FP)
- [x] `memory.zig` episodic store (32) + retrieve + slot fill
- [x] `slots.zig` 5W1H cards + curiosity (peer/template fill)
- [x] `pathways.zig` + `modulate.zig` seed-lawful gains + POOF/SUCTION
- [x] `organism.zig` continuous always-on tick loop
- [x] `fsot_mind.exe` (`selftest|learn|live|inject|structure|memory|organism|all`)
- [x] Host prints `FSOT_NO_PYTHON_CORE_OK` when full suite passes
- [x] Kernel: pathways + bus lite + `FSOT_MIND_BAREMETAL_OK`
- [x] Product boot: `python run_mind_boot.py` → spawns `fsot_mind` only
- [x] `bio_probe.zig` + `fsot_mind bio|stress` — FI metrics, multi-protocol stress
- [x] Allen-mapped params file → Zig FI; Python lab parity harness
- [x] Stress scorecard: CRITICAL=PASS SOFT=PASS (see ZIG_MIND_STRESS.md)
- [x] `brain.applyBioParams` — multi-region phenotype lock under FI bursts
- [x] **Full 64-codon PRIMARY map** + secondary + AA phase (`codon.zig`)
- [x] **Full ORF genotype spine** SCN/KCN/CACNA/LEAK + cell ORF overrides (`genotype.zig`)
- [x] **Full genetic W** motif/sparsity/recip/long-range/normalize (`genetic.zig`) — Python structure match: 26/4/2 E/I, 161 synapses, mean|W|=0.14
- [x] Typed population largest-remainder region mixes (thal/cortical/hipp)
- [x] Genetic parity harness: `scripts/parity_zig_genetic.py` CRITICAL=PASS
- [x] Continuous **intel** loop: sense→modulate→genetic step→encode→curiosity (`fsot_mind intel`)
- [x] **inject-file** ABI: feature text → organism bus (Python may only write the file)
- [x] QEMU bare metal: codon ATG + SCN ORF + genetic brain + bus → `FSOT_INTEL_BAREMETAL_OK`
- [ ] Stream real media decode (PyAV) writing inject files only
- [ ] Console UI spawns/controls `fsot_mind` only (no Python step loop)
- [ ] Flashable always-on boot image (future — not this stage)

## What was wrong before

Lab scripts (`run_boot_live.py`, short-horizon, etc.) ran **Python**
`FSOTBrainDesign.step` as the live mind. That produced good *science* numbers
but inverted the embodiment doctrine: the transplantable organism's neuron
must live in Zig (host + bare-metal QEMU), with Python as optional injector.

## Boot commands (mind authority)

```powershell
# Preferred product boot
python run_mind_boot.py
python run_mind_boot.py selftest
python run_mind_boot.py learn

# Direct Zig
cd embodiment\zig
zig build -Doptimize=ReleaseSafe
.\zig-out\bin\fsot_mind.exe all
.\zig-out\bin\fsot_mind.exe bio              # FI population metrics
.\zig-out\bin\fsot_mind.exe bio path\to\params.txt
.\zig-out\bin\fsot_mind.exe stress           # multi-protocol stress

# Lab harness: TRACE parity + Allen wet-lab + stress (writes artifacts)
python scripts/stress_zig_mind.py
```

## Stress / wet-lab scorecard (lab harness)

| Check | Role |
|-------|------|
| Neuron TRACE max\|dS\| | Zig host vs Python f64 step |
| FI pop rate/ISI/adapt | Same Allen-mapped params in Zig + Python |
| Allen ISI / adapt gates | Sample targets from ephys CSV |
| `FSOT_STRESS PASS` | unit, FI, net, brain, learn, organism |

See `artifacts/zig_mind_stress.json` and `data/results/ZIG_MIND_STRESS.md`.
