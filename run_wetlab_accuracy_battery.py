#!/usr/bin/env python3
"""
Full wet-lab accuracy battery — every reading we can check against real data.

Layers:
  T0  Structure: pin D1D38A, seeds, codon 64/64, folds atlas, Zig host
  T1  Order: PV > Pyr rates after scalpel
  T2  Class rates ≤2% Allen Cre (stretch 1%)
  T3  Learning: SME theta/gamma, study EEG contrast, consolidate top-1
  T4  Genetic: channel ORFs, genotype diversity, W non-empty

No free parameters on FSOT scalar. Public wet-lab authority only.

  python run_wetlab_accuracy_battery.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


class Battery:
    def __init__(self) -> None:
        self.rows: List[Dict[str, Any]] = []
        self.t0 = time.perf_counter()

    def check(
        self,
        tier: str,
        name: str,
        ok: bool,
        *,
        measured: Any = None,
        expected: Any = None,
        source: str = "",
        note: str = "",
        critical: bool = True,
    ) -> None:
        self.rows.append(
            {
                "tier": tier,
                "name": name,
                "ok": bool(ok),
                "critical": critical,
                "measured": measured,
                "expected": expected,
                "source": source,
                "note": note,
                "t_s": round(time.perf_counter() - self.t0, 2),
            }
        )
        tag = "PASS" if ok else ("FAIL" if critical else "SOFT")
        print(f"  [{tag}] {tier}/{name}")
        if measured is not None or expected is not None:
            print(f"         measured={measured}  expected={expected}")
        if source:
            print(f"         source={source}")
        if note and not ok:
            print(f"         note={note}")

    def t0_structure(self) -> None:
        print("\n=== T0 · Structure (math + genetics identity) ===")
        from fsot_nuron.archive_pin import pin_archive, check_local_seeds
        from fsot_nuron.chemical_codon import codon_path_verify
        from fsot_nuron.fsot_bridge import verify_fsot_bridge, fold_diagnostics
        from fsot_nuron.machine_encode import verify_machine_path

        ok_s, max_err, bad = check_local_seeds()
        self.check(
            "T0",
            "seeds_match_archive",
            ok_s,
            measured=max_err,
            expected="<1e-12 class",
            source="I:\\FSOT-Physical-Archive closed forms",
        )
        pin = pin_archive(write_snapshot=False)
        self.check(
            "T0",
            "archive_pin_D1D38A",
            bool(
                pin.connected
                and pin.seed_match_ok
                and pin.compute_matches_certificate
            ),
            measured=(pin.compute_sha256 or "")[:20],
            expected="D1D38A…",
            source="vendor/fsot_compute.py",
        )
        cv = codon_path_verify()
        self.check(
            "T0",
            "codon_map_64_roundtrip",
            bool(cv.get("perfect")),
            measured=f"{cv.get('roundtrip_ok')}/{cv.get('n_codons')}",
            expected="64/64",
            source="data/64_codon_trinary_map.txt (A,G=+1; C,T=-1)",
        )
        folds = fold_diagnostics()
        bio, neuro = folds.get("S_Biology"), folds.get("S_Neuroscience")
        self.check(
            "T0",
            "atlas_S_Biology",
            abs(float(bio) - 0.4447) < 0.01,
            measured=bio,
            expected="≈+0.445",
            source="fsot_compute DomainConfig Biology D_eff=12",
        )
        self.check(
            "T0",
            "atlas_S_Neuroscience",
            abs(float(neuro) - 0.5144) < 0.01,
            measured=neuro,
            expected="≈+0.514",
            source="fsot_compute Neuroscience D_eff=14",
        )
        br = verify_fsot_bridge()
        self.check(
            "T0",
            "fsot_bridge_zero_free",
            bool(br.get("ok") and br.get("free_parameters") == 0),
            measured=br.get("free_parameters"),
            expected=0,
            source="S=K(T1+T2+T3)",
        )
        mv = verify_machine_path("FSOT wetlab")
        self.check(
            "T0",
            "machine_abi_roundtrip",
            bool(mv.get("utf8_roundtrip_ok") and mv.get("frame_roundtrip_ok")),
            measured={
                "utf8": mv.get("utf8_roundtrip_ok"),
                "frame": mv.get("frame_roundtrip_ok"),
            },
            expected="lossless UTF-8 + frame",
            source="machine_encode (not Morse)",
        )
        zig = ROOT / "embodiment" / "zig" / "zig-out" / "bin" / "fsot_trit_host.exe"
        if zig.is_file():
            p = subprocess.run(
                [str(zig)], capture_output=True, text=True, timeout=60, cwd=str(zig.parent)
            )
            out = (p.stdout or "") + (p.stderr or "")
            self.check(
                "T0",
                "zig_host_body",
                p.returncode == 0 and "FSOT_TRIT PASS" in out,
                measured="FSOT_TRIT PASS" in out and "FSOT_FRAME PASS" in out,
                expected="FSOT_TRIT PASS (+ FSOT_FRAME if rebuilt)",
                source=str(zig),
            )
        else:
            self.check(
                "T0",
                "zig_host_body",
                False,
                critical=False,
                note="zig-out missing — rebuild with zig build",
                source=str(zig),
            )

    def t1_t2_allen(self) -> None:
        print("\n=== T1–T2 · Allen Cre class rates (wet-lab FI) ===")
        import torch
        from fsot_nuron.class_ephys import build_class_targets
        from fsot_nuron.cell_types import build_typed_population
        from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
        from fsot_nuron.scalpel_rate import scalpel_calibrate

        targets = build_class_targets(min_cells=15, mouse_only=True)
        need = ("Pyr", "PV", "SST", "VIP")
        for lab in need:
            t = targets.get(lab)
            self.check(
                "T1",
                f"allen_target_{lab}",
                t is not None and t.n_cells >= 15,
                measured={
                    "n": getattr(t, "n_cells", None),
                    "rate_Hz": getattr(t, "mean_rate_Hz", None),
                },
                expected="public Allen Cre means",
                source="Allen Cell Types Database (mouse, min_cells=15)",
            )

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
            d_eff=d_eff, fire_threshold=thr, vrest_mV=vrest, mode_name="wetlab_battery"
        )
        focus = [c for c in need if c in labels and c in targets]
        report = scalpel_calibrate(
            net,
            labels,
            phenotypes,
            targets,
            focus_order=list(focus),
            tol=0.02,
            max_iters=28,
            steps=1400,
            require_classes=list(focus),
        )
        pyr = report.classes.get("Pyr")
        pv = report.classes.get("PV")
        self.check(
            "T1",
            "pv_faster_than_pyr",
            bool(pv and pyr and pv.measured_Hz > pyr.measured_Hz),
            measured={
                "PV_Hz": getattr(pv, "measured_Hz", None),
                "Pyr_Hz": getattr(pyr, "measured_Hz", None),
            },
            expected="PV >> Pyr (cortical order)",
            source="Allen wet-lab order",
        )
        for lab in focus:
            st = report.classes[lab]
            self.check(
                "T2",
                f"rate_{lab}_within_2pct",
                st.rel_err == st.rel_err and st.rel_err <= 0.02,
                measured={
                    "target_Hz": st.target_Hz,
                    "measured_Hz": st.measured_Hz,
                    "rel_err": st.rel_err,
                },
                expected="|err| ≤ 2%",
                source="Allen Cre FI rate",
            )
        self.check(
            "T2",
            "scalpel_all_focus_2pct",
            bool(report.ok),
            measured=report.ok,
            expected=True,
            source="scalpel_calibrate tol=0.02",
        )

        # 1% climb: continuous-ms + long FI (integer-spike bound requires T≳4s for Pyr ~16 Hz)
        from fsot_nuron.precision_climb import precision_micro_climb

        dt_ms, sim_ms = 0.5, 4200.0
        steps1 = int(round(sim_ms / dt_ms))
        g1 = build_typed_population(64, seed=42, diversity=True)
        labels1 = [getattr(g, "cell_type", "Pyr") for g in g1]
        ph1 = [dict(g.phenotype) for g in g1]
        net1 = FSOTNeuronBatch(NeuronConfig(n_units=64, dt_ms=dt_ms), device="cpu")
        net1.apply_bio_params(
            d_eff=torch.tensor([p["d_eff"] for p in ph1], dtype=net1.dtype),
            fire_threshold=torch.tensor([p["fire_threshold"] for p in ph1], dtype=net1.dtype),
            vrest_mV=torch.tensor(
                [p.get("vrest_mV", -70.0) for p in ph1], dtype=net1.dtype
            ),
            mode_name="wetlab_1pct",
        )
        report1 = precision_micro_climb(
            net1,
            labels1,
            ph1,
            targets,
            tol=0.01,
            max_rounds=48,
            steps=steps1,
            seed_order=list(focus),
        )
        for lab in focus:
            st = report1.classes.get(lab)
            if st is None:
                continue
            self.check(
                "T2",
                f"rate_{lab}_within_1pct",
                st.rel_err == st.rel_err and st.rel_err <= 0.01,
                measured={
                    "target_Hz": st.target_Hz,
                    "measured_Hz": st.measured_Hz,
                    "rel_err": st.rel_err,
                    "method": "precision_micro_climb",
                    "sim_ms": sim_ms,
                    "dt_ms": dt_ms,
                },
                expected="|err| ≤ 1% (continuous-ms climb)",
                source="Allen Cre FI rate + precision_climb",
                critical=False,
            )
        self.check(
            "T2",
            "precision_all_focus_1pct",
            bool(report1.ok),
            measured=report1.ok,
            expected=True,
            source="precision_micro_climb tol=0.01 dt=0.5 sim_ms=4200",
            critical=False,
        )

        # persist for UI (prefer 1% report if green)
        out = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tol": 0.01 if report1.ok else 0.02,
            "report": (report1 if report1.ok else report).to_dict(),
            "report_2pct": report.to_dict(),
            "report_1pct": report1.to_dict(),
            "gates": {
                "scalpel_ok": report.ok,
                "precision_1pct": report1.ok,
            },
            "battery": True,
            "dt_ms": dt_ms,
            "sim_ms": sim_ms,
        }
        (ROOT / "artifacts").mkdir(parents=True, exist_ok=True)
        (ROOT / "artifacts" / "scalpel_rates.json").write_text(
            json.dumps(out, indent=2), encoding="utf-8"
        )
        (ROOT / "artifacts" / "precision_climb.json").write_text(
            json.dumps(
                {
                    "generated_at": out["generated_at"],
                    "tol": 0.01,
                    "report": report1.to_dict(),
                    "gates": {"precision_1pct": report1.ok},
                    "method": "precision_micro_climb",
                    "dt_ms": dt_ms,
                    "sim_ms": sim_ms,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def t3_learning(self) -> None:
        print("\n=== T3 · Learning wet-lab (study EEG + SME + consolidate) ===")
        from fsot_nuron.learning_eeg_study import build_study_eeg_report
        from fsot_nuron.brain_architecture import run_brain_design_suite
        from fsot_nuron.learning_memory import learning_probe

        study = build_study_eeg_report()
        self.check(
            "T3",
            "mental_state_eeg_loaded",
            study.mental_state_ok,
            measured=study.mental_label_counts,
            expected="concentrate/neutral/relaxed public EEG",
            source=study.mental_state_path or "Kaggle mental-state CSV",
            critical=False,  # literature path still valid without CSV
        )
        c = study.concentrate_vs_relax or {}
        th = c.get("theta_concentrate_over_relax")
        self.check(
            "T3",
            "study_theta_elevated_vs_rest",
            th is not None and th == th and th > 1.0,
            measured=th,
            expected=">1.0 (concentrate > relax energy proxy)",
            source="public mental-state EEG feature matrix",
            critical=bool(study.mental_state_ok),
        )
        self.check(
            "T3",
            "literature_sme_priors",
            "sederberg_2003_sme" in study.literature,
            measured=list(study.literature.keys()),
            expected="Sederberg SME + Creery consolidation",
            source="iEEG literature (coded priors)",
        )

        suite = run_brain_design_suite(
            steps=150, device="cpu", profile="ai_efficient", sensory=False
        )
        brain = suite["brain"]
        cons = learning_probe(
            brain,
            n_items=8,
            encode_steps=250,
            retrieve_steps=200,
            seed=7,
            delay_steps=150,
            consolidate=True,
            consolidate_rest_steps=300,
            replay_rounds=2,
            replay_steps=100,
            item_mode="fsot_machine",
        )
        chance = 1.0 / 8
        self.check(
            "T3",
            "sme_theta_encode_gt_rest",
            cons.sme_theta_encode_gt_rest,
            measured=cons.sme_theta_encode_gt_rest,
            expected=True,
            source="Sederberg-style direction on spike-band proxy",
        )
        self.check(
            "T3",
            "sme_gamma_encode_gt_rest",
            cons.sme_gamma_encode_gt_rest,
            measured=cons.sme_gamma_encode_gt_rest,
            expected=True,
            source="Sederberg-style direction on spike-band proxy",
        )
        self.check(
            "T3",
            "consolidate_top1_ge_half",
            cons.top1_accuracy >= 0.5,
            measured=cons.top1_accuracy,
            expected="≥0.5",
            source="FSOT machine items + offline replay",
        )
        self.check(
            "T3",
            "consolidate_above_chance",
            cons.top1_accuracy > chance,
            measured=cons.top1_accuracy,
            expected=f"> {chance}",
            source="8-item chance floor",
        )

    def t4_genetic(self) -> None:
        print("\n=== T4 · Genetic / cellular code structure ===")
        from fsot_nuron.genetic_genotype import (
            CHANNEL_GENE_ORFS,
            genetic_authority_report,
            build_population_genotypes,
        )
        from fsot_nuron.genetic_network import GeneticNeuralNetwork, GeneticNetworkConfig
        import torch

        auth = genetic_authority_report()
        for gene in ("SCN", "KCN", "CACNA", "LEAK"):
            n = auth["channel_genes"][gene]["n_codons"]
            self.check(
                "T4",
                f"gene_ORF_{gene}",
                n >= 4 and gene in CHANNEL_GENE_ORFS,
                measured={"n_codons": n, "dna": CHANNEL_GENE_ORFS[gene]},
                expected="≥4 codons DNA ORF",
                source="codon map + standard genetic code → phenotype",
            )
        pop = build_population_genotypes(32, seed=1, diversity=True)
        spins = {round(g.composite_spin, 4) for g in pop}
        self.check(
            "T4",
            "genotype_diversity",
            len(spins) >= 2,
            measured=len(spins),
            expected="≥2 unique composite spins",
            source="codon-derived spins",
        )
        gnet = GeneticNeuralNetwork(
            GeneticNetworkConfig(n_units=32, connectivity="genetic_sparse", seed=0),
            device="cpu",
        )
        S, fired, _, _, _ = gnet.step(torch.ones(32) * 0.5)
        self.check(
            "T4",
            "genetic_synapses_nonempty",
            int((gnet.W != 0).sum()) >= 16,
            measured=int((gnet.W != 0).sum()),
            expected="seed-folded W from trinary spins",
            source="trinary_pair_interaction + φ geometry",
        )
        self.check(
            "T4",
            "genetic_step_finite_S",
            bool(float(S.mean()) == float(S.mean())),
            measured=float(S.mean()),
            expected="finite S",
            source="FSOTNeuronBatch + genetic W",
        )

    def write(self) -> Path:
        crit_fail = [r for r in self.rows if not r["ok"] and r["critical"]]
        soft_fail = [r for r in self.rows if not r["ok"] and not r["critical"]]
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "duration_s": round(time.perf_counter() - self.t0, 2),
            "n_checks": len(self.rows),
            "n_pass": sum(1 for r in self.rows if r["ok"]),
            "critical_fails": crit_fail,
            "soft_fails": soft_fail,
            "checks": self.rows,
            "doctrine": "public wet-lab authority; zero free params on FSOT scalar",
        }
        art = ROOT / "artifacts"
        art.mkdir(parents=True, exist_ok=True)
        path = art / "wetlab_accuracy_battery.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        res = ROOT / "data" / "results"
        res.mkdir(parents=True, exist_ok=True)
        (res / "wetlab_accuracy_battery.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )

        md = [
            "# Wet-lab accuracy battery",
            "",
            f"Generated: `{report['generated_at']}` · **{report['n_pass']}/{report['n_checks']}** pass · {report['duration_s']}s",
            "",
            "## Critical failures",
            "",
        ]
        if not crit_fail:
            md.append("_None — no skeptical gaps on critical wet-lab gates._")
        else:
            for r in crit_fail:
                md.append(
                    f"- **{r['tier']}/{r['name']}** measured=`{r['measured']}` expected=`{r['expected']}` ({r['source']})"
                )
        md += ["", "## Soft / stretch", ""]
        if not soft_fail:
            md.append("_None._")
        else:
            for r in soft_fail:
                md.append(
                    f"- **{r['tier']}/{r['name']}** measured=`{r['measured']}` expected=`{r['expected']}`"
                )
        md += [
            "",
            "## Full checklist",
            "",
            "| Tier | Check | OK | Measured | Expected | Source |",
            "|------|-------|:--:|----------|----------|--------|",
        ]
        for r in self.rows:
            md.append(
                f"| {r['tier']} | {r['name']} | {'Y' if r['ok'] else 'N'} | "
                f"`{json.dumps(r['measured'])[:40] if not isinstance(r['measured'], (str, int, float, bool, type(None))) else r['measured']}` | "
                f"{r['expected']} | {r['source'][:40]} |"
            )
        md += [
            "",
            "Authority: Allen Cell Types · 64-codon map · archive D1D38A · study EEG · SME literature.",
            "",
        ]
        (res / "WETLAB_ACCURACY_BATTERY.md").write_text("\n".join(md), encoding="utf-8")
        (ROOT / "docs" / "WETLAB_ACCURACY_BATTERY.md").write_text(
            "\n".join(md), encoding="utf-8"
        )
        print(f"\nWrote {res / 'WETLAB_ACCURACY_BATTERY.md'}")
        return path


def main() -> int:
    print("=== FSOT wet-lab accuracy battery ===")
    print("Compare every available reading to public experimental authority.")
    b = Battery()
    try:
        b.t0_structure()
        b.t1_t2_allen()
        b.t3_learning()
        b.t4_genetic()
    except Exception:
        print(traceback.format_exc())
        b.check("X", "battery_exception", False, note=traceback.format_exc()[:200])
    b.write()
    crit = [r for r in b.rows if not r["ok"] and r["critical"]]
    print("\n=== SUMMARY ===")
    print(f"pass {sum(1 for r in b.rows if r['ok'])}/{len(b.rows)}")
    print(f"critical fails: {len(crit)}")
    for r in crit:
        print(f"  - {r['tier']}/{r['name']}")
    return 1 if crit else 0


if __name__ == "__main__":
    raise SystemExit(main())
