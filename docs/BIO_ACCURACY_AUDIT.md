# Biological accuracy audit (readings vs FSOT Fixed mind)

**Purpose:** Keep the mind claimable as a **genetic / neural process model** on computer hardware, with **trinary genetic code** and **FSOT mathematics** — without pretending full wet-lab equivalence yet.

**Doctrine:** No history pollution. STEM/literacy truth curriculum only. Moral/human nuance later (“don’t eat the apple before you’re ready”).

---

## What current neuroscience says (high level)

### Adult hippocampal neurogenesis (AHN)
- In **rodents**, AHN is solid: new dentate gyrus granule cells, heightened plasticity early, contribution to **pattern separation** and memory.
- In **humans**, AHN remains **studied and debated** in magnitude/age profile, but recent work still treats hippocampal plasticity and (where present) immature neuron programs as relevant to memory/mood; AD and aging studies track neurogenesis-related markers.
- **Implication for us:** Do **not** claim unlimited new neurons every tick. Prefer **rewiring + limited hipp plasticity** (matches our “synaptogenesis over mass birth” stance).

### LTP / LTD / STDP
- **LTP:** co-active or causal pre→post strengthens synapses.
- **LTD:** weaker/anti-causal timing can weaken.
- **STDP:** spike timing (pre before post ≈ potentiation; reverse ≈ depression) is a standard model (Bi & Poo; Song–Miller–Abbott).
- **Implication:** Discrete-tick STDP with FSOT-scaled Δw is a **lawful first-order** model of plasticity — not full Ca²⁺/CaMKII/AMPA trafficking.

### Glia
- Astrocytes / oligodendrocytes / microglia shape synapse formation, pruning, energy, and neuromodulation (“tripartite synapse,” myelin, immune prune).
- **Implication:** We **do not** implement glia yet — **acknowledged gap** and next depth target (hidden processes that correlate with information flow).

### Information & “hidden” processes
- Brain computation is not only point-neuron spikes: neuromodulation, oscillations, inhibition balancing, glial supply, vascular coupling.
- **Implication:** Our 32-unit Fixed lattice is a **seed-lawful core**, not a complete connectome. Depth roadmap expands process fidelity under FSOT, not free parameters.

---

## Our map (claimable now)

| Process | Implemented? | FSOT / genetic link | Bio accuracy status |
|---------|----------------|---------------------|---------------------|
| Spike + membrane-like S dynamics | Yes (`neuron_fixed`) | d_eff, channels from genotype | Coarse but continuous Fixed |
| Genetic W assembly | Yes (`genetic_fixed.fsotPairWeight`) | spin×charge×geom(φ,π,e) | **FSOT-solid** pair law |
| Anatomical routes | Yes (`pathways_fixed`) | thal/sens/assoc/hipp | Simplified neocortex+loops |
| Hebb co-fire | Yes | HEBB_LR | Classic; no full STDP alone |
| **STDP timing** | **Yes now** (`stdp_fixed`) | Δw ∝ η·ψ_con·fsotPairWeight | First-order STDP + FSOT |
| Synaptogenesis (new contact) | Yes | birth W from FSOT pair | Structural plasticity stand-in |
| Prune / LTD residual | Yes | decay + near-zero wipe | Simplified |
| Adult neurogenesis mass birth | **No (by design)** | hipp region only | Aligns with “limited AHN” caution |
| Concept / association bonds | Yes | Δbond ∝ ψ_con·\|pair\| | Memory association layer |
| Novel thought | Bond-composed only | No free prose | Correct for truth doctrine |
| Glia (astro/micro/oligo) | **Yes** (`glia_fixed`) | supply/load poof·suction; η scale; prune; myelo | Process-level, not full wet glia |
| Molecular cascade (CaMKII/AMPA/protein) | **Yes** (`molecular_fixed`) | tag→camk→ampa→protein→consolidate W | Compressed late-LTP stand-in |
| Full STDP curve + multi-timescale | Partial | discrete windows | **Gap — deepen** |
| History / moral corpus | **Excluded** | — | Intentional |

---

## Genetics as code (trinary)

```text
codon / ORF  →  genotype_fixed (spin, charge, cell type, synapse_sign)
             →  genetic_fixed.fsotPairWeight  (trinaryPairInteraction + geom + elec)
             →  W matrix on Fixed lattice
             →  neuron step + STDP updates
```

- **Hardware** = computer (silicon).  
- **Genetics** = **code** (trinary-ish spin/charge interactions, not DNA base-for-base).  
- **FSOT** supplies the **mathematical relationship** of a connection so plasticity is not “magic learning rate only.”

Bond / STDP solidification:

```text
Δw_stdp = sign(Δt) · η · f( fsotPairWeight(spin_pre, spin_post, q_pre, q_post, dist) )
Δbond   = ψ_con · |fsotPairWeight(concept_a, concept_b)| · scale
```

---

## Gaps we will close (depth order)

1. ~~**STDP**~~ — done (`stdp_fixed`); refine multi-timescale later.  
2. ~~**Glial / metabolic**~~ — done v1 (`glia_fixed` astro/micro/oligo).  
3. ~~**Molecular cascade**~~ — done v1 (`molecular_fixed` tag→camk→ampa→protein).  
4. **Inhibition / E-I balance** — tighten motif law under load.  
5. **Richer hipp neurogenesis proxy** — rare new hipp units under activity.  
6. **Multi-timescale STDP + true molecular delay** — longer late-LTP consolidation.  
7. **Only later:** broader world knowledge / moral nuance (after truth STEM depth is solid).

---

## How to re-check after changes

```powershell
cd embodiment\zig
zig build -Doptimize=ReleaseFast
.\zig-out\bin\fsot_mind.exe pathways   # STDP + FSOT bonds + bio map print
.\zig-out\bin\fsot_mind.exe depth      # paraphrase understand
.\zig-out\bin\fsot_mind.exe mnist      # vision truth bar
.\zig-out\bin\fsot_mind.exe ladder     # full grade bars
```

Update this audit whenever a bio claim changes. Prefer **cite mechanism + limitation** over marketing language.
