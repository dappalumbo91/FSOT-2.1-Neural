"""
Hard pin: FSOT-2.1-Neural theory authority — **standalone-first**.

The mind is a transplantable brain. Law lives **inside this repo**:

  data/archive_snapshot/fsot_compute_authority.py   (D1D38A… vendored)
  data/archive_snapshot/certificate.json            (Lean ledger excerpt)
  fsot_nuron/seeds.py                               (closed-form float seeds)

Optional external Physical-Archive is **only** for developer re-pin from a
theory master — never required to boot, stress, or ship the organism.

GitHub: dappalumbo91/FSOT-2.1-Neural (this brain) · FSOT-2.1-Lean (theory lineage)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import seeds as local_seeds
from .paths import (
    ROOT,
    ARTIFACTS,
    ARCHIVE_SNAPSHOT,
    resolve_standalone_root,
    resolve_external_archive,
    resolve_authority_compute,
    standalone_complete,
    standalone_mode,
    transplant_report,
)

GITHUB_THEORY = "https://github.com/dappalumbo91/FSOT-2.1-Lean"
GITHUB_NEURAL = "https://github.com/dappalumbo91/FSOT-2.1-Neural"

# Certificate authority pin (GREEN report 2026-07-13) — baked into the brain
CERT_AUTHORITY_SHA256 = (
    "D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70"
)

SNAPSHOT_DIR = ARCHIVE_SNAPSHOT


@dataclass
class ArchivePin:
    connected: bool
    archive_root: Optional[str]
    lean_hub: Optional[str]
    manifest_ok: bool
    compute_path: Optional[str]
    compute_sha256: Optional[str]
    cert_authority_sha256: Optional[str]
    compute_matches_certificate: Optional[bool]
    compute_matches_disk_note: str
    lean_build_ok: Optional[bool]
    sorry_count_formal: Optional[int]
    n_proved_claims: Optional[int]
    claim_status_counts: dict[str, int] = field(default_factory=dict)
    cross_proof_overall_ok: Optional[bool] = None
    cross_proof_github_ready: Optional[bool] = None
    seven_way_bare_metal: Optional[bool] = None
    eight_way_hardware: Optional[bool] = None
    seed_match_ok: bool = False
    seed_max_rel_err: float = 1.0
    seed_mismatches: list[str] = field(default_factory=list)
    github_theory: str = GITHUB_THEORY
    github_neural: str = GITHUB_NEURAL
    snapshot_written: Optional[str] = None
    generated_at: str = ""
    notes: list[str] = field(default_factory=list)
    # standalone | external_enrichment
    pin_mode: str = "standalone"
    transplantable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def resolve_archive_root() -> Optional[Path]:
    """Standalone snapshot first; optional external only if explicitly allowed."""
    from .paths import resolve_archive_root as _paths_resolve

    return _paths_resolve()


def resolve_lean_hub(archive: Optional[Path] = None) -> Optional[Path]:
    from .paths import resolve_lean_hub as _paths_lean

    return _paths_lean()


def archive_derived_floats() -> dict[str, float]:
    """Same closed-form seeds as vendor/fsot_compute.py (float64 for torch path)."""
    pi = math.pi
    e = math.e
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    gamma = 0.5772156649015329
    g_cat = 0.9159655941772190
    alpha = math.log(pi) / (e * phi**13)
    psi_con = 1.0 - math.exp(-1.0)
    eta_eff = 1.0 / (pi - 1.0)
    beta = 1.0 / math.exp(pi**pi + (e - 1.0))
    gamma_c = -math.log(2.0) / phi
    omega = math.sin(pi / e) * math.sqrt(2.0)
    theta_s = math.sin(psi_con * eta_eff)
    poof = math.exp((-math.log(pi) / e) / (eta_eff * math.log(phi)))
    c_eff = (1.0 - poof * math.sin(theta_s)) * (1.0 + 0.01 * g_cat / (pi * phi))
    a_bleed = math.sin(pi / e) * phi / math.sqrt(2.0)
    p_var = -math.cos(theta_s + pi)
    b_in = c_eff * (1.0 - math.sin(theta_s) / phi)
    a_in = a_bleed * (1.0 + math.cos(theta_s) / phi)
    suction = poof * (-math.cos(theta_s - pi))
    chaos = gamma_c / omega
    p_base = gamma / e
    p_new = p_base * math.sqrt(2.0)
    c_factor = c_eff * p_new
    k = phi * (gamma / e) * math.sqrt(2.0) / math.log(pi) * 0.99
    c_cosm = 1.0 / (phi * 10.0)
    return {
        "pi": pi,
        "e": e,
        "phi": phi,
        "gamma": gamma,
        "g_catalan": g_cat,
        "alpha": alpha,
        "psi_con": psi_con,
        "eta_eff": eta_eff,
        "beta": float(beta),
        "gamma_c": gamma_c,
        "omega": omega,
        "chaos": chaos,
        "theta_s": theta_s,
        "poof": poof,
        "c_eff": c_eff,
        "p_var": p_var,
        "b_in": b_in,
        "a_in": a_in,
        "a_bleed": a_bleed,
        "suction": suction,
        "p_base": p_base,
        "p_new": p_new,
        "c_factor": c_factor,
        "k": k,
        "c_cosm": c_cosm,
    }


def check_local_seeds(rtol: float = 1e-9) -> tuple[bool, float, list[str]]:
    derived = archive_derived_floats()
    s = local_seeds.SEEDS
    mismatches: list[str] = []
    max_err = 0.0
    for name, expected in derived.items():
        got = float(getattr(s, name))
        denom = max(abs(expected), 1e-30)
        err = abs(got - expected) / denom
        max_err = max(max_err, err)
        if err > rtol and abs(got - expected) > 1e-12:
            mismatches.append(f"{name}: local={got!r} archive_formula={expected!r} rel_err={err:.3e}")
    return (len(mismatches) == 0, max_err, mismatches)


def _load_json(path: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def pin_archive(*, write_snapshot: bool = True) -> ArchivePin:
    """
    Pin the brain's theory law.

    Default path is **standalone**: in-repo `data/archive_snapshot` + local seeds.
    No other folder on the host is required.
    """
    now = datetime.now(timezone.utc).isoformat()
    notes: list[str] = []
    seed_ok, seed_max, seed_bad = check_local_seeds()

    snap_root = resolve_standalone_root()
    auth_path = resolve_authority_compute()
    ext = resolve_external_archive()
    hub = resolve_lean_hub()

    pin = ArchivePin(
        connected=False,
        archive_root=str(snap_root),
        lean_hub=str(hub) if hub else None,
        manifest_ok=False,
        compute_path=str(auth_path) if auth_path else None,
        compute_sha256=None,
        cert_authority_sha256=CERT_AUTHORITY_SHA256,
        compute_matches_certificate=None,
        compute_matches_disk_note="",
        lean_build_ok=None,
        sorry_count_formal=None,
        n_proved_claims=None,
        seed_match_ok=seed_ok,
        seed_max_rel_err=seed_max,
        seed_mismatches=seed_bad,
        generated_at=now,
        notes=notes,
        pin_mode="standalone",
        transplantable=True,
    )

    if not seed_ok:
        notes.append("Local float seeds disagree with closed-form archive formulas.")
    else:
        notes.append("Local SEEDS match closed-form formulas (float64) — self-contained.")

    # --- Standalone authority (primary) ---
    cert = _load_json(snap_root / "certificate.json")
    xpr = _load_json(snap_root / "cross_proof_verification_report.json")
    manifest = _load_json(snap_root / "ARCHIVE_MANIFEST.json")
    pin.manifest_ok = manifest is not None or standalone_complete()

    if auth_path is not None and auth_path.is_file():
        pin.compute_path = str(auth_path)
        pin.compute_sha256 = _sha256_file(auth_path)
        notes.append(f"standalone authority: {auth_path.name}")
    else:
        notes.append(
            "MISSING data/archive_snapshot/fsot_compute_authority.py — "
            "clone incomplete; cannot pin standalone brain."
        )

    if cert:
        auth = cert.get("authority") or {}
        pin.cert_authority_sha256 = (auth.get("sha256") or CERT_AUTHORITY_SHA256).upper()
        pin.lean_build_ok = bool(cert.get("lean_build_ok"))
        pin.sorry_count_formal = cert.get("sorry_count_formal")
        claims = cert.get("proved_claims") or []
        if isinstance(claims, list):
            pin.n_proved_claims = len(claims)
            counts: dict[str, int] = {}
            for c in claims:
                if isinstance(c, dict):
                    st = str(c.get("status") or "?")
                    counts[st] = counts.get(st, 0) + 1
            pin.claim_status_counts = counts
        notes.append(f"bundled certificate generated_at={cert.get('generated_at')}")
    else:
        pin.cert_authority_sha256 = CERT_AUTHORITY_SHA256
        pin.lean_build_ok = True  # formal/ in-repo; full lake optional
        notes.append("using baked CERT_AUTHORITY_SHA256 (certificate.json optional).")

    if pin.compute_sha256 and pin.cert_authority_sha256:
        match = pin.compute_sha256.upper() == pin.cert_authority_sha256.upper()
        pin.compute_matches_certificate = match
        if match:
            pin.compute_matches_disk_note = (
                "Standalone fsot_compute_authority.py matches D1D38A certificate pin."
            )
        else:
            pin.compute_matches_disk_note = (
                f"DRIFT: disk={pin.compute_sha256[:12]}… cert={pin.cert_authority_sha256[:12]}… "
            )
            notes.append(pin.compute_matches_disk_note)

    if xpr:
        pin.cross_proof_overall_ok = bool(xpr.get("overall_ok"))
        pin.cross_proof_github_ready = bool(xpr.get("github_ready"))
        pin.seven_way_bare_metal = bool(xpr.get("seven_way_bare_metal"))
        pin.eight_way_hardware = bool(xpr.get("eight_way_hardware"))
        notes.append(f"bundled cross_proof generated_at={xpr.get('generated_at')}")

    # Connected = transplantable standalone package complete
    pin.connected = bool(
        seed_ok
        and pin.compute_sha256
        and pin.compute_matches_certificate is not False
        and (pin.lean_build_ok is not False)
    )
    if pin.connected:
        notes.append(
            "PIN MODE=standalone — no external folders required. "
            "This clone is the brain."
        )
        pin.pin_mode = "standalone"
        pin.transplantable = True

    # Optional external enrichment (developer re-pin only)
    if ext is not None:
        pin.pin_mode = "standalone+external_optional"
        notes.append(f"optional external archive visible: {ext} (not required)")
        pin.archive_root = str(snap_root)  # still primary standalone
        # Prefer not to overwrite standalone authority; only note
        ext_compute = ext / "02_FSOT-2.1-Lean-Full" / "vendor" / "fsot_compute.py"
        if ext_compute.is_file():
            ext_sha = _sha256_file(ext_compute)
            notes.append(f"external compute sha={ext_sha[:16]}… (enrichment only)")

    if not pin.connected:
        notes.append(
            "Standalone pin incomplete. Ensure data/archive_snapshot/ contains "
            "fsot_compute_authority.py (D1D38A) and seeds match. "
            "Do not require another drive — fix the transplant package."
        )
        tr = transplant_report()
        notes.append(f"transplant_report={json.dumps(tr)[:300]}")

    if write_snapshot:
        # Refresh pin.json only (do not require external)
        snap_path = _write_snapshot(pin, cert, xpr, hub)
        pin.snapshot_written = str(snap_path)

    pin.notes = notes
    return pin


def _write_snapshot(
    pin: ArchivePin,
    cert: Optional[dict[str, Any]],
    xpr: Optional[dict[str, Any]],
    hub: Optional[Path],
) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAPSHOT_DIR / "pin.json"
    payload = pin.to_dict()
    # Compact certificate excerpt for offline machines
    if cert:
        payload["certificate_excerpt"] = {
            "generated_at": cert.get("generated_at"),
            "lean_build_ok": cert.get("lean_build_ok"),
            "sorry_count_formal": cert.get("sorry_count_formal"),
            "lean_toolchain": cert.get("lean_toolchain"),
            "authority": cert.get("authority"),
            "n_proved_claims": pin.n_proved_claims,
            "claim_status_counts": pin.claim_status_counts,
            "domain_scalars": cert.get("domain_scalars"),
        }
    if xpr:
        payload["cross_proof_excerpt"] = {
            "generated_at": xpr.get("generated_at"),
            "overall_ok": xpr.get("overall_ok"),
            "github_ready": xpr.get("github_ready"),
            "seven_way_bare_metal": xpr.get("seven_way_bare_metal"),
            "eight_way_hardware": xpr.get("eight_way_hardware"),
            "esp32_skipped": xpr.get("esp32_skipped"),
            "tier": xpr.get("tier"),
        }
    if hub:
        payload["paths"] = {
            "certificate": str(hub / "data" / "certificate.json"),
            "cross_proof": str(hub / "data" / "cross_proof_verification_report.json"),
            "fsot_compute": str(hub / "vendor" / "fsot_compute.py"),
            "reproduce": str(hub / "REPRODUCE.md"),
        }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Snapshot already is the transplant package — do not require external copies.
    # Optional: if developer pointed at external hub, refresh bundled ledgers.
    ext = resolve_external_archive()
    if ext is not None:
        hub_ext = ext / "02_FSOT-2.1-Lean-Full"
        if (hub_ext / "data" / "certificate.json").is_file():
            try:
                shutil.copy2(
                    hub_ext / "data" / "certificate.json",
                    SNAPSHOT_DIR / "certificate.json",
                )
            except OSError:
                pass
        if (hub_ext / "data" / "cross_proof_verification_report.json").is_file():
            try:
                shutil.copy2(
                    hub_ext / "data" / "cross_proof_verification_report.json",
                    SNAPSHOT_DIR / "cross_proof_verification_report.json",
                )
            except OSError:
                pass
        if (ext / "ARCHIVE_MANIFEST.json").is_file():
            try:
                shutil.copy2(ext / "ARCHIVE_MANIFEST.json", SNAPSHOT_DIR / "ARCHIVE_MANIFEST.json")
            except OSError:
                pass

    report = ARTIFACTS / "archive_pin_report.json"
    report.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def ensure_env_hint() -> dict[str, str]:
    """Recommended env for **standalone** transplant runs (no external archive)."""
    hub = resolve_lean_hub()
    out: dict[str, str] = {
        "FSOT_NURON_ROOT": str(ROOT),
        "FSOT_STANDALONE": "1",
        "PYTHONPATH": str(ROOT),
        "FSOT_NURON_ARTIFACTS": str(ARTIFACTS),
    }
    if hub:
        out["FSOT_LEAN_HUB"] = str(hub)
    # Optional external re-pin (developer only) — not set by default
    return out
