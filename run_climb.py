#!/usr/bin/env python3
"""
SOTA climb: hierarchical long IMDB (more samples) + fixed learned attention + multi-task.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fsot_nuron.deep_readout import (
    eval_dataset_attention,
    eval_dataset_deep,
    eval_multitask_domains,
)
from fsot_nuron.paths import ARTIFACTS, ROOT as R


def main() -> int:
    results = []
    imdb = R / "data" / "external" / "nlp" / "imdb_50k" / "IMDB Dataset.csv"
    sent = R / "data" / "kaggle_datasets" / "sentiment_tiny" / "sentiment_analysis.csv"
    fin = R / "data" / "external" / "nlp" / "financial_sentiment" / "data.csv"
    sms = R / "data" / "kaggle_datasets" / "sms_spam" / "spam.csv"

    print("=== 1) IMDB hierarchical long (more docs, multi-seed) ===")
    if imdb.is_file():
        best = None
        for seed in (42, 7, 99):
            r = eval_dataset_deep(
                imdb,
                max_docs=360,
                long_context=True,
                seed=seed,
            )
            r["tag"] = f"imdb_hier_seed{seed}"
            results.append(r)
            print(
                f"  seed={seed} test={r.get('test_acc'):.3f} bal={r.get('balanced_accuracy'):.3f} "
                f"n={r.get('n_train')}+{r.get('n_test')} encode_s={r.get('encode_seconds'):.0f}"
            )
            if best is None or (r.get("test_acc") or 0) > (best.get("test_acc") or 0):
                best = r
        if best:
            print(f"  BEST imdb hierarchical test={best.get('test_acc'):.3f}")

    print("=== 2) IMDB learned attention (fixed residual attn) ===")
    if imdb.is_file():
        r = eval_dataset_attention(
            imdb, max_docs=320, long_context=True, t_pool=64, seed=42
        )
        r["tag"] = "imdb_attention_v2"
        results.append(r)
        print(
            f"  test={r.get('test_acc'):.3f} bal={r.get('balanced_accuracy'):.3f} "
            f"train={r.get('train_acc'):.3f} encode_s={r.get('encode_seconds'):.0f}"
        )

    print("=== 3) Sentiment medium deep multi-seed ===")
    if sent.is_file():
        best = None
        for seed in (42, 7, 99):
            r = eval_dataset_deep(
                sent, max_docs=420, long_context=False, seed=seed, n_units=40
            )
            r["tag"] = f"sentiment_deep_seed{seed}"
            results.append(r)
            print(f"  seed={seed} test={r.get('test_acc'):.3f}")
            if best is None or (r.get("test_acc") or 0) > (best.get("test_acc") or 0):
                best = r
        if best:
            print(f"  BEST sentiment deep test={best.get('test_acc'):.3f}")

    print("=== 4) Sentiment learned attention ===")
    if sent.is_file():
        r = eval_dataset_attention(
            sent, max_docs=400, long_context=False, t_pool=80, seed=42
        )
        r["tag"] = "sentiment_attention_v2"
        results.append(r)
        print(
            f"  test={r.get('test_acc'):.3f} train={r.get('train_acc'):.3f}"
        )

    print("=== 5) Financial attention + deep ===")
    if fin.is_file():
        r = eval_dataset_deep(fin, max_docs=400, long_context=False, n_units=40)
        r["tag"] = "financial_deep"
        results.append(r)
        print(f"  deep test={r.get('test_acc'):.3f}")
        r2 = eval_dataset_attention(
            fin, max_docs=400, long_context=False, t_pool=72
        )
        r2["tag"] = "financial_attention_v2"
        results.append(r2)
        print(f"  attn test={r2.get('test_acc'):.3f}")

    print("=== 6) Multi-task domains ===")
    mt_paths = [p for p in (sent, fin, sms) if p.is_file()]
    mt = eval_multitask_domains(mt_paths, max_docs_each=200)
    mt["tag"] = "multitask"
    results.append(mt)
    print(
        f"  overall={mt.get('test_acc')} per_domain={mt.get('per_domain_test_acc')}"
    )

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "goal": "climb IMDB toward 0.65+ and 3-class sentiment; learned attention + multi-seed hier",
        "prior_best": {"imdb": 0.556, "sentiment": 0.565, "sms": 0.93},
        "results": results,
    }
    dest = R / "data" / "results" / "climb_suite.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "climb_suite.json").write_text(
        json.dumps(out, indent=2, default=str), encoding="utf-8"
    )

    # bests
    def best_of(prefix: str) -> float:
        vals = [
            r.get("test_acc")
            for r in results
            if str(r.get("tag", "")).startswith(prefix) and r.get("test_acc") is not None
        ]
        return max(vals) if vals else float("nan")

    lines = [
        "# SOTA climb suite",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        f"- Best IMDB hierarchical: **{best_of('imdb_hier'):.3f}** (prior 0.556)",
        f"- Best IMDB attention: **{best_of('imdb_attention'):.3f}**",
        f"- Best sentiment deep: **{best_of('sentiment_deep'):.3f}** (prior 0.565)",
        f"- Best sentiment attention: **{best_of('sentiment_attention'):.3f}**",
        f"- Multitask overall: **{mt.get('test_acc')}** · per-domain `{mt.get('per_domain_test_acc')}`",
        "",
        "| Tag | Test | Bal | Train | N_test |",
        "|-----|------|-----|-------|--------|",
    ]
    for r in results:
        if r.get("error"):
            lines.append(f"| {r.get('tag')} | ERR | | | |")
            continue
        lines.append(
            f"| {r.get('tag')} | **{r.get('test_acc', 0):.3f}** | "
            f"{r.get('balanced_accuracy', r.get('test_acc', 0)):.3f} | "
            f"{r.get('train_acc', float('nan'))} | {r.get('n_test', '')} |"
        )
    lines += ["", f"JSON: `{dest}`", ""]
    md = R / "data" / "results" / "CLIMB.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    (R / "CLIMB.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", dest)
    print("\n".join(lines[:20]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
