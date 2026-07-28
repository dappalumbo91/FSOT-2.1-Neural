#!/usr/bin/env python3
"""
FSOT Neural Console v0.3 — bootable local product shell (tkinter, no web).

Doctrine: pin archive math → fold diagnostics → machine body I/O → engines.
You can open this window and *see* pin status, S folds, and run science jobs.
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
        self.title("FSOT Neural Console v0.3 — bootable (local, no web)")
        self.geometry("1180x800")
        self.minsize(960, 640)
        self.configure(bg="#1a1d23")
        self._log_q: queue.Queue[str] = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._boot_ok = False
        self._build()
        self.after(100, self._drain_log)
        self._log(
            "FSOT Neural Console v0.3\n"
            "Authority: I:\\FSOT-Physical-Archive  ·  S = K(T1+T2+T3)\n"
            "Machine body I/O primary · Morse secondary · no free parameters on scalar\n"
            "Click BOOT SYSTEM or wait for auto-boot…\n"
        )
        self.after(300, self._auto_boot)

    def _build(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # --- Top boot banner ---
        banner = tk.Frame(self, bg="#0d1117", height=72)
        banner.pack(fill=tk.X, side=tk.TOP)
        banner.pack_propagate(False)

        self.boot_title = tk.Label(
            banner,
            text="FSOT NEURAL  ·  BOOTING…",
            font=("Segoe UI", 14, "bold"),
            fg="#58a6ff",
            bg="#0d1117",
            anchor="w",
        )
        self.boot_title.pack(side=tk.LEFT, padx=12, pady=8)

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
            text="S_bio=…  S_neuro=…  S_body=…",
            font=("Consolas", 10),
            fg="#3fb950",
            bg="#0d1117",
            anchor="w",
        )
        self.fold_strip.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)

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
            text="Accurate neurons → intelligence · FSOT-bridged body · local product",
            font=("Segoe UI", 12, "bold"),
        )
        hdr.pack(anchor=tk.W, padx=8, pady=(8, 4))

        boot_row = ttk.Frame(self.tab_dash)
        boot_row.pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(boot_row, text="▶ BOOT SYSTEM", command=self._boot_system).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(boot_row, text="Refresh folds", command=self._refresh_banner).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Label(
            boot_row,
            text="Boot = pin + FSOT bridge + machine ABI (fail-closed if archive off)",
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=10)

        btn_row = ttk.Frame(self.tab_dash)
        btn_row.pack(fill=tk.X, padx=8, pady=4)
        actions = [
            ("Archive pin", self._cmd_pin),
            ("Scalpel 1%", self._cmd_scalpel),
            ("Intel probe", self._cmd_intel),
            ("Quick intel", self._cmd_intel_quick),
            ("Machine ✓", self._cmd_machine_verify),
            ("FSOT bridge", self._cmd_fsot_bridge),
            ("Zig parity", self._cmd_parity),
            ("QEMU body", self._cmd_qemu),
        ]
        for i, (label, cmd) in enumerate(actions):
            b = ttk.Button(btn_row, text=label, command=cmd)
            b.grid(row=0, column=i, padx=2, pady=4, sticky="ew")
            btn_row.columnconfigure(i, weight=1)

        info = ttk.LabelFrame(self.tab_dash, text="Status / last boot report")
        info.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.status = scrolledtext.ScrolledText(info, height=20, wrap=tk.WORD, font=("Consolas", 10))
        self.status.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.status.insert(
            tk.END,
            "Waiting for boot…\n"
            "Checkpoint science floor: v0.5.0-bio-intel\n"
            "Docs: FSOT_APPLICATION_NEURAL.md · MACHINE_ENCODING.md · CHECKPOINT_v0.5.md\n",
        )

        # --- Encoding playground ---
        ttk.Label(
            self.tab_enc,
            text="OS-native body: MACHINE (UTF-8 / T1 / ABI). Coupled through FSOT S when injecting.",
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
        ttk.Button(btn_enc, text="Translate → machine words / ABI", command=self._do_encode).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_enc, text="Chem→machine DNA", command=self._do_chem_bridge).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_enc, text="Inject (FSOT-coupled)", command=self._do_inject).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_enc, text="Compare paths", command=self._do_compare_paths).pack(
            side=tk.LEFT, padx=2
        )

        self.enc_out = scrolledtext.ScrolledText(self.tab_enc, height=18, font=("Consolas", 9))
        self.enc_out.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # --- Live metrics ---
        live_hdr = ttk.Frame(self.tab_live)
        live_hdr.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(
            live_hdr,
            text="Live local panel — folds, pin, last probe artifacts (no web).",
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
        ttk.Button(foot, text="MACHINE_ENCODING", command=self._open_machine_doc).pack(
            side=tk.RIGHT, padx=2
        )
        ttk.Button(foot, text="FSOT application", command=self._open_fsot_app_doc).pack(
            side=tk.RIGHT, padx=2
        )
        ttk.Button(foot, text="Checkpoint", command=self._open_checkpoint).pack(side=tk.RIGHT)

    # ----- logging / workers -----

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
                self.after(0, self._refresh_live)
            except Exception as e:
                self._log(f"ERROR: {e}\n")

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    # ----- boot -----

    def _auto_boot(self) -> None:
        self._boot_system()

    def _boot_system(self) -> None:
        """In-process boot: pin + folds + machine verify (visible immediately)."""

        def work() -> None:
            lines = ["=== BOOT SEQUENCE ===\n"]
            ok = True
            try:
                from fsot_nuron.fsot_bridge import require_pin, verify_fsot_bridge, fold_diagnostics
                from fsot_nuron.machine_encode import verify_machine_path, path_recommendation

                pin = require_pin(write_snapshot=False)
                lines.append(f"PIN connected={pin.connected}\n")
                lines.append(f"  seed_match_ok={pin.seed_match_ok}\n")
                lines.append(f"  authority={(pin.compute_sha256 or '')[:20]}…\n")
                lines.append(f"  lean_build_ok={pin.lean_build_ok}  seven_way={pin.seven_way_bare_metal}\n")

                folds = fold_diagnostics()
                lines.append("\nFOLD DIAGNOSTICS (archive engine):\n")
                for name, fd in folds.get("folds", {}).items():
                    lines.append(
                        f"  {name:18} S={fd['S']:+.6f}  trit={fd['trit']}  D_eff={fd['D_eff']}\n"
                    )

                br = verify_fsot_bridge()
                lines.append(f"\nBridge ok={br.get('ok')}  free_parameters={br.get('free_parameters')}\n")
                lines.append(f"  formula={br.get('formula')}\n")

                mv = verify_machine_path("FSOT neural")
                lines.append(
                    f"\nMachine ABI utf8_ok={mv.get('utf8_roundtrip_ok')}  "
                    f"frame_ok={mv.get('frame_roundtrip_ok')}  chem_ok={mv.get('chem_bridge_ok')}\n"
                )
                lines.append(f"Path rec: {path_recommendation()['summary']}\n")

                ok = bool(
                    pin.connected
                    and pin.seed_match_ok
                    and br.get("ok")
                    and mv.get("utf8_roundtrip_ok")
                    and mv.get("frame_roundtrip_ok")
                )
                lines.append("\n" + ("BOOT PASS — system ready.\n" if ok else "BOOT FAIL — check archive.\n"))
            except Exception as e:
                ok = False
                lines.append(f"\nBOOT ERROR: {e}\n")

            report = "".join(lines)
            self._log(report)

            def ui() -> None:
                self._boot_ok = ok
                self.status.delete("1.0", tk.END)
                self.status.insert(tk.END, report)
                if ok:
                    self.boot_title.config(text="FSOT NEURAL  ·  ONLINE", fg="#3fb950")
                    self.boot_badge.config(text="● PIN OK", fg="#3fb950")
                else:
                    self.boot_title.config(text="FSOT NEURAL  ·  FAULT", fg="#f85149")
                    self.boot_badge.config(text="● PIN FAIL", fg="#f85149")
                self._refresh_banner()
                self._refresh_live()

            self.after(0, ui)

        threading.Thread(target=work, daemon=True).start()

    def _refresh_banner(self) -> None:
        try:
            from fsot_nuron.fsot_bridge import fold_diagnostics

            f = fold_diagnostics()
            self.fold_strip.config(
                text=(
                    f"S_bio={f.get('S_Biology'):+.4f}   "
                    f"S_neuro={f.get('S_Neuroscience'):+.4f}   "
                    f"S_body={f.get('S_Computer_Body'):+.4f}   "
                    f"pin={'OK' if f.get('pin_ok') else 'NO'}"
                )
            )
            if f.get("pin_ok"):
                self.boot_badge.config(text="● PIN OK", fg="#3fb950")
        except Exception as e:
            self.fold_strip.config(text=f"fold error: {e}")

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
        """Faster probe for interactive seeing (still FSOT-bridged items)."""
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

    def _cmd_qemu(self) -> None:
        ps1 = ROOT / "embodiment" / "zig" / "run_qemu.ps1"
        self._run_async(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
            cwd=ROOT / "embodiment" / "zig",
        )

    # ----- encode tab -----

    def _do_encode(self) -> None:
        from fsot_nuron.machine_encode import (
            EncodePath,
            translate,
            path_recommendation,
            build_machine_frame,
        )
        from fsot_nuron.fsot_bridge import bridge_machine_payload

        text = self.enc_in.get("1.0", tk.END).strip()
        path = EncodePath(self.path_var.get())
        out = translate(text, path=path)
        frame = build_machine_frame(text, path=path)
        fsot = {}
        if path is not EncodePath.MORSE:
            try:
                fsot = bridge_machine_payload(text) if path is EncodePath.MACHINE else {}
            except Exception as e:
                fsot = {"error": str(e)}
        payload = {
            "recommendation": path_recommendation(),
            "result": out,
            "abi_frame": frame.to_dict(),
            "fsot_bridge": {
                "fold": fsot.get("fold"),
                "modulators": fsot.get("modulators"),
                "drivers": fsot.get("drivers"),
            }
            if fsot
            else None,
        }
        self.enc_out.delete("1.0", tk.END)
        self.enc_out.insert(tk.END, json.dumps(payload, indent=2)[:14000])

    def _do_chem_bridge(self) -> None:
        from fsot_nuron.machine_encode import chemical_signals_to_machine
        from fsot_nuron.fsot_bridge import bridge_chemical_dna

        text = self.enc_in.get("1.0", tk.END).strip()
        dna = text if all(c in "ACGTacgtUuNn \n" for c in text[:80]) else "ATGAAACGGTTTGCG"
        out = chemical_signals_to_machine(dna)
        fsot = bridge_chemical_dna(dna)
        self.enc_out.delete("1.0", tk.END)
        self.enc_out.insert(
            tk.END,
            "Chemical → machine + FSOT Biology fold\n"
            + json.dumps({"abi": out, "fsot_bridge": fsot}, indent=2)[:14000],
        )

    def _do_inject(self) -> None:
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
            "packet": pkt.to_dict(),
            "external_drive": {
                "n_units": int(ext.numel()),
                "nonzero": int((ext != 0).sum()),
                "mean": float(ext.mean()),
                "max": float(ext.max()),
                "sens_slice_head": ext[:8].tolist(),
            },
            "note": "FSOT-coupled when path is machine/chemical (meta.S / meta.fold).",
        }
        self.enc_out.delete("1.0", tk.END)
        self.enc_out.insert(tk.END, json.dumps(report, indent=2)[:12000])
        self._log(
            f"[inject] path={path} S={pkt.meta.get('S')} strength={pkt.strength:.3f} "
            f"nonzero={report['external_drive']['nonzero']}\n"
        )

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
            }
        self.enc_out.delete("1.0", tk.END)
        self.enc_out.insert(tk.END, "Path comparison\n" + json.dumps(rows, indent=2))

    def _refresh_live(self) -> None:
        lines = ["=== Live metrics (local) ===\n"]
        try:
            from fsot_nuron.fsot_bridge import fold_diagnostics, verify_fsot_bridge
            from fsot_nuron.machine_encode import path_recommendation, verify_machine_path

            f = fold_diagnostics()
            br = verify_fsot_bridge()
            ver = verify_machine_path("FSOT")
            lines.append("Folds:\n")
            lines.append(json.dumps(f, indent=2, default=str)[:3000] + "\n\n")
            lines.append(
                "Bridge ok={}  Machine utf8={} frame={}\n\n".format(
                    br.get("ok"), ver.get("utf8_roundtrip_ok"), ver.get("frame_roundtrip_ok")
                )
            )
            lines.append("Encoding: " + path_recommendation()["summary"] + "\n\n")
        except Exception as e:
            lines.append(f"metrics error: {e}\n")

        for name in ("intelligence_probe.json", "scalpel_rates.json"):
            p = ROOT / "artifacts" / name
            if p.is_file():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    slim = {
                        "file": name,
                        "generated_at": data.get("generated_at"),
                        "gates": data.get("gates"),
                        "fsot_folds": data.get("fsot_folds")
                        or {
                            "S_Biology": (data.get("fsot_folds") or {}).get("S_Biology"),
                        },
                        "params": data.get("params"),
                    }
                    if "results" in data:
                        slim["results_keys"] = list(data["results"].keys())
                        for k, v in data["results"].items():
                            if isinstance(v, dict) and "top1_accuracy" in v:
                                slim[f"top1_{k}"] = v["top1_accuracy"]
                    lines.append(f"Artifact {name}:\n")
                    lines.append(json.dumps(slim, indent=2, default=str)[:2500] + "\n\n")
                except Exception as e:
                    lines.append(f"artifact {name}: {e}\n")

        lines.append(f"ROOT: {ROOT}\n")
        self.live_out.delete("1.0", tk.END)
        self.live_out.insert(tk.END, "".join(lines))

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
