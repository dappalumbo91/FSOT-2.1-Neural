#!/usr/bin/env python3
"""
Watch one media file with subtitle-style dialogue + AV bind + knowledge + memory.

  python run_episode_watch.py --path "G:\\movies\\Brave (2012) [1080p]\\Brave.2012.1080p.BRrip.x264.YIFY.mp4"
  python run_episode_watch.py --path "...mp4" --stt
  python run_episode_watch.py --recall "Brave"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("FSOT_STANDALONE", "1")
os.environ.setdefault("PYTHONPATH", str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="")
    ap.add_argument("--moments", type=int, default=12)
    ap.add_argument("--stt", action="store_true", help="use STT as subtitles if no .srt")
    ap.add_argument("--recall", default="", help="query episode memory in plain English")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    from fsot_nuron.knowledge.episode_memory import (
        list_episodes,
        recall_plain_english,
    )

    if args.list:
        rows = list_episodes()
        print(f"episodes stored: {len(rows)}")
        for r in rows[:20]:
            print(f"  {r.get('episode_id')}: {r.get('title')} [{r.get('caption_source')}]")
        return 0

    if args.recall:
        print(recall_plain_english(args.recall))
        return 0

    path = Path(args.path) if args.path else None
    if path is None or not path.is_file():
        # default: Brave has sidecar srt
        cand = Path(r"G:\movies\Brave (2012) [1080p]\Brave.2012.1080p.BRrip.x264.YIFY.mp4")
        path = cand if cand.is_file() else None
    if path is None or not path.is_file():
        print("Need --path to a media file (with optional .srt sidecar).")
        return 1

    from fsot_nuron.sensory.cross_modal import (
        iter_audiovisual_moments,
        cross_modal_association,
    )
    from fsot_nuron.sensory.media_meta import extract_media_metadata
    from fsot_nuron.knowledge.dialogue_bind import process_episode_with_subtitles
    from fsot_nuron.knowledge.subtitles import find_sidecar_subtitles, load_subtitles
    from fsot_nuron.paths import ARTIFACTS

    print("=== FSOT episode watch (subtitles + AV + knowledge + memory) ===")
    print(f"path: {path}")
    sub = find_sidecar_subtitles(path)
    print(f"sidecar subtitles: {sub}")
    if sub:
        print(f"  cues loaded: {len(load_subtitles(path))}")

    meta = extract_media_metadata(path)
    moments = list(
        iter_audiovisual_moments(path, max_moments=args.moments, frame_stride=36)
    )
    av = cross_modal_association(moments)
    symbols = []
    for c in av.get("clusters") or []:
        for s in c.get("top_symbols") or []:
            if isinstance(s, dict) and s.get("symbol"):
                symbols.append(s["symbol"])
    for s in av.get("cross_modal_symbols") or []:
        if isinstance(s, dict) and s.get("symbol"):
            symbols.append(s["symbol"])
    print(
        f"AV moments={av.get('n_moments')} soundtrack={av.get('has_soundtrack')} "
        f"bind={av.get('mean_bind')} speech_band={av.get('mean_speech_band')}"
    )
    print(f"symbols: {symbols[:12]}")

    rep = process_episode_with_subtitles(
        path,
        moments=moments,
        symbols=symbols,
        title=meta.title,
        prefer_stt=bool(args.stt),
        save_memory=True,
        av_stats=av,
    )
    print(f"\ncaption_source={rep.caption_source} cues={rep.n_cues} "
          f"dialogue_moments={rep.n_moments_with_dialogue}")
    print(f"sample lines: {rep.sample_lines[:5]}")
    print(f"episode_id={rep.episode_id}")
    print(f"memory: {rep.memory_path}")
    print("\n--- plain English ---\n")
    print(rep.plain_english)

    out = ARTIFACTS / "episode_watch_last.json"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    d = rep.to_dict()
    # trim
    d["moment_bindings"] = d.get("moment_bindings", [])[:12]
    if "cross_feed" in d and isinstance(d["cross_feed"], dict):
        d["cross_feed"]["packets"] = (d["cross_feed"].get("packets") or [])[:4]
    out.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    print("\nRecall later: python run_episode_watch.py --recall \"Brave\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
