"""
Document reading — actual page text, not next-token prediction.

Supports: .md .txt .rst .csv .json .pdf (pypdf when installed)
Words on the page → UTF-8 → machine/trinary (body language) → knowledge bind.

Standalone: missing pypdf simply skips PDF; markdown/txt always work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from ..paths import ROOT, DATA
from ..machine_encode import text_to_utf8_trits, encode_to_sensory_packet, EncodePath
from ..fsot_bridge import bridge_machine_payload
from ..sensory.packets import SensoryPacket, SensoryModality
from .cross_feed import cross_feed_episode


TEXT_EXTS = {".md", ".txt", ".rst", ".csv", ".json", ".tex", ".py", ".lean"}
PDF_EXTS = {".pdf"}


@dataclass
class DocumentChunk:
    path: str
    title: str
    index: int
    text: str
    n_chars: int
    n_trits: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentReadReport:
    path: str
    title: str
    kind: str  # markdown | text | pdf | other
    n_chunks: int
    n_chars: int
    n_trits_total: int
    sample_text: str
    plain_english: str
    symbols_guessed: List[str]
    knowledge_keys: List[str]
    S_couple: Optional[float]
    packets_n: int
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def discover_documents(
    roots: Optional[Sequence[Path]] = None,
    *,
    max_files: int = 40,
) -> List[Path]:
    if roots is None:
        roots = [
            DATA / "literature",
            ROOT / "docs",
            DATA / "knowledge",
        ]
    out: List[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for p in sorted(root.rglob("*")):
                if not p.is_file():
                    continue
                if p.suffix.lower() in TEXT_EXTS | PDF_EXTS:
                    # skip huge binary-ish / cache
                    if p.name.startswith(".") or "__pycache__" in p.parts:
                        continue
                    if p.stat().st_size > 8_000_000 and p.suffix.lower() != ".pdf":
                        continue
                    out.append(p)
                if len(out) >= max_files:
                    return out
        except OSError:
            continue
    return out


def read_text_file(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=enc, errors="replace")
        except OSError:
            continue
    return ""


def read_pdf_text(path: Path, max_pages: int = 40) -> str:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        parts = []
        for i, page in enumerate(reader.pages[:max_pages]):
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                parts.append(t)
        return "\n\n".join(parts)
    except Exception as e:
        return f""


def load_document_text(path: Path, max_pages: int = 40) -> tuple[str, str, List[str]]:
    """Returns (text, kind, notes)."""
    ext = path.suffix.lower()
    notes: List[str] = []
    if ext in PDF_EXTS:
        text = read_pdf_text(path, max_pages=max_pages)
        kind = "pdf"
        if not text.strip():
            notes.append("pdf extract empty (scanned image PDF needs OCR later)")
    elif ext in TEXT_EXTS:
        text = read_text_file(path)
        kind = "markdown" if ext == ".md" else "text"
    else:
        text = read_text_file(path)
        kind = "other"
    # normalize whitespace lightly — keep structure for reading
    text = text.replace("\r\n", "\n")
    return text, kind, notes


def chunk_text(text: str, *, chunk_chars: int = 1200, max_chunks: int = 24) -> List[str]:
    text = text.strip()
    if not text:
        return []
    # prefer paragraph breaks
    paras = re.split(r"\n\s*\n", text)
    chunks: List[str] = []
    buf = ""
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) + 2 <= chunk_chars:
            buf = (buf + "\n\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
            if len(p) > chunk_chars:
                for i in range(0, len(p), chunk_chars):
                    chunks.append(p[i : i + chunk_chars])
                buf = ""
            else:
                buf = p
        if len(chunks) >= max_chunks:
            return chunks[:max_chunks]
    if buf and len(chunks) < max_chunks:
        chunks.append(buf)
    return chunks[:max_chunks]


def guess_symbols_from_text(text: str) -> List[str]:
    """Lightweight symbol priors from word presence (not LLM). Word-boundary safe."""
    low = text.lower()
    lexicon_keys = [
        "adventure time",
        "consciousness",
        "person", "human", "animal", "dog", "cat", "face", "place",
        "music", "dialogue", "action", "cartoon", "movie", "war", "space",
        "finn", "jake", "neuron", "brain", "codon", "trinary",
        "scalar", "science", "theory", "shakespeare",
    ]
    hits = []
    for k in lexicon_keys:
        if " " in k:
            if k in low:
                hits.append(k)
        else:
            if re.search(rf"\b{re.escape(k)}\b", low):
                hits.append(k)
    # reading always has linguistic "scene" structure
    if "theorem" in low or "formula" in low or "proof" in low:
        hits.append("theory")
    if "stage" in low or "act " in low or "scene" in low:
        hits.append("scene")
    # dedupe
    out = []
    seen = set()
    for h in hits:
        if h not in seen:
            out.append(h)
            seen.add(h)
    return out[:16]


def read_document(
    path: Path | str,
    *,
    chunk_chars: int = 1000,
    max_chunks: int = 12,
    inject_packets: bool = True,
) -> tuple[DocumentReadReport, List[SensoryPacket]]:
    """
    Read a document into chunks, compact each to trinary, cross-feed knowledge.
    Returns report + sensory packets for the living brain.
    """
    path = Path(path)
    notes: List[str] = []
    text, kind, n0 = load_document_text(path)
    notes.extend(n0)
    title = path.stem.replace("_", " ")
    chunks_txt = chunk_text(text, chunk_chars=chunk_chars, max_chunks=max_chunks)
    symbols = guess_symbols_from_text(text[:8000])
    packets: List[SensoryPacket] = []
    n_trits = 0
    S = None

    for i, ch in enumerate(chunks_txt):
        tr = text_to_utf8_trits(ch)
        n_trits += len(tr)
        if inject_packets:
            try:
                # reading → assoc (language) + hipp (episodic page memory)
                for region, strength in (("assoc", 0.5), ("hipp", 0.35)):
                    pkt = encode_to_sensory_packet(
                        ch[:1500],
                        path=EncodePath.MACHINE,
                        target_region=region,
                        strength=strength,
                    )
                    pkt.meta["kind"] = "document_read"
                    pkt.meta["doc_path"] = str(path)
                    pkt.meta["chunk"] = i
                    pkt.meta["title"] = title
                    packets.append(pkt)
            except Exception as e:
                notes.append(f"chunk {i} encode: {e}")

    # knowledge cross-feed from whole-doc sample
    sample = text[:2000]
    cf = cross_feed_episode(
        symbols=symbols,
        title=title,
        transcript=sample,  # treat page text like "heard/read language"
        path_hint=str(path),
        sensory_notes=f"Document read ({kind}): {len(chunks_txt)} chunks, {len(text)} chars.",
    )
    notes.extend(cf.notes)
    if inject_packets:
        # rehydrate a few knowledge packets
        for pd in cf.packets[:8]:
            try:
                packets.append(
                    SensoryPacket(
                        modality=SensoryModality(pd["modality"])
                        if isinstance(pd.get("modality"), str)
                        else pd["modality"],
                        target_region=pd.get("target_region") or "assoc",
                        features=list(pd.get("features") or []),
                        strength=float(pd.get("strength") or 0.4),
                        timestamp_ms=float(pd.get("timestamp_ms") or 0.0),
                        meta=dict(pd.get("meta") or {}),
                    )
                )
            except Exception:
                pass
    try:
        br = bridge_machine_payload(sample[:500] or title)
        S = float((br.get("modulators") or {}).get("S"))
    except Exception:
        S = cf.S_couple

    report = DocumentReadReport(
        path=str(path),
        title=title,
        kind=kind,
        n_chunks=len(chunks_txt),
        n_chars=len(text),
        n_trits_total=n_trits,
        sample_text=sample[:400],
        plain_english=cf.plain_english,
        symbols_guessed=symbols,
        knowledge_keys=[e.get("key") for e in cf.entries_used if isinstance(e, dict)],
        S_couple=S,
        packets_n=len(packets),
        notes=notes,
    )
    return report, packets
