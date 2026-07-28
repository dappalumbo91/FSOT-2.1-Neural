# Product UI & display — local, no web primary

Goal: a **usable product** with a **nice visual system**, while the neural core can still drop to **bare metal / QEMU**.  
Constraint you set: **local**, not a web app as the main interface.

---

## 1. How normal operating systems get a display

Rough stack (desktop PC):

```text
App draws pixels (Direct3D / Vulkan / OpenGL / GDI / Metal)
        ↓
OS window compositor (DWM on Windows, Wayland/X11 on Linux)
        ↓
GPU driver
        ↓
Framebuffer → monitor (HDMI/DP)
```

The app never “is” the GPU; it asks the OS for a **window** and a **swap chain**.  
Keyboard/mouse come through the OS event queue.

**Servers / headless:** no monitor; only logs (serial, stdout) — like our QEMU kernel today.

---

## 2. What QEMU has (guest “machine” display)

Inside QEMU the “PC” can expose:

| Device | What you get | Effort | Look & feel |
|--------|--------------|--------|-------------|
| **Serial UART** | Text log only | Done | Terminal / log file |
| **VGA text mode** (`0xB8000`) | 80×25 characters | Low–med | Retro console |
| **VGA / Bochs framebuffer** | Linear pixel buffer | Med | Full software UI in guest |
| **VirtIO-GPU** | Modern virtual GPU | Higher | Guest draws; host shows QEMU window |
| **Host window (`-display gtk/sdl`)** | You *see* the guest framebuffer | Config | QEMU’s window is the screen |

So: **operating systems use framebuffer + GPU**. QEMU **emulates** that so a guest kernel *or* guest OS can paint. Our Zig kernel currently uses **serial only** (correct for bring-up).

---

## 3. Two product architectures (pick one primary)

### Option P1 — **Host-native UI + brain engine** (recommended for “usable product” now)

```text
┌─────────────────────────────────────────┐
│  Local desktop app (no browser, no HTTP) │
│  charts · graph · controls · playback    │
└─────────────────┬───────────────────────┘
                  │ local IPC only
                  │ (named pipe / shared memory / stdin protocol)
┌─────────────────▼───────────────────────┐
│  Brain engine                             │
│  Python lab  and/or  Zig native process   │
└─────────────────┬───────────────────────┘
                  │ optional
┌─────────────────▼───────────────────────┐
│  QEMU freestanding Zig (verification body)│
│  serial telemetry → UI log pane           │
└─────────────────────────────────────────┘
```

**Pros:** Beautiful UI with normal GPU; fast iteration; feels like a real product.  
**Cons:** Brain is not *only* inside QEMU (QEMU remains proof-of-body).  
**Fits your constraint:** 100% local, **no web server**, no cloud.

### Option P2 — **UI drawn inside QEMU guest**

```text
Zig (or mini userspace) writes pixels → VirtIO-GPU / framebuffer
QEMU window shows it on the host monitor
```

**Pros:** Single “machine” story; closer to “the mind is the OS of the body.”  
**Cons:** You reinvent windowing, fonts, widgets inside freestanding code; much slower to make “nice.”  
**Use when:** you want a **self-contained silicon organism** demo after the product UI exists.

### Option P3 — Hybrid (best long game)

- **Daily product:** P1 native UI  
- **Body verification:** P2 or serial-only QEMU  
- Same trit/brain ABI so both talk the same language  

### Option P4 — **Scavenge open-source Linux display stack** (strong recommendation)

**Do not reinvent windows, fonts, input, and compositors in freestanding Zig.**  
Reuse what Linux already solved under open licenses.

```text
┌──────────────────────────────────────────────────┐
│  Your FSOT app (Python/Zig)                        │
│  GTK / Qt / Dear ImGui / SDL  (existing widgets)   │
└──────────────────────┬───────────────────────────┘
                       │ uses
┌──────────────────────▼───────────────────────────┐
│  Linux userspace (open source)                     │
│  FreeType (fonts) · Pango · Cairo · libinput       │
│  Wayland or X11 · Mesa (OpenGL/Vulkan) · DRM/KMS   │
└──────────────────────┬───────────────────────────┘
                       │ runs on
┌──────────────────────▼───────────────────────────┐
│  A) Host Linux / WSL2-with-WSLg / dual-boot        │  easiest product
│  B) Minimal Linux *guest* in QEMU (Buildroot/Alpine)│ body + display together
│  C) Same guest kernel + your Zig brain as a process │ organism + UI
└──────────────────────────────────────────────────┘
```

**What you scavenge (examples, all FOSS):**

| Need | Open-source component | License examples |
|------|------------------------|------------------|
| Fonts rendering | FreeType, HarfBuzz, Pango | FTL/GPL, MIT |
| 2D vector / UI paint | Cairo, Skia | MPL/MIT |
| Windowing | Wayland (wlroots), X11 | MIT |
| Full toolkits | GTK 4, Qt (LGPL), FLTK | LGPL/GPL |
| Immediate-mode UI | Dear ImGui, Nuklear | MIT |
| GPU | Mesa | MIT |
| Tiny stack | DirectFB / DRM dumb buffer + FreeType | various |
| Whole minimal OS | Alpine, Buildroot, Yocto, FreeBSD | various |

**You still write:** FSOT brain, scalpel, memory probe, telemetry, product layout.  
**You do not write:** font engines, Unicode shaping, window managers, GPU drivers.

**QEMU fit:** boot **Alpine or Buildroot Linux** as the guest (not bare metal for the *product* UI path). Run:

- `fsot_brain` (Zig or Python) as a normal Linux process  
- UI as another process or same process with GTK/Qt/ImGui  
- Optional: keep **freestanding Zig kernel** as a second QEMU machine for verification only  

**Windows host fit:** develop UI with the same idea — use existing stacks (Qt/PySide, Dear PyGui) which themselves wrap OS fonts/windowing. Or run Linux guest under QEMU/WSL for a pure Linux scavenged stack.

**Licensing note:** prefer MIT/BSD/Apache/LGPL toolkits for a product you control; read GPL implications if you statically link GPL-only pieces. Alpine + MIT/LGPL UI is a common pattern.

**Why this beats pure freestanding UI:** months of work become days; “nice” is free; you stay local and offline-capable; bare-metal freestanding remains for *body law*, not *chrome*.

---

## 4. Local UI toolkits (no web primary)

| Stack | Look | Language fit | Notes |
|-------|------|--------------|-------|
| **Dear ImGui** (+ OpenGL/Vulkan/DX) | Pro tools, real-time graphs | C++/Zig bindings | Excellent for live spike/region meters; pure local |
| **Dear PyGui** | Similar, Python | Python lab | Fastest path from current `run_*.py` stack |
| **Qt / PySide6** | Full desktop app | Python | Dockable panels, plots (QtCharts), native feel |
| **WinUI 3 / WPF** | Windows-native | C# | Best Windows polish; IPC to Python/Zig |
| **egui (Rust)** | Immediate-mode | Rust | If engine shifts more to Rust |
| **Raylib / SDL2 custom** | Game-like | C/Zig | Full control, more DIY widgets |
| **Obsidian vault** (already) | Graph of notes | Files only | Design board, not live control |

**Avoid as primary:** Electron/Tauri *if* you want zero web tech. (They package a browser; local but not “non-web.”)  
**Acceptable later:** optional local-only HTML export of reports — not the live console.

**Recommendation for FSOT-Neural product v1:**

1. **Scavenge Linux UI stack (P4)** *or* host **Dear PyGui / PySide6** on Windows — both reuse fonts/windows instead of inventing them.  
2. Prefer: **Python brain + scavenged toolkit** first; **Zig brain as Linux process** second; **freestanding QEMU** stays the accuracy/body gate.  
3. Live views: region rates, class locks, encode/retrieve, band meters, serial/log from engine.  
4. Optional later: full **Alpine/Buildroot guest** so “the organism” boots Linux + your UI + your brain in one QEMU window.

---

## 5. How the UI talks to the brain (local only)

| Channel | Web? | Use |
|---------|------|-----|
| **In-process Python API** | No | Simplest v1 |
| **Named pipe / Unix socket** | No | UI ↔ Zig engine |
| **Shared memory ring buffer** | No | High-rate spike streams |
| **QEMU serial file / pipe** | No | Telemetry from freestanding kernel |
| HTTP localhost | Technically local but “web-shaped” | Avoid as primary |

Protocol sketch (binary or JSON lines):

```text
CMD scalpel lock tol=0.01
CMD probe items=12 delay=600 consolidate=1
CMD step n=100
EVT rates pyr=16.3 pv=83.2 ...
EVT retrieve top1=0.75
EVT serial "FSOT_FP PASS"
```

---

## 6. Visual system — what to show (product screens)

| Screen | Content |
|--------|---------|
| **Dashboard** | Pin status, scalpel class errors, last probe scores |
| **Brain map** | Regions (thal/sens/assoc/hipp), live rates, E/I |
| **Cell classes** | Pyr/PV/SST/VIP vs Allen targets (bar + error %) |
| **Memory lab** | Encode list, delay slider, consolidate button, confusion |
| **Bands** | Theta/alpha/gamma meters (model-Hz) |
| **Body** | QEMU run button, serial console pane, FP PASS badge |
| **Thesis** | Link to checkpoint metrics (read-only) |

Looks “neurological”: activity heat on regions, spike rasters, fingerprint similarity matrix — all local GPU.

---

## 7. Relation to “dropping to bare metal”

| Layer | Role in product |
|-------|-----------------|
| **Accurate science core** | Frozen at v0.5 checkpoint |
| **Engine** | Python now; Zig for speed/body |
| **UI** | Host-native (recommended) |
| **QEMU** | Proves the body still boots; serial/FP; optional guest graphics later |

You do **not** need the UI to live at BIOS level to have a product.  
You **do** need the **brain calculations** able to live there — which we already gate with QEMU.

---

## 8. Proposed product milestone (next build phase)

**FSOT Neural Console v0.5 (local product screens) — landed**  
**FSOT Neural Console v0.6 — adaptive body + Obsidian Visual — landed**  
**FSOT Neural Console v0.7 — multi-region + host senses + self-mod + live vault — landed**

```powershell
python run_console.py
python run_stress_suite.py          # stage break map
python run_stress_suite.py --quick
```

| Screen | Content |
|--------|---------|
| Dashboard | Boot checklist, pin, hardware adaptation strip, stress buttons, science jobs |
| Cell classes | Pyr/PV/SST/VIP vs Allen wet-lab (from scalpel artifacts) |
| Memory lab | FSOT-bridged encode/delay/retrieve scores |
| Encode | Machine ★ / chemical / Morse + inject |
| Body | **Adaptive host sensors** (CPU/RAM/disk/CUDA/psutil) + Zig host + QEMU |
| **Visual** | **Multi-region Obsidian graph** (thal/sens/assoc/hipp) · host senses · POOF/SUCTION · live vault ticks |
| Live / stress | Folds + stress break map |
| Engine log | Subprocess stdout |

### v0.6 doctrine (computer as body)

- **Not locked to one PC:** `fsot_nuron/hardware_body.py` re-probes on every boot (`discover_hardware`).
- **Adaptation:** recommended `device` / `n_units` / `dt_ms` from available RAM, CPU, CUDA.
- **Interoception:** `sample_metrics` → `MetricPacket` → `SYS_METRIC` thalamic packet (autonomic plant).
- **Visual:** `product/console/visual_brain.py` — genetic sparse W as Obsidian graph; live `step()` with host-metric modulation.
- Missing sensors **gracefully omit** (strength 0) — same mind, different bodies.

1. Science frozen: `v0.5.0-bio-intel` (+ continuous-ms ≤1% timing path)  
2. `product/console/` via **tkinter** (host OS fonts/windows; no web)  
3. Stress suite: `run_stress_suite.py` → `docs/STRESS_STAGE_REPORT.md`  
4. Later: Dear PyGui/GTK-on-Alpine upgrade without changing brain ABI  

Encoding doctrine: [`docs/MACHINE_ENCODING.md`](MACHINE_ENCODING.md).  
Application recipe: [`docs/FSOT_APPLICATION_NEURAL.md`](FSOT_APPLICATION_NEURAL.md).  
Hardware body: [`docs/HARDWARE_BODY.md`](HARDWARE_BODY.md).

---

## 9. Short answers to your questions

**“How do OSes normally display?”**  
Apps draw into OS-managed GPU buffers; compositor sends frames to the monitor.

**“We’re in QEMU — how do we display?”**  
Either paint a **guest framebuffer/VirtIO-GPU** (inside the machine), or run a **host app** that displays while the brain runs in-process or in QEMU with serial/IPC (recommended for a nice UI).

**“Local, no web?”**  
Yes: native toolkit + local IPC. QEMU window is local too if you go full guest graphics later.
