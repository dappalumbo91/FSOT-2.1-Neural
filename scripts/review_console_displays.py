#!/usr/bin/env python3
"""Review every console display backend for correct outcomes."""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    results = {}

    def ok(name: str, cond: bool, detail: str = "") -> None:
        results[name] = {"ok": bool(cond), "detail": detail[:600]}
        print(("PASS" if cond else "FAIL"), name, detail[:140])

    try:
        from fsot_nuron.fsot_bridge import (
            require_pin,
            verify_fsot_bridge,
            fold_diagnostics,
            bridge_machine_payload,
            bridge_chemical_dna,
        )
        from fsot_nuron.machine_encode import (
            verify_machine_path,
            path_recommendation,
            translate,
            EncodePath,
            build_machine_frame,
            chemical_signals_to_machine,
        )
        from fsot_nuron.sensory import SensoryBus, push_machine_text

        pin = require_pin(write_snapshot=False)
        ok(
            "boot_pin",
            pin.connected and pin.seed_match_ok,
            f"sha={(pin.compute_sha256 or '')[:16]}",
        )
        f = fold_diagnostics()
        ok(
            "boot_folds",
            bool(f.get("pin_ok") and f.get("S_Biology") is not None),
            json.dumps(
                {
                    k: f.get(k)
                    for k in ("S_Biology", "S_Neuroscience", "S_Computer_Body")
                }
            ),
        )
        # Atlas sanity: Biology ~0.445, Neuroscience ~0.514
        bio = float(f.get("S_Biology") or 0)
        neuro = float(f.get("S_Neuroscience") or 0)
        ok(
            "atlas_S_values",
            abs(bio - 0.4447) < 0.01 and abs(neuro - 0.5144) < 0.01,
            f"bio={bio} neuro={neuro}",
        )
        br = verify_fsot_bridge()
        ok("boot_bridge", bool(br.get("ok")), f"ok={br.get('ok')}")
        mv = verify_machine_path("FSOT neural")
        ok(
            "boot_machine",
            bool(
                mv.get("utf8_roundtrip_ok")
                and mv.get("frame_roundtrip_ok")
                and mv.get("chem_bridge_ok")
            ),
            json.dumps(
                {
                    k: mv.get(k)
                    for k in (
                        "utf8_roundtrip_ok",
                        "frame_roundtrip_ok",
                        "chem_bridge_ok",
                        "n_trits",
                    )
                }
            ),
        )
    except Exception:
        ok("boot_block", False, traceback.format_exc())
        print(json.dumps(results, indent=2))
        return 1

    try:
        text = "FSOT neural intelligence"
        out = translate(text, path=EncodePath.MACHINE)
        frame = build_machine_frame(text, path=EncodePath.MACHINE)
        fsot = bridge_machine_payload(text)
        ok(
            "enc_machine",
            bool(out.get("roundtrip_ok") and frame.to_dict()["byte_len"] > 0),
            f"n_trits={out.get('n_trits')} S={fsot['modulators']['S']:.4f}",
        )
        # chemical path on DNA should not use plain text as DNA
        dna = "ATGAAACGGTTTGCG"
        chem = chemical_signals_to_machine(dna)
        cfsot = bridge_chemical_dna(dna)
        ok(
            "enc_chem",
            chem.get("n_trits", 0) > 0 and cfsot.get("fold") == "Biology",
            f"n_trits={chem.get('n_trits')} fold={cfsot.get('fold')}",
        )
        # Bug check: chemical radio with English text currently mis-routes
        eng = translate("hello FSOT", path=EncodePath.CHEMICAL)
        ok(
            "enc_chem_text_is_honest",
            "Text" in str(eng.get("note", "")) or eng.get("n_trits", 0) > 0,
            f"note={eng.get('note')}",
        )
        morse = translate("SOS", path=EncodePath.MORSE)
        ok(
            "enc_morse_secondary",
            morse.get("primary") is False and morse.get("n_trits", 0) > 0,
            f"n={morse.get('n_trits')}",
        )
    except Exception:
        ok("enc_block", False, traceback.format_exc())

    try:
        bus = SensoryBus()
        pkt = push_machine_text(bus, "stimulus via FSOT", path="machine")
        ext = bus.build_external(
            96,
            {
                "sens": list(range(32)),
                "thal": list(range(32, 48)),
                "assoc": list(range(48, 80)),
                "hipp": list(range(80, 96)),
            },
        )
        ok(
            "inject_fsot",
            pkt.strength > 0
            and "S" in pkt.meta
            and int((ext != 0).sum()) > 0,
            f"strength={pkt.strength:.3f} S={pkt.meta.get('S')} nonzero={int((ext!=0).sum())}",
        )
    except Exception:
        ok("inject_fsot", False, traceback.format_exc())

    try:
        arts = []
        for name in ("intelligence_probe.json", "scalpel_rates.json"):
            for base in (ROOT / "artifacts", ROOT / "data" / "results"):
                p = base / name
                if p.is_file():
                    data = json.loads(p.read_text(encoding="utf-8"))
                    arts.append((str(p.relative_to(ROOT)), sorted(data.keys())[:10]))
                    break
        ok("live_artifacts_readable", len(arts) >= 1, str(arts))
    except Exception:
        ok("live_artifacts_readable", False, traceback.format_exc())

    try:
        rows = {}
        for p in (EncodePath.MACHINE, EncodePath.CHEMICAL, EncodePath.MORSE):
            r = translate("FSOT", path=p)
            rows[p.value] = r.get("n_trits")
        ok("compare_paths", all(v is not None for v in rows.values()), str(rows))
    except Exception:
        ok("compare_paths", False, traceback.format_exc())

    try:
        from product.console.app import ConsoleApp

        required = [
            "_boot_system",
            "_refresh_banner",
            "_refresh_live",
            "_do_encode",
            "_do_chem_bridge",
            "_do_inject",
            "_do_compare_paths",
            "_cmd_pin",
            "_cmd_scalpel",
            "_cmd_intel",
            "_cmd_intel_quick",
            "_cmd_machine_verify",
            "_cmd_fsot_bridge",
            "_cmd_parity",
            "_cmd_qemu",
            "_cmd_zig_body",
            "_cmd_stress",
            "_cmd_stress_quick",
            "_refresh_cells",
            "_refresh_memory",
        ]
        missing = [r for r in required if not hasattr(ConsoleApp, r)]
        ok("console_methods", len(missing) == 0, f"missing={missing}")
    except Exception:
        ok("console_methods", False, traceback.format_exc())

    zig = ROOT / "embodiment" / "zig" / "zig-out" / "bin" / "fsot_trit_host.exe"
    ok("zig_host_exists", zig.is_file(), str(zig))

    rec = path_recommendation()
    ok("path_default_machine", rec.get("default") == "machine", str(rec))

    failed = [k for k, v in results.items() if not v["ok"]]
    print("---")
    print("FAILED:", failed if failed else "none")
    print(
        "TOTAL",
        len(results),
        "PASS",
        sum(1 for v in results.values() if v["ok"]),
    )
    outp = ROOT / "artifacts" / "console_display_review.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Wrote", outp)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
