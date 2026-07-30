#!/usr/bin/env python3
"""Export experience-school atomics into Zig brain_teach lessons.tsv.

  python scripts/export_brain_teach_bank.py
  → writes I:/fsot-neuron-zig/data/curriculum/brain_teach/lessons.tsv
    (or --out path)

Then: cd fsot-neuron-zig ; fsot_mind brain-learn
"""
from __future__ import annotations
import argparse
from pathlib import Path

ROOT_ZIG = Path(r"I:\fsot-neuron-zig")
DEFAULT_OUT = ROOT_ZIG / "data" / "curriculum" / "brain_teach" / "lessons.tsv"

# Portable atomics (match Python experience school surfaces)
ROWS = [
    ("half of two", "one", "Half of two is one."),
    ("half of four", "two", "Half of four is two."),
    ("half of eight", "four", "Half of eight is four."),
    ("half of twelve", "six", "Half of twelve is six."),
    ("half of twenty four", "twelve", "Half of twenty four is twelve."),
    ("twice two", "four", "Twice two is four."),
    ("twice four", "eight", "Twice four is eight."),
    ("twice six", "twelve", "Twice six is twelve."),
    ("twice eight", "sixteen", "Twice eight is sixteen."),
    ("three times three", "nine", "Three times three is nine."),
    ("three times six", "eighteen", "Three times six is eighteen."),
    ("four times three", "twelve", "Four times three is twelve."),
    ("five times four", "twenty", "Five times four is twenty."),
    ("ten plus ten", "twenty", "Ten plus ten is twenty."),
    ("fifteen minus five", "ten", "Fifteen minus five is ten."),
    ("thirty minus ten", "twenty", "Thirty minus ten is twenty."),
    ("twenty five percent of forty", "ten", "Twenty five percent of forty is ten."),
    ("ten percent of fifty", "five", "Ten percent of fifty is five."),
    ("a score is twenty", "twenty", "A score is twenty."),
    ("half of fifty", "twentyfive", "Half of fifty is twenty five."),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# question\tanswer\tfact", "# exported for fsot_mind brain-learn (real OrganismF)"]
    for q, a, f in ROWS:
        lines.append(f"{q}\t{a}\t{f}")
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(ROWS)} lessons → {args.out}")
    print("Run: fsot_mind brain-learn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
