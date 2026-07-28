#!/usr/bin/env python3
"""
FSOT-2.1-Neural stage stress suite.

Purpose: push this stage until it breaks, while measuring wet-lab accuracy.
Doctrine: archive pin → folds → domain engines; biology accuracy first.

Stages:
  A  Foundation (pin, codon, atlas S)
  B  Machine body ABI scale
  C  Genetic / multi-region scale
  D  Scalpel Allen class rates (1% then 2% fallback)
  E  Intelligence probe ladder (items / delay)
  F  Zig body host
  G  Console display review

Usage:
  python run_stress_suite.py
  python run_stress_suite.py --quick   # skip heaviest intel ladder rungs
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("FSOT_PHYSICAL_ARCHIVE", r"I:\FSOT-Physical-Archive")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StressSuite:
    def __init__(self, quick: bool = False) -> None:
        self.quick = quick
        self.results: List[Dict[str, Any]] = []
        self.breaks: List[Dict[str, Any]] = []
        self.t0 = time.perf_counter()

    def record(
        self,
        stage: str,
        name: str,
        ok: bool,
        *,
        critical: bool = False,
        metrics: Optional[Dict[str, Any]] = None,
        error: str = "",
        note: str = "",
    ) -> None:
        row = {
            "stage": stage,
            "name": name,
            "ok": bool(ok),
            "critical": critical,
            "metrics": metrics or {},
            "error": error[:800] if error else "",
            "note": note,
            "t_s": round(time.perf_counter() - self.t0, 2),
        }
        self.results.append(row)
        tag = "PASS" if ok else ("BREAK" if critical else "SOFT")
        print(f"  [{tag}] {stage}/{name}" + (f"  {note}" if note else ""))
        if metrics:
            for k, v in list(metrics.items())[:8]:
                print(f"         {k}={v}")
        if error and not ok:
            print(f"         err: {error[:200]}")
        if not ok:
            self.breaks.append(row)

    # ----- stages -----

    def stage_A_foundation(self) -> None:
        print("\n=== A · Foundation (math + genetics authority) ===")
        try:
            from fsot_nuron.archive_pin import pin_archive, check_local_seeds
            from fsot_nuron.chemical_codon import codon_path_verify
            from fsot_nuron.fsot_bridge import verify_fsot_bridge, fold_diagnostics

            ok_s, max_err, bad = check_local_seeds()
            self.record(
                "A",
                "seeds_vs_archive",
                ok_s,
                critical=True,
                metrics={"max_rel_err": max_err, "bad": bad[:5]},
            )
            pin = pin_archive(write_snapshot=False)
            self.record(
                "A",
                "archive_pin",
                bool(pin.connected and pin.seed_match_ok and pin.compute_matches_certificate),
                critical=True,
                metrics={
                    "connected": pin.connected,
                    "seed_match_ok": pin.seed_match_ok,
                    "sha": (pin.compute_sha256 or "")[:16],
                    "seven_way": pin.seven_way_bare_metal,
                },
            )
            cv = codon_path_verify()
            self.record(
                "A",
                "codon_64_map",
                bool(cv.get("perfect")),
                critical=True,
                metrics={"roundtrip": f"{cv.get('roundtrip_ok')}/{cv.get('n_codons')}"},
            )
            folds = fold_diagnostics()
            bio = float(folds.get("S_Biology") or 0)
            neuro = float(folds.get("S_Neuroscience") or 0)
            atlas_ok = abs(bio - 0.4447) < 0.01 and abs(neuro - 0.5144) < 0.01
            self.record(
                "A",
                "atlas_domain_S",
                atlas_ok,
                critical=True,
                metrics={"S_Biology": bio, "S_Neuroscience": neuro},
                note="Biology≈0.445 Neuroscience≈0.514",
            )
            br = verify_fsot_bridge()
            self.record(
                "A",
                "fsot_bridge",
                bool(br.get("ok")),
                critical=True,
                metrics={"free_parameters": br.get("free_parameters"), "atlas_ok": br.get("atlas_ok")},
            )
        except Exception as e:
            self.record("A", "foundation_block", False, critical=True, error=traceback.format_exc())

    def stage_B_machine(self) -> None:
        print("\n=== B · Machine body ABI scale ===")
        try:
            from fsot_nuron.machine_encode import (
                verify_machine_path,
                translate,
                EncodePath,
                build_machine_frame,
                MachineFrame,
                text_to_utf8_trits,
                trits_to_utf8_text,
            )
            from fsot_nuron.fsot_bridge import bridge_machine_payload
            from fsot_nuron.sensory import SensoryBus, push_machine_text

            mv = verify_machine_path("FSOT neural stress")
            self.record(
                "B",
                "machine_verify",
                bool(mv.get("utf8_roundtrip_ok") and mv.get("frame_roundtrip_ok")),
                critical=True,
                metrics=mv,
            )

            # Scale payloads
            sizes = [1, 16, 256, 4096] if self.quick else [1, 16, 256, 4096, 16384]
            for n in sizes:
                payload = ("FSOT-" + "αβγ" * 8) * max(1, n // 20)
                payload = payload[:n] if len(payload) > n else payload.ljust(n, "x")
                trits = text_to_utf8_trits(payload)
                back = trits_to_utf8_text(trits)
                fr = build_machine_frame(payload)
                raw = fr.to_bytes()
                fr2 = MachineFrame.from_bytes(raw)
                ok = back == payload and fr2.n_trits == fr.n_trits
                self.record(
                    "B",
                    f"payload_{n}B",
                    ok,
                    critical=n <= 4096,
                    metrics={
                        "n_trits": len(trits),
                        "frame_bytes": len(raw),
                        "roundtrip": back == payload,
                    },
                )

            # Morse secondary must not be primary
            morse = translate("SOS", path=EncodePath.MORSE)
            self.record(
                "B",
                "morse_secondary",
                morse.get("primary") is False,
                metrics={"n_trits": morse.get("n_trits")},
            )

            # Inject many packets
            bus = SensoryBus(max_queue=512)
            n_pkt = 50 if self.quick else 200
            for i in range(n_pkt):
                push_machine_text(bus, f"pkt-{i}-stress", path="machine")
            # bus max 512 but drain in build
            ext = bus.build_external(128, {"sens": list(range(64)), "thal": list(range(64, 128))})
            self.record(
                "B",
                f"inject_{n_pkt}_packets",
                int((ext != 0).sum()) > 0,
                metrics={"nonzero": int((ext != 0).sum()), "mean": float(ext.mean())},
            )

            # Bridge S stays finite under large text
            big = "neural " * 500
            br = bridge_machine_payload(big)
            S = br["modulators"]["S"]
            self.record(
                "B",
                "bridge_large_text",
                abs(S) < 10 and br["modulators"]["sensory_strength"] > 0,
                metrics={"S": S, "strength": br["modulators"]["sensory_strength"]},
            )
        except Exception as e:
            self.record("B", "machine_block", False, critical=True, error=traceback.format_exc())

    def stage_C_scale(self) -> None:
        print("\n=== C · Genetic / multi-region scale ===")
        try:
            import torch
            from fsot_nuron.genetic_network import GeneticNeuralNetwork, GeneticNetworkConfig
            from fsot_nuron.brain_architecture import run_brain_design_suite

            unit_counts = [32, 64] if self.quick else [32, 64, 128, 256]
            for n in unit_counts:
                t1 = time.perf_counter()
                gcfg = GeneticNetworkConfig(n_units=n, connectivity="genetic_sparse", seed=0)
                gnet = GeneticNeuralNetwork(gcfg, device="cpu")
                spikes = 0
                steps = 40 if self.quick else 80
                for _ in range(steps):
                    S, fired, _, _, _ = gnet.step(torch.ones(n) * 0.45)
                    spikes += int(fired.sum())
                dt = time.perf_counter() - t1
                self.record(
                    "C",
                    f"genetic_net_n{n}",
                    spikes >= 0 and float(S.mean()) == float(S.mean()),  # finite
                    critical=n <= 128,
                    metrics={
                        "spikes_total": spikes,
                        "S_mean": float(S.mean()),
                        "synapses": int((gnet.W != 0).sum()),
                        "wall_s": round(dt, 2),
                    },
                )

            t1 = time.perf_counter()
            suite = run_brain_design_suite(
                steps=80 if self.quick else 200,
                device="cpu",
                profile="ai_efficient",
                sensory=False,
            )
            dt = time.perf_counter() - t1
            brain = suite.get("brain")
            n_units = getattr(brain, "n_units", 0) if brain is not None else 0
            self.record(
                "C",
                "multi_region_brain",
                brain is not None and n_units > 0,
                critical=True,
                metrics={"n_units": n_units, "wall_s": round(dt, 2), "keys": list(suite.keys())[:12]},
            )
        except Exception as e:
            self.record("C", "scale_block", False, critical=True, error=traceback.format_exc())

    def stage_D_scalpel(self) -> None:
        print("\n=== D · Scalpel Allen wet-lab class rates ===")
        try:
            from fsot_nuron.class_ephys import build_class_targets
            from fsot_nuron.cell_types import build_typed_population
            from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
            from fsot_nuron.scalpel_rate import scalpel_calibrate
            import torch

            targets = build_class_targets(min_cells=15, mouse_only=True)
            need = {"Pyr", "PV", "SST", "VIP"}
            have = set(targets.keys())
            self.record(
                "D",
                "allen_targets_loaded",
                need.issubset(have),
                critical=True,
                metrics={
                    k: {
                        "n": targets[k].n_cells,
                        "rate_Hz": targets[k].mean_rate_Hz,
                    }
                    for k in sorted(have & need)
                },
            )

            for tol in ([0.02] if self.quick else [0.01, 0.02]):
                genotypes = build_typed_population(64, seed=42, diversity=True)
                labels = [getattr(g, "cell_type", "Pyr") for g in genotypes]
                phenotypes = [dict(g.phenotype) for g in genotypes]
                net = FSOTNeuronBatch(NeuronConfig(n_units=64), device="cpu")
                d_eff = torch.tensor([p["d_eff"] for p in phenotypes], dtype=net.dtype)
                thr = torch.tensor([p["fire_threshold"] for p in phenotypes], dtype=net.dtype)
                vrest = torch.tensor(
                    [p.get("vrest_mV", -70.0) for p in phenotypes], dtype=net.dtype
                )
                net.apply_bio_params(
                    d_eff=d_eff, fire_threshold=thr, vrest_mV=vrest, mode_name="stress"
                )
                focus = [c for c in ("Pyr", "PV", "SST", "VIP") if c in labels and c in targets]
                t1 = time.perf_counter()
                report = scalpel_calibrate(
                    net,
                    labels,
                    phenotypes,
                    targets,
                    focus_order=focus,
                    tol=tol,
                    max_iters=18 if self.quick else 28,
                    steps=900 if self.quick else 1400,
                    require_classes=focus,
                )
                dt = time.perf_counter() - t1
                class_rows = {}
                for lab, st in report.classes.items():
                    class_rows[lab] = {
                        "target_Hz": st.target_Hz,
                        "measured_Hz": st.measured_Hz,
                        "rel_err": st.rel_err,
                        "within_tol": st.rel_err == st.rel_err and st.rel_err <= tol,
                    }
                within = sum(1 for v in class_rows.values() if v["within_tol"])
                self.record(
                    "D",
                    f"scalpel_tol_{tol:.0%}",
                    bool(report.ok),
                    critical=(tol >= 0.02),  # 2% is hard floor; 1% may soft-break
                    metrics={
                        "scalpel_ok": report.ok,
                        "classes_within": f"{within}/{len(class_rows)}",
                        "wall_s": round(dt, 2),
                        **{f"{k}_err": v["rel_err"] for k, v in class_rows.items()},
                    },
                    note="1% is stretch; 2% wet-lab floor if 1% fails",
                )
                # Persist last for UI
                out = {
                    "generated_at": _now(),
                    "tol": tol,
                    "report": report.to_dict(),
                    "gates": {"scalpel_ok": report.ok},
                    "stress": True,
                }
                (ROOT / "artifacts").mkdir(parents=True, exist_ok=True)
                (ROOT / "artifacts" / "scalpel_rates.json").write_text(
                    json.dumps(out, indent=2), encoding="utf-8"
                )
        except Exception as e:
            self.record("D", "scalpel_block", False, critical=True, error=traceback.format_exc())

    def stage_E_intelligence(self) -> None:
        print("\n=== E · Intelligence probe ladder (FSOT-bridged items) ===")
        try:
            from fsot_nuron.scalpel_brain import build_scalpel_brain
            from fsot_nuron.brain_architecture import run_brain_design_suite
            from fsot_nuron.learning_memory import learning_probe

            # Prefer scalpel brain; fall back to design suite
            brain = None
            try:
                brain, report, meta = build_scalpel_brain(
                    profile="ai_efficient", device="cpu", tol=0.02
                )
                self.record(
                    "E",
                    "scalpel_brain_build",
                    brain is not None,
                    metrics={"scalpel_ok": getattr(report, "ok", None), "meta": str(meta)[:120]},
                )
            except Exception as e:
                suite = run_brain_design_suite(
                    steps=200, device="cpu", profile="ai_efficient", sensory=False
                )
                brain = suite["brain"]
                self.record(
                    "E",
                    "scalpel_brain_build",
                    False,
                    note="fell back to design suite",
                    error=str(e),
                )

            assert brain is not None
            # Ladder: find where accuracy collapses
            ladder = (
                [(4, 50, 120, 100), (6, 100, 150, 120)]
                if self.quick
                else [
                    (4, 0, 150, 120),
                    (6, 200, 200, 180),
                    (12, 400, 280, 220),
                    (16, 600, 300, 240),
                    (24, 800, 280, 200),
                ]
            )
            last_ok_top1 = None
            for n_items, delay, enc, ret in ladder:
                t1 = time.perf_counter()
                rep = learning_probe(
                    brain,
                    n_items=n_items,
                    encode_steps=enc,
                    retrieve_steps=ret,
                    seed=7,
                    delay_steps=delay,
                    consolidate=False,
                    item_mode="fsot_machine",
                )
                dt = time.perf_counter() - t1
                chance = 1.0 / max(1, n_items)
                above = rep.top1_accuracy > chance
                half = rep.top1_accuracy >= 0.5
                # Critical break: at ≤12 items should stay above chance and preferably ≥0.5
                critical = n_items <= 12
                ok = above and (half if n_items <= 12 else above)
                if ok:
                    last_ok_top1 = (n_items, rep.top1_accuracy)
                self.record(
                    "E",
                    f"intel_items{n_items}_delay{delay}",
                    ok,
                    critical=critical and not above,
                    metrics={
                        "top1": rep.top1_accuracy,
                        "chance": chance,
                        "sim+": rep.mean_correct_sim,
                        "sim-": rep.mean_incorrect_sim,
                        "sme_theta": rep.sme_theta_encode_gt_rest,
                        "sme_gamma": rep.sme_gamma_encode_gt_rest,
                        "wall_s": round(dt, 2),
                        "notes": rep.notes[:80],
                    },
                    note="FSOT machine items; break when top1≤chance or <0.5 at ≤12",
                )
                # Persist last for UI
                art = {
                    "generated_at": _now(),
                    "stress": True,
                    "params": {
                        "items": n_items,
                        "delay_steps": delay,
                        "item_mode": "fsot_machine",
                    },
                    "results": {
                        "delay": {
                            "top1_accuracy": rep.top1_accuracy,
                            "mean_correct_sim": rep.mean_correct_sim,
                            "mean_incorrect_sim": rep.mean_incorrect_sim,
                        }
                    },
                    "gates": {
                        "above_chance": above,
                        "ge_half": half,
                    },
                }
                (ROOT / "artifacts").mkdir(parents=True, exist_ok=True)
                (ROOT / "artifacts" / "intelligence_probe.json").write_text(
                    json.dumps(art, indent=2), encoding="utf-8"
                )
                # Early stop if fully collapsed
                if rep.top1_accuracy <= chance and n_items >= 12:
                    self.record(
                        "E",
                        "ladder_stop_collapsed",
                        False,
                        note=f"stopped ladder after items={n_items} top1={rep.top1_accuracy}",
                    )
                    break

            self.record(
                "E",
                "ladder_summary",
                last_ok_top1 is not None,
                metrics={"last_ok": last_ok_top1},
            )
        except Exception as e:
            self.record("E", "intel_block", False, critical=True, error=traceback.format_exc())

    def stage_F_zig(self) -> None:
        print("\n=== F · Zig body host ===")
        zig = ROOT / "embodiment" / "zig" / "zig-out" / "bin" / "fsot_trit_host.exe"
        if not zig.is_file():
            self.record(
                "F",
                "zig_host_present",
                False,
                critical=False,
                note="missing exe — soft break; build with zig build",
            )
            return
        self.record("F", "zig_host_present", True, metrics={"path": str(zig)})
        try:
            p = subprocess.run(
                [str(zig)],
                cwd=str(zig.parent),
                capture_output=True,
                text=True,
                timeout=60,
            )
            out = (p.stdout or "") + (p.stderr or "")
            ok = p.returncode == 0 and "FSOT_TRIT PASS" in out
            self.record(
                "F",
                "zig_host_run",
                ok,
                critical=True,
                metrics={
                    "returncode": p.returncode,
                    "head": out[:200].replace("\n", " | "),
                },
            )
        except Exception as e:
            self.record("F", "zig_host_run", False, critical=True, error=str(e))

    def stage_G_console(self) -> None:
        print("\n=== G · Console display review ===")
        try:
            p = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "review_console_displays.py")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
            )
            ok = p.returncode == 0
            self.record(
                "G",
                "console_displays",
                ok,
                critical=True,
                metrics={"returncode": p.returncode},
                note=(p.stdout or "")[-300:].replace("\n", " | "),
            )
        except Exception as e:
            self.record("G", "console_displays", False, critical=True, error=str(e))

    def write_report(self) -> Path:
        art = ROOT / "artifacts"
        art.mkdir(parents=True, exist_ok=True)
        critical_breaks = [b for b in self.breaks if b.get("critical")]
        soft_breaks = [b for b in self.breaks if not b.get("critical")]
        report = {
            "generated_at": _now(),
            "quick": self.quick,
            "duration_s": round(time.perf_counter() - self.t0, 2),
            "n_tests": len(self.results),
            "n_pass": sum(1 for r in self.results if r["ok"]),
            "n_fail": sum(1 for r in self.results if not r["ok"]),
            "critical_breaks": critical_breaks,
            "soft_breaks": soft_breaks,
            "results": self.results,
            "doctrine": "wet-lab accuracy first; pin D1D38A; machine body; FSOT bridge",
        }
        path = art / "stress_suite_report.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        md_lines = [
            "# Stress suite report — stage break map",
            "",
            f"Generated: `{report['generated_at']}`  ",
            f"Duration: **{report['duration_s']}s**  ·  tests **{report['n_pass']}/{report['n_tests']}** pass  ",
            f"Mode: `{'quick' if self.quick else 'full'}`",
            "",
            "## Doctrine",
            "",
            "- Archive pin **D1D38A** + codon map",
            "- Allen wet-lab class rates (scalpel)",
            "- Intelligence via **FSOT machine** items (not Morse)",
            "- Biology accuracy before performance",
            "",
            "## Critical breaks (must fix before next climb)",
            "",
        ]
        if not critical_breaks:
            md_lines.append("_None — critical path held._")
        else:
            for b in critical_breaks:
                md_lines.append(
                    f"- **{b['stage']}/{b['name']}** — {b.get('note') or b.get('error') or 'failed'}"
                )
                if b.get("metrics"):
                    md_lines.append(f"  - metrics: `{json.dumps(b['metrics'])[:200]}`")
        md_lines += ["", "## Soft breaks (known stretch / scale)", ""]
        if not soft_breaks:
            md_lines.append("_None._")
        else:
            for b in soft_breaks:
                md_lines.append(
                    f"- **{b['stage']}/{b['name']}** — {b.get('note') or 'failed'}  "
                    f"`{json.dumps(b.get('metrics') or {})[:160]}`"
                )
        md_lines += [
            "",
            "## Full results",
            "",
            "| Stage | Name | OK | Critical | t(s) |",
            "|-------|------|:--:|:--------:|-----:|",
        ]
        for r in self.results:
            md_lines.append(
                f"| {r['stage']} | {r['name']} | {'Y' if r['ok'] else 'N'} | "
                f"{'Y' if r['critical'] else ''} | {r['t_s']} |"
            )
        md_lines += [
            "",
            "## Where to go next",
            "",
            "1. Fix any **critical** breaks first (pin, codon, scalpel 2%, zig host).",
            "2. Soft breaks at 1% scalpel or high item counts define the accuracy frontier.",
            "3. After green critical path: Zig machine-frame inject + live brain meters in UI.",
            "",
            f"JSON: `artifacts/stress_suite_report.json`",
            "",
        ]
        md_path = ROOT / "docs" / "STRESS_STAGE_REPORT.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        res = ROOT / "data" / "results"
        res.mkdir(parents=True, exist_ok=True)
        (res / "STRESS_STAGE_REPORT.md").write_text("\n".join(md_lines), encoding="utf-8")
        (res / "stress_suite_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote {path}")
        print(f"Wrote {md_path}")
        return path


def main() -> int:
    ap = argparse.ArgumentParser(description="FSOT Neural stage stress suite")
    ap.add_argument("--quick", action="store_true", help="lighter ladder (faster)")
    args = ap.parse_args()

    print("=== FSOT-2.1-Neural STRESS SUITE ===")
    print("Find break points while holding wet-lab accuracy.")
    print(f"quick={args.quick}")

    s = StressSuite(quick=args.quick)
    s.stage_A_foundation()
    s.stage_B_machine()
    s.stage_C_scale()
    s.stage_D_scalpel()
    s.stage_E_intelligence()
    s.stage_F_zig()
    s.stage_G_console()
    s.write_report()

    crit = [b for b in s.breaks if b.get("critical")]
    print("\n=== SUMMARY ===")
    print(f"pass {sum(1 for r in s.results if r['ok'])}/{len(s.results)}")
    print(f"critical breaks: {len(crit)}")
    print(f"soft breaks: {len(s.breaks) - len(crit)}")
    if crit:
        print("CRITICAL:")
        for b in crit:
            print(f"  - {b['stage']}/{b['name']}")
        return 1
    print("CRITICAL PATH GREEN — soft breaks (if any) define the frontier.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
