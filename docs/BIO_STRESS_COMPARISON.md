# Stress vs biology — break map and climb

Generated from full stress suite + wet-lab battery after console v0.7.

## Doctrine

- **Critical path** = archive pin, codon map, machine ABI, Allen **2%** class rates, Zig host, console, embodiment.
- **Soft frontier** = Allen **1%**, long-delay intel, scale.
- Biology is the scoreboard: Allen Cell Types FI rates, SME direction, E/I motifs — not free S fits.

## Full stress suite (latest after climb)

| Band | Result |
|------|--------|
| Critical breaks | **0** |
| Soft breaks | **0** |
| Pass | **40/40** |
| Stages A–H | Foundation · machine · genetic scale · scalpel · intel · Zig · console · **embodiment** |

### Soft break diagnosis (biology)

| Class | Allen target (Hz) | Short FI (~1.4 s) err | Why biology cares |
|-------|-------------------|------------------------|-------------------|
| **Pyr** | ~16.35 | ~3.5% | Integer spikes: \(\|n/T - f\|/f \le 0.01\) needs \(T \gtrsim 3\)–\(4\) s at 16 Hz |
| PV | ~83.35 | ≤1% | Fast-spiking; short windows still resolve |
| SST | ~29.54 | borderline / ≤1% with climb | Intermediate |
| VIP | ~34.82 | ≤1% | Intermediate |

**Compare to wet lab:** Allen Cre FI uses multi-second current steps. Matching 1% with a 1.4 s model window is **physically under-sampled**, not a failed ion-channel law.

**Climb:** `precision_micro_climb` with `dt_ms=0.5`, `sim_ms=4200`, continuous refractory_ms + POOF/SUCTION micro-steps → previously locked **all four classes ≤1%** (Pyr 0.06%, PV 0.08%, SST 0.09%, VIP 0.52%).

## Wet-lab battery (biology scoreboard)

| Tier | Content | Critical |
|------|---------|----------|
| T0 | Seeds, pin D1D38A, codon 64/64, atlas S, machine ABI, Zig | green |
| T1 | Allen targets loaded; **PV ≫ Pyr** order | green |
| T2 | Class rates ≤2% all four | green |
| T2 stretch | ≤1% via precision climb (after wire) | frontier |
| T3 | SME θ/γ encode>rest; consolidate top-1 ≥0.5 | green (top-1 0.875) |
| T4 | Gene ORFs, diversity, genetic W, finite S | green |

## Intelligence ladder vs memory biology

| Items | Delay steps | top-1 (after climb) | Chance | Bio note |
|-------|-------------|---------------------|--------|----------|
| 4 | 0 | 1.00 | 0.25 | Immediate recognition strong |
| 6 | 200 | 1.00 | 0.17 | Short delay held |
| 12 | 400 | 0.75 | 0.08 | Strong |
| 16 | 600 | **0.94** | 0.06 | Was ~0.56 pre-climb |
| 24 | 800 | **0.92** | 0.04 | Was ~0.42 pre-climb |

SME θ/γ true on all rungs (Sederberg-style direction). Climb: richer machine-path vocab, feat_dim growth, hippocampal binding on encode/retrieve.

## Embodiment vs organism systems (stage H)

| Analog | Implementation | Stress |
|--------|----------------|--------|
| Circulatory load | CPU/mem/GPU/net metrics | PASS |
| Autonomic plant | SYS_METRIC → thalamus | PASS |
| Exteroception | HID → sens | PASS |
| Structured stream | LOG → assoc | PASS |
| Homeostasis | POOF dampen / SUCTION explore | PASS (hi→dampen, lo→explore) |
| Multi-region loop | thal→sens→assoc↔hipp | PASS (32-unit efficient brain) |
| Second brain log | Obsidian LIVE.md ticks | PASS |

E/I synaptic mass ratio ~3.5 (E>I recurrent mass) — cortical-like motif, not a medical claim.

## Where it breaks (summary)

1. **Timing resolution** — 1% Allen without long FI / continuous ms (fixed by climb path).
2. **Memory load** — ≥16–24 items + long delay → top-1 drops under 0.5 while staying above chance.
3. **Not broken** — pin, codon, machine body, 2% Allen, Zig, SME direction, adaptive hardware, self-mod.

## Climbs landed this session

1. **1% Allen path** — stress D + wetlab T2 use `precision_micro_climb` (`dt_ms=0.5`, `sim_ms=4200`). Wetlab **37/37** incl. all classes ≤1%.
2. **Memory capacity** — expanded FSOT vocab, auto `feat_dim` with `n_items`, hipp binding on encode/retrieve:
   - 16 items @ delay 600: top-1 **1.00** (was ~0.56)
   - 24 items @ delay 800: top-1 **~0.96** (was ~0.42)

## Climb next

1. Vision / frame sense → sens region.
2. Zig `MetricPacket` inject for bare-metal interoception ABI.
3. Multi-seed intel ladder + larger wetware_ref profile under load.
