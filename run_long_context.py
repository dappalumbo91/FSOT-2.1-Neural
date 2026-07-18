#!/usr/bin/env python3
"""Long-context / higher-capacity FSOT readout evaluation."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fsot_nuron.deep_readout import eval_dataset_deep
from fsot_nuron.paths import ARTIFACTS, ROOT as R


def main() -> int:
    targets = [
        (R / "data" / "external" / "nlp" / "imdb_50k" / "IMDB Dataset.csv", True, 240),
        (R / "data" / "kaggle_datasets" / "sentiment_tiny" / "sentiment_analysis.csv", False, 360),
        (R / "data" / "external" / "nlp" / "financial_sentiment" / "data.csv", False, 360),
        (R / "data" / "kaggle_datasets" / "sms_spam" / "spam.csv", False, 300),
        (R / "data" / "external" / "nlp" / "twitter_entity_sentiment" / "twitter_training.csv", False, 300),
        # force long-context on financial news too (sentences short but capacity path)
        (R / "data" / "external" / "nlp" / "financial_news_sentiment" / "all-data.csv", False, 360),
    ]
    # Also force a long-context IMDB-style pass is first; second pass: long forced on sentiment
    results = []
    for path, force_long, max_docs in targets:
        if not path.is_file():
            print("skip missing", path)
            continue
        print("=" * 60)
        print("EVAL", path, "long=" , force_long if force_long else "auto")
        r = eval_dataset_deep(
            path,
            max_docs=max_docs,
            long_context=True if force_long else None,
        )
        results.append(r)
        if r.get("error"):
            print(" ERROR", r["error"])
        else:
            print(
                f" test={r['test_acc']:.3f} bal={r['balanced_accuracy']:.3f} "
                f"long={r.get('long_context')} feat={r.get('n_features')} "
                f"chunks={r.get('max_chunks')} steps/chunk={r.get('max_steps_per_chunk')} "
                f"encode_s={r.get('encode_seconds'):.1f}"
            )

    # Forced long-context sentiment climb
    sent = R / "data" / "kaggle_datasets" / "sentiment_tiny" / "sentiment_analysis.csv"
    if sent.is_file():
        print("=" * 60)
        print("EVAL sentiment FORCED long-context capacity")
        r = eval_dataset_deep(sent, max_docs=360, long_context=True)
        r["dataset"] = r.get("dataset", "sentiment") + " [forced_long]"
        results.append(r)
        print(
            f" test={r.get('test_acc'):.3f} bal={r.get('balanced_accuracy'):.3f} "
            f"long={r.get('long_context')}"
        )

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "goal": "longer context + capacity for IMDB / multi-class SOTA climb",
        "results": results,
    }
    dest = R / "data" / "results" / "long_context_suite.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "long_context_suite.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = [
        "# Long-context / capacity suite",
        "",
        f"Generated: `{out['generated_at']}`",
        "",
        "| Dataset | Test | Bal | Long | Feats | Chunks | Steps/chunk |",
        "|---------|------|-----|------|-------|--------|-------------|",
    ]
    for r in results:
        if r.get("error"):
            lines.append(f"| {r.get('dataset')} | ERR | | | | | |")
            continue
        lines.append(
            f"| {r.get('dataset')} | **{r.get('test_acc'):.3f}** | {r.get('balanced_accuracy'):.3f} | "
            f"{r.get('long_context')} | {r.get('n_features')} | {r.get('max_chunks')} | "
            f"{r.get('max_steps_per_chunk')} |"
        )
    lines += [
        "",
        "Hierarchical path: document → overlapping chunks → per-chunk Morse/reservoir "
        "(head+tail sample if overlength) → mean/max/std/first/last pool → deeper FSOT-gated MLP.",
        "",
    ]
    md = R / "data" / "results" / "LONG_CONTEXT.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    (R / "LONG_CONTEXT.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", dest, md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
