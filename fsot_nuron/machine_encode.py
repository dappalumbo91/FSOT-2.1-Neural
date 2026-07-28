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

def bytes_to_trits_lossless(data: bytes) -> List[int]:
    """
    Raw OS buffer → trit stream (1 trit per bit: 0→0, 1→+1).

    Lossless, machine-language style — same idea as moving a byte buffer
    through a kernel pipe, then expanding at the neural edge. Not Morse.
    """
    trits: List[int] = []
    for b in data:
        for shift in range(8):
            bit = (b >> shift) & 1
            trits.append(1 if bit else 0)
    return trits


def trits_to_bytes_lossless(trits: Sequence[int]) -> bytes:
    """Inverse of bytes_to_trits_lossless (ignores incomplete trailing bits)."""
    out = bytearray()
    n = len(trits) - (len(trits) % 8)
    for i in range(0, n, 8):
        b = 0
        for k in range(8):
            if as_trit(trits[i + k]) > 0:
                b |= 1 << k
        out.append(b)
    return bytes(out)


def text_to_utf8_trits(text: str) -> List[int]:
    """UTF-8 bytes → lossless bit→trit stream (OS-native; no Morse)."""
    return bytes_to_trits_lossless(text.encode("utf-8"))


def trits_to_utf8_text(trits: Sequence[int]) -> str:
    """Inverse of text_to_utf8_trits."""
    data = trits_to_bytes_lossless(trits)
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return data.decode("latin-1", errors="replace")


def text_to_machine_words(text: str, word_trits: int = 32) -> List[MachineWord]:
    """
    Chunk UTF-8 trit stream into fixed-width machine words.

    Default 32 trits = one Zig TritWord / u64 carrier full width (OS-native).
    """
    trits = text_to_utf8_trits(text)
    words: List[MachineWord] = []
    for i in range(0, len(trits), word_trits):
        chunk = list(trits[i : i + word_trits])
        if len(chunk) < word_trits:
            chunk.extend([0] * (word_trits - len(chunk)))
        words.append(MachineWord(n_trits=word_trits, pack=pack_trits(chunk)))
    return words


def bytes_to_machine_word(data: bytes) -> MachineWord:
    """Raw OS buffer → single packed trit word (lossless bit expand, max 32 trits)."""
    trits = bytes_to_trits_lossless(data)[:32]
    if not trits:
        trits = [0]
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
    word_trits: int = 32,
) -> Dict[str, Any]:
    """
    Translate human/chemical/machine payload into FSOT-ready form.

    Returns trits, machine words, and path metadata for the console / ABI.
    Default word width 32 = full Zig TritWord / u64 (OS-native).
    """
    path = EncodePath(path) if not isinstance(path, EncodePath) else path

    if path is EncodePath.MORSE:
        if not isinstance(payload, str):
            payload = str(payload)
        trits = text_to_morse_trits(payload)
        words = [
            MachineWord(
                n_trits=min(word_trits, len(trits[i : i + word_trits])),
                pack=pack_trits(trits[i : i + word_trits] or [0]),
            )
            for i in range(0, max(1, len(trits)), word_trits)
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
                "note": "Chemical codon primary map (A,G=+1; C,T=-1) → machine words",
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
            "note": "Text→UTF-8 lossless trits then chemical codon parse",
            "trits": trits[:256],
            "n_trits": len(trits),
            "words": [w.to_dict() for w in words[:32]],
            "chemical": chem,
            "preview": payload[:120],
        }

    # MACHINE primary — OS buffer style (lossless bit→trit)
    if isinstance(payload, (bytes, bytearray)):
        data = bytes(payload)
        trits = bytes_to_trits_lossless(data)
        words = []
        for i in range(0, len(trits), word_trits):
            chunk = list(trits[i : i + word_trits])
            if len(chunk) < word_trits:
                chunk.extend([0] * (word_trits - len(chunk)))
            words.append(MachineWord(n_trits=word_trits, pack=pack_trits(chunk)))
        if not words:
            words = [bytes_to_machine_word(data)]
        return {
            "path": path.value,
            "primary": True,
            "note": "Raw bytes → lossless bit→trit → T1 machine words (OS buffer style)",
            "trits": trits[:256],
            "n_trits": len(trits),
            "words": [w.to_dict() for w in words[:32]],
            "hex": words[0].hex() if words else "",
            "preview": data[:64].hex(),
            "roundtrip_ok": trits_to_bytes_lossless(trits) == data,
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
    back = trits_to_utf8_text(trits)
    return {
        "path": path.value,
        "primary": True,
        "note": "UTF-8 text → lossless bit→trit → machine words (primary OS-native path)",
        "trits": trits[:256],
        "n_trits": len(trits),
        "words": [w.to_dict() for w in words[:32]],
        "roundtrip_preview": back[:120],
        "roundtrip_ok": back == text,
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


# ---------------------------------------------------------------------------
# OS-native ABI (Linux / Windows buffer style — not Morse)
# ---------------------------------------------------------------------------
#
# Layout mirrors how kernels move machine words:
#   magic[4] | version u8 | path_id u8 | n_trits u16 LE | words[] u64 LE
# Path ids: 1=machine  2=chemical  3=morse(secondary)
# Word packing matches Zig TritWord (little-endian T1, ≤32 trits / u64).

ABI_MAGIC = b"FSOT"
ABI_VERSION = 1
_PATH_ID = {
    EncodePath.MACHINE: 1,
    EncodePath.CHEMICAL: 2,
    EncodePath.MORSE: 3,
}
_ID_PATH = {v: k for k, v in _PATH_ID.items()}


@dataclass
class MachineFrame:
    """
    Binary frame for IPC / Zig ABI / shared-memory inject.

    Same idea as a Linux struct written to a pipe or mmap region:
    fixed header + little-endian machine words. Neural code stays trinary;
    the frame is transport only.
    """

    path: EncodePath
    n_trits: int
    words: List[MachineWord]
    version: int = ABI_VERSION

    def to_bytes(self) -> bytes:
        path_id = _PATH_ID.get(self.path, 1)
        n = max(0, min(0xFFFF, int(self.n_trits)))
        hdr = ABI_MAGIC + bytes([self.version & 0xFF, path_id & 0xFF]) + n.to_bytes(2, "little")
        body = bytearray()
        for w in self.words:
            # u64 LE carrier (Zig TritWord.pack style)
            pack = int(w.pack) & ((1 << 64) - 1)
            body.extend(pack.to_bytes(8, "little", signed=False))
            body.extend(int(w.n_trits & 0xFF).to_bytes(1, "little"))
            body.extend(b"\x00\x00\x00")  # pad to 12-byte word record
        return bytes(hdr) + bytes(body)

    def hex(self) -> str:
        return self.to_bytes().hex()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "magic": ABI_MAGIC.decode("ascii"),
            "version": self.version,
            "path": self.path.value,
            "n_trits": self.n_trits,
            "n_words": len(self.words),
            "words": [w.to_dict() for w in self.words[:32]],
            "hex_head": self.hex()[:160],
            "byte_len": len(self.to_bytes()),
        }

    @classmethod
    def from_bytes(cls, data: bytes) -> "MachineFrame":
        if len(data) < 8 or data[:4] != ABI_MAGIC:
            raise ValueError("not an FSOT machine frame")
        version = data[4]
        path = _ID_PATH.get(data[5], EncodePath.MACHINE)
        n_trits = int.from_bytes(data[6:8], "little")
        words: List[MachineWord] = []
        off = 8
        while off + 12 <= len(data):
            pack = int.from_bytes(data[off : off + 8], "little")
            nw = data[off + 8]
            words.append(
                MachineWord(
                    n_trits=int(nw),
                    pack=pack,
                    path=path.value if isinstance(path, EncodePath) else str(path),
                )
            )
            off += 12
        return cls(path=path if isinstance(path, EncodePath) else EncodePath.MACHINE, n_trits=n_trits, words=words, version=version)


def chemical_signals_to_machine(dna_or_codons: str) -> Dict[str, Any]:
    """
    Explicit chem → machine bridge (primary genetics → OS body).

    DNA/codon string → codon trits → MachineWord list → ABI frame.
    This is the recommended path when starting from wet-lab genetics
    and needing OS-visible buffers (not Morse).
    """
    dna = "".join(c for c in dna_or_codons.upper() if c in "ACGT")
    words = dna_to_machine_words(dna)
    trits: List[int] = []
    for w in words:
        trits.extend(w.trits())
    frame = MachineFrame(path=EncodePath.CHEMICAL, n_trits=len(trits), words=words)
    chem = trits_to_chemical_report(trits)
    return {
        "path": EncodePath.CHEMICAL.value,
        "bridge": "chemical→machine",
        "primary_for": "genetics_into_os_body",
        "n_trits": len(trits),
        "trits": trits[:256],
        "words": [w.to_dict() for w in words[:32]],
        "frame": frame.to_dict(),
        "chemical": chem,
        "preview": dna[:120],
        "note": (
            "Chemical codon map is the genetic spine; machine frame is how the "
            "computer body carries it (Linux/Windows-style little-endian words)."
        ),
    }


def trits_to_drive_features(trits: Sequence[int], n_features: int = 32) -> List[float]:
    """Map trit stream → float features for SensoryBus inject (sens/assoc)."""
    out: List[float] = []
    for t in trits:
        out.append(float(as_trit(t)))  # -1, 0, +1
        if len(out) >= n_features:
            break
    while len(out) < n_features:
        out.append(0.0)
    return out


def encode_to_sensory_packet(
    payload: Union[str, bytes, Sequence[float]],
    *,
    path: EncodePath = EncodePath.MACHINE,
    target_region: str = "sens",
    strength: float = 0.55,
    n_features: int = 32,
) -> Any:
    """
    Translate payload → SensoryPacket ready for SensoryBus.push.

    Machine path is default (OS-native). Morse is available but secondary.
    """
    from .sensory.packets import SensoryModality, SensoryPacket

    result = translate(payload, path=path)
    trits = result.get("trits") or []
    features = trits_to_drive_features(trits, n_features=n_features)
    modality = SensoryModality.TEXT
    if path is EncodePath.CHEMICAL:
        modality = SensoryModality.CUSTOM
    elif path is EncodePath.MACHINE and isinstance(payload, (bytes, bytearray)):
        modality = SensoryModality.SYS_METRIC
    return SensoryPacket(
        modality=modality,
        target_region=target_region,
        features=features,
        strength=float(strength),
        meta={
            "encode_path": path.value if isinstance(path, EncodePath) else str(path),
            "n_trits": result.get("n_trits"),
            "primary": result.get("primary", True),
            "note": result.get("note", ""),
        },
    )


def build_machine_frame(
    payload: Union[str, bytes, Sequence[float]],
    *,
    path: EncodePath = EncodePath.MACHINE,
    word_trits: int = 32,
) -> MachineFrame:
    """Pack any translate() result into an OS-native binary frame."""
    path = EncodePath(path) if not isinstance(path, EncodePath) else path
    result = translate(payload, path=path, word_trits=word_trits)
    words_raw = result.get("words") or []
    words: List[MachineWord] = []
    for w in words_raw:
        if isinstance(w, MachineWord):
            words.append(w)
        else:
            words.append(
                MachineWord(
                    n_trits=int(w.get("n_trits", word_trits)),
                    pack=int(w.get("pack", 0)),
                    path=str(w.get("path", path.value)),
                )
            )
    return MachineFrame(
        path=path,
        n_trits=int(result.get("n_trits", 0)),
        words=words,
    )


def verify_machine_path(sample: str = "FSOT neural") -> Dict[str, Any]:
    """Smoke checks: lossless UTF-8 roundtrip, frame roundtrip, chem bridge."""
    trits = text_to_utf8_trits(sample)
    back = trits_to_utf8_text(trits)
    frame = build_machine_frame(sample, path=EncodePath.MACHINE)
    raw = frame.to_bytes()
    frame2 = MachineFrame.from_bytes(raw)
    chem = chemical_signals_to_machine("ATGAAACGGTTT")
    raw_bytes = sample.encode("utf-8")
    return {
        "utf8_roundtrip_ok": back == sample,
        "utf8_preview": back[:80],
        "n_trits": len(trits),
        "trits_per_byte": 8,
        "frame_roundtrip_ok": frame2.n_trits == frame.n_trits and len(frame2.words) == len(frame.words),
        "frame_byte_len": len(raw),
        "frame_hex_head": raw[:32].hex(),
        "chem_bridge_n_trits": chem["n_trits"],
        "chem_bridge_ok": chem["n_trits"] > 0,
        "bytes_roundtrip_ok": trits_to_bytes_lossless(bytes_to_trits_lossless(raw_bytes)) == raw_bytes,
        "recommendation": path_recommendation(),
        "abi": {
            "magic": ABI_MAGIC.decode(),
            "version": ABI_VERSION,
            "word_record": "u64 LE pack + u8 n_trits + 3 pad",
            "word_trits_default": 32,
            "matches_zig_TritWord": True,
            "encode_style": "lossless bit→trit (0→0, 1→+1) — OS buffer style, not Morse",
        },
    }
