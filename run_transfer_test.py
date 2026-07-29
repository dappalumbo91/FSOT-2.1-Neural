#!/usr/bin/env python3
"""Teach A → probe without title tokens (transfer)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    from fsot_nuron.benchmarks.transfer_test import run_transfer_tests

    print("=== FSOT TRANSFER TEST ===")
    rep = run_transfer_tests(max_pairs=3)
    print(
        f"ok={rep.ok} pairs={rep.n_pairs} mean_hit={rep.mean_hit_rate:.3f} "
        f"curiosity={rep.mean_curiosity:.3f}"
    )
    for p in rep.pairs:
        print(
            f"  {p.teach_title[:40]!r}: hits={p.n_hits}/{p.n_probes} "
            f"rate={p.hit_rate:.3f} cur={p.curiosity_resolved:.3f}"
        )
    print("Wrote artifacts/transfer_test_last.json")
    print("Wrote data/results/TRANSFER_TEST.md")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
