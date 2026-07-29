#!/usr/bin/env python3
"""Grow en_roles.tsv for the Zig English codec (teacher → student).

Default LLM teacher = **local Ollama** (free, already on your machine).
No paid API required.

Examples:
  python run_lexicon_teacher.py --offline --target 500
  python run_lexicon_teacher.py --llm --target 800
  python run_lexicon_teacher.py --llm --model qwen3.5:4b --target 1000
  python run_lexicon_teacher.py --list-models
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
    p = argparse.ArgumentParser(
        description="FSOT lexicon teacher — local Ollama by default (not part of the mind)"
    )
    p.add_argument("--offline", action="store_true", help="Free word-list expansion only")
    p.add_argument(
        "--llm",
        action="store_true",
        help="Use local Ollama teacher after offline seed (default provider=ollama)",
    )
    p.add_argument(
        "--provider",
        default="ollama",
        choices=("ollama", "local", "xai", "openai", "remote"),
        help="Teacher backend (default: ollama local). Remote only if you insist.",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Ollama model name (default: auto-pick qwen3.5:4b / fsot-gemma / first available)",
    )
    p.add_argument("--target", type=int, default=500, help="Target vocabulary size")
    p.add_argument("--list-models", action="store_true", help="List Ollama models and exit")
    p.add_argument("--json", action="store_true", help="Print JSON report")
    args = p.parse_args()

    from fsot_nuron.lexicon_teacher import ollama_list_models, resolve_ollama_model, teach

    if args.list_models:
        models = ollama_list_models()
        print("OLLAMA_HOST models:")
        for m in models:
            print(f"  {m}")
        try:
            print("auto_pick=", resolve_ollama_model(None))
        except Exception as e:
            print("auto_pick_error=", e)
        return 0 if models else 1

    if not args.offline and not args.llm:
        args.offline = True

    rep = teach(
        offline=args.offline or not args.llm,
        llm=args.llm,
        target=args.target,
        provider=args.provider,
        model=args.model,
    )
    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        print("=== FSOT LEXICON TEACHER ===")
        print(f"mode={rep['mode']} teacher={rep.get('teacher')} target={rep['target']}")
        print(f"path={rep['path']}")
        print(f"size {rep['before']} → {rep['after']} (+{rep['added']})")
        print("by_role:", rep["by_role"])
        if rep.get("teacher_error"):
            print("teacher_error:", rep["teacher_error"])
        print(rep["doctrine"])
        if rep.get("teacher_error") and args.llm:
            print("FSOT_LEXICON_TEACHER_PARTIAL")
            return 1
        print("FSOT_LEXICON_TEACHER_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
