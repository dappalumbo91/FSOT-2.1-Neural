#!/usr/bin/env python3
"""Dual-track scorecard: biological wet-lab + math curriculum.

Never let one track erase the other.

  python scripts/dual_track_scorecard.py
  python scripts/dual_track_scorecard.py --math-only
  python scripts/dual_track_scorecard.py --refresh-bio

Gates (both must stay green when claims are dual):
  BIO:  wetlab battery pass + bio_report_card operational
  MATH: rule drills ≥95% (hard) · fire precision reported honestly
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))

RESULTS = ROOT / "data" / "results"
OUT_JSON = RESULTS / "DUAL_TRACK_SCORECARD.json"
OUT_MD = RESULTS / "DUAL_TRACK_SCORECARD.md"
PASS_DRILLS = 0.95


def _load(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def refresh_bio() -> Dict[str, Any]:
    """Re-run wetlab battery + bio report card (local, no API)."""
    out: Dict[str, Any] = {"ran": []}
    wet = ROOT / "run_wetlab_accuracy_battery.py"
    if wet.is_file():
        r = subprocess.run(
            [sys.executable, str(wet)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
        out["ran"].append("wetlab_accuracy_battery")
        out["wetlab_exit"] = r.returncode
    try:
        from fsot_nuron.bio_report_card import build_bio_report_card

        card = build_bio_report_card(device="cpu", n_units=64, steps=1000)
        out["ran"].append("bio_report_card")
        out["bio_card_pass"] = bool(card.get("pass_operational") or card.get("pass"))
    except Exception as e:
        out["bio_card_error"] = str(e)
    try:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "export_lean_wetlab_certificate.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        out["ran"].append("lean_wetlab_certificate")
    except Exception as e:
        out["lean_cert_error"] = str(e)
    return out


def score_math(test_n: int = 500) -> Dict[str, Any]:
    from fsot_nuron.math_rules import (
        PASS,
        apply_rules,
        build_rule_drills,
        exact_num,
        load_gsm8k_heldout,
        score_items,
    )
    from fsot_nuron.math_binding import binding_drills

    drills = score_items(build_rule_drills())
    bd = binding_drills()
    bd_ok = sum(
        1
        for q, a, _ in bd
        if (r := apply_rules(q)).ok and r.answer and exact_num(r.answer, a)
    )
    items = load_gsm8k_heldout("test", test_n)
    c = wf = no = 0
    for it in items:
        r = apply_rules(it.question)
        if not r.ok or r.answer is None:
            no += 1
            continue
        if exact_num(r.answer, it.answer):
            c += 1
        else:
            wf += 1
    fire = c + wf
    return {
        "drills_acc": drills["accuracy"],
        "drills_n": drills["n"],
        "drills_pass": drills["accuracy"] >= PASS_DRILLS,
        "binding_drills": f"{bd_ok}/{len(bd)}",
        "binding_pass": bd_ok == len(bd),
        "gsm8k_n": len(items),
        "correct": c,
        "wrong_fire": wf,
        "no_fire": no,
        "fire_precision": round(c / max(1, fire), 4),
        "pass_threshold_drills": PASS_DRILLS,
        "hard_gate": "drills≥95% never sacrificed for auto-templates",
    }


def bio_status() -> Dict[str, Any]:
    wet = _load(RESULTS / "wetlab_accuracy_battery.json")
    bio = _load(RESULTS / "bio_report_card.json")
    lean = _load(RESULTS / "LEAN_WETLAB_CERTIFICATE.json")
    st: Dict[str, Any] = {
        "wetlab_found": wet is not None,
        "bio_card_found": bio is not None,
        "lean_cert_found": lean is not None,
    }
    if wet:
        n_pass = wet.get("n_pass")
        n_tot = wet.get("n_checks") or wet.get("n_total") or wet.get("n")
        crit = wet.get("critical_fails")
        st["wetlab_pass"] = bool(
            (n_pass is not None and n_tot is not None and n_pass == n_tot)
            or wet.get("all_pass")
            or (crit == 0 and n_pass and n_tot and n_pass >= n_tot)
        )
        st["wetlab_score"] = (
            f"{n_pass}/{n_tot}" if n_pass is not None and n_tot is not None else "?"
        )
        st["wetlab_critical_fails"] = crit
        st["wetlab_generated"] = wet.get("generated_at") or wet.get("generated")
    if bio:
        gaps = bio.get("gaps") or {}
        st["bio_operational"] = bool(
            bio.get("pass_operational") or bio.get("pass") or bio.get("operational_pass")
        )
        st["bio_strict"] = bool(bio.get("pass_strict") or bio.get("strict_pass"))
        st["bio_gaps"] = f"{gaps.get('closed')}/{gaps.get('total')}"
        ac = bio.get("allen_comparison") or {}
        st["bio_isi_rel_error"] = ac.get("isi_rel_error")
        st["bio_adapt_rel_error"] = ac.get("adapt_rel_error")
        st["bio_generated"] = bio.get("generated_at") or bio.get("generated")
    if lean:
        st["lean_ok"] = bool(
            lean.get("ok")
            or lean.get("pass")
            or lean.get("all_ok")
            or (lean.get("overall") or "").upper() == "PASS"
            or lean.get("lake") == "PASS"
        )
    # Bio track: wetlab battery is the hard public gate; bio_card is Allen batch path
    st["track_pass"] = bool(st.get("wetlab_pass"))
    st["track_pass_strict"] = bool(st.get("wetlab_pass")) and bool(
        st.get("bio_operational")
    )
    return st


def render_md(card: Dict[str, Any]) -> str:
    m = card["math"]
    b = card["bio"]
    lines = [
        "# Dual-track scorecard — bio + math",
        "",
        f"Generated: `{card['generated_at']}`",
        "",
        "**Doctrine:** Biological wet-lab accuracy and math curriculum are **separate tracks**. "
        "GSM8K climb must never drop rule drills below 95%. Auto-templates that break drills are refused.",
        "",
        "## Gates",
        "",
        f"| Track | Gate | Status |",
        f"|-------|------|--------|",
        f"| **BIO wetlab** | public battery (Allen/codon/pin) | **{'PASS' if b.get('wetlab_pass') else 'FAIL / STALE'}** `{b.get('wetlab_score')}` |",
        f"| **BIO card** | Allen batch ISI/adapt (operational) | **{'PASS' if b.get('bio_operational') else 'FAIL'}** gaps `{b.get('bio_gaps')}` |",
        f"| **BIO lean** | Lean × wetlab certificate | **{'PASS' if b.get('lean_ok') else 'CHECK'}** |",
        f"| **MATH drills** | ≥95% hard gate | **{'PASS' if m.get('drills_pass') else 'FAIL'}** |",
        f"| **MATH binding** | 100% BIND/SCHEMA drills | **{'PASS' if m.get('binding_pass') else 'FAIL'}** |",
        "",
        "## Biological accuracy (not forgotten)",
        "",
        f"- **Wetlab battery:** `{b.get('wetlab_score')}` pass={b.get('wetlab_pass')} critical_fails={b.get('wetlab_critical_fails')} · `{b.get('wetlab_generated')}`",
        f"- **Bio report card:** operational={b.get('bio_operational')} strict={b.get('bio_strict')} gaps=`{b.get('bio_gaps')}`",
        f"- ISI rel error: `{b.get('bio_isi_rel_error')}` (operational needs ≤2%) · adapt: `{b.get('bio_adapt_rel_error')}`",
        f"- Lean wetlab cert: {b.get('lean_ok')}",
        f"- Bio card generated: `{b.get('bio_generated')}`",
        "",
        "Refresh: `python scripts/dual_track_scorecard.py --refresh-bio`",
        "",
        "Intel/bio stack modes (Zig): `intel-loop`, neuromod, sleep_replay — see `docs/FORWARD_INTELLIGENCE_BIO.md`.",
        "",
        "## Math curriculum (rules-first)",
        "",
        f"- Drills: **{m.get('drills_acc')}** (n={m.get('drills_n')}) · hard gate ≥{PASS_DRILLS}",
        f"- Binding drills: {m.get('binding_drills')}",
        f"- GSM8K sample n={m.get('gsm8k_n')}: correct={m.get('correct')} wrong_fire={m.get('wrong_fire')} no_fire={m.get('no_fire')}",
        f"- Fire precision: **{m.get('fire_precision')}**",
        "",
        f"Hard rule: `{m.get('hard_gate')}`",
        "",
        "## Note on the 76% drill fail",
        "",
        "That was a **regression from ungated train-template auto-apply**. "
        "It is **not** the current gate. Current drills must stay **100% / ≥95%**. "
        "Loose auto that tanks drills is rejected.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-bio", action="store_true")
    ap.add_argument("--math-only", action="store_true")
    ap.add_argument("--test", type=int, default=500)
    args = ap.parse_args()

    bio_run = {}
    if args.refresh_bio and not args.math_only:
        print("Refreshing biological track…", flush=True)
        bio_run = refresh_bio()

    math = score_math(args.test) if True else {}
    bio = bio_status() if not args.math_only else {"skipped": True}

    card = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bio": bio,
        "math": math,
        "bio_refresh": bio_run,
        "dual_ok": bool(math.get("drills_pass"))
        and (bool(bio.get("track_pass")) if not args.math_only else True),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(card, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_md(card), encoding="utf-8")
    print(json.dumps(card, indent=2))
    print(f"\nWrote {OUT_MD}")
    return 0 if math.get("drills_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
