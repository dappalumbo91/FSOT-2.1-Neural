#!/usr/bin/env python3
"""
FSOT Neural Console v0.1 — local desktop UI (tkinter, no web server).

Scavenges the host OS windowing/fonts via tkinter (and optionally Dear PyGui later).
Drives checkpoint science: pin, scalpel, intelligence probe, encoding playground, QEMU.
"""

from __future__ import annotations

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
        self.title("FSOT Neural Console v0.1 — local (no web)")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self._log_q: queue.Queue[str] = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._build()
        self.after(100, self._drain_log)
        self._log(
            "FSOT Neural Console — checkpoint v0.5 science floor.\n"
            "UI uses host OS fonts/windows (tkinter). Brain stays local IPC/subprocess.\n"
            "Encoding default: MACHINE (UTF-8/T1 packs), not Morse.\n"
        )

    def _build(self) -> None:
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.tab_dash = ttk.Frame(nb)
        self.tab_enc = ttk.Frame(nb)
        self.tab_log = ttk.Frame(nb)
        nb.add(self.tab_dash, text="Dashboard")
        nb.add(self.tab_enc, text="Machine encode")
        nb.add(self.tab_log, text="Engine log")

        # --- Dashboard ---
        hdr = ttk.Label(
            self.tab_dash,
            text="Accurate neurons → intelligence · local product shell",
            font=("Segoe UI", 12, "bold"),
        )
        hdr.pack(anchor=tk.W, padx=8, pady=(8, 4))

        btn_row = ttk.Frame(self.tab_dash)
        btn_row.pack(fill=tk.X, padx=8, pady=4)
        actions = [
            ("Archive pin", self._cmd_pin),
            ("Scalpel 1%", self._cmd_scalpel),
            ("Intel probe (suite)", self._cmd_intel),
            ("Zig parity", self._cmd_parity),
            ("QEMU body check", self._cmd_qemu),
        ]
        for i, (label, cmd) in enumerate(actions):
            b = ttk.Button(btn_row, text=label, command=cmd)
            b.grid(row=0, column=i, padx=4, pady=4, sticky="ew")
            btn_row.columnconfigure(i, weight=1)

        info = ttk.LabelFrame(self.tab_dash, text="Status / quick facts")
        info.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.status = scrolledtext.ScrolledText(info, height=18, wrap=tk.WORD, font=("Consolas", 10))
        self.status.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.status.insert(
            tk.END,
            "Checkpoint: v0.5.0-bio-intel\n"
            "Allen class rates ≤1% · encode/delay/consolidate probe · Zig@QEMU FP\n"
            "Docs: CHECKPOINT_v0.5.md · PRODUCT_UI_AND_DISPLAY.md · machine_encode.py\n\n"
            "Use buttons above to run local engines (subprocess). Log tab shows output.\n",
        )

        # --- Encoding playground ---
        ttk.Label(
            self.tab_enc,
            text="Translate text for the neural body — MACHINE path preferred (OS-native).",
            font=("Segoe UI", 10),
        ).pack(anchor=tk.W, padx=8, pady=4)

        path_row = ttk.Frame(self.tab_enc)
        path_row.pack(fill=tk.X, padx=8)
        ttk.Label(path_row, text="Path:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value="machine")
        for p, lab in (
            ("machine", "Machine (UTF-8 / T1) ★"),
            ("chemical", "Chemical codon"),
            ("morse", "Morse (secondary)"),
        ):
            ttk.Radiobutton(path_row, text=lab, variable=self.path_var, value=p).pack(
                side=tk.LEFT, padx=6
            )

        self.enc_in = scrolledtext.ScrolledText(self.tab_enc, height=6, font=("Consolas", 10))
        self.enc_in.pack(fill=tk.X, padx=8, pady=4)
        self.enc_in.insert(tk.END, "FSOT neural intelligence")

        ttk.Button(self.tab_enc, text="Translate → machine words / trits", command=self._do_encode).pack(
            anchor=tk.W, padx=8, pady=4
        )
        self.enc_out = scrolledtext.ScrolledText(self.tab_enc, height=16, font=("Consolas", 9))
        self.enc_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # --- Log ---
        self.log = scrolledtext.ScrolledText(self.tab_log, wrap=tk.WORD, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        foot = ttk.Frame(self)
        foot.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(foot, text=f"ROOT: {ROOT}", font=("Segoe UI", 8)).pack(side=tk.LEFT)
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

    def _cmd_parity(self) -> None:
        self._run_async([sys.executable, str(ROOT / "scripts" / "parity_zig_neuron.py")])

    def _cmd_qemu(self) -> None:
        ps1 = ROOT / "embodiment" / "zig" / "run_qemu.ps1"
        self._run_async(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
            cwd=ROOT / "embodiment" / "zig",
        )

    def _do_encode(self) -> None:
        from fsot_nuron.machine_encode import EncodePath, translate, path_recommendation
        import json

        text = self.enc_in.get("1.0", tk.END).strip()
        path = EncodePath(self.path_var.get())
        out = translate(text, path=path)
        rec = path_recommendation()
        self.enc_out.delete("1.0", tk.END)
        self.enc_out.insert(
            tk.END,
            json.dumps({"recommendation": rec, "result": out}, indent=2)[:12000],
        )

    def _open_checkpoint(self) -> None:
        p = ROOT / "CHECKPOINT_v0.5.md"
        if p.is_file():
            os.startfile(str(p))  # Windows
        else:
            messagebox.showinfo("Missing", str(p))


def main() -> None:
    app = ConsoleApp()
    app.mainloop()


if __name__ == "__main__":
    main()
