#!/usr/bin/env python3
"""
FSOT Neural Console v0.5 — product screens (tkinter, local, no web).

Aligned with docs/PRODUCT_UI_AND_DISPLAY.md:
  Dashboard · Cell classes · Memory · Encode · Body · Live · Log

Display doctrine:
  - Human summary first (plain English)
  - Wet-lab accuracy numbers (Allen rates, probe top-1)
  - Archive FSOT pin/bridge on every claim path
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk, messagebox
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("PYTHONPATH", str(ROOT))
os.environ.setdefault("FSOT_PHYSICAL_ARCHIVE", r"I:\FSOT-Physical-Archive")

ZIG_HOST = ROOT / "embodiment" / "zig" / "zig-out" / "bin" / "fsot_trit_host.exe"
ZIG_QEMU = ROOT / "embodiment" / "zig" / "run_qemu.ps1"


# ---------------------------------------------------------------------------
# Formatters — readable outcomes for every display surface
# ---------------------------------------------------------------------------

def _fmt_yes(v: Any) -> str:
    return "YES" if v else "NO"


def format_boot_report(
    pin: Any,
    folds: Dict[str, Any],
    bridge: Dict[str, Any],
    machine: Dict[str, Any],
    zig_ok: Optional[bool],
) -> str:
    lines = [
        "BOOT CHECKLIST",
        "==============",
        "",
        "What this means:",
        "  The archive math is pinned, domain folds recompute S = K(T1+T2+T3),",
        "  and the machine body ABI (not Morse) round-trips correctly.",
        "",
        f"1. Archive pin ............. {_fmt_yes(pin.connected)}",
        f"   Seed match .............. {_fmt_yes(pin.seed_match_ok)}",
        f"   Authority hash .......... {(pin.compute_sha256 or 'missing')[:24]}…",
        f"   Lean proved / 7-way ..... {_fmt_yes(pin.lean_build_ok)} / {_fmt_yes(pin.seven_way_bare_metal)}",
        "",
        "2. Domain folds (preregistered — not free fits)",
    ]
    for name, fd in (folds.get("folds") or {}).items():
        lines.append(
            f"   {name:18}  S = {fd['S']:+.4f}   trit = {fd['trit']:+d}   D_eff = {fd['D_eff']}"
        )
    lines += [
        "",
        "   Expected atlas: Biology ≈ +0.445 · Neuroscience ≈ +0.514",
        f"   Atlas match ............. {_fmt_yes(bridge.get('atlas_ok'))}",
        "",
        f"3. FSOT bridge ............. {_fmt_yes(bridge.get('ok'))}",
        f"   Free parameters ......... {bridge.get('free_parameters', '?')}",
        f"   Formula ................. {bridge.get('formula')}",
        "",
        f"4. Machine ABI (body I/O)",
        f"   UTF-8 lossless .......... {_fmt_yes(machine.get('utf8_roundtrip_ok'))}",
        f"   Frame round-trip ........ {_fmt_yes(machine.get('frame_roundtrip_ok'))}",
        f"   Chem→machine ............ {_fmt_yes(machine.get('chem_bridge_ok'))}",
        f"   Trits for sample ........ {machine.get('n_trits')}",
        "",
        f"5. Zig body host present ... {_fmt_yes(zig_ok)}",
        f"   Path: {ZIG_HOST if zig_ok else '(build with zig build in embodiment/zig)'}",
        "",
    ]
    boot_ok = bool(
        pin.connected
        and pin.seed_match_ok
        and bridge.get("ok")
        and machine.get("utf8_roundtrip_ok")
        and machine.get("frame_roundtrip_ok")
    )
    lines.append("RESULT: " + ("BOOT PASS — system ready to run science buttons." if boot_ok else "BOOT FAIL — fix archive pin / FSOT_PHYSICAL_ARCHIVE."))
    lines.append("")
    return "\n".join(lines), boot_ok


def format_encode_summary(text: str, path: str, out: Dict[str, Any], frame: Dict[str, Any], fsot: Optional[Dict[str, Any]]) -> str:
    lines = [
        "MACHINE ENCODE SUMMARY",
        "======================",
        "",
        f"Input text ........ {text[:80]!r}",
        f"Path .............. {path.upper()}" + ("  ★ primary body path" if path == "machine" else ""),
        f"Primary path? ..... {_fmt_yes(out.get('primary', path != 'morse'))}",
        f"What it did ....... {out.get('note', '')}",
        "",
        f"Trit count ........ {out.get('n_trits')}",
        f"Machine words ..... {len(out.get('words') or [])}",
        f"ABI frame bytes ... {frame.get('byte_len')}",
        f"ABI magic ......... {frame.get('magic')} v{frame.get('version')}",
        f"Hex head .......... {(frame.get('hex_head') or '')[:48]}…",
    ]
    if out.get("roundtrip_ok") is not None:
        lines.append(f"UTF-8 round-trip .. {_fmt_yes(out.get('roundtrip_ok'))}")
        if out.get("roundtrip_preview"):
            lines.append(f"Round-trip text ... {out.get('roundtrip_preview')!r}")
    if fsot and fsot.get("modulators"):
        m = fsot["modulators"]
        lines += [
            "",
            "FSOT couple (through archive scalar — not a free constant)",
            f"  Fold ............ {fsot.get('fold')}",
            f"  S ............... {m.get('S'):+.6f}" if isinstance(m.get("S"), (int, float)) else f"  S ............... {m.get('S')}",
            f"  Trit ............ {m.get('trit')}",
            f"  Sensory strength  {m.get('sensory_strength'):.3f}" if isinstance(m.get("sensory_strength"), (int, float)) else "",
            f"  Feature gain .... {m.get('feature_gain')}",
        ]
    if path == "morse":
        lines += [
            "",
            "NOTE: Morse is SECONDARY (human telegraphy demo only).",
            "      Prefer MACHINE for the computer body.",
        ]
    lines += ["", "Detail (first words):"]
    for i, w in enumerate((out.get("words") or [])[:3]):
        lines.append(f"  word[{i}] n_trits={w.get('n_trits')} hex={w.get('hex', '')[:16]}")
    lines.append("")
    return "\n".join(lines)


def format_chem_summary(dna: str, abi: Dict[str, Any], fsot: Dict[str, Any]) -> str:
    chem = abi.get("chemical") or {}
    m = (fsot.get("modulators") or {})
    lines = [
        "CHEMICAL → MACHINE SUMMARY",
        "==========================",
        "",
        f"DNA used .......... {dna[:60]}",
        f"Codons / trits .... {chem.get('n_codons')} / {abi.get('n_trits')}",
        f"AA sequence ....... {chem.get('aa_sequence', '')[:40]}",
        f"Map perfect? ...... {_fmt_yes((chem.get('verify') or {}).get('perfect'))}",
        "",
        "FSOT Biology fold couple",
        f"  Fold ............ {fsot.get('fold')}",
        f"  S ............... {m.get('S'):+.6f}" if isinstance(m.get("S"), (int, float)) else f"  S ............... {m.get('S')}",
        f"  Strength ........ {m.get('sensory_strength'):.3f}" if isinstance(m.get("sensory_strength"), (int, float)) else "",
        "",
        "Meaning: codon map is the genetic spine; machine frame carries it as OS words.",
        "",
    ]
    return "\n".join(lines)


def format_inject_summary(path: str, pkt: Any, ext_stats: Dict[str, Any]) -> str:
    meta = pkt.meta if hasattr(pkt, "meta") else {}
    lines = [
        "SENSORY INJECT SUMMARY",
        "======================",
        "",
        f"Encode path ....... {path}",
        f"Target region ..... {pkt.target_region}",
        f"Modality .......... {pkt.modality.value if hasattr(pkt.modality, 'value') else pkt.modality}",
        f"Strength .......... {pkt.strength:.3f}  (FSOT-coupled when machine/chemical)",
        f"Features (head) ... {[round(x, 3) for x in (pkt.features or [])[:8]]}",
        "",
        "FSOT meta on packet",
        f"  Bridge .......... {meta.get('fsot_bridge')}",
        f"  Fold ............ {meta.get('fold')}",
        f"  S ............... {meta.get('S')}",
        f"  Trit ............ {meta.get('trit')}",
        "",
        "External drive into multi-region brain (demo layout)",
        f"  Units ............ {ext_stats.get('n_units')}",
        f"  Non-zero units ... {ext_stats.get('nonzero')}",
        f"  Mean / max ....... {ext_stats.get('mean'):.4f} / {ext_stats.get('max'):.4f}",
        f"  Sensory head ..... {[round(x, 3) for x in ext_stats.get('sens_slice_head', [])]}",
        "",
        "Outcome: packet is ready for SensoryBus → brain.step external drive.",
        "",
    ]
    return "\n".join(lines)


def format_compare_summary(text: str, rows: Dict[str, Dict[str, Any]]) -> str:
    lines = [
        "PATH COMPARISON",
        "===============",
        "",
        f"Input: {text[:60]!r}",
        "",
        f"{'path':12} {'primary':8} {'trits':>8} {'words':>6} {'frameB':>8}  role",
        "-" * 72,
    ]
    roles = {
        "machine": "OS body ★",
        "chemical": "DNA/codon genetics",
        "morse": "human demo only",
    }
    for p, r in rows.items():
        lines.append(
            f"{p:12} {str(r.get('primary')):8} {r.get('n_trits') or 0:8} "
            f"{r.get('n_words') or 0:6} {r.get('frame_bytes') or 0:8}  {roles.get(p, '')}"
        )
    lines += [
        "",
        "Prefer MACHINE for the computer body. Chemical for genetics. Morse is secondary.",
        "",
    ]
    return "\n".join(lines)


def format_live_metrics(
    folds: Dict[str, Any],
    bridge: Dict[str, Any],
    machine: Dict[str, Any],
    artifacts: List[str],
) -> str:
    lines = [
        "LIVE METRICS",
        "============",
        "",
        f"Pin OK ............ {_fmt_yes(folds.get('pin_ok'))}",
        f"Bridge OK ......... {_fmt_yes(bridge.get('ok'))}",
        f"Machine UTF-8 ..... {_fmt_yes(machine.get('utf8_roundtrip_ok'))}",
        f"Machine frame ..... {_fmt_yes(machine.get('frame_roundtrip_ok'))}",
        "",
        "Domain S (live recompute through archive engine)",
        f"  Biology ......... {folds.get('S_Biology'):+.4f}" if folds.get("S_Biology") is not None else "  Biology ......... ?",
        f"  Neuroscience .... {folds.get('S_Neuroscience'):+.4f}" if folds.get("S_Neuroscience") is not None else "  Neuroscience .... ?",
        f"  Computer_Body ... {folds.get('S_Computer_Body'):+.4f}" if folds.get("S_Computer_Body") is not None else "  Computer_Body ... ?",
        "",
        "Last science artifacts (if you ran Scalpel / Intel)",
    ]
    if not artifacts:
        lines.append("  (none yet — run Quick intel or Scalpel from Dashboard)")
    else:
        lines.extend(artifacts)
    lines += ["", f"Project root: {ROOT}", ""]
    return "\n".join(lines)


def _load_artifact_summaries() -> List[str]:
    out: List[str] = []
    for name in ("intelligence_probe.json", "scalpel_rates.json"):
        path = None
        for base in (ROOT / "artifacts", ROOT / "data" / "results"):
            p = base / name
            if p.is_file():
                path = p
                break
        if path is None:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            out.append(f"  {name}: read error {e}")
            continue
        if name.startswith("intelligence"):
            tops = []
            for k, v in (data.get("results") or {}).items():
                if isinstance(v, dict) and "top1_accuracy" in v:
                    tops.append(f"{k}={v['top1_accuracy']:.3f}")
            folds = data.get("fsot_folds") or {}
            out.append(f"  INTEL  ({path.parent.name}/{name})")
            out.append(f"    top-1: {', '.join(tops) if tops else 'n/a'}")
            out.append(f"    item_mode: {(data.get('params') or {}).get('item_mode')}")
            out.append(
                f"    S_bio={folds.get('S_Biology')}  S_neuro={folds.get('S_Neuroscience')}"
            )
            gates = data.get("gates") or {}
            bad = [k for k, v in gates.items() if v is False]
            out.append(f"    gates failed: {bad if bad else 'none'}")
        else:
            gates = data.get("gates") or {}
            out.append(f"  SCALPEL ({path.parent.name}/{name})")
            out.append(f"    scalpel_ok: {gates.get('scalpel_ok')}  tol={data.get('tol')}")
            rep = (data.get("report") or {}).get("classes") or data.get("report") or {}
            # report.classes structure varies
            classes = rep if isinstance(rep, dict) and any(
                isinstance(v, dict) and "rel_err" in v for v in rep.values()
            ) else (data.get("report") or {}).get("classes") or {}
            if not classes and isinstance(data.get("report"), dict):
                classes = data["report"].get("classes") or {}
            for lab, st in list(classes.items())[:6]:
                if isinstance(st, dict):
                    out.append(
                        f"    {lab}: target={st.get('target_Hz')} measured={st.get('measured_Hz')} "
                        f"err={st.get('rel_err')}"
                    )
            folds = data.get("fsot_folds") or {}
            if folds:
                out.append(
                    f"    S_bio={folds.get('S_Biology')}  S_neuro={folds.get('S_Neuroscience')}"
                )
    return out


def _looks_like_dna(text: str) -> bool:
    if not text or len(text) < 3:
        return False
    cleaned = "".join(c for c in text.upper() if c.isalpha())
    if len(cleaned) < 3:
        return False
    return all(c in "ACGTUN" for c in cleaned)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class ConsoleApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FSOT Neural Console v0.5 — product screens · local · no web")
        self.geometry("1220x840")
        self.minsize(1000, 680)
        self.configure(bg="#1a1d23")
        self._log_q: queue.Queue[str] = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._boot_ok = False
        self._zig_fp = False
        self._build()
        self.after(100, self._drain_log)
        self._log(
            "FSOT Neural Console v0.5 (product design screens)\n"
            "Dashboard · Cell classes · Memory · Encode · Body · Live\n"
            "Archive math · wet-lab scalpel · FSOT machine intel · Zig body\n"
        )
        self.after(250, self._auto_boot)

    def _build(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        banner = tk.Frame(self, bg="#0d1117", height=78)
        banner.pack(fill=tk.X, side=tk.TOP)
        banner.pack_propagate(False)

        self.boot_title = tk.Label(
            banner,
            text="FSOT NEURAL  ·  BOOTING…",
            font=("Segoe UI", 15, "bold"),
            fg="#58a6ff",
            bg="#0d1117",
            anchor="w",
        )
        self.boot_title.pack(side=tk.LEFT, padx=12, pady=6)

        self.boot_badge = tk.Label(
            banner,
            text="● PIN ?",
            font=("Consolas", 11, "bold"),
            fg="#8b949e",
            bg="#0d1117",
        )
        self.boot_badge.pack(side=tk.RIGHT, padx=12)

        self.fold_strip = tk.Label(
            banner,
            text="S_bio=…   S_neuro=…   S_body=…",
            font=("Consolas", 11),
            fg="#3fb950",
            bg="#0d1117",
            anchor="w",
        )
        self.fold_strip.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.tab_dash = ttk.Frame(nb)
        self.tab_cells = ttk.Frame(nb)
        self.tab_mem = ttk.Frame(nb)
        self.tab_enc = ttk.Frame(nb)
        self.tab_body = ttk.Frame(nb)
        self.tab_live = ttk.Frame(nb)
        self.tab_log = ttk.Frame(nb)
        nb.add(self.tab_dash, text="Dashboard")
        nb.add(self.tab_cells, text="Cell classes")
        nb.add(self.tab_mem, text="Memory lab")
        nb.add(self.tab_enc, text="Encode")
        nb.add(self.tab_body, text="Body (Zig)")
        nb.add(self.tab_live, text="Live / stress")
        nb.add(self.tab_log, text="Engine log")

        # ----- Dashboard (design §6) -----
        ttk.Label(
            self.tab_dash,
            text="Dashboard — pin · wet-lab accuracy · last probe · stress",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor=tk.W, padx=8, pady=(8, 2))
        ttk.Label(
            self.tab_dash,
            text="Lab UI (Python) + body (Zig) + math (I:\\FSOT-Physical-Archive). No web.",
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W, padx=8, pady=(0, 6))

        boot_row = ttk.Frame(self.tab_dash)
        boot_row.pack(fill=tk.X, padx=8, pady=2)
        ttk.Button(boot_row, text="▶ BOOT SYSTEM", command=self._boot_system).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(boot_row, text="Refresh S folds", command=self._refresh_banner).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(boot_row, text="STRESS SUITE", command=self._cmd_stress).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(boot_row, text="Stress (quick)", command=self._cmd_stress_quick).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(boot_row, text="Wet-lab battery", command=self._cmd_wetlab).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(boot_row, text="Genome-as-code", command=self._cmd_cellular).pack(
            side=tk.LEFT, padx=2
        )

        btn_row = ttk.Frame(self.tab_dash)
        btn_row.pack(fill=tk.X, padx=8, pady=6)
        actions = [
            ("Pin archive", self._cmd_pin),
            ("Scalpel 1%", self._cmd_scalpel),
            ("Intel (full)", self._cmd_intel),
            ("Quick intel", self._cmd_intel_quick),
            ("Machine ABI", self._cmd_machine_verify),
            ("FSOT bridge", self._cmd_fsot_bridge),
            ("Zig parity", self._cmd_parity),
            ("Zig body", self._cmd_zig_body),
        ]
        for i, (label, cmd) in enumerate(actions):
            ttk.Button(btn_row, text=label, command=cmd).grid(
                row=0, column=i, padx=2, pady=2, sticky="ew"
            )
            btn_row.columnconfigure(i, weight=1)

        info = ttk.LabelFrame(self.tab_dash, text="Readable status (boot / last report)")
        info.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.status = scrolledtext.ScrolledText(
            info, height=20, wrap=tk.WORD, font=("Consolas", 10), bg="#0d1117", fg="#e6edf3",
            insertbackground="#e6edf3",
        )
        self.status.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.status.insert(tk.END, "Waiting for boot…\n")

        # ----- Cell classes (Allen wet-lab) -----
        ttk.Label(
            self.tab_cells,
            text="Cell classes — Pyr / PV / SST / VIP vs Allen wet-lab rates",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor=tk.W, padx=8, pady=6)
        cell_btns = ttk.Frame(self.tab_cells)
        cell_btns.pack(fill=tk.X, padx=8)
        ttk.Button(cell_btns, text="Run scalpel 1%", command=self._cmd_scalpel).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(cell_btns, text="Refresh from artifacts", command=self._refresh_cells).pack(
            side=tk.LEFT, padx=2
        )
        self.cells_out = scrolledtext.ScrolledText(
            self.tab_cells, wrap=tk.WORD, font=("Consolas", 10), bg="#0d1117", fg="#e6edf3",
            insertbackground="#e6edf3",
        )
        self.cells_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.cells_out.insert(tk.END, "Run Scalpel or Stress to fill Allen class table.\n")

        # ----- Memory lab -----
        ttk.Label(
            self.tab_mem,
            text="Memory lab — encode / delay / retrieve (FSOT machine items)",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor=tk.W, padx=8, pady=6)
        mem_btns = ttk.Frame(self.tab_mem)
        mem_btns.pack(fill=tk.X, padx=8)
        ttk.Button(mem_btns, text="Quick intel", command=self._cmd_intel_quick).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(mem_btns, text="Study EEG path", command=self._cmd_learning_eeg).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(mem_btns, text="Consolidate ladder", command=self._cmd_consolidate).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(mem_btns, text="Full suite (slow)", command=self._cmd_intel).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(mem_btns, text="Refresh results", command=self._refresh_memory).pack(
            side=tk.LEFT, padx=2
        )
        self.mem_out = scrolledtext.ScrolledText(
            self.tab_mem, wrap=tk.WORD, font=("Consolas", 10), bg="#0d1117", fg="#e6edf3",
            insertbackground="#e6edf3",
        )
        self.mem_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.mem_out.insert(
            tk.END,
            "Items are FSOT-bridged text labels (machine path), not Morse.\n"
            "Run Quick intel to see top-1 after delay.\n",
        )

        # ----- Encode -----
        ttk.Label(
            self.tab_enc,
            text="Body language: MACHINE (bytes → trits → OS words). Coupled through FSOT S on inject.",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W, padx=8, pady=4)

        path_row = ttk.Frame(self.tab_enc)
        path_row.pack(fill=tk.X, padx=8)
        ttk.Label(path_row, text="Path:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value="machine")
        for p, lab in (
            ("machine", "Machine ★"),
            ("chemical", "Chemical / DNA"),
            ("morse", "Morse (demo)"),
        ):
            ttk.Radiobutton(path_row, text=lab, variable=self.path_var, value=p).pack(
                side=tk.LEFT, padx=8
            )

        self.enc_in = scrolledtext.ScrolledText(self.tab_enc, height=4, font=("Consolas", 11))
        self.enc_in.pack(fill=tk.X, padx=8, pady=4)
        self.enc_in.insert(tk.END, "FSOT neural intelligence")

        btn_enc = ttk.Frame(self.tab_enc)
        btn_enc.pack(fill=tk.X, padx=8, pady=2)
        for lab, cmd in (
            ("Translate", self._do_encode),
            ("Chem / DNA bridge", self._do_chem_bridge),
            ("Inject into bus", self._do_inject),
            ("Compare paths", self._do_compare_paths),
        ):
            ttk.Button(btn_enc, text=lab, command=cmd).pack(side=tk.LEFT, padx=3)

        self.enc_out = scrolledtext.ScrolledText(
            self.tab_enc, height=20, font=("Consolas", 10), bg="#0d1117", fg="#e6edf3",
            insertbackground="#e6edf3",
        )
        self.enc_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # ----- Body (Zig / QEMU) -----
        ttk.Label(
            self.tab_body,
            text="Body — Zig host executable + QEMU freestanding guest",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor=tk.W, padx=8, pady=6)
        ttk.Label(
            self.tab_body,
            text="Python is the lab UI. Zig is the silicon body (trinary step). QEMU proves bare metal.",
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W, padx=8)
        body_btns = ttk.Frame(self.tab_body)
        body_btns.pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(body_btns, text="Run Zig host exe", command=self._cmd_zig_body).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(body_btns, text="Zig ↔ Python parity", command=self._cmd_parity).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(body_btns, text="QEMU guest", command=self._cmd_qemu).pack(
            side=tk.LEFT, padx=2
        )
        self.zig_badge = ttk.Label(body_btns, text="FP: unknown", font=("Consolas", 10))
        self.zig_badge.pack(side=tk.RIGHT, padx=8)
        self.body_out = scrolledtext.ScrolledText(
            self.tab_body, wrap=tk.WORD, font=("Consolas", 10), bg="#0d1117", fg="#e6edf3",
            insertbackground="#e6edf3",
        )
        self.body_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.body_out.insert(
            tk.END,
            f"Host binary:\n  {ZIG_HOST}\n  present={ZIG_HOST.is_file()}\n\n"
            f"QEMU script:\n  {ZIG_QEMU}\n  present={ZIG_QEMU.is_file()}\n\n"
            "Click Run Zig host — Engine log should show FSOT_TRIT PASS.\n",
        )

        # ----- Live / stress -----
        live_hdr = ttk.Frame(self.tab_live)
        live_hdr.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(
            live_hdr,
            text="Live pin / folds / stress break map (plain English).",
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT)
        ttk.Button(live_hdr, text="Refresh", command=self._refresh_live).pack(side=tk.RIGHT)
        ttk.Button(live_hdr, text="STRESS SUITE", command=self._cmd_stress).pack(
            side=tk.RIGHT, padx=4
        )

        self.live_out = scrolledtext.ScrolledText(
            self.tab_live, wrap=tk.WORD, font=("Consolas", 10), bg="#0d1117", fg="#e6edf3",
            insertbackground="#e6edf3",
        )
        self.live_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Log
        self.log = scrolledtext.ScrolledText(
            self.tab_log, wrap=tk.WORD, font=("Consolas", 9), bg="#0d1117", fg="#c9d1d9",
            insertbackground="#c9d1d9",
        )
        self.log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        foot = ttk.Frame(self)
        foot.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(foot, text=f"ROOT: {ROOT}", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        ttk.Button(foot, text="Docs: encoding", command=self._open_machine_doc).pack(
            side=tk.RIGHT, padx=2
        )
        ttk.Button(foot, text="Docs: FSOT app", command=self._open_fsot_app_doc).pack(
            side=tk.RIGHT, padx=2
        )
        ttk.Button(foot, text="Checkpoint", command=self._open_checkpoint).pack(side=tk.RIGHT)

    # ----- plumbing -----

    def _log(self, msg: str) -> None:
        self._log_q.put(msg)

    def _drain_log(self) -> None:
        try:
            while True:
                msg = self._log_q.get_nowait()
                self.log.insert(tk.END, msg)
                self.log.see(tk.END)
        except queue.Empty:
            pass
        self.after(100, self._drain_log)

    def _set_status(self, text: str) -> None:
        self.status.delete("1.0", tk.END)
        self.status.insert(tk.END, text)

    def _set_enc(self, text: str) -> None:
        self.enc_out.delete("1.0", tk.END)
        self.enc_out.insert(tk.END, text)

    def _run_async(self, args: List[str], cwd: Optional[Path] = None) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Busy", "An engine job is already running — see Engine log.")
            return

        def work() -> None:
            self._log(f"\n$ {' '.join(str(a) for a in args)}\n")
            try:
                env = os.environ.copy()
                env["PYTHONPATH"] = str(ROOT)
                env.setdefault("FSOT_PHYSICAL_ARCHIVE", r"I:\FSOT-Physical-Archive")
                p = subprocess.Popen(
                    args,
                    cwd=str(cwd or ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                    bufsize=1,
                )
                assert p.stdout is not None
                for line in p.stdout:
                    self._log(line)
                code = p.wait()
                self._log(f"\n[exit {code}]  →  {'PASS' if code == 0 else 'FAIL'}\n")
                self.after(0, self._refresh_live)
                self.after(0, self._refresh_banner)
            except Exception as e:
                self._log(f"ERROR: {e}\n")

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    # ----- boot / banner / live -----

    def _auto_boot(self) -> None:
        self._boot_system()

    def _boot_system(self) -> None:
        def work() -> None:
            try:
                from fsot_nuron.fsot_bridge import (
                    require_pin,
                    verify_fsot_bridge,
                    fold_diagnostics,
                )
                from fsot_nuron.machine_encode import verify_machine_path

                pin = require_pin(write_snapshot=False)
                folds = fold_diagnostics()
                br = verify_fsot_bridge()
                mv = verify_machine_path("FSOT neural")
                zig_ok = ZIG_HOST.is_file()
                report, ok = format_boot_report(pin, folds, br, mv, zig_ok)
                self._log(report + "\n")

                def ui() -> None:
                    self._boot_ok = ok
                    self._set_status(report)
                    if ok:
                        self.boot_title.config(text="FSOT NEURAL  ·  ONLINE", fg="#3fb950")
                        self.boot_badge.config(text="● PIN OK", fg="#3fb950")
                    else:
                        self.boot_title.config(text="FSOT NEURAL  ·  FAULT", fg="#f85149")
                        self.boot_badge.config(text="● PIN FAIL", fg="#f85149")
                    self._refresh_banner()
                    self._refresh_live()

                self.after(0, ui)
            except Exception as e:
                msg = f"BOOT ERROR\n==========\n{e}\n\nSet FSOT_PHYSICAL_ARCHIVE=I:\\FSOT-Physical-Archive\n"
                self._log(msg)

                def ui_err() -> None:
                    self._boot_ok = False
                    self._set_status(msg)
                    self.boot_title.config(text="FSOT NEURAL  ·  FAULT", fg="#f85149")
                    self.boot_badge.config(text="● PIN FAIL", fg="#f85149")

                self.after(0, ui_err)

        threading.Thread(target=work, daemon=True).start()

    def _refresh_banner(self) -> None:
        try:
            from fsot_nuron.fsot_bridge import fold_diagnostics

            f = fold_diagnostics()
            self.fold_strip.config(
                text=(
                    f"S_bio={f.get('S_Biology'):+.4f}    "
                    f"S_neuro={f.get('S_Neuroscience'):+.4f}    "
                    f"S_body={f.get('S_Computer_Body'):+.4f}    "
                    f"pin={'OK' if f.get('pin_ok') else 'NO'}"
                )
            )
            if f.get("pin_ok"):
                self.boot_badge.config(text="● PIN OK", fg="#3fb950")
            else:
                self.boot_badge.config(text="● PIN NO", fg="#f85149")
        except Exception as e:
            self.fold_strip.config(text=f"fold error: {e}")

    def _refresh_live(self) -> None:
        try:
            from fsot_nuron.fsot_bridge import fold_diagnostics, verify_fsot_bridge
            from fsot_nuron.machine_encode import verify_machine_path

            f = fold_diagnostics()
            br = verify_fsot_bridge()
            mv = verify_machine_path("FSOT")
            arts = _load_artifact_summaries()
            text = format_live_metrics(f, br, mv, arts)
            # Append stress report if present
            sp = ROOT / "artifacts" / "stress_suite_report.json"
            if sp.is_file():
                try:
                    sr = json.loads(sp.read_text(encoding="utf-8"))
                    text += "\nSTRESS SUITE\n============\n"
                    text += f"pass {sr.get('n_pass')}/{sr.get('n_tests')}  duration={sr.get('duration_s')}s\n"
                    text += f"critical breaks: {len(sr.get('critical_breaks') or [])}\n"
                    text += f"soft breaks: {len(sr.get('soft_breaks') or [])}\n"
                    for b in (sr.get("critical_breaks") or [])[:8]:
                        text += f"  CRITICAL {b.get('stage')}/{b.get('name')}\n"
                    for b in (sr.get("soft_breaks") or [])[:8]:
                        text += f"  soft     {b.get('stage')}/{b.get('name')}\n"
                    text += "\nSee docs/STRESS_STAGE_REPORT.md\n"
                except Exception as e:
                    text += f"\nstress report read error: {e}\n"
        except Exception as e:
            text = f"LIVE METRICS ERROR\n==================\n{e}\n"
        self.live_out.delete("1.0", tk.END)
        self.live_out.insert(tk.END, text)
        # Also refresh product screens that show artifacts
        try:
            self._refresh_cells()
            self._refresh_memory()
        except Exception:
            pass

    # ----- engine commands -----

    def _cmd_pin(self) -> None:
        self._run_async([sys.executable, str(ROOT / "run_archive_pin.py")])

    def _cmd_scalpel(self) -> None:
        self._run_async(
            [
                sys.executable,
                str(ROOT / "run_scalpel_rates.py"),
                "--focus",
                "Pyr,PV,SST,VIP",
                "--tol",
                "0.01",
            ]
        )

    def _cmd_intel(self) -> None:
        self._run_async(
            [
                sys.executable,
                str(ROOT / "run_intelligence_probe.py"),
                "--suite",
                "--items",
                "12",
                "--delay-steps",
                "600",
                "--tol",
                "0.01",
                "--item-mode",
                "fsot_machine",
            ]
        )

    def _cmd_intel_quick(self) -> None:
        self._run_async(
            [
                sys.executable,
                str(ROOT / "run_intelligence_probe.py"),
                "--items",
                "6",
                "--delay-steps",
                "200",
                "--encode-steps",
                "200",
                "--retrieve-steps",
                "180",
                "--skip-scalpel",
                "--item-mode",
                "fsot_machine",
            ]
        )

    def _cmd_machine_verify(self) -> None:
        self._run_async(
            [sys.executable, str(ROOT / "run_machine_encode.py"), "--verify", "--inject-demo"]
        )

    def _cmd_fsot_bridge(self) -> None:
        self._run_async([sys.executable, str(ROOT / "run_fsot_bridge.py")])

    def _cmd_parity(self) -> None:
        self._run_async([sys.executable, str(ROOT / "scripts" / "parity_zig_neuron.py")])

    def _cmd_zig_body(self) -> None:
        """Run the real Zig host executable (not Python)."""
        if not ZIG_HOST.is_file():
            messagebox.showwarning(
                "Zig body missing",
                f"No host binary at:\n{ZIG_HOST}\n\nBuild: cd embodiment\\zig && zig build",
            )
            self._set_status(
                "ZIG BODY\n========\nMissing executable.\n"
                f"Expected: {ZIG_HOST}\n"
                "Build with: cd embodiment\\zig ; zig build\n"
            )
            if hasattr(self, "zig_badge"):
                self.zig_badge.config(text="FP: missing")
            return

        def work() -> None:
            self._log(f"\n$ {ZIG_HOST}\n")
            try:
                p = subprocess.run(
                    [str(ZIG_HOST)],
                    cwd=str(ZIG_HOST.parent),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                out = (p.stdout or "") + (p.stderr or "")
                self._log(out + f"\n[exit {p.returncode}]\n")
                ok = p.returncode == 0 and "FSOT_TRIT PASS" in out

                def ui() -> None:
                    self._zig_fp = ok
                    if hasattr(self, "zig_badge"):
                        self.zig_badge.config(
                            text="FP: PASS" if ok else "FP: FAIL"
                        )
                    if hasattr(self, "body_out"):
                        self.body_out.delete("1.0", tk.END)
                        self.body_out.insert(
                            tk.END,
                            f"ZIG HOST RUN\n============\n"
                            f"Result: {'PASS' if ok else 'FAIL'}\n"
                            f"returncode={p.returncode}\n\n{out[:4000]}\n",
                        )

                self.after(0, ui)
            except Exception as e:
                self._log(f"ERROR: {e}\n")

        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Busy", "An engine job is already running.")
            return
        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _cmd_qemu(self) -> None:
        if not ZIG_QEMU.is_file():
            messagebox.showwarning("Missing", str(ZIG_QEMU))
            return
        self._run_async(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ZIG_QEMU)],
            cwd=ROOT / "embodiment" / "zig",
        )

    def _cmd_stress(self) -> None:
        self._run_async([sys.executable, str(ROOT / "run_stress_suite.py")])

    def _cmd_stress_quick(self) -> None:
        self._run_async([sys.executable, str(ROOT / "run_stress_suite.py"), "--quick"])

    def _cmd_learning_eeg(self) -> None:
        self._run_async([sys.executable, str(ROOT / "run_learning_eeg_study.py")])

    def _cmd_consolidate(self) -> None:
        self._run_async(
            [
                sys.executable,
                str(ROOT / "run_consolidate_study.py"),
                "--items",
                "8",
                "--delay-steps",
                "300",
            ]
        )

    def _cmd_wetlab(self) -> None:
        self._run_async([sys.executable, str(ROOT / "run_wetlab_accuracy_battery.py")])

    def _cmd_cellular(self) -> None:
        self._run_async(
            [sys.executable, str(ROOT / "run_cellular_expand.py"), "--check", "--expand", "64"]
        )

    def _refresh_cells(self) -> None:
        lines = [
            "CELL CLASSES vs ALLEN WET-LAB",
            "=============================",
            "",
        ]
        path = None
        for base in (ROOT / "artifacts", ROOT / "data" / "results"):
            p = base / "scalpel_rates.json"
            if p.is_file():
                path = p
                break
        if path is None:
            lines.append("No scalpel_rates.json yet. Run Scalpel 1% or Stress suite.\n")
            self.cells_out.delete("1.0", tk.END)
            self.cells_out.insert(tk.END, "\n".join(lines))
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            tol = data.get("tol")
            lines.append(f"Source: {path}")
            lines.append(f"Tolerance: {tol}")
            lines.append(f"scalpel_ok: {(data.get('gates') or {}).get('scalpel_ok')}")
            lines.append("")
            lines.append(f"{'Class':6} {'Target Hz':>10} {'Measured':>10} {'Rel err':>10}  OK?")
            lines.append("-" * 48)
            classes = {}
            rep = data.get("report") or {}
            if isinstance(rep, dict):
                classes = rep.get("classes") or {}
            for lab, st in sorted(classes.items()):
                if not isinstance(st, dict):
                    continue
                err = st.get("rel_err")
                ok = err is not None and err == err and tol is not None and err <= tol
                lines.append(
                    f"{lab:6} {st.get('target_Hz', 0):10.2f} {st.get('measured_Hz', 0):10.2f} "
                    f"{(err or 0):10.1%}  {'YES' if ok else 'NO'}"
                )
            folds = data.get("fsot_folds") or {}
            if folds:
                lines += [
                    "",
                    f"FSOT S_bio={folds.get('S_Biology')}  S_neuro={folds.get('S_Neuroscience')}",
                ]
            lines.append("")
            lines.append("Authority: Allen Cell Types Cre-line means (public wet-lab data).")
        except Exception as e:
            lines.append(f"Error: {e}")
        self.cells_out.delete("1.0", tk.END)
        self.cells_out.insert(tk.END, "\n".join(lines))

    def _refresh_memory(self) -> None:
        lines = [
            "MEMORY LAB RESULTS",
            "==================",
            "",
            "Items use FSOT machine bridge (not Morse).",
            "",
        ]
        path = None
        for base in (ROOT / "artifacts", ROOT / "data" / "results"):
            p = base / "intelligence_probe.json"
            if p.is_file():
                path = p
                break
        if path is None:
            lines.append("No intelligence_probe.json yet. Run Quick intel.\n")
            self.mem_out.delete("1.0", tk.END)
            self.mem_out.insert(tk.END, "\n".join(lines))
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            lines.append(f"Source: {path}")
            lines.append(f"Generated: {data.get('generated_at')}")
            params = data.get("params") or {}
            lines.append(f"Items: {params.get('items')}  delay: {params.get('delay_steps')}  mode: {params.get('item_mode')}")
            lines.append("")
            for k, v in (data.get("results") or {}).items():
                if isinstance(v, dict) and "top1_accuracy" in v:
                    lines.append(
                        f"  {k:16} top-1 = {v['top1_accuracy']:.3f}  "
                        f"sim+={v.get('mean_correct_sim')}  sim-={v.get('mean_incorrect_sim')}"
                    )
            gates = data.get("gates") or {}
            if gates:
                lines.append("")
                lines.append("Gates:")
                for gk, gv in gates.items():
                    lines.append(f"  {gk}: {gv}")
            folds = data.get("fsot_folds") or {}
            if folds.get("S_Biology") is not None:
                lines.append(
                    f"\nFSOT S_bio={folds.get('S_Biology')}  S_neuro={folds.get('S_Neuroscience')}"
                )
        except Exception as e:
            lines.append(f"Error: {e}")
        self.mem_out.delete("1.0", tk.END)
        self.mem_out.insert(tk.END, "\n".join(lines))

    # ----- encode tab (readable outcomes) -----

    def _do_encode(self) -> None:
        from fsot_nuron.machine_encode import (
            EncodePath,
            translate,
            build_machine_frame,
        )
        from fsot_nuron.fsot_bridge import bridge_machine_payload, bridge_chemical_dna

        text = self.enc_in.get("1.0", tk.END).strip()
        if not text:
            self._set_enc("No input text.\n")
            return
        path_s = self.path_var.get()
        path = EncodePath(path_s)

        # Honest chemical: if user selected chemical but typed English, warn
        if path is EncodePath.CHEMICAL and not _looks_like_dna(text):
            self._set_enc(
                "CHEMICAL PATH NOTE\n"
                "==================\n"
                "You selected Chemical / DNA, but the input does not look like DNA (A/C/G/T).\n"
                f"Input: {text[:80]!r}\n\n"
                "Options:\n"
                "  • Paste DNA like ATGAAACGG and click Chem / DNA bridge\n"
                "  • Or switch Path to Machine ★ for English text\n"
            )
            return

        out = translate(text, path=path)
        frame = build_machine_frame(text, path=path).to_dict()
        fsot: Optional[Dict[str, Any]] = None
        try:
            if path is EncodePath.MACHINE:
                fsot = bridge_machine_payload(text)
            elif path is EncodePath.CHEMICAL and _looks_like_dna(text):
                fsot = bridge_chemical_dna(text)
        except Exception as e:
            fsot = {"error": str(e)}

        summary = format_encode_summary(text, path_s, out, frame, fsot)
        self._set_enc(summary)
        self._log(f"[encode] path={path_s} n_trits={out.get('n_trits')} primary={out.get('primary')}\n")

    def _do_chem_bridge(self) -> None:
        from fsot_nuron.machine_encode import chemical_signals_to_machine
        from fsot_nuron.fsot_bridge import bridge_chemical_dna

        text = self.enc_in.get("1.0", tk.END).strip()
        if _looks_like_dna(text):
            dna = "".join(c for c in text.upper() if c in "ACGT")
            note = ""
        else:
            dna = "ATGAAACGGTTTGCG"
            note = f"(input was not DNA — using demo ORF {dna})\n\n"

        abi = chemical_signals_to_machine(dna)
        fsot = bridge_chemical_dna(dna)
        self._set_enc(note + format_chem_summary(dna, abi, fsot))
        self._log(
            f"[chem] dna_len={len(dna)} n_trits={abi.get('n_trits')} "
            f"S={fsot['modulators'].get('S')}\n"
        )

    def _do_inject(self) -> None:
        from fsot_nuron.sensory import SensoryBus, push_machine_text

        text = self.enc_in.get("1.0", tk.END).strip()
        if not text:
            self._set_enc("No input to inject.\n")
            return
        path = self.path_var.get()
        if path == "chemical" and not _looks_like_dna(text):
            self._set_enc(
                "INJECT NOTE\n===========\n"
                "Chemical path needs DNA bases. Switch to Machine or paste DNA.\n"
            )
            return

        bus = SensoryBus()
        pkt = push_machine_text(bus, text, path=path)
        region_index = {
            "sens": list(range(0, 32)),
            "thal": list(range(32, 48)),
            "assoc": list(range(48, 80)),
            "hipp": list(range(80, 96)),
        }
        ext = bus.build_external(96, region_index)
        stats = {
            "n_units": int(ext.numel()),
            "nonzero": int((ext != 0).sum()),
            "mean": float(ext.mean()),
            "max": float(ext.max()),
            "sens_slice_head": ext[:8].tolist(),
        }
        self._set_enc(format_inject_summary(path, pkt, stats))
        self._log(
            f"[inject] path={path} S={pkt.meta.get('S')} strength={pkt.strength:.3f} "
            f"nonzero={stats['nonzero']}\n"
        )

    def _do_compare_paths(self) -> None:
        from fsot_nuron.machine_encode import EncodePath, translate, build_machine_frame

        text = self.enc_in.get("1.0", tk.END).strip() or "FSOT"
        rows: Dict[str, Dict[str, Any]] = {}
        for p in (EncodePath.MACHINE, EncodePath.CHEMICAL, EncodePath.MORSE):
            r = translate(text, path=p)
            fr = build_machine_frame(text, path=p)
            rows[p.value] = {
                "primary": r.get("primary"),
                "n_trits": r.get("n_trits"),
                "n_words": len(r.get("words") or []),
                "frame_bytes": fr.to_dict()["byte_len"],
            }
        self._set_enc(format_compare_summary(text, rows))

    def _open_checkpoint(self) -> None:
        p = ROOT / "CHECKPOINT_v0.5.md"
        if p.is_file():
            os.startfile(str(p))
        else:
            messagebox.showinfo("Missing", str(p))

    def _open_machine_doc(self) -> None:
        p = ROOT / "docs" / "MACHINE_ENCODING.md"
        if p.is_file():
            os.startfile(str(p))

    def _open_fsot_app_doc(self) -> None:
        p = ROOT / "docs" / "FSOT_APPLICATION_NEURAL.md"
        if p.is_file():
            os.startfile(str(p))


def main() -> None:
    app = ConsoleApp()
    app.mainloop()


if __name__ == "__main__":
    main()
