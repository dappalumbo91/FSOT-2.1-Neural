#!/usr/bin/env python3
"""
Boot the standalone brain and let it learn multi-modally with minimal instruction.

  python run_autonomous_learn.py
  python run_autonomous_learn.py --docs-only
  python run_autonomous_learn.py --max-docs 8 --videos 1 --frames 10

Optional media (not required):
  $env:FSOT_MEDIA_ROOTS = "G:\\movies;G:\\showes;G:\\Debut"
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
    ap = argparse.ArgumentParser(description="Autonomous multi-modal FSOT learn session")
    ap.add_argument("--max-docs", type=int, default=5)
    ap.add_argument("--videos", type=int, default=1)
    ap.add_argument("--audio", type=int, default=1)
    ap.add_argument("--frames", type=int, default=10)
    ap.add_argument("--docs-only", action="store_true")
    ap.add_argument("--media-only", action="store_true")
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    from fsot_nuron.learn.autonomous_loop import run_autonomous_learn
    from fsot_nuron.paths import ARTIFACTS, transplant_report
    from fsot_nuron.knowledge.episode_memory import list_episodes, recall_plain_english

    print("=== FSOT AUTONOMOUS MULTI-MODAL LEARN ===")
    print("Standalone brain · documents + optional media · no per-item prompts")
    tr = transplant_report()
    print(f"transplant: standalone_complete={tr.get('standalone_complete')} "
          f"authority={tr.get('authority')}")

    rep = run_autonomous_learn(
        max_docs=args.max_docs,
        max_videos=0 if args.docs_only else args.videos,
        max_audio=0 if args.docs_only else args.audio,
        media_frames=args.frames,
        include_media=not args.docs_only,
        include_docs=not args.media_only,
        device=args.device,
    )

    print("\n--- digest ---\n")
    print(rep.plain_english_digest)
    print("\n--- pattern census (top) ---")
    for k, v in list(rep.pattern_census.items())[:15]:
        print(f"  {k}: {v}")
    print("\n--- documents ---")
    for d in rep.document_summaries:
        print(f"  [{d.get('kind')}] {d.get('title')}: "
              f"chars={d.get('n_chars')} trits={d.get('n_trits')} "
              f"keys={d.get('knowledge_keys')}")
    print("\n--- media ---")
    for m in rep.media_summaries:
        print(f"  {m.get('title')}: symbols={m.get('symbols')} av={m.get('av')}")
    print("\n--- notes (tail) ---")
    for n in rep.notes[-12:]:
        print(f"  {n}")

    # show memory list
    eps = list_episodes(limit=12)
    print(f"\nepisode memories now: {len(eps)}")
    for e in eps[:8]:
        print(f"  {e.get('episode_id')}: {e.get('title')} [{e.get('caption_source')}]")

    md = ROOT / "data" / "results" / "AUTONOMOUS_LEARN.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(
        "\n".join(
            [
                "# Autonomous multi-modal learn",
                "",
                f"Started: `{rep.started_at}`  ",
                f"Finished: `{rep.finished_at}`  ",
                f"Pin: **{rep.pin_mode}** connected={rep.pin_connected}",
                "",
                "## Digest",
                "",
                rep.plain_english_digest,
                "",
                "## Pattern census",
                "",
                "```",
                json.dumps(rep.pattern_census, indent=2),
                "```",
                "",
                f"JSON: `{ARTIFACTS / 'autonomous_learn_last.json'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {md}")
    print(f"Wrote {ARTIFACTS / 'autonomous_learn_last.json'}")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
