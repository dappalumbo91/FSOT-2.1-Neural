"""Portable paths for the FSOT Neural workspace — **standalone-first**.

Doctrine (transplantable brain):
  - Everything required to boot, compute, and verify lives **inside this repo**.
  - Authority math is vendored at `data/archive_snapshot/` (D1D38A pin).
  - Wet-lab / codon / Allen data under `data/`.
  - External folders (other drives, Desktop copies, Physical-Archive) are
    **optional enrichment only** — never required to run or stress the mind.
  - Bare-metal Zig body + formal/ Lean live in-repo under embodiment/ and formal/.

Do not hard-code another machine's absolute paths as dependencies.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get("FSOT_NURON_ARTIFACTS", str(ROOT / "artifacts")))
ARTIFACTS.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)
# Bundled theory authority — the brain's own copy of the law
ARCHIVE_SNAPSHOT = DATA / "archive_snapshot"
STANDALONE_AUTHORITY = ARCHIVE_SNAPSHOT / "fsot_compute_authority.py"
DOCS = ROOT / "docs"
FORMAL = ROOT / "formal"
EMBODIMENT = ROOT / "embodiment"


def _env_path(name: str) -> Path | None:
    v = os.environ.get(name)
    if not v:
        return None
    p = Path(v)
    return p if str(p) else None


def standalone_mode() -> bool:
    """
    Default True: mind runs from in-repo snapshot only.
    Set FSOT_STANDALONE=0 and FSOT_PHYSICAL_ARCHIVE=... only when re-pinning
    from an optional external theory master (developer workflow).
    """
    v = os.environ.get("FSOT_STANDALONE", "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def standalone_complete() -> bool:
    """True when the transplant package has authority + seed pin materials."""
    if not STANDALONE_AUTHORITY.is_file():
        return False
    # certificate optional but preferred; pin.json or AUTHORITY_PIN enough
    has_pin = (ARCHIVE_SNAPSHOT / "fsot_compute_AUTHORITY_PIN.json").is_file() or (
        ARCHIVE_SNAPSHOT / "pin.json"
    ).is_file()
    return has_pin


def resolve_standalone_root() -> Path:
    """Always the in-repo authority root (may be incomplete on broken clones)."""
    return ARCHIVE_SNAPSHOT.resolve()


def resolve_external_archive() -> Path | None:
    """
    Optional external theory master — only if env explicitly set.
    Never required for boot. Not used when standalone_mode() is True unless
    FSOT_ALLOW_EXTERNAL_ARCHIVE=1.
    """
    if standalone_mode() and os.environ.get("FSOT_ALLOW_EXTERNAL_ARCHIVE", "0") not in (
        "1",
        "true",
        "yes",
    ):
        return None
    for key in ("FSOT_PHYSICAL_ARCHIVE", "FSOT_ARCHIVE_ROOT"):
        p = _env_path(key)
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


def resolve_archive_root() -> Path | None:
    """
    Primary authority for the neural mind = standalone snapshot when complete.
    Falls back to optional external only when allowed.
    """
    if standalone_complete():
        return resolve_standalone_root()
    ext = resolve_external_archive()
    if ext is not None:
        return ext
    # Last resort: incomplete clone still points at snapshot dir for messages
    if ARCHIVE_SNAPSHOT.is_dir():
        return resolve_standalone_root()
    return None


def resolve_lean_hub() -> Path | None:
    """
    Lean hub: prefer in-repo `formal/` for neural proofs.
    Optional external 02_FSOT-2.1-Lean-Full only when re-pinning theory.
    """
    # Neural formalization is transplantable in-repo
    if FORMAL.is_dir() and (
        (FORMAL / "lakefile.lean").is_file()
        or (FORMAL / "FSOT").is_dir()
        or any(FORMAL.glob("*.lean"))
    ):
        return FORMAL.resolve()
    for key in ("FSOT_LEAN_HUB", "FSOT_CANONICAL_LEAN_HUB"):
        p = _env_path(key)
        if p is not None and p.is_dir():
            return p.resolve()
    ext = resolve_external_archive()
    if ext is not None:
        hub = ext / "02_FSOT-2.1-Lean-Full"
        if hub.is_dir():
            return hub.resolve()
    return FORMAL.resolve() if FORMAL.is_dir() else None


def resolve_authority_compute() -> Path | None:
    """Path to vendored fsot_compute authority (standalone first)."""
    if STANDALONE_AUTHORITY.is_file():
        return STANDALONE_AUTHORITY.resolve()
    ext = resolve_external_archive()
    if ext is not None:
        p = ext / "02_FSOT-2.1-Lean-Full" / "vendor" / "fsot_compute.py"
        if p.is_file():
            return p.resolve()
    return None


def resolve_public_data() -> Path | None:
    """In-repo data only by default — no external public-data drive required."""
    p = _env_path("FSOT_EXTERNAL_DATA_ROOT")
    if p is not None and p.is_dir():
        return p.resolve()
    # Prefer local data tree
    if DATA.is_dir():
        return DATA.resolve()
    return None


# Resolved at import (portable)
ARCHIVE_ROOT = resolve_archive_root()
LEAN_HUB = resolve_lean_hub()
PUBLIC_DATA = resolve_public_data()

# Local Allen / bio data — **in-repo only** (no Desktop / other-project paths)
ALLEN_CANDIDATES = [
    Path(os.environ["FSOT_ALLEN_EPHYS"]) if os.environ.get("FSOT_ALLEN_EPHYS") else None,
    ROOT / "data" / "eeg" / "allen_ephys" / "ephys_features.csv",
    ROOT / "data" / "allen_ephys_features.csv",
]

CELLS_JSON_CANDIDATES = [
    ROOT / "data" / "eeg" / "allen_ephys" / "cells.json",
    ROOT / "data" / "allen_cells.json",
]

CODON_MAP_CANDIDATES = [
    ROOT / "data" / "64_codon_trinary_map.txt",
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


def transplant_report() -> dict:
    """Human-readable: what this clone needs vs has (no external required)."""
    return {
        "standalone_mode": standalone_mode(),
        "standalone_complete": standalone_complete(),
        "repo_root": str(ROOT),
        "authority": str(resolve_authority_compute()) if resolve_authority_compute() else None,
        "archive_root": str(ARCHIVE_ROOT) if ARCHIVE_ROOT else None,
        "lean_hub": str(LEAN_HUB) if LEAN_HUB else None,
        "codon_map": str(find_codon_map()) if find_codon_map() else None,
        "allen_ephys": str(find_allen_ephys()) if find_allen_ephys() else None,
        "zig_host": str(EMBODIMENT / "zig" / "zig-out" / "bin" / "fsot_trit_host.exe"),
        "external_archive_optional": str(resolve_external_archive())
        if resolve_external_archive()
        else None,
        "doctrine": "Brain is transplantable: clone repo + Python deps; no other folders required.",
    }
