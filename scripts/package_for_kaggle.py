#!/usr/bin/env python3
"""
Build a Kaggle *code* package (NOT the emotions CSV).

Output: dist/fsot-2-1-neural-kaggle.zip
Upload as a Kaggle Dataset (your code) and attach to the notebook alongside
birdy654/eeg-brainwave-dataset-feeling-emotions as a separate input.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "dist"
OUT_ZIP = OUT_DIR / "fsot-2-1-neural-kaggle.zip"

INCLUDE_GLOBS = [
    "fsot_nuron/**/*.py",
    "data/itu_morse.json",
    "data/64_codon_trinary_map.txt",
    "data/neuro_failure_boundaries.json",
    "data/literature/*.md",
    "data/literature/*.txt",
    "requirements.txt",
    "LICENSE",
    "NOTICE",
    "VERIFICATION.md",
    "README.md",
]

EXCLUDE_PARTS = {
    "__pycache__",
    ".pyc",
    "kaggle_emotions",
    "allen_ephys",
    "emotions.csv",
    "ephys.nwb",
    "artifacts",
}


def wanted(path: Path) -> bool:
    s = str(path).replace("\\", "/")
    for ex in EXCLUDE_PARTS:
        if ex in s:
            return False
    return True


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()

    files: list[Path] = []
    for pattern in INCLUDE_GLOBS:
        files.extend(ROOT.glob(pattern))
    files = [p for p in files if p.is_file() and wanted(p)]

    with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            arc = p.relative_to(ROOT).as_posix()
            zf.write(p, arcname=arc)
        # small marker
        zf.writestr(
            "KAGGLE_CODE_PACKAGE.txt",
            "FSOT-2.1-Neural code package. Does NOT include third-party emotions.csv.\n"
            "Attach birdy654/eeg-brainwave-dataset-feeling-emotions separately.\n",
        )

    print(f"Wrote {OUT_ZIP} ({OUT_ZIP.stat().st_size} bytes)")
    print(f"Files: {len(files)}")
    print("Upload this zip as a Kaggle Dataset (your code), then Add Data in the notebook.")


if __name__ == "__main__":
    main()
