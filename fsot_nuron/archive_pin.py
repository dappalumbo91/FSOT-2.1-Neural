"""
Hard pin: FSOT-2.1-Neural ↔ physical archive / theory hub.

The neuron substrate is not a free-floating experiment. Authority lives at:

  I:/FSOT-Physical-Archive          (master, when present)
  02_FSOT-2.1-Lean-Full             (canonical Lean + vendor/fsot_compute)
  GitHub dappalumbo91/FSOT-2.1-Lean (public theory)

This module resolves those roots, hashes the compute authority, reads the
certificate / cross-proof ledgers when available, and checks that local
float seeds match archive-derived constants.
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
from .paths import ROOT, ARTIFACTS

GITHUB_THEORY = "https://github.com/dappalumbo91/FSOT-2.1-Lean"
GITHUB_NEURAL = "https://github.com/dappalumbo91/FSOT-2.1-Neural"

# Certificate authority pin (GREEN report 2026-07-13)
CERT_AUTHORITY_SHA256 = (
    "D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70"
)

ARCHIVE_CANDIDATES = [
    Path(os.environ["FSOT_PHYSICAL_ARCHIVE"])
    if os.environ.get("FSOT_PHYSICAL_ARCHIVE")
    else None,
    Path(os.environ["FSOT_ARCHIVE_ROOT"])
    if os.environ.get("FSOT_ARCHIVE_ROOT")
    else None,
    Path(r"I:\FSOT-Physical-Archive"),
    Path(r"I:/FSOT-Physical-Archive"),
]

SNAPSHOT_DIR = ROOT / "data" / "archive_snapshot"


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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def resolve_archive_root() -> Optional[Path]:
    for p in ARCHIVE_CANDIDATES:
        if p is None:
            continue
        try:
            rp = p.resolve()
        except OSError:
            continue
        if rp.is_dir() and (rp / "ARCHIVE_MANIFEST.json").is_file():
            return rp
        if rp.is_dir() and (rp / "02_FSOT-2.1-Lean-Full").is_dir():
            return rp
    return None


def resolve_lean_hub(archive: Optional[Path] = None) -> Optional[Path]:
    env = os.environ.get("FSOT_LEAN_HUB") or os.environ.get("FSOT_CANONICAL_LEAN_HUB")
    if env:
        p = Path(env)
        if p.is_dir():
            return p.resolve()
    arch = archive or resolve_archive_root()
    if arch is None:
        return None
    hub = arch / "02_FSOT-2.1-Lean-Full"
    return hub if hub.is_dir() else None


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
    p_new = (gamma / e) * math.sqrt(2.0)
    c_factor = c_eff * p_new
    k = phi * (gamma / e) * math.sqrt(2.0) / math.log(pi) * 0.99
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
        "chaos": chaos,
        "theta_s": theta_s,
        "poof": poof,
        "c_eff": c_eff,
        "p_var": p_var,
        "b_in": b_in,
        "a_in": a_in,
        "a_bleed": a_bleed,
        "suction": suction,
        "p_new": p_new,
        "c_factor": c_factor,
        "k": k,
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
    now = datetime.now(timezone.utc).isoformat()
    notes: list[str] = []
    archive = resolve_archive_root()
    hub = resolve_lean_hub(archive)

    seed_ok, seed_max, seed_bad = check_local_seeds()

    pin = ArchivePin(
        connected=False,
        archive_root=str(archive) if archive else None,
        lean_hub=str(hub) if hub else None,
        manifest_ok=False,
        compute_path=None,
        compute_sha256=None,
        cert_authority_sha256=None,
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
    )

    if not seed_ok:
        notes.append("Local float seeds disagree with archive closed-form formulas.")
    else:
        notes.append("Local SEEDS match archive closed-form (float64).")

    if archive is None:
        notes.append(
            "Physical archive not found. Set FSOT_PHYSICAL_ARCHIVE or install "
            "I:\\FSOT-Physical-Archive. Seeds still self-check against formulas."
        )
        # Offline snapshot may still exist
        snap = SNAPSHOT_DIR / "pin.json"
        if snap.is_file():
            prev = _load_json(snap)
            if prev:
                notes.append(f"Using last local snapshot at {snap}")
                pin.cert_authority_sha256 = prev.get("cert_authority_sha256")
                pin.lean_build_ok = prev.get("lean_build_ok")
                pin.n_proved_claims = prev.get("n_proved_claims")
                pin.cross_proof_overall_ok = prev.get("cross_proof_overall_ok")
        pin.notes = notes
        return pin

    manifest_path = archive / "ARCHIVE_MANIFEST.json"
    manifest = _load_json(manifest_path) if manifest_path.is_file() else None
    pin.manifest_ok = manifest is not None
    if manifest:
        canon = manifest.get("canonical_lean_hub")
        if canon:
            notes.append(f"manifest.canonical_lean_hub={canon}")
        policy = manifest.get("canonical_policy")
        if policy:
            notes.append(str(policy)[:200])

    if hub is None:
        notes.append("Lean hub 02_FSOT-2.1-Lean-Full missing under archive.")
        pin.notes = notes
        return pin

    compute = hub / "vendor" / "fsot_compute.py"
    if compute.is_file():
        pin.compute_path = str(compute)
        pin.compute_sha256 = _sha256_file(compute)
    else:
        notes.append("vendor/fsot_compute.py missing under Lean hub.")

    cert_path = hub / "data" / "certificate.json"
    cert = _load_json(cert_path) if cert_path.is_file() else None
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
        notes.append(f"certificate generated_at={cert.get('generated_at')}")
    else:
        pin.cert_authority_sha256 = CERT_AUTHORITY_SHA256
        notes.append("certificate.json not found; using baked CERT_AUTHORITY_SHA256.")

    if pin.compute_sha256 and pin.cert_authority_sha256:
        match = pin.compute_sha256 == pin.cert_authority_sha256.upper()
        pin.compute_matches_certificate = match
        if match:
            pin.compute_matches_disk_note = "vendor/fsot_compute.py matches certificate authority hash."
        else:
            pin.compute_matches_disk_note = (
                f"DRIFT: disk={pin.compute_sha256[:12]}… cert={pin.cert_authority_sha256[:12]}… "
                "Re-pin compute or regenerate certificate before claim-sensitive theory runs."
            )
            notes.append(pin.compute_matches_disk_note)

    xp = hub / "data" / "cross_proof_verification_report.json"
    xpr = _load_json(xp) if xp.is_file() else None
    if xpr:
        pin.cross_proof_overall_ok = bool(xpr.get("overall_ok"))
        pin.cross_proof_github_ready = bool(xpr.get("github_ready"))
        pin.seven_way_bare_metal = bool(xpr.get("seven_way_bare_metal"))
        pin.eight_way_hardware = bool(xpr.get("eight_way_hardware"))
        notes.append(f"cross_proof generated_at={xpr.get('generated_at')}")

    # Connected = archive+hub present + seeds match + (cert lean ok if present)
    pin.connected = bool(
        archive
        and hub
        and pin.manifest_ok
        and seed_ok
        and (pin.lean_build_ok is not False)
    )
    if pin.connected and pin.compute_matches_certificate is False:
        notes.append(
            "Archive is linked but compute hash drifts from certificate — "
            "neural substrate still uses closed-form seeds (OK); theory claims need re-pin."
        )

    if write_snapshot:
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

    # Lightweight copies of full ledgers when archive present (for GitHub-free offline pin)
    if hub and (hub / "data" / "certificate.json").is_file():
        try:
            shutil.copy2(
                hub / "data" / "certificate.json",
                SNAPSHOT_DIR / "certificate.json",
            )
        except OSError:
            pass
    if hub and (hub / "data" / "cross_proof_verification_report.json").is_file():
        try:
            shutil.copy2(
                hub / "data" / "cross_proof_verification_report.json",
                SNAPSHOT_DIR / "cross_proof_verification_report.json",
            )
        except OSError:
            pass
    # Manifest excerpt
    arch = resolve_archive_root()
    if arch and (arch / "ARCHIVE_MANIFEST.json").is_file():
        try:
            shutil.copy2(arch / "ARCHIVE_MANIFEST.json", SNAPSHOT_DIR / "ARCHIVE_MANIFEST.json")
        except OSError:
            pass

    report = ARTIFACTS / "archive_pin_report.json"
    report.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def ensure_env_hint() -> dict[str, str]:
    """Return recommended env vars for portable runs with archive present."""
    arch = resolve_archive_root()
    hub = resolve_lean_hub(arch)
    out: dict[str, str] = {
        "FSOT_NURON_ROOT": str(ROOT),
    }
    if arch:
        out["FSOT_PHYSICAL_ARCHIVE"] = str(arch)
        out["FSOT_EXTERNAL_DATA_ROOT"] = str(arch / "03_FSOT-PublicData")
        out["FSOT_ANOMALY_CACHE_ROOT"] = str(
            arch / "03_FSOT-PublicData" / "anomaly_observables"
        )
    if hub:
        out["FSOT_LEAN_HUB"] = str(hub)
        out["FSOT_CANONICAL_LEAN_HUB"] = str(hub)
    return out
