#!/usr/bin/env python3
"""
Machine encoding smoke — primary OS-native body path (not Morse).

Examples:
  python run_machine_encode.py
  python run_machine_encode.py --text "hello body" --path machine
  python run_machine_encode.py --dna ATGAAACGG --path chemical
  python run_machine_encode.py --verify
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="FSOT machine encoding (primary body I/O)")
    ap.add_argument("--text", default="FSOT neural intelligence")
    ap.add_argument("--dna", default="", help="DNA string for chemical→machine bridge")
    ap.add_argument(
        "--path",
        default="machine",
        choices=["machine", "chemical", "morse"],
        help="machine = OS-native (default); morse = secondary demo only",
    )
    ap.add_argument("--verify", action="store_true", help="run ABI / roundtrip checks")
    ap.add_argument("--inject-demo", action="store_true", help="encode → SensoryBus demo")
    args = ap.parse_args()

    from fsot_nuron.machine_encode import (
        EncodePath,
        translate,
        path_recommendation,
        build_machine_frame,
        chemical_signals_to_machine,
        verify_machine_path,
        encode_to_sensory_packet,
    )

    print("=== FSOT machine encoding ===")
    print("Primary body path: MACHINE (UTF-8 / bytes / T1 packs → OS words)")
    print("Secondary: Morse (human telegraphy demos only)")
    print(json.dumps(path_recommendation(), indent=2))
    print()

    if args.verify:
        rep = verify_machine_path(args.text)
        print("--- verify ---")
        print(json.dumps(rep, indent=2))
        ok = (
            rep.get("frame_roundtrip_ok")
            and rep.get("chem_bridge_ok")
            and rep.get("utf8_roundtrip_ok")
            and rep.get("bytes_roundtrip_ok")
            and rep.get("n_trits", 0) > 0
        )
        print(f"\nverify_ok: {ok}")
        if not ok:
            return 1

    if args.dna:
        chem = chemical_signals_to_machine(args.dna)
        print("--- chemical → machine bridge ---")
        print(json.dumps({k: chem[k] for k in chem if k != "words"}, indent=2)[:4000])
        print(f"words[0:3]: {chem['words'][:3]}")
    else:
        path = EncodePath(args.path)
        out = translate(args.text, path=path)
        frame = build_machine_frame(args.text, path=path)
        print(f"--- translate path={path.value} ---")
        slim = {k: out[k] for k in out if k not in ("words", "trits")}
        slim["trits_head"] = out.get("trits", [])[:24]
        slim["n_words"] = len(out.get("words") or [])
        slim["frame"] = frame.to_dict()
        print(json.dumps(slim, indent=2)[:6000])

    if args.inject_demo:
        from fsot_nuron.sensory import SensoryBus, push_machine_text

        bus = SensoryBus()
        pkt = push_machine_text(bus, args.text, path=args.path)
        region_index = {"sens": list(range(16)), "thal": list(range(16, 24))}
        ext = bus.build_external(24, region_index)
        print("\n--- sensory inject demo ---")
        print(f"packet modality={pkt.modality.value} region={pkt.target_region}")
        print(f"features head={pkt.features[:12]}")
        print(f"external drive nonzero={int((ext != 0).sum())} / {ext.numel()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
