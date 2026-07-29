# Host I/O in Zig — no C/Rust required

**Repo path only.** Doctrine for sensory/motor hardware access.

## Why not C or Rust “above” Zig?

Zig already does what C and Rust do for systems work:

| Need | Zig |
|------|-----|
| Bare metal / freestanding | Yes (`main_kernel`, QEMU) |
| Call OS / Win32 / libc / syscalls | Yes (`extern`, `std.os`) |
| Drivers / MMIO (with privilege) | Yes (same as C) |
| Link GDI, WASAPI, PipeWire, ALSA | Yes (system libraries) |
| No GC, explicit control | Yes |

**C** is only needed as an *ABI* when an existing library is C-only (you still call it *from Zig*).  
**Rust** is optional taste/ecosystem, not a capability gap.

**Mind authority stays Zig Fixed.** Host I/O is a *plant layer* that produces feature frames for `sensory_fixed` / `inject_io_fixed` — same as biological receptors → thalamus/cortex.

```text
mic / speakers / display framebuffer / plant metrics
        │  (Zig host I/O)
        ▼
  Fixed feature packets (vision / audio / hid / metric)
        │
        ▼
  anatomical routes (thal / sens / assoc / hipp)
        │
        ▼
  genetic fixed brain + speech organ (efferent → speakers later)
```

## Linux as a map, not a dependency

Open-source Linux (ALSA/PipeWire, DRM/KMS, evdev) is an **excellent guide** for *what* to implement. On Windows we use the local equivalents (WASAPI, DXGI/GDI, HID). Same *roles*, different syscalls. Mind code does not care.

## Display as sensory input (not screenshots)

| Wrong | Right |
|-------|--------|
| Save PNG every N seconds and reload | Continuous **framebuffer / compositor capture** |
| “Hijack HDMI wire” (hardware tap) | Sample what the **display path already composed** |

**Windows:** Desktop Duplication (DXGI) or GDI `BitBlt` of desktop DC — live pixels, no file.  
**Linux:** PipeWire screen cast or DRM dumb buffer (privileged).

This is **exteroception of the visual workspace** the body is driving — analogous to eyes looking at the world the body acts in, not a camera app screenshot workflow.

## Audio (mic + speakers)

| Direction | Role |
|-----------|------|
| **Mic** | Afferent → `audio` modality features (RMS, simple bands) |
| **Speakers** | Efferent endpoint for speech organ acoustics (later: render motor→sound) |

Most machines have both. Wire immediately when present; degrade gracefully when not.

## Capability growth (honest stages)

1. **Now:** Zig host sample → Fixed inject → bio routes → organism (this tree).  
2. **Next:** DXGI Desktop Duplication, WASAPI exclusive/loopback, speaker render of speech organ.  
3. **Later:** richer phoneme hearing, continuous motor trajectories, Linux native backends.

Speech *understanding* and deep vision ID remain **capability** work; **wiring** is plant I/O.
