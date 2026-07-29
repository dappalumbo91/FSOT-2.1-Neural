#!/usr/bin/env python3
"""
Stress + wet-lab parity suite for Zig mind authority.

1) Neuron step TRACE parity (Zig host vs Python f64)
2) Export Allen-mapped params → Zig FI population
3) Same FI protocol on Python batch → compare metrics
4) Gate both against Allen population targets (when CSV present)
5) Run Zig stress suite (learn/brain/organism)

Writes:
  artifacts/zig_mind_stress.json
  data/results/ZIG_MIND_STRESS.md
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
ZIG_DIR = ROOT / "embodiment" / "zig"
ART = ROOT / "artifacts"
RES = ROOT / "data" / "results"
sys.path.insert(0, str(ROOT))


def find_zig() -> Optional[str]:
    import shutil

    z = shutil.which("zig")
    if z:
        return z
    pkgs = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    if pkgs.is_dir():
        for p in pkgs.rglob("zig.exe"):
            return str(p)
    return None


def mind_exe() -> Path:
    for name in ("fsot_mind.exe", "fsot_mind"):
        p = ZIG_DIR / "zig-out" / "bin" / name
        if p.is_file():
            return p
    raise FileNotFoundError("fsot_mind binary missing — run zig build in embodiment/zig")


def host_exe() -> Optional[Path]:
    for name in ("fsot_trit_host.exe", "fsot_trit_host"):
        p = ZIG_DIR / "zig-out" / "bin" / name
        if p.is_file():
            return p
    return None


def ensure_built() -> None:
    zig = find_zig()
    if not zig:
        raise RuntimeError("zig not found")
    r = subprocess.run(
        [zig, "build", "-Doptimize=ReleaseSafe"],
        cwd=str(ZIG_DIR),
        capture_output=True,
        text=True,
        timeout=300,
    )
    # mind may install even if host is locked
    if not mind_exe().is_file():
        raise RuntimeError(f"build failed / no mind exe\n{r.stderr[-2000:]}")


def run_mind(args: List[str], timeout: int = 180) -> Tuple[int, str]:
    exe = mind_exe()
    r = subprocess.run(
        [str(exe), *args],
        cwd=str(ZIG_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    blob = (r.stdout or "") + "\n" + (r.stderr or "")
    return r.returncode, blob


def _first_float(text: str, pattern: str) -> Optional[float]:
    m = re.search(pattern, text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def parse_kv(text: str, prefix: str = "") -> Dict[str, float]:
    out: Dict[str, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        if prefix and not k.startswith(prefix):
            continue
        try:
            # ints too
            if re.fullmatch(r"-?\d+", v.strip()):
                out[k] = float(int(v.strip()))
            else:
                out[k] = float(v.strip())
        except ValueError:
            continue
    return out


def python_neuron_trace(n_steps: int = 200):
    import torch
    from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
    from fsot_nuron.scalar import compute_scalar_float

    s0 = compute_scalar_float(
        N=4.0, P=3.0, D_eff=13.0, recent_hits=0.0, delta_psi=0.1, delta_theta=1.0, rho=1.0, observed=True
    )
    cfg = NeuronConfig(n_units=1)
    net = FSOTNeuronBatch(cfg, device="cpu", dtype=torch.float64)
    net.reset()
    rows = []
    for t in range(n_steps):
        stim = 0.65 if (t % 80) < 20 else 0.05
        S, fired, phase, tern = net.step(torch.tensor([stim], dtype=torch.float64))
        rows.append(
            {
                "t": t,
                "S": float(S[0].item()),
                "fired": int(fired[0].item()),
                "ternary": int(tern[0].item()),
            }
        )
    return s0, rows


def zig_host_trace() -> Tuple[float, List[dict]]:
    exe = host_exe()
    if exe is None:
        # try build host only
        zig = find_zig()
        if zig:
            subprocess.run([zig, "build", "host"], cwd=str(ZIG_DIR), capture_output=True, text=True, timeout=300)
        exe = host_exe()
    if exe is None:
        return float("nan"), []
    r = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    text = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"SCALAR_NEURO_DPI0\.1=([^\s]+)", text)
    s0 = float(m.group(1)) if m else float("nan")
    rows = []
    if "TRACE_BEGIN" in text and "TRACE_END" in text:
        block = text.split("TRACE_BEGIN", 1)[1].split("TRACE_END", 1)[0].strip()
        for line in block.splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 4:
                rows.append(
                    {
                        "t": int(parts[0]),
                        "S": float(parts[1]),
                        "fired": int(parts[2]),
                        "ternary": int(parts[3]),
                    }
                )
    return s0, rows


def export_allen_params(n_units: int = 32, path: Optional[Path] = None) -> Dict[str, Any]:
    """Write Allen-mapped params for Zig bio mode."""
    from fsot_nuron.allen_data import load_ephys_csv, sample_cells, map_allen_to_fsot_params, population_stats

    path = path or (ART / "zig_bio_params.txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = load_ephys_csv()
    meta: Dict[str, Any] = {"n_source": len(rows), "path": str(path)}
    if not rows:
        # default lines
        lines = [str(n_units)]
        for i in range(n_units):
            ref = 45 + (i % 8)
            lines.append(f"13.0 1.05 {ref} 0.03 0.991 0.7 0.48")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        meta["source"] = "defaults_no_allen_csv"
        return meta

    sample = sample_cells(rows, n=n_units, seed=42)
    params = [map_allen_to_fsot_params(r, mode="bio_match") for r in sample]
    lines = [str(len(params))]
    for p in params:
        lines.append(
            "{d_eff} {fire} {ref} {ag} {ad} {astep} {fi}".format(
                d_eff=float(p["d_eff"]),
                fire=float(p["fire_threshold"]),
                ref=int(p["refractory_steps"]),
                ag=float(p["adapt_gain"]),
                ad=float(p["adapt_decay"]),
                astep=float(p.get("adapt_step", 0.7)),
                fi=float(p["fi_stim"]),
            )
        )
    path.write_text("# Allen bio_match mapped params for Zig\n" + "\n".join(lines) + "\n", encoding="utf-8")
    meta["source"] = "allen_csv"
    meta["n_units"] = len(params)
    meta["allen_pop"] = population_stats(rows)
    meta["mean_target_isi"] = sum(p.get("isi_target", 70) for p in params) / len(params)
    # map_allen may use different keys — pull from rows
    isis = [r.avg_isi_ms for r in sample if r.avg_isi_ms == r.avg_isi_ms and r.avg_isi_ms > 5]
    ads = [r.adaptation for r in sample if r.adaptation == r.adaptation]
    meta["sample_mean_isi_ms"] = sum(isis) / len(isis) if isis else None
    meta["sample_mean_adapt"] = sum(ads) / len(ads) if ads else None
    meta["param_keys"] = list(params[0].keys()) if params else []
    return meta


def python_fi_population(params_path: Path, steps: int = 1200) -> Dict[str, float]:
    """Mirror Zig FI population using same param file + Python neuron_batch."""
    import torch
    from fsot_nuron.neuron_batch import FSOTNeuronBatch, NeuronConfig
    from fsot_nuron.bio_metrics import population_profiles, summarize_profiles

    text = params_path.read_text(encoding="utf-8")
    lines = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    n = int(lines[0])
    rows = []
    for line in lines[1 : 1 + n]:
        parts = line.split()
        rows.append(
            {
                "d_eff": float(parts[0]),
                "fire_threshold": float(parts[1]),
                "refractory_steps": int(float(parts[2])),
                "adapt_gain": float(parts[3]),
                "adapt_decay": float(parts[4]),
                "adapt_step": float(parts[5]),
                "fi_stim": float(parts[6]),
            }
        )
    n = len(rows)
    cfg = NeuronConfig(n_units=n)
    net = FSOTNeuronBatch(cfg, device="cpu", dtype=torch.float64)
    net.apply_bio_params(
        d_eff=torch.tensor([r["d_eff"] for r in rows], dtype=torch.float64),
        fire_threshold=torch.tensor([r["fire_threshold"] for r in rows], dtype=torch.float64),
        adapt_gain=torch.tensor([r["adapt_gain"] for r in rows], dtype=torch.float64),
        adapt_decay=torch.tensor([r["adapt_decay"] for r in rows], dtype=torch.float64),
        refractory_steps=torch.tensor([r["refractory_steps"] for r in rows], dtype=torch.int32),
        adapt_step=torch.tensor([r["adapt_step"] for r in rows], dtype=torch.float64),
        fi_stim=torch.tensor([r["fi_stim"] for r in rows], dtype=torch.float64),
        mode_name="bio_match",
    )
    net.reset()
    hist_S = torch.empty(steps, n, dtype=torch.float64)
    hist_f = torch.empty(steps, n, dtype=torch.bool)
    stim = torch.tensor([r["fi_stim"] for r in rows], dtype=torch.float64)
    for t in range(steps):
        S, fired, _, _ = net.step(stim)
        hist_S[t] = S
        hist_f[t] = fired
    profs = population_profiles(hist_f, hist_S, dt_ms=1.0)
    summary = summarize_profiles(profs)
    return {
        "mean_rate_Hz": float(summary.get("mean_firing_rate_Hz") or 0),
        "mean_isi_ms": float(summary.get("mean_isi_ms") or 0),
        "mean_adapt": float(summary.get("mean_adaptation_index") or 0),
        "mean_isi_cv": float(summary.get("mean_isi_cv") or 0),
        "mean_S": float(summary.get("mean_S") or 0),
        "mean_Vm_mV": float(summary.get("mean_Vm_proxy_mV") or 0),
    }


def rel_err(a: float, b: float) -> float:
    if a != a or b != b:
        return float("nan")
    return abs(a - b) / max(abs(b), 1e-9)


def main() -> int:
    t0 = time.time()
    ART.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gates": {},
        "metrics": {},
        "notes": [],
    }

    print("=== Zig mind stress + wet-lab parity ===")
    ensure_built()
    report["mind_exe"] = str(mind_exe())

    # --- 1) Neuron TRACE parity ---
    print("--- neuron TRACE parity ---")
    py_s0, py_rows = python_neuron_trace(200)
    zig_s0, zig_rows = zig_host_trace()
    max_ds = 0.0
    spike_mm = 0
    tern_mm = 0
    if len(zig_rows) == len(py_rows) and zig_rows:
        for a, b in zip(py_rows, zig_rows):
            max_ds = max(max_ds, abs(a["S"] - b["S"]))
            if a["fired"] != b["fired"]:
                spike_mm += 1
            if a["ternary"] != b["ternary"]:
                tern_mm += 1
        ok_trace = max_ds < 1e-5 and spike_mm == 0 and tern_mm <= 2
        ok_scalar = abs(py_s0 - zig_s0) < 1e-9 or abs(py_s0 - zig_s0) / max(abs(py_s0), 1e-12) < 1e-8
    else:
        ok_trace = False
        ok_scalar = False
        report["notes"].append(f"trace length py={len(py_rows)} zig={len(zig_rows)}")
    report["gates"]["neuron_scalar"] = ok_scalar
    report["gates"]["neuron_trace"] = ok_trace
    report["metrics"]["max_abs_dS"] = max_ds
    report["metrics"]["spike_mismatch"] = spike_mm
    report["metrics"]["scalar_py"] = py_s0
    report["metrics"]["scalar_zig"] = zig_s0
    print(f"  scalar ok={ok_scalar} trace ok={ok_trace} max|dS|={max_ds:.3e} spike_mm={spike_mm}")

    # --- 2) Allen params + Zig bio + Python FI ---
    print("--- Allen params + FI bio ---")
    params_path = ART / "zig_bio_params.txt"
    allen_meta = export_allen_params(32, params_path)
    report["allen"] = {k: v for k, v in allen_meta.items() if k != "allen_pop"}
    if "allen_pop" in allen_meta:
        ap = allen_meta["allen_pop"]
        report["allen"]["pop_mean_isi"] = ap.get("mean_avg_isi_ms") if isinstance(ap, dict) else None
        report["allen"]["pop_mean_adapt"] = ap.get("mean_adaptation") if isinstance(ap, dict) else None

    # Zig needs absolute or relative path from ZIG_DIR cwd — use absolute
    code, bio_text = run_mind(["bio", str(params_path)], timeout=300)
    zig_bio = parse_kv(bio_text, "BIO_FI_")
    # also bare keys without requiring all
    for k, v in parse_kv(bio_text).items():
        if k.startswith("BIO_FI_"):
            zig_bio[k] = v
    report["metrics"]["zig_bio"] = zig_bio
    report["gates"]["zig_bio_pass"] = code == 0 and "FSOT_BIO PASS" in bio_text
    print(f"  zig bio exit={code} PASS={report['gates']['zig_bio_pass']}")
    if zig_bio:
        print(
            f"  zig rate={zig_bio.get('BIO_FI_mean_rate_Hz')} "
            f"isi={zig_bio.get('BIO_FI_mean_isi_ms')} "
            f"adapt={zig_bio.get('BIO_FI_mean_adapt')}"
        )

    py_bio = python_fi_population(params_path, steps=1200)
    report["metrics"]["python_bio"] = py_bio
    print(
        f"  py  rate={py_bio['mean_rate_Hz']:.4f} isi={py_bio['mean_isi_ms']:.4f} "
        f"adapt={py_bio['mean_adapt']:.4f}"
    )

    # Parity Zig vs Python FI
    z_rate = zig_bio.get("BIO_FI_mean_rate_Hz", float("nan"))
    z_isi = zig_bio.get("BIO_FI_mean_isi_ms", float("nan"))
    z_ad = zig_bio.get("BIO_FI_mean_adapt", float("nan"))
    # Allow modest gap: discrete dynamics + any residual path differences
    rate_re = rel_err(z_rate, py_bio["mean_rate_Hz"])
    isi_re = rel_err(z_isi, py_bio["mean_isi_ms"])
    adapt_abs = abs(z_ad - py_bio["mean_adapt"]) if z_ad == z_ad else float("nan")
    # Gates: scientific agreement, not bit-identical multi-unit (default looser for rate)
    ok_fi_rate = rate_re == rate_re and rate_re < 0.25  # 25% relative
    ok_fi_isi = isi_re == isi_re and isi_re < 0.25
    ok_fi_adapt = adapt_abs == adapt_abs and adapt_abs < 0.15
    report["gates"]["fi_rate_parity"] = bool(ok_fi_rate)
    report["gates"]["fi_isi_parity"] = bool(ok_fi_isi)
    report["gates"]["fi_adapt_parity"] = bool(ok_fi_adapt)
    report["metrics"]["fi_rate_rel_err"] = rate_re
    report["metrics"]["fi_isi_rel_err"] = isi_re
    report["metrics"]["fi_adapt_abs_err"] = adapt_abs
    print(f"  FI parity rate_re={rate_re:.3f} isi_re={isi_re:.3f} adapt_abs={adapt_abs:.3f}")

    # Wet-lab gates vs Allen sample / population
    target_isi = allen_meta.get("sample_mean_isi_ms") or report["allen"].get("pop_mean_isi")
    target_ad = allen_meta.get("sample_mean_adapt") or report["allen"].get("pop_mean_adapt")
    wet = {}
    if target_isi and z_isi == z_isi:
        # bio_match refractory is ~0.72 * Allen ISI; observed ISI may track that band
        wet["isi_rel_err_vs_allen"] = rel_err(z_isi, float(target_isi))
        # tolerate 35% — protocol is constant FI not long square current clamp identical
        wet["isi_gate"] = wet["isi_rel_err_vs_allen"] < 0.35
    else:
        wet["isi_gate"] = None
        report["notes"].append("no Allen ISI target")
    if target_ad is not None and z_ad == z_ad:
        wet["adapt_abs_err_vs_allen"] = abs(z_ad - float(target_ad))
        wet["adapt_gate"] = wet["adapt_abs_err_vs_allen"] < 0.25
    else:
        wet["adapt_gate"] = None
    # rate band cortical
    wet["rate_band"] = bool(z_rate == z_rate and 5.0 <= z_rate <= 80.0)
    report["gates"]["wetlab_isi"] = wet.get("isi_gate")
    report["gates"]["wetlab_adapt"] = wet.get("adapt_gate")
    report["gates"]["wetlab_rate_band"] = wet["rate_band"]
    report["metrics"]["wetlab"] = wet
    report["metrics"]["allen_target_isi"] = target_isi
    report["metrics"]["allen_target_adapt"] = target_ad
    print(f"  wetlab rate_band={wet['rate_band']} isi_gate={wet.get('isi_gate')} adapt_gate={wet.get('adapt_gate')}")

    # --- 3) 64-codon genetic foundation ---
    print("--- 64-codon genetic ---")
    gcode, gtext = run_mind(["genetic"], timeout=120)
    report["gates"]["zig_codon_genetic"] = gcode == 0 and "FSOT_GENETIC PASS" in gtext
    report["metrics"]["genetic"] = {
        "scn_expr": _first_float(gtext, r"SCN spin=\S+ expr=([^\s]+)"),
        "pyr_spin": _first_float(gtext, r"Pyr spin=([^\s]+)"),
        "pv_ref": _first_float(gtext, r"PV\s+spin=\S+ ref=([^\s]+)"),
    }
    print(f"  genetic PASS={report['gates']['zig_codon_genetic']}")

    # --- 4) Zig stress suite ---
    print("--- zig stress ---")
    scode, stext = run_mind(["stress"], timeout=300)
    report["gates"]["zig_stress"] = scode == 0 and "FSOT_STRESS PASS" in stext
    report["metrics"]["stress"] = parse_kv(stext, "STRESS_")
    print(f"  stress PASS={report['gates']['zig_stress']}")

    # --- 5) learn top1 ---
    lcode, ltext = run_mind(["learn"], timeout=120)
    report["gates"]["zig_learn"] = lcode == 0 and "FSOT_LEARN PASS" in ltext
    m = re.search(r"LEARN top1=([^\s]+)", ltext)
    report["metrics"]["learn_top1"] = float(m.group(1)) if m else None

    # Overall
    critical = [
        report["gates"].get("neuron_scalar"),
        report["gates"].get("neuron_trace"),
        report["gates"].get("zig_codon_genetic"),
        report["gates"].get("zig_bio_pass"),
        report["gates"].get("zig_stress"),
        report["gates"].get("zig_learn"),
        report["gates"].get("wetlab_rate_band"),
    ]
    soft = [
        report["gates"].get("fi_rate_parity"),
        report["gates"].get("fi_isi_parity"),
        report["gates"].get("fi_adapt_parity"),
        report["gates"].get("wetlab_isi"),
        report["gates"].get("wetlab_adapt"),
    ]
    report["critical_ok"] = all(bool(x) for x in critical)
    report["soft_ok"] = all(x is None or bool(x) for x in soft)
    report["duration_s"] = round(time.time() - t0, 2)

    out_json = ART / "zig_mind_stress.json"
    out_json.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    md = []
    md.append("# Zig mind stress + wet-lab parity\n")
    md.append(f"Generated: `{report['generated_at']}`  \n")
    md.append(f"Duration: {report['duration_s']}s  \n\n")
    md.append("## Critical gates\n\n")
    md.append("| Gate | OK |\n|------|----|\n")
    for k in (
        "neuron_scalar",
        "neuron_trace",
        "zig_codon_genetic",
        "zig_bio_pass",
        "zig_stress",
        "zig_learn",
        "wetlab_rate_band",
    ):
        md.append(f"| {k} | {report['gates'].get(k)} |\n")
    md.append("\n## Soft / scientific agreement\n\n")
    md.append("| Gate | OK |\n|------|----|\n")
    for k in ("fi_rate_parity", "fi_isi_parity", "fi_adapt_parity", "wetlab_isi", "wetlab_adapt"):
        md.append(f"| {k} | {report['gates'].get(k)} |\n")
    md.append("\n## Metrics\n\n```json\n")
    md.append(json.dumps(report["metrics"], indent=2, default=str)[:4000])
    md.append("\n```\n")
    md.append(f"\n**critical_ok**={report['critical_ok']} **soft_ok**={report['soft_ok']}\n")
    md.append("\nDoctrine: neural authority is Zig; Python used here only for Allen map + parity lab.\n")
    (RES / "ZIG_MIND_STRESS.md").write_text("".join(md), encoding="utf-8")
    print(f"\nWrote {out_json}")
    print(f"Wrote {RES / 'ZIG_MIND_STRESS.md'}")
    print(f"CRITICAL={'PASS' if report['critical_ok'] else 'FAIL'} SOFT={'PASS' if report['soft_ok'] else 'FAIL'}")

    # thesis ledger
    try:
        from fsot_nuron.thesis_ledger import record_run

        record_run(
            "zig_mind_stress",
            profile="zig_f64_bio",
            gates={k: bool(v) if v is not None else False for k, v in report["gates"].items()},
            metrics=report["metrics"],
            notes="Zig mind stress + Allen FI parity",
            formulas_ref="docs/FORMULAS.md",
            extra={"doc": "data/results/ZIG_MIND_STRESS.md"},
        )
    except Exception as e:
        report["notes"].append(f"ledger skip: {e}")

    return 0 if report["critical_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
