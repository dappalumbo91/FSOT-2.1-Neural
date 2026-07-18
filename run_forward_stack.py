#!/usr/bin/env python3
"""
Run the full FSOT-2.1-Neural forward stack and write data/results + RESULTS.md.

Order:
  1) CI smoke gates
  2) Hard multi-dataset scoreboard
  3) Bio report card
  4) PD EEG depth + PD failure probe
  5) Train/test readout learning
  6) Scale sweep + lesion consensus
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "data" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str]) -> int:
    print("\n>>>", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def write_results_md(payload: dict) -> Path:
    lines = [
        "# FSOT-2.1-Neural — Results",
        "",
        f"Generated: `{payload['generated_at']}`  ",
        f"Repo: https://github.com/dappalumbo91/FSOT-2.1-Neural  ",
        f"Theory: https://github.com/dappalumbo91/FSOT-2.1-Lean (`D1D38A` authority)",
        "",
        "## 1. Quality gates",
        "",
        f"- CI smoke: **{payload['smoke']}**",
        f"- Morse/codon verify: **{payload.get('language_verify', 'see smoke')}**",
        "",
        "## 2. Multi-dataset scoreboard (hard metrics)",
        "",
    ]
    board = payload.get("scoreboard") or {}
    for row in board.get("rank_by_fsot_fit") or []:
        m = row.get("metrics") or {}
        extra = []
        if "retrieval_top1_hard_acc" in m:
            extra.append(f"hard_top1={m['retrieval_top1_hard_acc']:.3f}")
        if "balanced_accuracy" in m:
            extra.append(f"bal={m['balanced_accuracy']:.3f}")
        if "fsot_fit_score" in m:
            extra.append(f"fit={m['fsot_fit_score']:.3f}")
        lines.append(
            f"- **{row.get('name')}** [{row.get('kind')}] rank#{row.get('rank')} "
            + (" ".join(extra) if extra else f"fit={row.get('fit')}")
        )
    lines += ["", f"_Full JSON: `data/results/multi_dataset_scoreboard.json`_", ""]

    card = payload.get("bio_card") or {}
    ac = card.get("allen_comparison") or {}
    lines += [
        "## 3. Bio report card (Allen-facing)",
        "",
        f"- Pass: **{card.get('pass')}**",
        f"- ISI rel error: **{ac.get('isi_rel_error')}**",
        f"- Adapt rel error: **{ac.get('adapt_rel_error')}**",
        f"- Gaps: **{(card.get('gaps') or {}).get('closed')}/{(card.get('gaps') or {}).get('total')}**",
        "",
        "_Details: `data/results/bio_report_card.md`_",
        "",
        "## 4. PD EEG depth",
        "",
    ]
    pd = payload.get("pd_eeg") or {}
    pr = pd.get("probe") or {}
    lines += [
        f"- Local EEG candidates: {pd.get('local_eeg_candidates')}",
        f"- Signal files scored: {(pd.get('measured') or {}).get('n_signal_files_scored')}",
        f"- Probe summary: `{json.dumps(pr.get('summary_excerpt') or pr, default=str)[:300]}`",
        "",
        "## 5. Train/test readout (learned, not LOO retrieval)",
        "",
    ]
    for r in (payload.get("readout") or {}).get("results") or []:
        if "error" in r:
            lines.append(f"- {r.get('dataset')}: ERROR {r.get('error')}")
        else:
            lines.append(
                f"- **{r.get('dataset')}**: train={r.get('train_acc'):.3f} "
                f"test={r.get('test_acc'):.3f} bal={r.get('balanced_accuracy'):.3f} "
                f"(n_test={r.get('n_test')})"
            )
    lines += ["", "## 6. Scale + lesion consensus", ""]
    sc = payload.get("scale") or {}
    for row in (sc.get("scale_sweep") or {}).get("rows") or []:
        lines.append(
            f"- {row.get('device')} n={row.get('n_units')}: "
            f"{row.get('unit_steps_per_s'):.0f} unit-steps/s"
        )
    lines += [
        "",
        f"- Lesion consensus backend: "
        f"`{((sc.get('lesion_consensus') or {}).get('healthy') or {}).get('backend')}`",
        "",
        "## Honesty",
        "",
        "- Retrieval ≠ diagnosis; train/test readout is a linear probe on FSOT fingerprints.",
        "- Bio card is computational Allen match under tolerances.",
        "- PD path uses local/OpenNeuro priors + optional lightweight signal stats.",
        "",
    ]
    path = RESULTS / "RESULTS.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    # also root RESULTS.md for GitHub browsing
    (ROOT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    import os

    os.environ.setdefault("PYTHONPATH", str(ROOT))
    payload: dict = {"generated_at": datetime.now(timezone.utc).isoformat()}

    # 1 smoke
    rc = _run([sys.executable, "scripts/ci_smoke.py"])
    payload["smoke"] = "PASS" if rc == 0 else "FAIL"
    if rc != 0:
        print("smoke failed; continuing other tracks")

    # 2 scoreboard
    print("\n=== multi-dataset scoreboard ===")
    from fsot_nuron.multi_dataset import run_scoreboard, SCOREBOARD_PATH
    import shutil

    board = run_scoreboard(max_files=15)
    # publish under data/results (tracked)
    pub = RESULTS / "multi_dataset_scoreboard.json"
    if SCOREBOARD_PATH.is_file():
        shutil.copy2(SCOREBOARD_PATH, pub)
    else:
        pub.write_text(json.dumps(board, indent=2), encoding="utf-8")
    payload["scoreboard"] = board
    print(f"scoreboard → {pub}")

    # 3 bio card
    print("\n=== bio report card ===")
    from fsot_nuron.bio_report_card import build_bio_report_card

    card = build_bio_report_card(device="cpu", n_units=64, steps=1000)
    payload["bio_card"] = card
    print("bio pass", card.get("pass"), "isi_err", (card.get("allen_comparison") or {}).get("isi_rel_error"))

    # 4 PD EEG
    print("\n=== PD EEG depth ===")
    from fsot_nuron.pd_eeg_depth import build_pd_eeg_depth_report

    pdrep = build_pd_eeg_depth_report(run_probe=True)
    payload["pd_eeg"] = pdrep
    print("pd path", pdrep.get("path"))

    # 5 readout learning
    print("\n=== train/test readout ===")
    from fsot_nuron.train_readout import run_readout_suite

    readout = run_readout_suite()
    payload["readout"] = readout

    # 6 scale + consensus
    print("\n=== scale + consensus ===")
    from fsot_nuron.scale_sweep import run_scale_and_consensus

    scale = run_scale_and_consensus()
    payload["scale"] = scale

    summary_path = RESULTS / "forward_stack_summary.json"
    # shrink for summary
    slim = {
        "generated_at": payload["generated_at"],
        "smoke": payload["smoke"],
        "scoreboard_n": board.get("n_datasets"),
        "bio_pass": card.get("pass"),
        "bio_isi_rel_error": (card.get("allen_comparison") or {}).get("isi_rel_error"),
        "readout": [
            {
                "dataset": r.get("dataset"),
                "test_acc": r.get("test_acc"),
                "balanced_accuracy": r.get("balanced_accuracy"),
            }
            for r in readout.get("results") or []
            if "error" not in r
        ],
        "scale_rows": len((scale.get("scale_sweep") or {}).get("rows") or []),
        "pd_candidates": pdrep.get("local_eeg_candidates"),
    }
    summary_path.write_text(json.dumps(slim, indent=2), encoding="utf-8")
    md = write_results_md(payload)
    print("\n=== DONE ===")
    print(md)
    print(summary_path)
    return 0 if payload["smoke"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
