# Learned capacity snapshot

**Date:** 2026-07-30  
**Branch:** `experiment/fsot-fixed-precision`  
**Doctrine:** experience → episodic hop traces → WM atomics → sleep → prove transfer  
**Not claimed:** full GSM8K test leaderboard; LLM-style Q→A stuffing

This is a **honest inventory** of what the organism has retained from teaching — not a scoreboard claim.

---

## Zig neurological brain (embodiment)

| | |
|--|--|
| **Tree** | [`embodiment/zig/`](../embodiment/zig/) |
| **Mind authority** | `zig build mind` → `fsot_mind` (multi-region + learn + inject) |
| **Host parity** | `zig build host` → trit/neuron parity with Python |
| **Bare metal** | `zig build kernel` → Multiboot ELF, QEMU serial `FSOT_TRIT PASS` |
| **Core modules** | `brain.zig` / `brain_fixed.zig`, `neuron*.zig`, `genetic*.zig`, `memory*.zig`, `learning*.zig`, `sleep_replay_fixed.zig`, `intel_loop_fixed.zig`, `claimability_fixed.zig`, `organism*.zig` |
| **Boot** | `BOOT_MIND.cmd` · `python run_mind_boot.py` (Zig steps neurons; Python does not) |

Build (Windows):

```powershell
cd embodiment\zig
zig build -Doptimize=ReleaseSafe
zig build mind -- all
```

Details: [`embodiment/zig/README.md`](../embodiment/zig/README.md) · [`docs/EMBODIMENT_ROADMAP.md`](EMBODIMENT_ROADMAP.md) · [`docs/STAGE_ZIG_NEURON_STEP.md`](STAGE_ZIG_NEURON_STEP.md)

**Binaries** (`zig-out/`, `$out`) are **not** committed — rebuild locally.

---

## Multi-hop math organism (Python bio schedule)

| | |
|--|--|
| **Code** | [`fsot_nuron/math_multihop_organism.py`](../fsot_nuron/math_multihop_organism.py) |
| **Teacher** | [`scripts/run_multihop_experience_learn.py`](../scripts/run_multihop_experience_learn.py) |
| **Lesson abstractor** | [`fsot_nuron/math_auto_templates.py`](../fsot_nuron/math_auto_templates.py) (school-side only) |
| **Trace bank (memory)** | [`data/math_learn/trace_bank.json`](../data/math_learn/trace_bank.json) |
| **Run report** | [`data/results/MATH_EXPERIENCE_LEARN.json`](../data/results/MATH_EXPERIENCE_LEARN.json) |

### Full GSM8K **train** experience run (2026-07-30)

| Metric | Value |
|--------|------:|
| Worked lessons loaded | 7378 |
| Successfully taught (encoded hop traces) | **7284** (~98.7%) |
| Traces retained in bank | **7283** |
| Taught-wording retention | **7283 / 7284 = 99.99%** |
| Novel-number transfer (prove) | **100 / 100 = 100%** |
| Mean trace strength (final) | ~2.51 |
| Trace bank size | ~5.7 MB |

Reproduce:

```powershell
$env:PYTHONPATH = (Get-Location).Path
$env:FSOT_STANDALONE = "1"
python scripts/run_multihop_experience_learn.py --train-limit 8000 --epochs 8 --practice-n 100
```

### What “learned” means here

1. Teacher shows worked solutions (`<<a op b = c>>` from train).
2. Organism stores a **hop trace** (method) keyed by language skeleton — not the test answer.
3. Practice replays the method on **novel numbers** through `apply_atomic` + WM.
4. Sleep densifies strong traces.
5. Prove = retention of taught wording + transfer to new numbers.

### Explicitly not claimed

- Official GSM8K **test** overall accuracy as a product metric  
- That soft transfer to *unseen story paraphrases* is solved  
- That Zig and Python multi-hop banks are fully fused in one process yet  

---

## Related artifacts

| Path | Role |
|------|------|
| `data/math_learn/episode_bank.json` | Older Q→A-style episodes (legacy + drills) |
| `data/math_templates/TRAIN_TEMPLATES.json` | Mined train templates (optional curriculum bulk) |
| `data/results/MATH_EXPERIENCE_LEARN.json` | Latest unattended school report |
| `docs/CAPABILITY_FRONTIER.md` | Unclaimed gaps |

---

## Dual stack (how the pieces fit)

```text
Zig mind (embodiment/zig)
  genetic neurons · multi-region brain · learn/sleep/claim loops
  computer-native I/O · parity with Python substrate

Python multi-hop organism (fsot_nuron)
  experience school · episodic hop traces · WM atomics
  capacity report above

Bridge (ongoing)
  claimability · intel-loop · shared doctrine train→sleep→prove
```

Update this file when a new full experience run or Zig mind milestone lands.
