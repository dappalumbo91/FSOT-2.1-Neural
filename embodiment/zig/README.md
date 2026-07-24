# FSOT trinary Zig body

Custom trinary substrate in **Zig** (host test + freestanding QEMU kernel).

## Why Zig here

- Less “batteries included” than Rust → we design trit ops ourselves  
- Matches SR-ITE Zig lineage on the physical archive  
- Freestanding + QEMU serial bring-up  

## I/O planes (see `docs/BARE_METAL_IO.md`)

| Plane | Channel |
|-------|---------|
| Logs / CI | **Serial UART COM1** |
| Mind | **Parallel TritWord** ops inside the kernel |
| Display | Later (not required for PASS) |

## Build

```powershell
cd "I:\fsot nuron\embodiment\zig"
zig build host     # native self-test
zig build kernel   # freestanding Multiboot ELF
```

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
