"""
Append-only scientific run ledger for the living thesis.

Local files only — no network. Used by runners to keep methods/results traceable.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import ROOT, DATA

LEDGER_DIR = DATA / "thesis_ledger"
LEDGER_PATH = LEDGER_DIR / "runs.jsonl"
LATEST_PATH = LEDGER_DIR / "latest.json"


def _git_sha() -> Optional[str]:
    head = ROOT / ".git" / "HEAD"
    try:
        if not head.is_file():
            return None
        ref = head.read_text(encoding="utf-8").strip()
        if ref.startswith("ref:"):
            ref_path = ROOT / ".git" / ref.split(" ", 1)[1].strip()
            if ref_path.is_file():
                return ref_path.read_text(encoding="utf-8").strip()[:12]
        return ref[:12]
    except OSError:
        return None


def record_run(
    experiment: str,
    *,
    profile: str = "",
    gates: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    formulas_ref: str = "docs/FORMULAS.md",
    thesis_ref: str = "docs/THESIS.md",
    notes: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Append one JSON line to data/thesis_ledger/runs.jsonl and write latest.json.
    """
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    row: Dict[str, Any] = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": experiment,
        "profile": profile,
        "git_sha": _git_sha(),
        "formulas_ref": formulas_ref,
        "thesis_ref": thesis_ref,
        "authority_pin_prefix": "D1D38A",
        "gates": gates or {},
        "metrics": metrics or {},
        "notes": notes,
        "efficiency_doctrine": "docs/EFFICIENCY_DOCTRINE.md",
    }
    if extra:
        row["extra"] = extra

    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
    LATEST_PATH.write_text(json.dumps(row, indent=2, default=str) + "\n", encoding="utf-8")
    return row


def read_latest() -> Optional[Dict[str, Any]]:
    if not LATEST_PATH.is_file():
        return None
    return json.loads(LATEST_PATH.read_text(encoding="utf-8"))
