#!/usr/bin/env python3
"""Connect / verify FSOT-2.1-Neural against I:\\FSOT-Physical-Archive."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="Pin neuron substrate to FSOT physical archive")
    ap.add_argument(
        "--archive",
        default=os.environ.get("FSOT_PHYSICAL_ARCHIVE", r"I:\FSOT-Physical-Archive"),
        help="Physical archive root",
    )
    ap.add_argument("--json", action="store_true", help="Print full pin JSON")
    ap.add_argument("--apply-env", action="store_true", help="Export FSOT_* env in this process")
    ap.add_argument("--strict", action="store_true", help="Exit 2 if compute hash drifts")
    args = ap.parse_args()

    os.environ["FSOT_PHYSICAL_ARCHIVE"] = str(Path(args.archive))
    from fsot_nuron.archive_pin import ensure_env_hint, pin_archive

    if args.apply_env:
        for k, v in ensure_env_hint().items():
            os.environ[k] = v
            print(f"export {k}={v}")

    pin = pin_archive(write_snapshot=True)
    d = pin.to_dict()

    print("=== FSOT-2.1-Neural ↔ Archive pin ===")
    print(f"connected:                 {pin.connected}")
    print(f"archive_root:              {pin.archive_root}")
    print(f"lean_hub:                  {pin.lean_hub}")
    print(f"manifest_ok:               {pin.manifest_ok}")
    print(f"seed_match_ok:             {pin.seed_match_ok} (max_rel_err={pin.seed_max_rel_err:.3e})")
    print(f"lean_build_ok:             {pin.lean_build_ok}")
    print(f"sorry_count_formal:        {pin.sorry_count_formal}")
    print(f"n_proved_claims:           {pin.n_proved_claims} {pin.claim_status_counts}")
    print(f"cross_proof_overall_ok:    {pin.cross_proof_overall_ok}")
    print(f"seven_way_bare_metal:      {pin.seven_way_bare_metal}")
    print(f"eight_way_hardware:        {pin.eight_way_hardware}")
    print(f"compute_sha256:            {(pin.compute_sha256 or '')[:16]}…")
    print(f"cert_authority_sha256:     {(pin.cert_authority_sha256 or '')[:16]}…")
    print(f"compute_matches_cert:      {pin.compute_matches_certificate}")
    if pin.compute_matches_disk_note:
        print(f"note: {pin.compute_matches_disk_note}")
    print(f"snapshot:                  {pin.snapshot_written}")
    print(f"theory:                    {pin.github_theory}")
    for n in pin.notes:
        print(f"  · {n}")

    if args.json:
        print(json.dumps(d, indent=2))

    if not pin.seed_match_ok:
        return 1
    if args.strict and pin.compute_matches_certificate is False:
        return 2
    if pin.archive_root and not pin.connected:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
