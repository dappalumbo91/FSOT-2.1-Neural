# FSOT trinary Zig neurological body

Custom trinary substrate in **Zig** — host mind, freestanding QEMU kernel, genetic neurons.

**Learned capacity snapshot (repo-wide):** [`docs/LEARNED_CAPACITY.md`](../../docs/LEARNED_CAPACITY.md)

## Why Zig here

- Less “batteries included” than Rust → we design trit ops ourselves  
- Matches SR-ITE Zig lineage on the physical archive  
- Freestanding + QEMU serial bring-up  
- **Mind authority** lives here: multi-region brain, learn/sleep, claimability, intel-loop  

## I/O planes (see `docs/BARE_METAL_IO.md`)

| Plane | Channel |
|-------|---------|
| Logs / CI | **Serial UART COM1** |
| Mind | **Parallel TritWord** ops inside the kernel |
| Display | Later (not required for PASS) |

## Build

```powershell
cd "I:\fsot nuron\embodiment\zig"
zig build -Doptimize=ReleaseSafe   # install all artifacts
zig build host                     # native trit/neuron parity host
zig build mind -- all              # **mind authority** (multi-region + learn)
zig build kernel                   # freestanding Multiboot ELF (QEMU)
```

| Binary | Role |
|--------|------|
| `fsot_mind.exe` | **Neural authority** — brain + learn + live + inject |
| `fsot_trit_host.exe` | Parity trace for Python harness |
| `fsot_trit_kernel` | Bare-metal mind self-test over serial |

From repo root: `python run_mind_boot.py` (spawns Zig; Python does not step neurons).

## QEMU

```powershell
# Requires qemu-system-x86_64 on PATH
.\run_qemu.ps1
# or:
qemu-system-x86_64 -display none -serial stdio -no-reboot -kernel zig-out\bin\fsot_trit_kernel
```

Expect: `FSOT_TRIT PASS` on the serial console.

## Parity with Python

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "."
python -c "from fsot_nuron.trinary_substrate import self_test; print(self_test())"
```

Both must report ok; codon ATG → `+1,-1,+1`.
