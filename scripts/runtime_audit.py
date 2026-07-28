#!/usr/bin/env python3
"""
Runtime dependency audit for the *accurate* FSOT-2.1-Neural system.

Traces which project modules are imported when primary entrypoints run
(import-only graph — no full scalpel). Writes docs-ready inventory.

  python scripts/runtime_audit.py
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_PHYSICAL_ARCHIVE", r"I:\FSOT-Physical-Archive")
os.environ.setdefault("PYTHONPATH", str(ROOT))

# Primary product / accuracy entrypoints (mission path)
ENTRYPOINTS = [
    ("run_archive_pin", "run_archive_pin"),
    ("run_fsot_bridge", "run_fsot_bridge"),
    ("run_machine_encode", "run_machine_encode"),
    ("run_scalpel_rates", "run_scalpel_rates"),
    ("run_intelligence_probe", "run_intelligence_probe"),
    ("run_learning_eeg_study", "run_learning_eeg_study"),
    ("run_stress_suite", "run_stress_suite"),
    ("run_console", "run_console"),
    ("product.console.app", "product.console.app"),
    ("scripts.review_console_displays", "scripts.review_console_displays"),
    ("scripts.parity_zig_neuron", "scripts.parity_zig_neuron"),
]

# Mission-critical package modules (expected)
CORE_PREFIX = "fsot_nuron"


def collect_fsot_modules() -> Dict[str, Any]:
    before = set(sys.modules.keys())
    # Import core paths used by product
    mods_to_touch = [
        "fsot_nuron.archive_pin",
        "fsot_nuron.fsot_bridge",
        "fsot_nuron.machine_encode",
        "fsot_nuron.scalar",
        "fsot_nuron.seeds",
        "fsot_nuron.chemical_codon",
        "fsot_nuron.genetic_genotype",
        "fsot_nuron.genetic_network",
        "fsot_nuron.neuron_batch",
        "fsot_nuron.cell_types",
        "fsot_nuron.class_ephys",
        "fsot_nuron.scalpel_rate",
        "fsot_nuron.scalpel_brain",
        "fsot_nuron.brain_architecture",
        "fsot_nuron.learning_memory",
        "fsot_nuron.learning_bands",
        "fsot_nuron.learning_eeg_study",
        "fsot_nuron.sensory",
        "fsot_nuron.sensory.bus",
        "fsot_nuron.sensory.packets",
        "fsot_nuron.trinary_substrate",
        "fsot_nuron.paths",
        "fsot_nuron.thesis_ledger",
        "fsot_nuron.allen_data",
        "fsot_nuron.bio_metrics",
        "product.console.app",
    ]
    errors = []
    for m in mods_to_touch:
        try:
            importlib.import_module(m)
        except Exception as e:
            errors.append({"module": m, "error": str(e)})
    after = set(sys.modules.keys())
    loaded = sorted(
        m
        for m in (after - before) | set(mods_to_touch)
        if m.startswith("fsot_nuron") or m.startswith("product")
    )
    # Also list all fsot_nuron files on disk
    pkg = ROOT / "fsot_nuron"
    on_disk = sorted(
        str(p.relative_to(ROOT)).replace("\\", "/")
        for p in pkg.rglob("*.py")
        if "__pycache__" not in str(p)
    )
    used_files = []
    for m in loaded:
        if m.startswith("fsot_nuron"):
            parts = m.split(".")
            # fsot_nuron.x.y → fsot_nuron/x/y.py or fsot_nuron/x.py
            rel = Path(*parts)
            cand = [
                ROOT / Path(*parts).with_suffix(".py"),
                ROOT / Path(*parts) / "__init__.py",
            ]
            for c in cand:
                if c.is_file():
                    used_files.append(str(c.relative_to(ROOT)).replace("\\", "/"))
                    break
    used_files = sorted(set(used_files))
    unused = sorted(set(on_disk) - set(used_files))
    return {
        "loaded_modules": loaded,
        "used_files": used_files,
        "on_disk_py": on_disk,
        "not_imported_this_audit": unused,
        "import_errors": errors,
    }


def classify_workspace() -> Dict[str, Any]:
    """High-level workspace roles for cleanup."""
    return {
        "mission_core": [
            "fsot_nuron/ (genetic, scalpel, learning, machine_encode, fsot_bridge, sensory)",
            "product/console/",
            "embodiment/zig/src/ + build.zig + run_qemu.ps1",
            "formal/ (Lean panel)",
            "data/64_codon_trinary_map.txt",
            "data/archive_snapshot/",
            "data/neuro_failure_boundaries.json",
            "run_archive_pin.py",
            "run_fsot_bridge.py",
            "run_machine_encode.py",
            "run_scalpel_rates.py",
            "run_intelligence_probe.py",
            "run_learning_eeg_study.py",
            "run_stress_suite.py",
            "run_console.py",
            "run_genetic_bio.py",
            "run_brain_design.py",
            "scripts/parity_zig_neuron.py",
            "scripts/runtime_audit.py",
            "scripts/review_console_displays.py",
            "scripts/ci_smoke.py",
            "docs/ (thesis, bio, learning, stress, runtime inventory)",
            "MISSION.md",
            "CHECKPOINT_v0.5.md",
            "requirements.txt",
            "pyproject.toml",
        ],
        "secondary_demo_keep_optional": [
            "run_language_loop.py / morse_itu (secondary Morse)",
            "run_climb.py / multi_dataset NLP scoreboards",
            "data/itu_morse.json",
            "data/literature/*",
        ],
        "local_only_not_github_payload": [
            "data/external/** (NLP/IMDB downloads — gitignored)",
            "data/kaggle_datasets/**/*.csv (large — gitignored)",
            "data/eeg/allen_ephys/*.nwb (gitignored)",
            "artifacts/ (runtime — gitignored json)",
            "embodiment/zig/.zig-cache / zig-out (gitignored)",
            "files-3ccbc49e/ (legacy dump — should NOT be on GitHub)",
            "__pycache__/",
        ],
        "cleanup_candidates_workspace": [
            "files-3ccbc49e/ — old morse/shakespeare experiments; not imported by mission",
            "data/external/nlp/* — IMDB/sentiment; mission says NLP secondary only",
            "data/results/* deep_nlp_*, multi_dataset_scoreboard, sota_fronts — demo scoreboards",
            "notebooks/ if empty or outdated",
            "dist/ build leftovers",
        ],
    }


def main() -> int:
    print("=== FSOT runtime / workspace audit ===")
    graph = collect_fsot_modules()
    roles = classify_workspace()

    print(f"fsot_nuron modules loaded: {len(graph['loaded_modules'])}")
    print(f"used files: {len(graph['used_files'])}")
    print(f"on disk py: {len(graph['on_disk_py'])}")
    print(f"not imported in this audit: {len(graph['not_imported_this_audit'])}")
    if graph["import_errors"]:
        print("import errors:", graph["import_errors"])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": "I:\\FSOT-Physical-Archive + data/archive_snapshot",
        "entrypoints": [e[0] for e in ENTRYPOINTS],
        "import_graph": graph,
        "workspace_roles": roles,
        "repro_commands": [
            "python run_archive_pin.py",
            "python run_fsot_bridge.py",
            "python run_stress_suite.py --quick",
            "python run_learning_eeg_study.py",
            "python run_console.py",
            "python scripts/runtime_audit.py",
        ],
    }

    art = ROOT / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "runtime_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Markdown inventory
    md = [
        "# Runtime inventory — accurate FSOT-2.1-Neural system",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "This audit lists what the **mission-accurate** path actually imports and uses,",
        "versus workspace bulk that is optional, demo, or local-only.",
        "",
        "## Authority",
        "",
        "| Layer | Path |",
        "|-------|------|",
        "| Physical archive | `I:\\FSOT-Physical-Archive` |",
        "| Compute pin | `vendor/fsot_compute.py` D1D38A… |",
        "| Codon map | `data/64_codon_trinary_map.txt` ≡ `I:\\64_codon_trinary_map.txt` |",
        "| Snapshot | `data/archive_snapshot/` |",
        "",
        "## Primary entrypoints (run these)",
        "",
    ]
    for cmd in report["repro_commands"]:
        md.append(f"- `{cmd}`")
    md += [
        "",
        "## Package modules loaded by audit import graph",
        "",
    ]
    for m in graph["loaded_modules"]:
        md.append(f"- `{m}`")
    md += [
        "",
        f"## Used files ({len(graph['used_files'])})",
        "",
    ]
    for f in graph["used_files"]:
        md.append(f"- `{f}`")
    md += [
        "",
        f"## On disk but not imported by this audit ({len(graph['not_imported_this_audit'])})",
        "",
        "These may still be used by secondary runners (Morse, NLP climb, EEG emotions demos).",
        "Safe cleanup only after confirming no entrypoint you care about imports them.",
        "",
    ]
    for f in graph["not_imported_this_audit"]:
        md.append(f"- `{f}`")
    md += [
        "",
        "## Mission core (keep)",
        "",
    ]
    for x in roles["mission_core"]:
        md.append(f"- {x}")
    md += [
        "",
        "## Secondary / optional",
        "",
    ]
    for x in roles["secondary_demo_keep_optional"]:
        md.append(f"- {x}")
    md += [
        "",
        "## Local-only (must not confuse GitHub repro)",
        "",
    ]
    for x in roles["local_only_not_github_payload"]:
        md.append(f"- {x}")
    md += [
        "",
        "## Cleanup candidates (workspace size)",
        "",
    ]
    for x in roles["cleanup_candidates_workspace"]:
        md.append(f"- {x}")
    md += [
        "",
        "## GitHub hygiene",
        "",
        "- Tracked file count should stay small (~mission + docs + thin data).",
        "- Large CSVs/NWB under `data/external` and kaggle paths are **gitignored**.",
        "- `files-3ccbc49e/` must stay **untracked** (legacy).",
        "- `artifacts/*.json` gitignored; keep `data/results/*.md` summaries if useful.",
        "",
        "JSON: `artifacts/runtime_audit.json`",
        "",
    ]
    out_md = ROOT / "docs" / "RUNTIME_INVENTORY.md"
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {out_md}")
    print(f"Wrote {art / 'runtime_audit.json'}")
    return 0 if not graph["import_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
