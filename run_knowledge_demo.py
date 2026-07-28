#!/usr/bin/env python3
"""
Demo: AV symbols + optional speech→text → local knowledge → machine/trinary → English.

  python run_knowledge_demo.py
  python run_knowledge_demo.py --stt   # local faster-whisper if installed
  python run_knowledge_demo.py --path "G:\\showes\\Adventure Time.Complete\\01.01 - Slumber Party Panic.mp4"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--path",
        default=r"G:\showes\Adventure Time.Complete\01.01 - Slumber Party Panic.mp4",
    )
    ap.add_argument("--stt", action="store_true", help="run local speech→text")
    ap.add_argument("--moments", type=int, default=10)
    ap.add_argument("--online", action="store_true", help="FSOT_KNOWLEDGE_ONLINE=1 wiki snippets")
    args = ap.parse_args()

    if args.online:
        os.environ["FSOT_KNOWLEDGE_ONLINE"] = "1"

    from fsot_nuron.sensory.cross_modal import (
        iter_audiovisual_moments,
        cross_modal_association,
    )
    from fsot_nuron.sensory.media_meta import extract_media_metadata
    from fsot_nuron.knowledge.cross_feed import cross_feed_episode
    from fsot_nuron.knowledge.speech_text import transcribe_audio_file
    from fsot_nuron.paths import ARTIFACTS
    from fsot_nuron.machine_encode import text_to_utf8_trits

    path = Path(args.path)
    print("=== FSOT knowledge cross-feed demo ===")
    print(f"path exists={path.is_file()}  {path}")
    if not path.is_file():
        print("Provide a real media path. Exiting.")
        return 1

    meta = extract_media_metadata(path)
    print(f"title={meta.title!r} kind={meta.kind} tags={meta.tags}")

    moments = list(
        iter_audiovisual_moments(path, max_moments=args.moments, frame_stride=48)
    )
    av = cross_modal_association(moments)
    print(
        f"AV: moments={av.get('n_moments')} soundtrack={av.get('has_soundtrack')} "
        f"bind={av.get('mean_bind')} speech_band={av.get('mean_speech_band')}"
    )

    symbols = []
    for c in av.get("clusters") or []:
        for s in c.get("top_symbols") or []:
            if isinstance(s, dict):
                symbols.append(s.get("symbol"))
    for s in av.get("cross_modal_symbols") or []:
        if isinstance(s, dict):
            symbols.append(s.get("symbol"))
    symbols = [s for s in symbols if s]
    print(f"stream symbols: {symbols[:12]}")

    transcript = ""
    if args.stt:
        print("STT (local faster-whisper)…")
        stt = transcribe_audio_file(path, max_s=35.0)
        print(f"  backend={stt.backend} ok={stt.ok}")
        if stt.ok:
            transcript = stt.text
            print(f"  text: {transcript[:300]}")
        else:
            print(f"  notes: {stt.notes}")

    cf = cross_feed_episode(
        symbols=symbols,
        title=meta.title,
        transcript=transcript,
        path_hint=str(path),
        sensory_notes=(
            f"AV co-stream bind={av.get('mean_bind')}; "
            f"speech_band={av.get('mean_speech_band')}; motion={av.get('mean_motion')}."
        ),
    )
    print("\n--- plain English (regurgitated understanding) ---\n")
    print(cf.plain_english)
    print("\n--- machine body language ---")
    print(f"n_trits={cf.n_trits}  S_couple={cf.S_couple}  packets={len(cf.packets)}")
    if cf.teach_bundle:
        head = cf.teach_bundle[:120]
        tr = text_to_utf8_trits(head)
        print(f"trit head (first 24): {tr[:24]}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "path": str(path),
        "meta": meta.to_dict(),
        "av": av,
        "symbols": symbols,
        "transcript": transcript,
        "cross_feed": cf.to_dict(),
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    p = ARTIFACTS / "knowledge_crossfeed_demo.json"
    # packets can be large — trim
    slim = dict(out)
    slim["cross_feed"] = dict(cf.to_dict())
    slim["cross_feed"]["packets"] = slim["cross_feed"].get("packets", [])[:4]
    p.write_text(json.dumps(slim, indent=2), encoding="utf-8")
    print(f"\nWrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
