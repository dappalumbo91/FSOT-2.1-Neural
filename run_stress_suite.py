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
  H  Embodiment v0.7 (host senses, self-mod, multi-region live, vault)

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

os.environ.setdefault("FSOT_STANDALONE", "1")
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

            focus_need = [c for c in ("Pyr", "PV", "SST", "VIP") if c in targets]
            # --- 2% floor (critical): short scalpel path ---
            genotypes = build_typed_population(64, seed=42, diversity=True)
            labels = [getattr(g, "cell_type", "Pyr") for g in genotypes]
            phenotypes = [dict(g.phenotype) for g in genotypes]
            net = FSOTNeuronBatch(NeuronConfig(n_units=64, dt_ms=1.0), device="cpu")
            d_eff = torch.tensor([p["d_eff"] for p in phenotypes], dtype=net.dtype)
            thr = torch.tensor([p["fire_threshold"] for p in phenotypes], dtype=net.dtype)
            vrest = torch.tensor(
                [p.get("vrest_mV", -70.0) for p in phenotypes], dtype=net.dtype
            )
            net.apply_bio_params(
                d_eff=d_eff, fire_threshold=thr, vrest_mV=vrest, mode_name="stress"
            )
            focus = [c for c in focus_need if c in labels]
            t1 = time.perf_counter()
            report2 = scalpel_calibrate(
                net,
                labels,
                phenotypes,
                targets,
                focus_order=focus,
                tol=0.02,
                max_iters=18 if self.quick else 28,
                steps=900 if self.quick else 1400,
                require_classes=focus,
            )
            dt2 = time.perf_counter() - t1
            class_rows2 = {
                lab: {
                    "target_Hz": st.target_Hz,
                    "measured_Hz": st.measured_Hz,
                    "rel_err": st.rel_err,
                    "within_tol": st.rel_err <= 0.02,
                }
                for lab, st in report2.classes.items()
            }
            within2 = sum(1 for v in class_rows2.values() if v["within_tol"])
            self.record(
                "D",
                "scalpel_tol_2%",
                bool(report2.ok),
                critical=True,
                metrics={
                    "scalpel_ok": report2.ok,
                    "classes_within": f"{within2}/{len(class_rows2)}",
                    "wall_s": round(dt2, 2),
                    **{f"{k}_err": v["rel_err"] for k, v in class_rows2.items()},
                },
                note="2% Allen wet-lab floor",
            )
            out = {
                "generated_at": _now(),
                "tol": 0.02,
                "report": report2.to_dict(),
                "gates": {"scalpel_ok": report2.ok},
                "stress": True,
            }
            (ROOT / "artifacts").mkdir(parents=True, exist_ok=True)
            (ROOT / "artifacts" / "scalpel_rates.json").write_text(
                json.dumps(out, indent=2), encoding="utf-8"
            )

            # --- 1% climb (soft→climb): continuous-ms + long FI (T≳4s for integer spikes) ---
            if not self.quick:
                from fsot_nuron.precision_climb import precision_micro_climb

                dt_ms = 0.5
                sim_ms = 4200.0
                steps1 = int(round(sim_ms / dt_ms))
                genotypes1 = build_typed_population(64, seed=42, diversity=True)
                labels1 = [getattr(g, "cell_type", "Pyr") for g in genotypes1]
                phenotypes1 = [dict(g.phenotype) for g in genotypes1]
                net1 = FSOTNeuronBatch(
                    NeuronConfig(n_units=64, dt_ms=dt_ms), device="cpu"
                )
                d1 = torch.tensor([p["d_eff"] for p in phenotypes1], dtype=net1.dtype)
                thr1 = torch.tensor(
                    [p["fire_threshold"] for p in phenotypes1], dtype=net1.dtype
                )
                vr1 = torch.tensor(
                    [p.get("vrest_mV", -70.0) for p in phenotypes1], dtype=net1.dtype
                )
                net1.apply_bio_params(
                    d_eff=d1, fire_threshold=thr1, vrest_mV=vr1, mode_name="stress_1pct"
                )
                focus1 = [c for c in focus_need if c in labels1]
                t1 = time.perf_counter()
                report1 = precision_micro_climb(
                    net1,
                    labels1,
                    phenotypes1,
                    targets,
                    tol=0.01,
                    max_rounds=48,
                    steps=steps1,
                    seed_order=focus1,
                )
                dt1 = time.perf_counter() - t1
                class_rows1 = {
                    lab: {
                        "target_Hz": st.target_Hz,
                        "measured_Hz": st.measured_Hz,
                        "rel_err": st.rel_err,
                        "within_tol": st.rel_err <= 0.01,
                    }
                    for lab, st in report1.classes.items()
                }
                within1 = sum(1 for v in class_rows1.values() if v["within_tol"])
                self.record(
                    "D",
                    "scalpel_tol_1%",
                    bool(report1.ok),
                    critical=False,  # soft if fails; climb path is the accuracy frontier
                    metrics={
                        "scalpel_ok": report1.ok,
                        "classes_within": f"{within1}/{len(class_rows1)}",
                        "wall_s": round(dt1, 2),
                        "dt_ms": dt_ms,
                        "sim_ms": sim_ms,
                        "method": "precision_micro_climb continuous-ms",
                        **{f"{k}_err": v["rel_err"] for k, v in class_rows1.items()},
                    },
                    note="1% needs T≳4s FI + continuous refractory (integer spike bound)",
                )
                out1 = {
                    "generated_at": _now(),
                    "tol": 0.01,
                    "report": report1.to_dict(),
                    "gates": {"scalpel_ok": report1.ok, "precision_1pct": report1.ok},
                    "stress": True,
                    "method": "precision_micro_climb",
                    "dt_ms": dt_ms,
                    "sim_ms": sim_ms,
                }
                (ROOT / "artifacts" / "precision_climb.json").write_text(
                    json.dumps(out1, indent=2), encoding="utf-8"
                )
                if report1.ok:
                    (ROOT / "artifacts" / "scalpel_rates.json").write_text(
                        json.dumps(out1, indent=2), encoding="utf-8"
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

    def stage_H_embodiment(self) -> None:
        """v0.7 body: adaptive hardware, senses, self-mod, multi-region visual path."""
        print("\n=== H · Embodiment (senses · self-mod · multi-region · vault) ===")
        try:
            from fsot_nuron.hardware_body import (
                discover_hardware,
                sample_metrics,
                boot_body_report,
                metrics_to_thalamic_packet,
            )
            from fsot_nuron.sensory.host_senses import (
                sample_host_senses,
                note_hid_key,
                note_hid_click,
                note_log_line,
                sample_net_util,
            )
            from fsot_nuron.self_modulation import modulate_from_metrics
            from fsot_nuron.sensory.bus import SensoryBus
            from fsot_nuron.brain_architecture import FSOTBrainDesign, BrainDesignConfig, BRAIN_PROFILES, DEFAULT_PROJECTIONS
            from fsot_nuron.obsidian_brain import ensure_live_vault, append_live_tick
            import torch

            # H1 adaptive hardware (not locked to one PC)
            hw = discover_hardware()
            body = boot_body_report()
            # H0 standalone pin (no external archive required)
            from fsot_nuron.archive_pin import pin_archive
            from fsot_nuron.paths import transplant_report, standalone_mode

            pin = pin_archive(write_snapshot=False)
            tr = transplant_report()
            self.record(
                "H",
                "standalone_transplant_pin",
                bool(pin.connected and pin.seed_match_ok and standalone_mode()),
                critical=True,
                metrics={
                    "pin_mode": getattr(pin, "pin_mode", None),
                    "transplantable": getattr(pin, "transplantable", None),
                    "sha": (pin.compute_sha256 or "")[:16],
                    "archive_root": (pin.archive_root or "")[-40:],
                    "standalone_complete": tr.get("standalone_complete"),
                    "external_optional": tr.get("external_archive_optional"),
                },
                note="brain must boot from in-repo snapshot only",
            )

            self.record(
                "H",
                "hardware_discover",
                bool(hw.cpu_count_logical >= 1 and hw.recommended_n_units >= 16),
                critical=True,
                metrics={
                    "system": hw.system,
                    "cpu_logical": hw.cpu_count_logical,
                    "device": hw.recommended_device,
                    "n_units": hw.recommended_n_units,
                    "dt_ms": hw.recommended_dt_ms,
                    "cuda": hw.cuda_available,
                    "sensors": hw.sensors_available[:12],
                },
                note="portable boot probe",
            )

            # H2 metrics + thalamic packet
            m = sample_metrics(hw)
            pkt = metrics_to_thalamic_packet(m)
            self.record(
                "H",
                "interoception_packet",
                pkt.target_region == "thal" and 0.0 <= m.as_drive_scalar() <= 1.0,
                critical=True,
                metrics={
                    "drive": round(m.as_drive_scalar(), 4),
                    "cpu": round(m.cpu_util, 4),
                    "mem": round(m.mem_util, 4),
                    "net": round(m.net_util, 4),
                    "strength": round(pkt.strength, 4),
                },
            )

            # H3 extended senses
            note_hid_key(6)
            note_hid_click(2)
            note_log_line("stress suite: scalpel PASS soft note")
            note_log_line("stress suite: ERROR injection for log feature density")
            sample_net_util()
            time.sleep(0.05)
            sample_net_util()
            snap = sample_host_senses(metric=m, include_audio=False)
            mods = {p.modality.value for p in snap.packets}
            self.record(
                "H",
                "host_senses_sample",
                "sys_metric" in mods and len(snap.packets) >= 2,
                critical=True,
                metrics={
                    "sensors_live": snap.sensors_live,
                    "modalities": sorted(mods),
                    "n_packets": len(snap.packets),
                    "hid": snap.hid,
                    "log": snap.log,
                },
            )

            # H4 self-modulation POOF / SUCTION (seed-derived)
            m_hi = type(m)(
                cpu_util=0.92, mem_util=0.88, disk_util=0.4, net_util=0.3, temp_norm=0.5
            )
            m_lo = type(m)(
                cpu_util=0.04, mem_util=0.08, disk_util=0.05, net_util=0.0, temp_norm=0.0
            )
            mod_hi = modulate_from_metrics(m_hi, hw, fire_frac=0.4)
            mod_lo = modulate_from_metrics(m_lo, hw, fire_frac=0.02)
            mod_mid = modulate_from_metrics(m, hw, fire_frac=0.1)
            poof_ok = mod_hi.mode == "dampen" and mod_hi.stim_scale < 1.0
            suction_ok = mod_lo.mode == "explore" and mod_lo.stim_scale >= 1.0
            self.record(
                "H",
                "self_mod_poof_suction",
                poof_ok and suction_ok,
                critical=True,
                metrics={
                    "hi_mode": mod_hi.mode,
                    "hi_stim": round(mod_hi.stim_scale, 4),
                    "lo_mode": mod_lo.mode,
                    "lo_stim": round(mod_lo.stim_scale, 4),
                    "mid_mode": mod_mid.mode,
                    "mid_stim": round(mod_mid.stim_scale, 4),
                },
                note="POOF dampens under load; SUCTION explores when spare",
            )

            # H5 multi-region brain + sensory bus inject
            prof = BRAIN_PROFILES["ai_efficient"]
            brain = FSOTBrainDesign(
                BrainDesignConfig(
                    regions=list(prof["regions"]),
                    projections=list(DEFAULT_PROJECTIONS),
                    seed=7,
                    device="cpu",
                    dt_ms=0.5,
                )
            )
            bus = SensoryBus()
            for p in snap.packets:
                bus.push(p)
            n = brain.n_units
            ext = bus.build_external(n, brain.region_index, device=brain.device, dtype=brain.net.dtype)
            fires = 0
            for t in range(80):
                e = torch.full((n,), 0.45 * mod_mid.stim_scale, device=brain.device, dtype=brain.net.dtype)
                if (t % 40) < 12:
                    for i in brain.region_index.get("thal", []):
                        e[i] = 0.75 * mod_mid.stim_scale
                e = (e + ext * 0.25).clamp(-0.8, 1.5)
                S, fired, *_ = brain.step(e)
                fires += int(fired.sum().item())
                if t == 0:
                    # only first step had bus drain; re-push lightly for continuity
                    for p in snap.packets[:2]:
                        bus.push(p)
                    ext = bus.build_external(
                        n, brain.region_index, device=brain.device, dtype=brain.net.dtype
                    )
            rates = {}
            for rid, ids in brain.region_index.items():
                # approximate from last fired window — use structure only
                rates[rid] = len(ids)
            self.record(
                "H",
                "multi_region_live_drive",
                brain.n_units >= 24 and fires >= 1 and set(brain.region_index) >= {"thal", "sens", "assoc", "hipp"},
                critical=True,
                metrics={
                    "n_units": brain.n_units,
                    "total_spikes_80": fires,
                    "regions": list(brain.region_index.keys()),
                    "region_sizes": {k: len(v) for k, v in brain.region_index.items()},
                    "mean_S": round(float(S.mean().item()), 4),
                },
                note="bio-like loop thal→sens→assoc↔hipp under host drive",
            )

            # H6 live vault append
            vault = ensure_live_vault()
            live_path = append_live_tick(
                step=80,
                fire_frac=fires / max(1, 80 * n),
                mean_S=float(S.mean().item()),
                load=m.as_drive_scalar(),
                mode=mod_mid.mode,
                stim_scale=mod_mid.stim_scale,
                rates_by_region={k: float(len(v)) for k, v in brain.region_index.items()},
            )
            self.record(
                "H",
                "live_obsidian_vault",
                live_path.is_file() and (vault / ".fsot_vault_marker").is_file(),
                critical=False,
                metrics={"vault": str(vault), "live_md": str(live_path)},
                note="soft — offline second-brain stream",
            )

            # H7 bio comparison snapshot: E/I mass + rate order intent
            struct = brain.structure_report()
            ei = float(struct.get("ei_mass_ratio") or 0)
            # Cortex-like: excitatory mass should dominate recurrent weights somewhat
            self.record(
                "H",
                "bio_ei_mass_ratio",
                ei > 0.5,
                critical=False,
                metrics={
                    "ei_mass_ratio": round(ei, 4),
                    "exc_mass": round(float(struct.get("excitatory_synaptic_mass") or 0), 4),
                    "inh_mass": round(float(struct.get("inhibitory_synaptic_mass") or 0), 4),
                },
                note="soft bio motif: E mass > half I (not medical claim)",
            )

            # H8 scale multi-region under recommended n (soft if slow)
            if not self.quick:
                try:
                    from product.console.visual_brain import build_region_brain_visual

                    t1 = time.perf_counter()
                    b2 = build_region_brain_visual(
                        profile="wetware_ref" if hw.recommended_n_units >= 64 else "ai_efficient",
                        device="cpu",
                        dt_ms=0.5,
                    )
                    for _ in range(40):
                        b2.step(0.55)
                    dt = time.perf_counter() - t1
                    self.record(
                        "H",
                        "visual_brain_factory",
                        b2.n_units >= 24 and dt < 30.0,
                        critical=False,
                        metrics={"n": b2.n_units, "wall_s": round(dt, 2)},
                    )
                except Exception as e:
                    self.record(
                        "H",
                        "visual_brain_factory",
                        False,
                        critical=False,
                        error=str(e),
                    )
        except Exception as e:
            self.record(
                "H",
                "embodiment_block",
                False,
                critical=True,
                error=traceback.format_exc(),
            )

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
            "- Computer body adaptive (senses · POOF/SUCTION · multi-region)",
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
            "1. Fix any **critical** breaks first (pin, codon, scalpel 2%, zig host, embodiment).",
            "2. Soft breaks at 1% scalpel or high item counts define the accuracy frontier.",
            "3. Compare soft intel/scalpel breaks to biology: SME, E/I, Allen class order.",
            "4. Climb: longer FI for 1%, consolidate ladder, vision sense, Zig metric inject.",
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
    s.stage_H_embodiment()
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
