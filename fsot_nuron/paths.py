"""Portable paths for the FSOT neuron workspace (Windows-first).

Resolves the physical archive hub when present so the neural substrate is
not an island next to FSOT 2.1 verification.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get("FSOT_NURON_ARTIFACTS", str(ROOT / "artifacts")))
ARTIFACTS.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "data"
ARCHIVE_SNAPSHOT = DATA / "archive_snapshot"


def _env_path(name: str) -> Path | None:
    v = os.environ.get(name)
    if not v:
        return None
    p = Path(v)
    return p if str(p) else None


def resolve_archive_root() -> Path | None:
    """Definitive master: I:/FSOT-Physical-Archive (or FSOT_PHYSICAL_ARCHIVE)."""
    candidates = [
        _env_path("FSOT_PHYSICAL_ARCHIVE"),
        _env_path("FSOT_ARCHIVE_ROOT"),
        Path(r"I:\FSOT-Physical-Archive"),
        Path(r"I:/FSOT-Physical-Archive"),
    ]
    for p in candidates:
        if p is None:
            continue
        try:
            rp = p.resolve()
        except OSError:
            continue
        if rp.is_dir() and (
            (rp / "ARCHIVE_MANIFEST.json").is_file()
            or (rp / "02_FSOT-2.1-Lean-Full").is_dir()
        ):
            return rp
    return None


def resolve_lean_hub() -> Path | None:
    """Canonical theory hub under the physical archive."""
    for key in ("FSOT_LEAN_HUB", "FSOT_CANONICAL_LEAN_HUB"):
        p = _env_path(key)
        if p is not None and p.is_dir():
            return p.resolve()
    arch = resolve_archive_root()
    if arch is None:
        return None
    hub = arch / "02_FSOT-2.1-Lean-Full"
    return hub if hub.is_dir() else None


def resolve_public_data() -> Path | None:
    p = _env_path("FSOT_EXTERNAL_DATA_ROOT")
    if p is not None and p.is_dir():
        return p.resolve()
    arch = resolve_archive_root()
    if arch is None:
        return None
    pd = arch / "03_FSOT-PublicData"
    return pd if pd.is_dir() else None


ARCHIVE_ROOT = resolve_archive_root()
LEAN_HUB = resolve_lean_hub()
PUBLIC_DATA = resolve_public_data()

# Local Allen / bio data candidates (first existing wins)
ALLEN_CANDIDATES = [
    Path(os.environ["FSOT_ALLEN_EPHYS"]) if os.environ.get("FSOT_ALLEN_EPHYS") else None,
    ROOT / "data" / "eeg" / "allen_ephys" / "ephys_features.csv",
    ROOT / "data" / "allen_ephys_features.csv",
    Path(r"C:\Users\damia\Desktop\nuron\cell data\allen_cell_types\ephys_features.csv"),
    Path(r"C:\Users\damia\Desktop\nuron\allen_cell_types\ephys_features.csv"),
    (PUBLIC_DATA / "allen_ephys_features.csv") if PUBLIC_DATA else None,
]

CELLS_JSON_CANDIDATES = [
    ROOT / "data" / "eeg" / "allen_ephys" / "cells.json",
    ROOT / "data" / "allen_cells.json",
    Path(r"C:\Users\damia\Desktop\nuron\cell data\allen_cell_types\cells.json"),
    Path(r"C:\Users\damia\Desktop\nuron\allen_cell_types\cells.json"),
]

CODON_MAP_CANDIDATES = [
    ROOT / "data" / "64_codon_trinary_map.txt",
    (ARCHIVE_ROOT / "04_Genetics-Longevity" / "64_codon_trinary_map.txt")
    if ARCHIVE_ROOT
    else None,
    (ARCHIVE_ROOT / "01_SR-ITE-USB-Original" / "3_driver_zig" / "64_codon_trinary_map.txt")
    if ARCHIVE_ROOT
    else None,
]


def find_allen_ephys() -> Path | None:
    for p in ALLEN_CANDIDATES:
        if p is not None and p.is_file():
            return p
    return None


def find_allen_cells_json() -> Path | None:
    for p in CELLS_JSON_CANDIDATES:
        if p is not None and p.is_file():
            return p
    return None


def find_codon_map() -> Path | None:
    for p in CODON_MAP_CANDIDATES:
        if p is not None and p.is_file():
            return p
    return None
