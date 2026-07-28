"""
Machine-oriented translation layer for FSOT neural I/O.

Primary path (recommended for computer body / OS-native interfacing):
  chemical codon trits  ↔  machine words (T1 pack, bytes, UTF-8)
  text/bytes            ↔  trit streams for sensory inject

Secondary path (legacy / human telegraphy demos):
  ITU Morse  ↔  trit  (kept optional; not required for intelligence)

Rationale: the brain is becoming a silicon-resident process. Morse is a
human radio alphabet. Operating systems move **machine words and bytes**.
FSOT trinary is the neural code; packing into OS-visible integers is the
ABI, same idea as Zig TritWord on bare metal.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .chemical_codon import (
    DNA_TO_AA,
    codon_path_verify,
    parse_codon_trinary_map,
    ternary_stream_to_codons,
)
from .trinary_substrate import (
    as_trit,
    pack_trits,
    unpack_trits,
    pack_codon,
    codon_primary,
    quantize_features_to_trits,
)


class EncodePath(str, Enum):
    MACHINE = "machine"  # primary: bytes / UTF-8 / T1 packs
    CHEMICAL = "chemical"  # DNA/codon ↔ trits ↔ AA
    MORSE = "morse"  # secondary: ITU Morse


@dataclass
class MachineWord:
    """OS-visible carrier for a trit word (little-endian T1 packing)."""

    n_trits: int
    pack: int  # unsigned int carrier
    path: str = EncodePath.MACHINE.value

    def trits(self) -> List[int]:
        return unpack_trits(self.pack, self.n_trits)

    def to_bytes(self, width: int = 8) -> bytes:
        """Export pack as little-endian bytes (width 1..8)."""
        w = max(1, min(8, width))
        return int(self.pack).to_bytes(w, byteorder="little", signed=False)

    def hex(self, width: int = 8) -> str:
        return self.to_bytes(width).hex()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["trits"] = self.trits()
        d["hex"] = self.hex()
        return d


# ---------------------------------------------------------------------------
# Machine path (primary)
# ---------------------------------------------------------------------------

def text_to_utf8_trits(text: str) -> List[int]:
    """
    UTF-8 bytes → trit stream via bit pairs (00→0, 01→+1, 10→-1, 11→+1).
    Dense, OS-native; no Morse.
    """
    data = text.encode("utf-8")
    trits: List[int] = []
    for b in data:
        for shift in (0, 2, 4, 6):
            pair = (b >> shift) & 0b11
            if pair == 0b00:
                trits.append(0)
            elif pair == 0b01:
                trits.append(1)
            elif pair == 0b10:
                trits.append(-1)
            else:
                trits.append(1)  # 11 → +1 (no illegal T1)
    return trits


def trits_to_utf8_text(trits: Sequence[int]) -> str:
    """Inverse of text_to_utf8_trits (best-effort; padding ignored)."""
    bits: List[int] = []
    for t in trits:
        tt = as_trit(t)
        if tt == 0:
            bits.extend([0, 0])
        elif tt > 0:
            bits.extend([0, 1])  # 01 — ambiguous with 11 path; use 01 only
        else:
            bits.extend([1, 0])
    # pack to bytes
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        b = 0
        for k in range(8):
            b |= (bits[i + k] & 1) << k
        out.append(b)
    try:
        return out.decode("utf-8", errors="replace")
    except Exception:
        return out.decode("latin-1", errors="replace")


def text_to_machine_words(text: str, word_trits: int = 27) -> List[MachineWord]:
    """Chunk UTF-8 trit stream into fixed-width machine words (default 27 = codon-ish geometry)."""
    trits = text_to_utf8_trits(text)
    words: List[MachineWord] = []
    for i in range(0, len(trits), word_trits):
        chunk = list(trits[i : i + word_trits])
        if len(chunk) < word_trits:
            chunk.extend([0] * (word_trits - len(chunk)))
        words.append(MachineWord(n_trits=word_trits, pack=pack_trits(chunk)))
    return words


def bytes_to_machine_word(data: bytes) -> MachineWord:
    """Raw OS buffer → single packed trit word (bit-pair expand, max 32 trits)."""
    trits: List[int] = []
    for b in data:
        for shift in (0, 2, 4, 6):
            pair = (b >> shift) & 0b11
            trits.append(0 if pair == 0 else (1 if pair in (1, 3) else -1))
            if len(trits) >= 32:
                break
        if len(trits) >= 32:
            break
    return MachineWord(n_trits=len(trits), pack=pack_trits(trits))


def features_to_machine_word(features: Sequence[float]) -> MachineWord:
    trits = quantize_features_to_trits(list(features))
    return MachineWord(n_trits=len(trits), pack=pack_trits(trits))


# ---------------------------------------------------------------------------
# Chemical path
# ---------------------------------------------------------------------------

def dna_to_machine_words(dna: str) -> List[MachineWord]:
    dna = dna.upper().replace("U", "T")
    words = []
    for i in range(0, len(dna) - 2, 3):
        codon = dna[i : i + 3]
        if len(codon) < 3 or any(c not in "ACGT" for c in codon):
            continue
        trip = codon_primary(codon)
        words.append(
            MachineWord(
                n_trits=3,
                pack=pack_trits(list(trip)),
                path=EncodePath.CHEMICAL.value,
            )
        )
    return words


def trits_to_chemical_report(trits: Sequence[int]) -> Dict[str, Any]:
    codons = ternary_stream_to_codons(list(trits))
    aa = "".join(c.get("aa", "?") for c in codons)
    return {
        "n_codons": len(codons),
        "aa_sequence": aa,
        "codons": codons[:32],
        "verify": codon_path_verify(),
    }


# ---------------------------------------------------------------------------
# Morse path (secondary)
# ---------------------------------------------------------------------------

def text_to_morse_trits(text: str) -> List[int]:
    """Optional legacy path — ITU Morse OOK → FSOT trinary (secondary)."""
    try:
        from .morse_itu import ITUMorseCodec

        codec = ITUMorseCodec()
        units = codec.text_to_units(text)
        return [as_trit(t) for t in codec.units_to_ternary(units)]
    except Exception:
        return text_to_utf8_trits(text)


# ---------------------------------------------------------------------------
# Unified facade
# ---------------------------------------------------------------------------

def translate(
    payload: Union[str, bytes, Sequence[float]],
    path: EncodePath = EncodePath.MACHINE,
    *,
    word_trits: int = 27,
) -> Dict[str, Any]:
    """
    Translate human/chemical/machine payload into FSOT-ready form.

    Returns trits, machine words, and path metadata for the console / ABI.
    """
    path = EncodePath(path) if not isinstance(path, EncodePath) else path

    if path is EncodePath.MORSE:
        if not isinstance(payload, str):
            payload = str(payload)
        trits = text_to_morse_trits(payload)
        words = [
            MachineWord(n_trits=min(27, len(trits[i : i + 27])), pack=pack_trits(trits[i : i + 27] or [0]))
            for i in range(0, max(1, len(trits)), 27)
        ]
        return {
            "path": path.value,
            "primary": False,
            "note": "Secondary Morse path — prefer machine for OS-native body",
            "trits": trits[:256],
            "n_trits": len(trits),
            "words": [w.to_dict() for w in words[:32]],
            "preview": payload[:120],
        }

    if path is EncodePath.CHEMICAL:
        if isinstance(payload, str) and all(c in "ACGTacgtUu \n" for c in payload[:200]):
            dna = "".join(c for c in payload.upper() if c in "ACGT")
            words = dna_to_machine_words(dna)
            trits: List[int] = []
            for w in words:
                trits.extend(w.trits())
            chem = trits_to_chemical_report(trits)
            return {
                "path": path.value,
                "primary": True,
                "note": "Chemical codon primary map (A,G=+1; C,T=-1)",
                "trits": trits[:256],
                "n_trits": len(trits),
                "words": [w.to_dict() for w in words[:32]],
                "chemical": chem,
                "preview": dna[:120],
            }
        # treat as text → utf8 trits → chemical readout
        if not isinstance(payload, str):
            payload = str(payload)
        trits = text_to_utf8_trits(payload)
        chem = trits_to_chemical_report(trits)
        words = text_to_machine_words(payload, word_trits=word_trits)
        return {
            "path": path.value,
            "primary": True,
            "note": "Text→UTF-8 trits then chemical codon parse",
            "trits": trits[:256],
            "n_trits": len(trits),
            "words": [w.to_dict() for w in words[:32]],
            "chemical": chem,
            "preview": payload[:120],
        }

    # MACHINE primary
    if isinstance(payload, (bytes, bytearray)):
        w = bytes_to_machine_word(bytes(payload))
        return {
            "path": path.value,
            "primary": True,
            "note": "Raw bytes → T1 machine word (OS buffer style)",
            "trits": w.trits(),
            "n_trits": w.n_trits,
            "words": [w.to_dict()],
            "hex": w.hex(),
            "preview": bytes(payload)[:64].hex(),
        }
    if isinstance(payload, (list, tuple)) and payload and isinstance(payload[0], (int, float)):
        w = features_to_machine_word(payload)  # type: ignore
        return {
            "path": path.value,
            "primary": True,
            "note": "Float features → quantized trits → machine word",
            "trits": w.trits(),
            "n_trits": w.n_trits,
            "words": [w.to_dict()],
            "preview": str(list(payload)[:16]),
        }
    text = str(payload)
    words = text_to_machine_words(text, word_trits=word_trits)
    trits = text_to_utf8_trits(text)
    return {
        "path": path.value,
        "primary": True,
        "note": "UTF-8 text → trit stream → machine words (primary OS-native path)",
        "trits": trits[:256],
        "n_trits": len(trits),
        "words": [w.to_dict() for w in words[:32]],
        "roundtrip_preview": trits_to_utf8_text(trits)[:120],
        "preview": text[:120],
    }


def path_recommendation() -> Dict[str, str]:
    return {
        "default": EncodePath.MACHINE.value,
        "for_os_body": EncodePath.MACHINE.value,
        "for_genetics": EncodePath.CHEMICAL.value,
        "for_legacy_demo": EncodePath.MORSE.value,
        "summary": (
            "Prefer machine (UTF-8/bytes/T1 packs) for computer-native intelligence; "
            "chemical for DNA/codon biology; Morse only for optional human telegraphy demos."
        ),
    }
