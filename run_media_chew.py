#!/usr/bin/env python3
"""
Chew optional media libraries as sensory input (vision + audio).

Standalone brain does NOT require media. These roots are *test injectors*
(like eyes/ears on the world), defaulting to:

  G:\\movies  G:\\showes  G:\\Debut

Usage:
  python run_media_chew.py
  python run_media_chew.py --roots "G:\\movies;G:\\showes;G:\\Debut"
  python run_media_chew.py --videos 2 --frames 16 --audio 2
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
    ap = argparse.ArgumentParser(description="FSOT media sensory chew (optional libraries)")
    ap.add_argument(
        "--roots",
        default=os.environ.get("FSOT_MEDIA_ROOTS", r"G:\movies;G:\showes;G:\Debut"),
        help="Media roots separated by ; (optional)",
    )
    ap.add_argument("--videos", type=int, default=2)
    ap.add_argument("--audio", type=int, default=2)
    ap.add_argument("--frames", type=int, default=20)
    ap.add_argument("--stride", type=int, default=24)
    ap.add_argument("--audio-windows", type=int, default=6)
    ap.add_argument("--profile", default="ai_efficient")
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    from fsot_nuron.sensory.media_stream import MediaChewConfig, chew_media, media_roots_from_env
    from fsot_nuron.paths import ARTIFACTS
    from fsot_nuron.archive_pin import pin_archive

    print("=== FSOT media sensory chew ===")
    print("Doctrine: optional world injectors — brain remains standalone without G: drives.")
    pin = pin_archive(write_snapshot=False)
    print(f"pin standalone={pin.connected} mode={getattr(pin, 'pin_mode', '?')} sha={(pin.compute_sha256 or '')[:16]}")

    roots = [p.strip() for p in args.roots.replace(",", ";").split(";") if p.strip()]
    # export for discover
    os.environ["FSOT_MEDIA_ROOTS"] = ";".join(roots)
    found = media_roots_from_env()
    print(f"roots requested: {roots}")
    print(f"roots present:   {[str(p) for p in found]}")

    cfg = MediaChewConfig(
        roots=[str(p) for p in found],
        max_video_files=args.videos,
        max_audio_files=args.audio,
        frames_per_video=args.frames,
        frame_stride=args.stride,
        audio_windows=args.audio_windows,
        profile=args.profile,
        device=args.device,
    )
    rep = chew_media(cfg)
    print("\n--- report ---")
    print(f"ok={rep.ok}")
    print(f"video_files={rep.n_video_files}  vision_packets={rep.n_vision_packets}")
    print(f"audio_files={rep.n_audio_files}  audio_packets={rep.n_audio_packets}")
    print(f"mean_luma={rep.mean_vision_luma:.4f}  mean_motion={rep.mean_motion:.4f}  mean_rms={rep.mean_audio_rms:.4f}")
    print(f"mean_S={rep.mean_S:.4f}  total_spikes={rep.total_spikes}")
    print(f"region |S| proxy: { {k: round(v, 4) for k, v in rep.region_rates.items()} }")
    print(f"sources: {rep.sources}")
    for n in rep.notes[:12]:
        print(f"  note: {n}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "standalone_pin": pin.connected,
        "report": rep.to_dict(),
        "config": {
            "roots": cfg.roots,
            "videos": cfg.max_video_files,
            "audio": cfg.max_audio_files,
            "frames": cfg.frames_per_video,
            "profile": cfg.profile,
        },
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / "media_chew_report.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    md = ROOT / "data" / "results" / "MEDIA_CHEW.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(
        "\n".join(
            [
                "# Media sensory chew",
                "",
                f"Generated: `{out['generated_at']}`",
                "",
                "Optional world injectors (movies / shows / music). Brain boots without them.",
                "",
                f"- Vision packets: **{rep.n_vision_packets}** from {rep.n_video_files} files",
                f"- Audio packets: **{rep.n_audio_packets}** from {rep.n_audio_files} files",
                f"- Mean luma / motion / RMS: **{rep.mean_vision_luma:.3f}** / **{rep.mean_motion:.3f}** / **{rep.mean_audio_rms:.3f}**",
                f"- Brain mean S / spikes: **{rep.mean_S:.3f}** / **{rep.total_spikes}**",
                f"- Region |S|: `{rep.region_rates}`",
                f"- Sources: {', '.join(rep.sources)}",
                "",
                "Decode: luma · RGB · hue hist · 8×8 retinotopic grid · edge · motion · FFT bands.",
                "",
                f"JSON: `{path}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {path}")
    print(f"Wrote {md}")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
