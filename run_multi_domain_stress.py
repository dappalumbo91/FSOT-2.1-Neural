#!/usr/bin/env python3
"""
Multi-domain stress test (docs, narrative, media, SME, 5W1H, authority).

  python run_multi_domain_stress.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    from fsot_nuron.benchmarks.multi_domain_stress import run_multi_domain_stress

    print("=== FSOT MULTI-DOMAIN STRESS ===")
    print("domains: authority · learning_sme · docs · narrative · media · short_horizon_5w1h")
    rep = run_multi_domain_stress()
    print(f"ok={rep.ok}  pass={rep.n_pass}/{rep.n_domains}  mean={rep.mean_score:.1f}")
    for d in rep.domains:
        flag = "PASS" if d.ok else "FAIL"
        print(f"  [{flag}] {d.score:5.1f}  {d.domain:22}  {d.metrics}")
    print("Wrote artifacts/multi_domain_stress_last.json")
    print("Wrote data/results/MULTI_DOMAIN_STRESS.md")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
