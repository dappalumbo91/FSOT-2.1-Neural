#!/usr/bin/env python3
"""Simulate the Kaggle notebook path using local emotions.csv."""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WORK = ROOT / "artifacts" / "kaggle_sim"
WORK.mkdir(parents=True, exist_ok=True)

# locate emotions
cands = [
    ROOT / "data" / "eeg" / "kaggle_emotions" / "emotions.csv",
    Path(r"D:\training data\archive\emotions.csv"),
]
EMO = next((p for p in cands if p.is_file()), None)
assert EMO, "emotions.csv missing"

# Morse RT
MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....",
    "I": "..", "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.",
    "Q": "--.-", "R": ".-.", "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
}
REV = {v: k for k, v in MORSE.items()}


def enc(t: str) -> str:
    return " / ".join(" ".join(MORSE[c] for c in w if c in MORSE) for w in t.upper().split() if any(c in MORSE for c in w))


def dec(m: str) -> str:
    return " ".join("".join(REV.get(t, "?") for t in w.split()) for w in m.split(" / "))


assert dec(enc("FSOT 21")) == "FSOT 21"

df = pd.read_csv(EMO)
cols = list(df.columns)
if cols[0].startswith("#"):
    cols[0] = cols[0].lstrip("#").strip()
    df.columns = cols
y = df["label"].astype(str).str.upper()
X = df.drop(columns=["label"]).select_dtypes(include=[np.number]).dropna(axis=1, how="all")
if X.shape[1] > 256:
    prefer = [c for c in X.columns if str(c).startswith("mean_") or str(c).startswith("fft_")]
    X = X[prefer[:256]] if len(prefer) >= 64 else X.iloc[:, :256]
energy_cv = float(X.abs().mean(axis=1).std() / (X.abs().mean(axis=1).mean() + 1e-12))

# package path
from fsot_nuron.emotions_eeg import compute_emotions_stats
from fsot_nuron.literature_chew import LiteratureMind

st = compute_emotions_stats(EMO)
mind = LiteratureMind(n_units=12, device="cpu")
if not mind.load_memory() or len(mind.memory) < 5:
    mind.chew_documents(max_chunks=20)
q = mind.query("What is Fluid Spacetime Omni-Theory?", top_k=2)

summary = {
    "emotions_csv": str(EMO),
    "n": int(df.shape[0]),
    "labels": y.value_counts().to_dict(),
    "energy_cv": energy_cv,
    "package_templates": st["emotion_lesion_templates"],
    "morse_ok": True,
    "query_ok": q.get("ok"),
    "answer_head": (q.get("answer") or "")[:500],
}
(WORK / "local_kaggle_smoke.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2)[:2000])
print("OK — Kaggle notebook logic smoke passed")
