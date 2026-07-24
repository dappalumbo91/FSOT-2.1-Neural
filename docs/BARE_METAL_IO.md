# Bare-metal I/O: serial, parallel, and “VGA”

How early firmware / QEMU kernels talk to the outside world — and what we use for the FSOT trinary body.

---

## 1. Serial (UART) — **use this first**

**What it is:** A **serial** link moves data **one bit at a time** (with start/stop framing) over a few wires. On PCs the classic console is **COM1** at I/O port **`0x3F8`** (16550 UART).

**What it is good for:**

- Boot logs (“did the kernel start?”)
- Test PASS/FAIL lines under QEMU (`-serial stdio`)
- Subconscious telemetry stream (metrics as text or trit-packed bytes)
- Matching your archive **QEMU golden_boot_serial** path

**What it is not:** High-bandwidth sensory bus by itself.

**Recommendation:** **Primary bring-up and always-on debug plane.** Our Zig kernel prints the trinary self-test over serial.

---

## 2. Parallel — two different meanings (don’t mix them)

### A) Classic PC “parallel port” (LPT, `0x378`)

Old printer port: **8 data lines at once** + handshakes. Rare on modern machines; QEMU can emulate it. Useful historically for GPIO-like bit banging, not a modern sensory standard.

### B) **Parallel datapath** (architecture — **this is what we want for trinary**)

“Parallel” here means: **many trits move in the same cycle** — a wide **TritWord** bus inside the brain kernel (e.g. 27 or 81 trits), not a 1990s printer port.

| Parallel (LPT) | Parallel (trinary datapath) |
|----------------|-----------------------------|
| External 8-bit cable era | Internal FSOT machine width |
| Optional in QEMU | **Core of embodiment** |
| Not required for boot | Required for non-dumb trit ops |

**Recommendation:** Implement **parallel trinary words inside Zig**; do **not** depend on PC LPT. Serial carries logs; parallel trit ops carry the mind.

---

## 3. VGA / display — **later sensory cortex, not early brain**

People say “VGA” when they mean **early video**:

| Mode | What it does |
|------|----------------|
| **VGA text mode** | 80×25 characters in video RAM (`0xB8000`) — crude console on screen |
| **VGA graphics** | Pixel framebuffer (legacy modes) |
| **Modern framebuffer / VirtIO-GPU** | QEMU/UEFI linear framebuffer — real vision path later |

**What display is good for:**

- Optional human-facing console
- Later **vision sensory** (render or ingest frames)

**What it is not good for first:**

- Proving trinary ops or kernel liveness (serial is simpler and scriptable)
- Subconscious plant metrics (serial/log is enough)

**Recommendation:** **Defer display.** Add framebuffer when U-Net / vision inject needs pixels. Not required for QEMU trinary gate.

---

## 4. How BIOS / firmware fits

Rough boot story on x86:

```text
Firmware (UEFI or legacy BIOS)
  → loads bootloader / multiboot kernel
  → CPU jumps to our _start
  → we own the machine (no OS)
  → we talk via:
       serial UART  (debug + telemetry)
       memory-mapped or port I/O
       later: virtio / framebuffer / disk
```

QEMU can:

- Emulate **serial** → your terminal (`-serial stdio`)
- Emulate **display** → window or none (`-display none` for CI)
- Load a **multiboot kernel** with `-kernel`

Your physical-archive verification already treats **QEMU serial (+ disk)** as a bare-metal truth path for the boot scalar. We mirror that for trinary.

---

## 5. Recommended combo for FSOT neural body

| Plane | Channel | Role |
|-------|---------|------|
| **Bring-up / logs** | **Serial UART** | Always on; QEMU CI; subconscious text/trit stream |
| **Mind datapath** | **Parallel TritWord** (internal) | Custom trit ops, codon words, W apply |
| **Vision (later)** | Framebuffer / VirtIO-GPU / shared mem | Sensory cortex, not boot |
| **Persistence** | Disk / virtio-blk / raw image | LTM / brain state on “body” storage |

So: **serial + parallel (trinary bus)** is exactly right.  
**VGA/display** is optional and later — and “VGA” is the old name for the display plane, not the right primary for a silicon brain’s thoughts.

---

## 6. Practical QEMU flags (this repo)

```powershell
# From embodiment/zig after build:
qemu-system-x86_64 -display none -serial stdio -no-reboot -kernel zig-out/bin/fsot_trit_kernel
```

Expect serial lines like `FSOT_TRIT PASS` / `FAIL`.
