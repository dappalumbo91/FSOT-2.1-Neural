#!/usr/bin/env python3
"""
FSOT Neural Console v0.2 — local desktop UI (tkinter, no web server).

Scavenges the host OS windowing/fonts via tkinter (Dear PyGui / GTK later).
Drives checkpoint science: pin, scalpel, intelligence probe, encoding, inject, QEMU.

Encoding doctrine: MACHINE (UTF-8 / T1 packs / OS words) is primary.
Morse is secondary (human telegraphy demos only).
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
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("PYTHONPATH", str(ROOT))
os.environ.setdefault("FSOT_PHYSICAL_ARCHIVE", r"I:\FSOT-Physical-Archive")


class ConsoleApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FSOT Neural Console v0.2 — local (no web)")
        self.geometry("1140x760")
        self.minsize(920, 620)
        self._log_q: queue.Queue[str] = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._build()
        self.after(100, self._drain_log)
        self._log(
            "FSOT Neural Console v0.2 — checkpoint v0.5 science floor.\n"
            "UI uses host OS fonts/windows (tkinter). Brain stays local IPC/subprocess.\n"
            "Encoding default: MACHINE (UTF-8/T1 packs / OS ABI words), not Morse.\n"
            "Chem → machine bridge available for DNA/codon into the body.\n"
        )
        self.after(200, self._refresh_live)

    def _build(self) -> None:
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.tab_dash = ttk.Frame(nb)
        self.tab_enc = ttk.Frame(nb)
        self.tab_live = ttk.Frame(nb)
        self.tab_log = ttk.Frame(nb)
        nb.add(self.tab_dash, text="Dashboard")
        nb.add(self.tab_enc, text="Machine encode")
        nb.add(self.tab_live, text="Live metrics")
        nb.add(self.tab_log, text="Engine log")

        # --- Dashboard ---
        hdr = ttk.Label(
            self.tab_dash,
            text="Accurate neurons → intelligence · local product shell · machine body I/O",
            font=("Segoe UI", 12, "bold"),
        )
        hdr.pack(anchor=tk.W, padx=8, pady=(8, 4))

        btn_row = ttk.Frame(self.tab_dash)
        btn_row.pack(fill=tk.X, padx=8, pady=4)
        actions = [
            ("Archive pin", self._cmd_pin),
            ("Scalpel 1%", self._cmd_scalpel),
            ("Intel probe", self._cmd_intel),
            ("Machine encode ✓", self._cmd_machine_verify),
            ("FSOT bridge", self._cmd_fsot_bridge),
            ("Zig parity", self._cmd_parity),
            ("QEMU body", self._cmd_qemu),
        ]
        for i, (label, cmd) in enumerate(actions):
            b = ttk.Button(btn_row, text=label, command=cmd)
            b.grid(row=0, column=i, padx=3, pady=4, sticky="ew")
            btn_row.columnconfigure(i, weight=1)

        info = ttk.LabelFrame(self.tab_dash, text="Status / quick facts")
        info.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.status = scrolledtext.ScrolledText(info, height=18, wrap=tk.WORD, font=("Consolas", 10))
        self.status.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.status.insert(
            tk.END,
            "Checkpoint: v0.5.0-bio-intel\n"
            "Allen class rates ≤1% · encode/delay/consolidate probe · Zig@QEMU FP\n"
            "Body I/O: MACHINE words (Linux/Windows-style LE packs) — Morse secondary\n"
            "Docs: CHECKPOINT_v0.5.md · MACHINE_ENCODING.md · PRODUCT_UI_AND_DISPLAY.md\n\n"
            "Buttons run local engines (subprocess). Log tab streams stdout.\n"
            "Machine encode tab: translate + inject into sensory bus demo.\n",
        )

        # --- Encoding playground ---
        ttk.Label(
            self.tab_enc,
            text="OS-native body language: MACHINE (UTF-8 / T1 packs / ABI frame). Morse = demos only.",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, padx=8, pady=4)

        path_row = ttk.Frame(self.tab_enc)
        path_row.pack(fill=tk.X, padx=8)
        ttk.Label(path_row, text="Path:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value="machine")
        for p, lab in (
            ("machine", "Machine (UTF-8 / T1) ★"),
            ("chemical", "Chemical → machine"),
            ("morse", "Morse (secondary)"),
        ):
            ttk.Radiobutton(path_row, text=lab, variable=self.path_var, value=p).pack(
                side=tk.LEFT, padx=6
            )

        self.enc_in = scrolledtext.ScrolledText(self.tab_enc, height=5, font=("Consolas", 10))
        self.enc_in.pack(fill=tk.X, padx=8, pady=4)
        self.enc_in.insert(tk.END, "FSOT neural intelligence")

        btn_enc = ttk.Frame(self.tab_enc)
        btn_enc.pack(fill=tk.X, padx=8, pady=2)
        ttk.Button(btn_enc, text="Translate → machine words / ABI frame", command=self._do_encode).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_enc, text="Chem→machine (DNA sample)", command=self._do_chem_bridge).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_enc, text="Inject → sensory bus demo", command=self._do_inject).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_enc, text="Compare all paths", command=self._do_compare_paths).pack(
            side=tk.LEFT, padx=2
        )

        self.enc_out = scrolledtext.ScrolledText(self.tab_enc, height=18, font=("Consolas", 9))
        self.enc_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # --- Live metrics ---
        live_hdr = ttk.Frame(self.tab_live)
        live_hdr.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(
            live_hdr,
            text="Lightweight live panel (no web). Refresh pulls pin + encode ABI locally.",
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT)
        ttk.Button(live_hdr, text="Refresh", command=self._refresh_live).pack(side=tk.RIGHT)

        self.live_out = scrolledtext.ScrolledText(self.tab_live, wrap=tk.WORD, font=("Consolas", 9))
        self.live_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # --- Log ---
        self.log = scrolledtext.ScrolledText(self.tab_log, wrap=tk.WORD, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        foot = ttk.Frame(self)
        foot.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(foot, text=f"ROOT: {ROOT}", font=("Segoe UI", 8)).pack(side=tk.LEFT)
        ttk.Button(foot, text="Open MACHINE_ENCODING.md", command=self._open_machine_doc).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(foot, text="Open checkpoint doc", command=self._open_checkpoint).pack(side=tk.RIGHT)

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

    def _run_async(self, args: List[str], cwd: Optional[Path] = None) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Busy", "An engine job is already running.")
            return

        def work() -> None:
            self._log(f"\n$ {' '.join(args)}\n")
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
                self._log(f"\n[exit {code}]\n")
            except Exception as e:
                self._log(f"ERROR: {e}\n")

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

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

    def _cmd_qemu(self) -> None:
        ps1 = ROOT / "embodiment" / "zig" / "run_qemu.ps1"
        self._run_async(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
            cwd=ROOT / "embodiment" / "zig",
        )

    def _do_encode(self) -> None:
        from fsot_nuron.machine_encode import (
            EncodePath,
            translate,
            path_recommendation,
            build_machine_frame,
        )

        text = self.enc_in.get("1.0", tk.END).strip()
        path = EncodePath(self.path_var.get())
        out = translate(text, path=path)
        frame = build_machine_frame(text, path=path)
        rec = path_recommendation()
        payload = {
            "recommendation": rec,
            "result": out,
            "abi_frame": frame.to_dict(),
        }
        self.enc_out.delete("1.0", tk.END)
        self.enc_out.insert(tk.END, json.dumps(payload, indent=2)[:14000])

    def _do_chem_bridge(self) -> None:
        from fsot_nuron.machine_encode import chemical_signals_to_machine

        text = self.enc_in.get("1.0", tk.END).strip()
        # If user typed DNA-ish, use it; else demo codon string
        dna = text if all(c in "ACGTacgtUuNn \n" for c in text[:80]) else "ATGAAACGGTTTGCG"
        out = chemical_signals_to_machine(dna)
        self.enc_out.delete("1.0", tk.END)
        self.enc_out.insert(
            tk.END,
            "Chemical signals → machine words (genetics into OS body)\n"
            + json.dumps(out, indent=2)[:14000],
        )

    def _do_inject(self) -> None:
        from fsot_nuron.machine_encode import EncodePath
        from fsot_nuron.sensory import SensoryBus, push_machine_text

        text = self.enc_in.get("1.0", tk.END).strip()
        path = self.path_var.get()
        bus = SensoryBus()
        pkt = push_machine_text(bus, text, path=path)
        region_index = {
            "sens": list(range(0, 32)),
            "thal": list(range(32, 48)),
            "assoc": list(range(48, 80)),
            "hipp": list(range(80, 96)),
        }
        ext = bus.build_external(96, region_index)
        report = {
            "encode_path": path,
            "primary": path != "morse",
            "packet": pkt.to_dict(),
            "external_drive": {
                "n_units": int(ext.numel()),
                "nonzero": int((ext != 0).sum()),
                "mean": float(ext.mean()),
                "max": float(ext.max()),
                "sens_slice_head": ext[:8].tolist(),
            },
            "note": "Packet enqueued and folded like a Linux process writing into a buffer the brain reads.",
        }
        self.enc_out.delete("1.0", tk.END)
        self.enc_out.insert(tk.END, json.dumps(report, indent=2)[:12000])
        self._log(f"[inject] path={path} nonzero_drive={report['external_drive']['nonzero']}\n")

    def _do_compare_paths(self) -> None:
        from fsot_nuron.machine_encode import EncodePath, translate, build_machine_frame

        text = self.enc_in.get("1.0", tk.END).strip() or "FSOT"
        rows = {}
        for p in (EncodePath.MACHINE, EncodePath.CHEMICAL, EncodePath.MORSE):
            r = translate(text, path=p)
            fr = build_machine_frame(text, path=p)
            rows[p.value] = {
                "primary": r.get("primary"),
                "n_trits": r.get("n_trits"),
                "n_words": len(r.get("words") or []),
                "note": r.get("note"),
                "frame_bytes": fr.to_dict()["byte_len"],
                "hex_head": fr.to_dict()["hex_head"][:48],
            }
        self.enc_out.delete("1.0", tk.END)
        self.enc_out.insert(
            tk.END,
            "Path comparison (prefer machine for OS-native body)\n"
            + json.dumps(rows, indent=2),
        )

    def _refresh_live(self) -> None:
        lines = ["=== Live metrics (local) ===\n"]
        try:
            from fsot_nuron.machine_encode import path_recommendation, verify_machine_path
            from fsot_nuron.fsot_bridge import verify_fsot_bridge

            rec = path_recommendation()
            ver = verify_machine_path("FSOT")
            br = verify_fsot_bridge()
            lines.append("Encoding recommendation:\n")
            lines.append(json.dumps(rec, indent=2) + "\n\n")
            lines.append("Machine ABI verify:\n")
            lines.append(
                json.dumps(
                    {
                        "frame_roundtrip_ok": ver.get("frame_roundtrip_ok"),
                        "utf8_roundtrip_ok": ver.get("utf8_roundtrip_ok"),
                        "chem_bridge_ok": ver.get("chem_bridge_ok"),
                        "n_trits": ver.get("n_trits"),
                    },
                    indent=2,
                )
                + "\n\n"
            )
            lines.append("FSOT bridge (through archive math):\n")
            lines.append(
                json.dumps(
                    {
                        "ok": br.get("ok"),
                        "S_Biology": br.get("S_Biology"),
                        "S_Neuroscience": br.get("S_Neuroscience"),
                        "atlas_ok": br.get("atlas_ok"),
                        "authority_sha256": (br.get("authority_sha256") or "")[:20] + "…",
                        "formula": br.get("formula"),
                        "free_parameters": br.get("free_parameters"),
                    },
                    indent=2,
                )
                + "\n\n"
            )
        except Exception as e:
            lines.append(f"machine/fsot bridge error: {e}\n")

        try:
            from fsot_nuron.archive_pin import pin_archive

            pin = pin_archive(write_snapshot=False)
            # pin may be dataclass or dict-like
            if hasattr(pin, "__dict__"):
                pd = {k: getattr(pin, k) for k in dir(pin) if not k.startswith("_") and not callable(getattr(pin, k))}
            else:
                pd = dict(pin) if isinstance(pin, dict) else {"pin": str(pin)}
            slim = {k: pd[k] for k in list(pd)[:20]}
            lines.append("Archive pin (head):\n")
            lines.append(json.dumps(slim, indent=2, default=str)[:2500] + "\n")
        except Exception as e:
            lines.append(f"archive pin: {e}\n")

        lines.append(f"\nROOT: {ROOT}\n")
        self.live_out.delete("1.0", tk.END)
        self.live_out.insert(tk.END, "".join(lines))

    def _open_checkpoint(self) -> None:
        p = ROOT / "CHECKPOINT_v0.5.md"
        if p.is_file():
            os.startfile(str(p))  # Windows
        else:
            messagebox.showinfo("Missing", str(p))

    def _open_machine_doc(self) -> None:
        p = ROOT / "docs" / "MACHINE_ENCODING.md"
        if p.is_file():
            os.startfile(str(p))
        else:
            messagebox.showinfo("Missing", str(p))


def main() -> None:
    app = ConsoleApp()
    app.mainloop()


if __name__ == "__main__":
    main()
