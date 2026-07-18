#!/usr/bin/env python3
"""Run all open SOTA refinement fronts and write data/results."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "data" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def main() -> int:
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "fronts": {}}

    print("=== 1-3 deep NLP + more data ===")
    from fsot_nuron.deep_readout import run_deep_nlp_suite

    nlp = run_deep_nlp_suite(max_docs=280)
    summary["fronts"]["deep_nlp"] = {
        "n": nlp.get("n_datasets"),
        "results": [
            {
                "dataset": r.get("dataset"),
                "test_acc": r.get("test_acc"),
                "balanced_accuracy": r.get("balanced_accuracy"),
                "n_classes": r.get("n_classes"),
                "error": r.get("error"),
            }
            for r in nlp.get("results") or []
        ],
    }

    print("=== 4 EEG bands ===")
    from fsot_nuron.eeg_bands import run_eeg_band_suite

    eeg = run_eeg_band_suite()
    summary["fronts"]["eeg_bands"] = {
        "n_reports": eeg.get("n_reports"),
        "n_edf_found": eeg.get("n_edf_found"),
    }

    print("=== 5 scale under learning ===")
    from fsot_nuron.scale_learning import run_scale_learning

    sc = run_scale_learning()
    summary["fronts"]["scale_learning"] = {
        "cpu_rows": len((sc.get("cpu_probe") or {}).get("rows") or []),
        "cuda": "cuda_probe" in sc,
    }

    # also refresh linear readout on sentiment for comparison
    print("=== linear readout refresh (sentiment/SMS) ===")
    from fsot_nuron.train_readout import run_readout_suite

    lin = run_readout_suite(n_seeds=3)
    summary["fronts"]["linear_readout"] = [
        {
            "dataset": r.get("dataset"),
            "test_acc": r.get("test_acc"),
            "multi_seed_test_mean": r.get("multi_seed_test_mean"),
        }
        for r in lin.get("results") or []
        if "error" not in r
    ]

    path = RESULTS / "sota_fronts_summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # human markdown
    lines = [
        "# SOTA fronts run",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Data (external I: drive)",
        "",
        "Downloads under `I:/fsot nuron/data/external/` — see `DOWNLOAD_MANIFEST.json`.",
        "",
        "## Deep FSOT readout (multi-domain NLP)",
        "",
    ]
    for r in summary["fronts"]["deep_nlp"]["results"]:
        if r.get("error"):
            lines.append(f"- {r.get('dataset')}: ERROR {r.get('error')}")
        else:
            lines.append(
                f"- **{r.get('dataset')}**: test={r.get('test_acc'):.3f} "
                f"bal={r.get('balanced_accuracy'):.3f} classes={r.get('n_classes')}"
            )
    lines += ["", "## Linear readout (baseline climb)", ""]
    for r in summary["fronts"]["linear_readout"]:
        lines.append(
            f"- {r.get('dataset')}: test={r.get('test_acc'):.3f} "
            f"seed_mean={r.get('multi_seed_test_mean'):.3f}"
        )
    lines += [
        "",
        f"## EEG bands: {summary['fronts']['eeg_bands']['n_reports']} reports, "
        f"EDF found={summary['fronts']['eeg_bands']['n_edf_found']}",
        "",
        f"## Scale-under-learning: cpu_rows={summary['fronts']['scale_learning']['cpu_rows']} "
        f"cuda={summary['fronts']['scale_learning']['cuda']}",
        "",
    ]
    md = RESULTS / "SOTA_FRONTS.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "SOTA_FRONTS.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", path, md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
