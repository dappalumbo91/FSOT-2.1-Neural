#!/usr/bin/env python3
"""
Chew literature + real neural signal context; query via Morse/FSOT articulation.

Examples:
  python run_chew_query.py --chew
  python run_chew_query.py --query "What is FSOT trinary Morse language?"
  python run_chew_query.py --chew --query "How does fluid spacetime relate to neurons?"
"""

from __future__ import annotations

import argparse
import json

from fsot_nuron.eeg_loader import build_real_signal_bundle
from fsot_nuron.eeg_sources import gather_eeg_context
from fsot_nuron.literature_chew import LiteratureMind
from fsot_nuron.paths import ARTIFACTS


DEFAULT_QUERIES = [
    "What is Fluid Spacetime Omni-Theory?",
    "How does Morse trinary encode language in FSOT?",
    "What is the role of the FSOT scalar and zero free parameters?",
    "How do neurons and refractory dynamics appear in the theory?",
]


def main() -> None:
    p = argparse.ArgumentParser(description="FSOT literature chew + Morse query")
    p.add_argument("--chew", action="store_true", help="ingest literature into memory")
    p.add_argument("--query", action="append", default=[], help="question (repeatable)")
    p.add_argument("--max-chunks", type=int, default=60)
    p.add_argument("--units", type=int, default=24)
    p.add_argument("--device", default="cpu")
    p.add_argument("--demo", action="store_true", help="chew + default question set")
    args = p.parse_args()

    print("=" * 64)
    print("FSOT-2.1-Neural — literature chew + Morse query articulation")
    print("=" * 64)

    # Real neural signal stack
    print("\n--- real neural signals (data/eeg) ---")
    sig = build_real_signal_bundle()
    print(f"  allen_nwb_ok: {sig.get('allen_nwb', {}).get('ok')}")
    if sig.get("allen_nwb", {}).get("ok"):
        agg = sig["allen_nwb"]["aggregate"]
        print(f"  NWB sweeps: {sig['allen_nwb']['n_sweeps_analyzed']}  isi_cv={agg.get('mean_isi_cv'):.3f}  zc={agg.get('mean_zero_cross_rate'):.3f}")
    print(f"  allen_features_ok: {sig.get('allen_features', {}).get('ok')} n={sig.get('allen_features', {}).get('n')}")
    print(f"  pd_priors_ok: {sig.get('pd_openneuro', {}).get('ok')}")
    eeg = gather_eeg_context(fetch_live=True)
    print(f"  openneuro_pd: {eeg.get('openneuro_pd', {}).get('ok')}  local_files={eeg.get('n_local_eeg')}")
    print(f"  pd_lesion: {eeg['pd_lesion_derived']['fsot_lesion']}")

    mind = LiteratureMind(n_units=args.units, device=args.device)
    if args.chew or args.demo:
        print("\n--- chewing literature ---")
        rep = mind.chew_documents(max_chunks=args.max_chunks)
        print(f"  docs={rep['n_docs']} chunks={rep['n_chunks']}")
        print(f"  sources={rep['sources']}")
    else:
        if not mind.load_memory():
            print("No memory yet. Re-run with --chew or --demo")
            return
        print(f"\nloaded memory: {len(mind.memory)} chunks")

    queries = list(args.query)
    if args.demo or not queries:
        queries = DEFAULT_QUERIES

    print("\n--- queries (Morse / fluid articulation) ---")
    results = []
    for q in queries:
        print(f"\nQ: {q}")
        r = mind.query(q, top_k=3)
        if not r.get("ok"):
            print(f"  ERR {r}")
            continue
        print(r["answer"])
        results.append(r)

    out = {
        "signal_bundle_ok": sig.get("ok"),
        "n_memory": len(mind.memory),
        "queries": results,
    }
    path = ARTIFACTS / "chew_query_report.json"
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nreport: {path}")


if __name__ == "__main__":
    main()
