"""
Literature chew + Morse query articulation.

Pipeline (not a giant LLM — FSOT substrate):
  1) Chunk literature into passages
  2) Encode each passage → ITU Morse units → reservoir (efficient)
  3) Store memory: text, ternary fingerprint, S-profile, reconstruction, chem
  4) Query: encode question → reservoir → match memories by fingerprint
  5) Articulate answer via Morse reconstruction + top passages + chemical family

Honest: retrieval + fluid dynamics + Morse alphabet — not free-parameter next-token LM.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch

from .chemical_codon import generative_chemical_report
from .morse_itu import ITUMorseCodec
from .paths import ROOT, ARTIFACTS
from .reservoir import FluidReservoir, ReservoirConfig

LIT_DIR = ROOT / "data" / "literature"
MEMORY_PATH = ARTIFACTS / "literature_memory.json"


def chunk_text(text: str, max_chars: int = 280, overlap: int = 40) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        piece = text[i : i + max_chars]
        # prefer break at sentence
        if len(piece) == max_chars:
            cut = max(piece.rfind(". "), piece.rfind("; "), piece.rfind(", "))
            if cut > max_chars // 3:
                piece = piece[: cut + 1]
        piece = piece.strip()
        if len(piece) > 40:
            chunks.append(piece)
        i += max(1, len(piece) - overlap)
    return chunks


def load_literature(paths: Optional[Sequence[Path]] = None, max_chars_total: int = 120_000) -> List[Dict[str, str]]:
    docs = []
    files = list(paths) if paths else sorted(LIT_DIR.glob("*.*"))
    budget = max_chars_total
    for p in files:
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if p.suffix.lower() == ".json":
            continue  # skip huge json
        # cap very large streams (shakespeare)
        if len(raw) > 80_000:
            raw = raw[:80_000]
        take = raw[:budget]
        budget -= len(take)
        docs.append({"path": str(p), "name": p.name, "text": take})
        if budget <= 0:
            break
    return docs


def _ternary_hist(tern: Sequence[int]) -> List[float]:
    n = max(len(tern), 1)
    c_m = sum(1 for t in tern if t < 0) / n
    c_z = sum(1 for t in tern if t == 0) / n
    c_p = sum(1 for t in tern if t > 0) / n
    # also blockiness
    runs = 1
    for a, b in zip(tern, tern[1:]):
        if a != b:
            runs += 1
    return [c_m, c_z, c_p, runs / n]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


@dataclass
class MemoryEntry:
    id: int
    source: str
    text: str
    morse: str
    ternary_hist: List[float]
    s_mean: float
    s_std: float
    fire_rate: float
    reconstructed: List[str]
    chemical_utterance: str
    aa_head: str


class LiteratureMind:
    """Chew documents; answer queries via Morse/reservoir memory."""

    def __init__(
        self,
        n_units: int = 24,
        device: Optional[str] = None,
        mode: str = "efficient",
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.n_units = n_units
        self.mode = mode
        self.codec = ITUMorseCodec()
        self.res = FluidReservoir(ReservoirConfig(n_units=n_units, device=self.device))
        self.memory: List[MemoryEntry] = []

    def _encode_drive(self, text: str, pad: int = 4) -> Tuple[torch.Tensor, List[int], str]:
        cleaned = self.codec.roundtrip_accuracy(text)["input_normalized"]
        if not cleaned:
            cleaned = "EMPTY"
        units = [0] * pad + self.codec.text_to_units(cleaned) + [0] * pad
        # cap length for speed
        if len(units) > 400:
            units = units[:400]
        stim = torch.tensor([0.12 + 0.78 * u for u in units], device=self.device, dtype=torch.float32)
        morse = self.codec.encode_text(cleaned)
        return stim, units, morse

    @torch.no_grad()
    def _run_passage(self, text: str) -> Dict[str, Any]:
        stim, units, morse = self._encode_drive(text)
        self.res.reset()
        out = self.res.run_sequence(stim, record=True)
        S = out["S_dec"]
        fired = out["fired_dec"]
        S_mean = S.mean(dim=1)
        tern = torch.zeros(S_mean.shape[0], dtype=torch.int8)
        tern = torch.where(S_mean > 0.4, torch.ones_like(tern), tern)
        tern = torch.where(S_mean < -0.05, -torch.ones_like(tern), tern)
        fire_any = fired.any(dim=1) if fired.ndim == 2 else fired
        tern = torch.where(fire_any.cpu(), torch.ones_like(tern), tern)
        tern_list = tern.tolist()
        # reconstruction from high-fire windows
        phrases = []
        score = fire_any.float().cpu() * (S_mean.cpu() > 0.3).float()
        idx = torch.nonzero(score > 0.15, as_tuple=False).flatten().tolist()
        orig = text.upper()
        seen = set()
        for i in idx[:20]:
            ci = min(int(i * len(orig) / max(len(tern_list), 1)), max(0, len(orig) - 1))
            phrase = orig[max(0, ci - 4) : min(len(orig), ci + 8)].strip()
            if len(phrase) > 3 and phrase not in seen:
                seen.add(phrase)
                phrases.append(phrase)
        chem = generative_chemical_report(tern_list)
        hist = _ternary_hist(tern_list)
        # Richer temporal fingerprint for SOTA-track readout (still seed-driven substrate)
        s = S_mean.cpu()
        fire_f = fire_any.float().cpu()
        T = max(int(s.numel()), 1)
        thirds = []
        for a, b in ((0, T // 3), (T // 3, 2 * T // 3), (2 * T // 3, T)):
            seg = s[a:b]
            fseg = fire_f[a:b]
            if seg.numel() == 0:
                thirds.extend([0.0, 0.0, 0.0])
            else:
                thirds.extend(
                    [
                        float(seg.mean()),
                        float(seg.std(unbiased=False)),
                        float(fseg.mean()),
                    ]
                )
        # Morse unit density (dash/dot/space structure in drive)
        u = units if units else [0]
        n_u = max(len(u), 1)
        u_hist = [
            sum(1 for x in u if x == 0) / n_u,
            sum(1 for x in u if x == 1) / n_u,
            sum(1 for x in u if x == 2) / n_u,
            sum(1 for x in u if x >= 3) / n_u,
            len(u) / 400.0,
        ]
        # Text surface cues (cheap; coupled to Morse length already)
        raw = text.upper()
        letters = sum(1 for c in raw if "A" <= c <= "Z")
        digits = sum(1 for c in raw if c.isdigit())
        punct = sum(1 for c in raw if c in "!?$%&@#*")
        spaces = raw.count(" ")
        ln = max(len(raw), 1)
        surface = [
            letters / ln,
            digits / ln,
            punct / ln,
            spaces / ln,
            min(len(raw) / 200.0, 1.5),
        ]
        fp = (
            hist
            + [
                float(s.mean()),
                float(s.std(unbiased=False)),
                float((s > 0.4).float().mean()),
                float(out["firing_rate_Hz"].mean().cpu()),
                float(s.min()),
                float(s.max()),
                float((s > 0.0).float().mean()),
            ]
            + thirds
            + u_hist
            + surface
        )
        return {
            "morse": morse,
            "fingerprint": fp,
            "s_mean": float(s.mean()),
            "s_std": float(s.std(unbiased=False)),
            "fire_rate": float(out["firing_rate_Hz"].mean().cpu()),
            "reconstructed": phrases[:8],
            "chemical_utterance": chem.get("enriched_utterance") or chem.get("chemical_utterance"),
            "aa_head": (chem.get("aa_sequence") or "")[:24],
            "ternary_hist": hist,
        }

    def chew_documents(self, max_chunks: int = 80) -> Dict[str, Any]:
        docs = load_literature()
        # Round-robin chunks across sources so one big file cannot monopolize memory
        per_doc = [chunk_text(d["text"]) for d in docs]
        indices = [0] * len(docs)
        while len(self.memory) < max_chunks:
            progressed = False
            for di, doc in enumerate(docs):
                if indices[di] >= len(per_doc[di]):
                    continue
                ch = per_doc[di][indices[di]]
                indices[di] += 1
                progressed = True
                r = self._run_passage(ch)
                self.memory.append(
                    MemoryEntry(
                        id=len(self.memory),
                        source=doc["name"],
                        text=ch,
                        morse=r["morse"][:200],
                        ternary_hist=r["fingerprint"],
                        s_mean=r["s_mean"],
                        s_std=r["s_std"],
                        fire_rate=r["fire_rate"],
                        reconstructed=r["reconstructed"],
                        chemical_utterance=r["chemical_utterance"] or "",
                        aa_head=r["aa_head"],
                    )
                )
                if len(self.memory) >= max_chunks:
                    break
            if not progressed:
                break
        self.save_memory()
        return {
            "n_docs": len(docs),
            "n_chunks": len(self.memory),
            "sources": sorted({m.source for m in self.memory}),
            "memory_path": str(MEMORY_PATH),
        }

    def save_memory(self) -> None:
        payload = {
            "n": len(self.memory),
            "entries": [asdict(m) for m in self.memory],
        }
        MEMORY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_memory(self) -> bool:
        if not MEMORY_PATH.is_file():
            return False
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        self.memory = [MemoryEntry(**e) for e in data.get("entries", [])]
        return True

    def query(self, question: str, top_k: int = 4) -> Dict[str, Any]:
        if not self.memory:
            if not self.load_memory():
                return {"ok": False, "reason": "empty memory — run chew first"}
        q = self._run_passage(question)
        qfp = q["fingerprint"]
        scored = []
        for m in self.memory:
            sim = _cosine(qfp, m.ternary_hist)
            # keyword boost (primary for meaning; fluid fingerprint secondary)
            qwords = set(re.findall(r"[A-Za-z0-9]+", question.upper()))
            # drop stopwords for overlap
            stop = {"WHAT", "IS", "THE", "A", "AN", "OF", "AND", "IN", "TO", "HOW", "DOES", "DO", "ARE"}
            qwords = {w for w in qwords if w not in stop and len(w) > 2}
            mwords = set(re.findall(r"[A-Za-z0-9]+", m.text.upper()))
            overlap = len(qwords & mwords) / max(len(qwords), 1)
            score = 0.40 * sim + 0.60 * overlap
            scored.append((score, m, overlap, sim))
        scored.sort(key=lambda x: -x[0])
        top = scored[:top_k]

        # Articulate answer
        passages = []
        recon = []
        chem_bits = []
        for score, m, overlap, sim in top:
            passages.append(
                {
                    "score": score,
                    "keyword_overlap": overlap,
                    "fluid_sim": sim,
                    "source": m.source,
                    "text": m.text,
                    "reconstructed": m.reconstructed,
                }
            )
            recon.extend(m.reconstructed[:2])
            if m.chemical_utterance:
                chem_bits.append(m.chemical_utterance.split("||")[0].strip())

        # Symbolic Morse path of question (exact alphabet layer)
        q_norm = self.codec.roundtrip_accuracy(question)["input_normalized"] or "Q"
        q_exact = self.codec.decode_morse_string(self.codec.encode_text(q_norm))

        # Compose answer: extractive synthesis from best memory
        body_parts = []
        for p in passages:
            t = p["text"].strip()
            if ". " in t:
                # prefer sentence containing a query keyword
                sents = re.split(r"(?<=[.!?])\s+", t)
                qwords = set(re.findall(r"[A-Za-z0-9]+", question.upper()))
                best = sents[0]
                for s in sents:
                    if any(w in s.upper() for w in qwords if len(w) > 3):
                        best = s
                        break
                t = best
            body_parts.append(f"[{p['source']} | match={p['score']:.2f}] {t}")

        if recon:
            recon_line = " | ".join(list(dict.fromkeys(recon))[:6])
        else:
            recon_line = "(sparse reconstruction)"

        # Short "articulation" line: join top extractive sentences
        articulate = " ".join(
            re.sub(r"\s+", " ", p["text"])[:220] for p in passages[:2]
        )
        answer = (
            f"QUERY (Morse-exact): {q_exact}\n"
            f"ARTICULATION:\n  {articulate}\n"
            f"EVIDENCE ({len(top)} memories; fluid+keyword match):\n"
            + "\n".join(f"  • {b}" for b in body_parts)
            + f"\nMORSE_ZONE_PHRASES: {recon_line}\n"
            f"CHEM: {chem_bits[0] if chem_bits else '(none)'}\n"
            f"RESERVOIR: S̄={q['s_mean']:.3f} rate={q['fire_rate']:.1f}Hz"
        )

        return {
            "ok": True,
            "question": question,
            "answer": answer,
            "top": passages,
            "query_morse_decode": q_exact,
            "query_reservoir": {
                "s_mean": q["s_mean"],
                "fire_rate": q["fire_rate"],
                "reconstructed": q["reconstructed"],
                "chemical": q["chemical_utterance"],
            },
            "n_memory": len(self.memory),
        }
