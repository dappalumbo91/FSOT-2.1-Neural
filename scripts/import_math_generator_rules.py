#!/usr/bin/env python3
"""Pull full Math-generator rule corpus into FSOT neural mind rulebook.

  python scripts/import_math_generator_rules.py
  python scripts/import_math_generator_rules.py --source "$FSOT_LOCAL_DATA/Math generator"
"""

from __future__ import annotations

import os as _os
from pathlib import Path as _Path

_REPO_ROOT = _Path(__file__).resolve().parents[1]


def _fsot_local_path(env, default):
    """Local path outside the repo: $env if set, else a path relative to the repo root."""
    _v = _os.environ.get(env, "").strip()
    return _Path(_v) if _v else _REPO_ROOT / default


import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    p = argparse.ArgumentParser(description="Import Math generator rules into monorepo")
    p.add_argument(
        "--source",
        default=os.environ.get("MATH_GENERATOR_ROOT", _os.fspath(_REPO_ROOT / 'data_external/local' / 'Math generator')),
    )
    args = p.parse_args()

    from fsot_nuron.math_rulebook_import import import_all

    man = import_all(Path(args.source))
    print(
        json.dumps(
            {
                "source": man["source"],
                "n_documents": man["n_documents"],
                "n_rules": man["n_rules"],
                "n_bank_rows": man.get("n_bank_rows"),
                "n_fsot_law_nodes_approx": man.get("n_fsot_algorithmic_law_nodes_approx"),
                "top_families": list(man["by_domain_family"].items())[:15],
                "written": man.get("written"),
            },
            indent=2,
        )
    )
    print(f"\nFSOT_MATH_RULEBOOK_IMPORT n_rules={man['n_rules']}")
    print("OUT data/math_rulebook/MASTER_RULEBOOK.json")
    print("BANK data/math_rulebook/bank.tsv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
