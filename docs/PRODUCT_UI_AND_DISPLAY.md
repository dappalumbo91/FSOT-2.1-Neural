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

1. **Dear PyGui** or **PySide6** control surface on Windows (talks to existing Python brain + scalpel + probe).  
2. Live views: region rates, class locks, encode/retrieve, band meters, serial log from QEMU.  
3. Parallel: Zig process ABI for when UI should call bare-metal-speed step without QEMU.  
4. Later: optional guest framebuffer for “organism display.”

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

**FSOT Neural Console v0.1 (local)**

1. Freeze science: `v0.5.0-bio-intel` tag  
2. Scaffold `product/console/` Dear PyGui or PySide app  
3. Buttons: Pin · Scalpel · Probe · Consolidate · QEMU check  
4. Panels: class accuracy, retrieve score, serial log  
5. No network listeners  

Then resume intelligence climbs from `INTELLIGENCE_ROADMAP_OPTIONS.md` **through the console**.

---

## 9. Short answers to your questions

**“How do OSes normally display?”**  
Apps draw into OS-managed GPU buffers; compositor sends frames to the monitor.

**“We’re in QEMU — how do we display?”**  
Either paint a **guest framebuffer/VirtIO-GPU** (inside the machine), or run a **host app** that displays while the brain runs in-process or in QEMU with serial/IPC (recommended for a nice UI).

**“Local, no web?”**  
Yes: native toolkit + local IPC. QEMU window is local too if you go full guest graphics later.
