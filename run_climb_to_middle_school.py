"""
Autonomous climb: rebuild open PK→G8 curriculum, run Zig ladder band-by-band
until middle school (grade8) straight-A or failure.

Logs to D:/fsot_training/logs when available, else data/results.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ZIG_DIR = ROOT / "embodiment" / "zig"
MIND = ZIG_DIR / "zig-out" / "bin" / "fsot_mind.exe"
LOG_DIR = Path("D:/fsot_training/logs") if Path("D:/fsot_training").exists() else (ROOT / "data" / "results")
BANDS = [
    "preschool",
    "kindergarten",
    "grade1",
    "grade2",
    "grade3",
    "grade4",
    "grade5",
    "grade6",
    "grade7",
    "grade8",
]


def log(msg: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    with (LOG_DIR / "climb_middle_school.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 3600) -> subprocess.CompletedProcess:
    log(f"$ {' '.join(cmd)}  (cwd={cwd or ROOT})")
    return subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "started": datetime.now(timezone.utc).isoformat(),
        "bands": [],
        "ok": False,
    }

    log("=== BUILD OPEN CURRICULUM PK→G8 ===")
    r = run([sys.executable, str(ROOT / "run_curriculum_open.py")])
    log(r.stdout[-4000:] if r.stdout else "")
    if r.returncode != 0:
        log(f"curriculum FAIL rc={r.returncode}\n{r.stderr[-2000:]}")
        report["error"] = "curriculum_build"
        (LOG_DIR / "climb_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 1

    log("=== ZIG BUILD ===")
    r = run(["zig", "build"], cwd=ZIG_DIR, timeout=600)
    if r.returncode != 0:
        log(f"zig build FAIL\n{r.stderr[-3000:]}\n{r.stdout[-1000:]}")
        report["error"] = "zig_build"
        (LOG_DIR / "climb_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 1
    if not MIND.is_file():
        log(f"missing {MIND}")
        return 1

    # full ladder first
    log("=== FULL LADDER PK→G8 ===")
    t0 = time.time()
    r = run([str(MIND), "ladder"], cwd=ZIG_DIR, timeout=7200)
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    log(out[-8000:])
    report["ladder_rc"] = r.returncode
    report["ladder_seconds"] = round(time.time() - t0, 1)
    report["ladder_ok"] = r.returncode == 0 and "FSOT_LADDER PASS" in out

    # if full ladder failed, still probe per-band for diagnostics
    if not report["ladder_ok"]:
        log("=== PER-BAND DIAGNOSTIC ===")
        for b in BANDS:
            br = run([str(MIND), b], cwd=ZIG_DIR, timeout=1800)
            bout = (br.stdout or "") + "\n" + (br.stderr or "")
            ok = br.returncode == 0 and "FSOT_BAND_PASS" in bout
            report["bands"].append({"band": b, "ok": ok, "rc": br.returncode, "tail": bout[-1500:]})
            log(f"BAND {b} ok={ok}")
            if not ok:
                break
    else:
        for b in BANDS:
            report["bands"].append({"band": b, "ok": True})

    report["finished"] = datetime.now(timezone.utc).isoformat()
    report["ok"] = bool(report["ladder_ok"])
    (LOG_DIR / "climb_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    log(f"=== DONE ok={report['ok']} ===")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
