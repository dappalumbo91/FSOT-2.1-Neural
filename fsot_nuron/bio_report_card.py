"""Shipable bio validation report card from Allen-facing validation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import ARTIFACTS, ROOT
from .validate import run_validation

RESULTS_DIR = ROOT / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CARD_JSON = RESULTS_DIR / "bio_report_card.json"
CARD_MD = RESULTS_DIR / "bio_report_card.md"


def build_bio_report_card(
    *,
    n_units: int = 64,
    steps: int = 1000,
    device: str = "cpu",
    write: bool = True,
) -> Dict[str, Any]:
    report = run_validation(
        n_units=n_units,
        steps=steps,
        device=device,
        use_api=False,
        mode="bio_match",
        both_modes=True,
        calibrate=True,
    )
    bm = (report.get("modes") or {}).get("bio_match") or report
    gaps = bm.get("gaps") or report.get("gaps") or {}
    comp = bm.get("comparison_to_allen_sample") or report.get("comparison_to_allen_sample") or {}
    verdict = bm.get("verdict") or report.get("verdict") or {}
    eff = report.get("efficiency") or {}

    card = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "package": "FSOT-2.1-Neural",
        "primary_mode": report.get("primary_mode", "bio_match"),
        "device": report.get("device") or device,
        "n_units": report.get("n_units") or n_units,
        "steps": report.get("steps") or steps,
        "allen_comparison": {
            "isi_ms_sim": comp.get("fsot_mean_isi_ms_evoked"),
            "isi_ms_allen": comp.get("allen_mean_avg_isi_ms"),
            "isi_rel_error": comp.get("isi_rel_error"),
            "adapt_sim": comp.get("fsot_mean_adaptation_evoked"),
            "adapt_allen": comp.get("allen_mean_adaptation"),
            "adapt_rel_error": comp.get("adaptation_rel_error"),
            "rate_evoked_Hz": comp.get("fsot_mean_rate_evoked_Hz"),
        },
        "gaps": {
            "closed": gaps.get("n_closed"),
            "total": gaps.get("n_total"),
            "all_closed": gaps.get("all_closed"),
            "rows": gaps.get("rows"),
        },
        "verdict": verdict,
        "bands": {
            "evoked_pass": verdict.get("evoked_band_pass_rate"),
            "spontaneous_pass": verdict.get("spontaneous_band_pass_rate"),
            "rest_pass": verdict.get("rest_band_pass_rate"),
        },
        "efficiency_ledger": eff,
        "honesty": (
            "Allen-facing computational match under stated tolerances. "
            "Not a wet-lab electrophysiology claim. 1 ms step grid floors residual ISI error. "
            "pass_strict requires all gaps closed; pass_operational requires ISI+bands closed "
            "and adaptation within 25% (sign/order still primary for AHP)."
        ),
        "pass_strict": bool(gaps.get("all_closed"))
        and float(verdict.get("evoked_band_pass_rate") or 0) >= 1.0,
        "pass_operational": (
            float(verdict.get("evoked_band_pass_rate") or 0) >= 1.0
            and float(verdict.get("spontaneous_band_pass_rate") or 0) >= 1.0
            and float(verdict.get("rest_band_pass_rate") or 0) >= 1.0
            and float(comp.get("isi_rel_error") or 1.0) <= 0.02
            and float(comp.get("adaptation_rel_error") or 1.0) <= 0.25
        ),
    }
    card["pass"] = card["pass_operational"]

    md = _to_markdown(card)
    if write:
        CARD_JSON.write_text(json.dumps(card, indent=2), encoding="utf-8")
        CARD_MD.write_text(md, encoding="utf-8")
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "bio_report_card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    card["paths"] = {"json": str(CARD_JSON), "md": str(CARD_MD)}
    card["markdown"] = md
    return card


def _to_markdown(card: Dict[str, Any]) -> str:
    ac = card["allen_comparison"]
    g = card["gaps"]
    lines = [
        "# FSOT-2.1-Neural bio report card",
        "",
        f"Generated: `{card['generated_at']}`  ",
        f"Mode: **{card['primary_mode']}** · units={card['n_units']} · steps={card['steps']} · device={card['device']}",
        "",
        f"**Pass (operational):** {'YES' if card.get('pass_operational') else 'NO'}  ",
        f"**Pass (strict all-gaps):** {'YES' if card.get('pass_strict') else 'NO'}",
        "",
        "## Allen comparison (evoked)",
        "",
        "| Metric | Sim | Allen | Rel error |",
        "|--------|-----|-------|-----------|",
        f"| Mean ISI (ms) | {_fmt(ac.get('isi_ms_sim'))} | {_fmt(ac.get('isi_ms_allen'))} | {_pct(ac.get('isi_rel_error'))} |",
        f"| Adaptation index | {_fmt(ac.get('adapt_sim'))} | {_fmt(ac.get('adapt_allen'))} | {_pct(ac.get('adapt_rel_error'))} |",
        f"| Evoked rate (Hz) | {_fmt(ac.get('rate_evoked_Hz'))} | — | — |",
        "",
        f"Gaps closed: **{g.get('closed')}/{g.get('total')}**",
        "",
        "## Band pass rates",
        "",
        f"- Evoked: {card['bands'].get('evoked_pass')}",
        f"- Spontaneous: {card['bands'].get('spontaneous_pass')}",
        f"- Rest: {card['bands'].get('rest_pass')}",
        "",
        f"_{card['honesty']}_",
        "",
    ]
    return "\n".join(lines)


def _fmt(x: Any) -> str:
    try:
        return f"{float(x):.4f}"
    except (TypeError, ValueError):
        return "—"


def _pct(x: Any) -> str:
    try:
        return f"{100.0 * float(x):.2f}%"
    except (TypeError, ValueError):
        return "—"
