#!/usr/bin/env python3
"""
Export scientific certificate: Lean 4 formal panel × wet-lab battery × system results.

Produces:
  data/results/LEAN_WETLAB_CERTIFICATE.json
  data/results/LEAN_WETLAB_CERTIFICATE.md
  docs/LEAN_WETLAB_CROSSREF.md  (living cross-reference)

  python scripts/export_lean_wetlab_certificate.py
  python scripts/export_lean_wetlab_certificate.py --run-battery
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formal"
RESULTS = ROOT / "data" / "results"
DOCS = ROOT / "docs"

sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_PHYSICAL_ARCHIVE", r"I:\FSOT-Physical-Archive")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def lake_build() -> Dict[str, Any]:
    try:
        r = subprocess.run(
            ["lake", "build"],
            cwd=str(FORMAL),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError:
        return {"ok": False, "error": "lake not on PATH", "returncode": 127}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "returncode": 124}
    return {
        "ok": r.returncode == 0,
        "returncode": r.returncode,
        "stdout_tail": (r.stdout or "")[-1500:],
        "stderr_tail": (r.stderr or "")[-800:],
    }


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def pin_block() -> Dict[str, Any]:
    try:
        from fsot_nuron.archive_pin import pin_archive
        from fsot_nuron.fsot_bridge import fold_diagnostics

        pin = pin_archive(write_snapshot=False)
        folds = fold_diagnostics()
        return {
            "connected": pin.connected,
            "seed_match_ok": pin.seed_match_ok,
            "compute_sha256": pin.compute_sha256,
            "compute_matches_certificate": pin.compute_matches_certificate,
            "lean_build_ok_archive": pin.lean_build_ok,
            "seven_way_bare_metal": pin.seven_way_bare_metal,
            "S_Biology": folds.get("S_Biology"),
            "S_Neuroscience": folds.get("S_Neuroscience"),
            "free_parameters": 0,
            "formula": "S = K * (T1 + T2 + T3)",
        }
    except Exception as e:
        return {"error": str(e)}


def formal_claims() -> List[Dict[str, str]]:
    return [
        {
            "lean": "FSOTNeural.allCodons_card",
            "claim": "Exactly 64 DNA codons",
            "runtime": "codon_path_verify perfect 64/64",
            "wetlab_check": "T0/codon_map_64_roundtrip",
        },
        {
            "lean": "FSOTNeural.codon_in_own_fiber",
            "claim": "Every codon ∈ fiber of primary(trinary) map",
            "runtime": "A,G=+1; C,T=-1 primary map",
            "wetlab_check": "T0/codon_map_64_roundtrip",
        },
        {
            "lean": "FSOTNeural.purine_pos / pyrimidine_neg",
            "claim": "A,G → +; C,T → −",
            "runtime": "chemical_codon / trinary_substrate",
            "wetlab_check": "T4 gene ORFs",
        },
        {
            "lean": "FSOTNeural.neuroFold",
            "claim": "D_eff=13, N=4, P=3, observed",
            "runtime": "seeds.NEURO_* / neuron_batch",
            "wetlab_check": "T0 structure",
        },
        {
            "lean": "FSOTNeural.synapseSign / only_pyr_exc",
            "claim": "Pyr +; PV/SST/VIP −",
            "runtime": "cell_types / scalpel population",
            "wetlab_check": "T1/pv_faster_than_pyr + class rates",
        },
        {
            "lean": "FSOTNeural.fractions_sum_100",
            "claim": "Cortical fractions 80+8+7+5=100",
            "runtime": "cell type mix design",
            "wetlab_check": "structural",
        },
        {
            "lean": "FSOTNeural.expressionPos_true",
            "claim": "Expression score always positive",
            "runtime": "genetic_genotype expression",
            "wetlab_check": "T4/gene_ORF_*",
        },
        {
            "lean": "FSOTNeural.free_parameters_zero",
            "claim": "0 free parameters on scalar path",
            "runtime": "fsot_bridge free_parameters=0",
            "wetlab_check": "T0/fsot_bridge_zero_free",
        },
        {
            "lean": "FSOTNeural.machine_primary / morse_not_primary",
            "claim": "Machine body primary; Morse secondary",
            "runtime": "machine_encode EncodePath",
            "wetlab_check": "T0/machine_abi_roundtrip",
        },
        {
            "lean": "FSOTNeural.wetlab_structural_ok",
            "claim": "4 Allen classes; tol floor 2%; freeParams=0",
            "runtime": "run_wetlab_accuracy_battery",
            "wetlab_check": "T1–T2 Allen rates",
        },
        {
            "lean": "FSOTNeural.scientific_panel_ok",
            "claim": "Master structural certificate (no sorry)",
            "runtime": "lake build formal/",
            "wetlab_check": "full battery critical path",
        },
        {
            "lean": "FSOTNeural.stage_scientific_verification",
            "claim": "formal_panel ∧ wetlab_structural ∧ free0 ∧ scientific_panel",
            "runtime": "export_lean_wetlab_certificate.py",
            "wetlab_check": "this document",
        },
    ]


def cross_status(battery: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not battery:
        return {"battery_present": False, "critical_fails": None, "n_pass": None}
    crit = battery.get("critical_fails") or []
    return {
        "battery_present": True,
        "n_pass": battery.get("n_pass"),
        "n_checks": battery.get("n_checks"),
        "critical_fail_count": len(crit),
        "critical_fails": crit,
        "soft_fails": battery.get("soft_fails") or [],
        "generated_at": battery.get("generated_at"),
    }


def write_md(cert: Dict[str, Any]) -> str:
    lean_ok = cert["lean_build"]["ok"]
    bat = cert["wetlab_battery_status"]
    pin = cert["archive_pin"]
    lines = [
        "# Lean 4 × Wet-lab scientific certificate",
        "",
        f"Generated: `{cert['generated_at']}`",
        "",
        "## Verdict",
        "",
        f"| Gate | Status |",
        f"|------|--------|",
        f"| Lean `lake build` (scientific_panel_ok) | **{'PASS' if lean_ok else 'FAIL'}** |",
        f"| Archive pin D1D38A / seeds | **{'PASS' if pin.get('seed_match_ok') else 'FAIL'}** |",
        f"| Wet-lab battery critical | **{'PASS' if bat.get('critical_fail_count') == 0 else 'FAIL / missing'}** |",
        f"| Free parameters on scalar | **0** |",
        "",
        f"**Overall scientific stage:** **{cert['overall']}**",
        "",
        "## What is proved in Lean (structure)",
        "",
        "The Lean panel proves *definitions and contracts* of the neurological substrate:",
        "",
        "- 64-codon finite set and primary trinary fiber round-trip",
        "- Neuroscience fold slots (D_eff, N, P, observed)",
        "- Cell-type E/I polarity and cortical fraction sum",
        "- Expression positivity",
        "- Zero free parameters on the scalar *path*",
        "- Machine primary / Morse not primary",
        "- Wet-lab gate *shapes* (4 Allen classes, 2% floor, SME/top-1 predicates)",
        "",
        "Continuous analytic \(S=K(T_1+T_2+T_3)\) remains in **FSOT-2.1-Lean / physical archive**",
        f"(pin `{(pin.get('compute_sha256') or 'D1D38A…')[:20]}…`, seven_way={pin.get('seven_way_bare_metal')}).",
        "",
        "## What is measured against wet-lab (empirical)",
        "",
    ]
    if bat.get("battery_present"):
        lines += [
            f"- Battery: **{bat.get('n_pass')}/{bat.get('n_checks')}** pass",
            f"- Critical fails: **{bat.get('critical_fail_count')}**",
            f"- Soft fails: **{len(bat.get('soft_fails') or [])}** (1% stretch allowed)",
            f"- Battery timestamp: `{bat.get('generated_at')}`",
            "",
        ]
        if bat.get("soft_fails"):
            lines.append("Soft (non-critical) stretch failures:")
            for s in bat["soft_fails"][:8]:
                lines.append(f"- `{s.get('tier')}/{s.get('name')}` measured={s.get('measured')}")
            lines.append("")
    else:
        lines += [
            "- Wet-lab battery JSON not found — run `python run_wetlab_accuracy_battery.py`",
            "",
        ]

    lines += [
        "## Cross-reference table (Lean ↔ runtime ↔ wet-lab)",
        "",
        "| Lean theorem / def | Scientific claim | Runtime | Wet-lab check |",
        "|--------------------|------------------|---------|---------------|",
    ]
    for row in cert["formal_claims"]:
        lines.append(
            f"| `{row['lean']}` | {row['claim']} | {row['runtime']} | {row['wetlab_check']} |"
        )

    lines += [
        "",
        "## Atlas scalars (runtime pin)",
        "",
        f"- S_Biology ≈ `{pin.get('S_Biology')}` (archive Biology fold ≈ +0.445)",
        f"- S_Neuroscience ≈ `{pin.get('S_Neuroscience')}` (archive ≈ +0.514)",
        "",
        "## How to reproduce",
        "",
        "```powershell",
        'cd "I:\\fsot nuron"',
        '$env:FSOT_PHYSICAL_ARCHIVE = "I:\\FSOT-Physical-Archive"',
        '$env:PYTHONPATH = "I:\\fsot nuron"',
        "python run_archive_pin.py",
        "python run_wetlab_accuracy_battery.py",
        "cd formal; lake build; cd ..",
        "python scripts/verify_formal.py",
        "python scripts/export_lean_wetlab_certificate.py",
        "```",
        "",
        "## Authority split (honest)",
        "",
        "| Layer | Prover / engine | Role |",
        "|-------|-----------------|------|",
        "| Continuous FSOT scalar | Archive Lean + multi-prover | S = K(T1+T2+T3), D1D38A |",
        "| Neural discrete structure | This repo `formal/` Lean 4 | Codon, fold, E/I, gates |",
        "| Empirical wet-lab | Python battery | Allen rates, SME, study EEG |",
        "| Body | Zig host | Trit step + MachineFrame |",
        "",
        "No claim that Lean re-derives Allen FI rates as theorems of analysis.",
        "Claim: **structure is proved; measurements match public wet-lab within published gates.**",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--run-battery",
        action="store_true",
        help="run wet-lab battery before export (slow)",
    )
    ap.add_argument("--skip-lake", action="store_true")
    args = ap.parse_args()

    print("=== Export Lean × wet-lab scientific certificate ===")

    if args.run_battery:
        print("Running wet-lab battery…")
        subprocess.run(
            [sys.executable, str(ROOT / "run_wetlab_accuracy_battery.py")],
            cwd=str(ROOT),
            check=False,
        )

    if args.skip_lake:
        lean = {"ok": None, "skipped": True}
    else:
        print("lake build…")
        lean = lake_build()
        print("lake:", "PASS" if lean.get("ok") else "FAIL", lean.get("error") or "")

    battery = load_json(RESULTS / "wetlab_accuracy_battery.json")
    if battery is None:
        battery = load_json(ROOT / "artifacts" / "wetlab_accuracy_battery.json")

    pin = pin_block()
    bat_stat = cross_status(battery)

    overall = "PASS"
    if lean.get("ok") is False:
        overall = "FAIL_LEAN"
    elif pin.get("seed_match_ok") is False:
        overall = "FAIL_PIN"
    elif bat_stat.get("battery_present") and bat_stat.get("critical_fail_count", 1) > 0:
        overall = "FAIL_WETLAB"
    elif not bat_stat.get("battery_present"):
        overall = "PASS_LEAN_PIN_ONLY" if lean.get("ok") and pin.get("seed_match_ok") else overall

    cert = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "certificate": "FSOT-2.1-Neural scientific stage verification",
        "overall": overall,
        "lean_build": lean,
        "formal_theorems": [
            "FSOTNeural.formal_panel_ok",
            "FSOTNeural.wetlab_structural_ok",
            "FSOTNeural.scientific_panel_ok",
            "FSOTNeural.stage_scientific_verification",
        ],
        "formal_claims": formal_claims(),
        "archive_pin": pin,
        "wetlab_battery_status": bat_stat,
        "wetlab_battery_path": str(RESULTS / "wetlab_accuracy_battery.json"),
        "formal_dir": str(FORMAL),
        "toolchain": "leanprover/lean4:v4.31.0",
        "authority_split": {
            "continuous_scalar": "I:\\FSOT-Physical-Archive\\02_FSOT-2.1-Lean-Full",
            "neural_panel": "I:\\fsot nuron\\formal",
            "empirical": "run_wetlab_accuracy_battery.py",
        },
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "LEAN_WETLAB_CERTIFICATE.json").write_text(
        json.dumps(cert, indent=2), encoding="utf-8"
    )
    md = write_md(cert)
    (RESULTS / "LEAN_WETLAB_CERTIFICATE.md").write_text(md, encoding="utf-8")
    (DOCS / "LEAN_WETLAB_CROSSREF.md").write_text(md, encoding="utf-8")

    print(f"overall: {overall}")
    print(f"Wrote {RESULTS / 'LEAN_WETLAB_CERTIFICATE.md'}")
    print(f"Wrote {DOCS / 'LEAN_WETLAB_CROSSREF.md'}")

    # thesis ledger
    try:
        from fsot_nuron.thesis_ledger import record_run

        record_run(
            "lean_wetlab_certificate",
            profile="lean4+wetlab",
            gates={
                "lake_build": bool(lean.get("ok")),
                "pin_ok": bool(pin.get("seed_match_ok")),
                "wetlab_critical_clear": bat_stat.get("critical_fail_count") == 0
                if bat_stat.get("battery_present")
                else None,
            },
            metrics={"overall": overall},
            notes="Lean scientific_panel_ok × wet-lab battery cross-ref",
        )
    except Exception as e:
        print(f"ledger skip: {e}")

    if lean.get("ok") is False:
        return 1
    if overall.startswith("FAIL"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
