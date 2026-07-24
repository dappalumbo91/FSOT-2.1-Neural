"""
FSOT trinary substrate — reference oracle for bare-metal ports.

Goal: trinary is the *machine* model (T = {-1,0,+1}), not a veneer on binary NNs.
Binary containers (T1/T3 packing into integer words) are *transport carriers*
during development; semantics and ops are trinary all the way down.

See docs/TRINARY_BARE_METAL.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union

import torch

Trit = int  # -1 | 0 | +1 only


def as_trit(x: Union[int, float]) -> Trit:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def neg(t: Trit) -> Trit:
    return as_trit(-int(t))


def pair(a: Trit, b: Trit) -> Trit:
    """Multiplicative pair in T (used in synaptic trinary term)."""
    return as_trit(int(a) * int(b))


def sum_sat(a: Trit, b: Trit) -> Trit:
    return as_trit(int(a) + int(b))


def consensus(a: Trit, b: Trit) -> Trit:
    return a if a == b else 0


def from_S(S: float, lo: float = -0.4, hi: float = 0.4) -> Trit:
    if S < lo:
        return -1
    if S > hi:
        return 1
    return 0


def base_primary(base: str) -> Trit:
    """A,G → +1; C,T → −1 (FSOT primary codon law)."""
    b = base.upper()
    if b in ("A", "G"):
        return 1
    if b in ("C", "T"):
        return -1
    raise ValueError(f"invalid base {base!r}")


def codon_primary(codon: str) -> Tuple[Trit, Trit, Trit]:
    if len(codon) != 3:
        raise ValueError("codon length must be 3")
    c = codon.upper()
    return base_primary(c[0]), base_primary(c[1]), base_primary(c[2])


# --- packing: trinary wire format on integer carriers (not the end ontology) ---

# T1: 2 bits per trit — 01 = +1, 11 = -1, 00 = 0; 10 illegal
_T1_POS = 0b01
_T1_NEG = 0b11
_T1_ZERO = 0b00


def pack_t1(t: Trit) -> int:
    t = as_trit(t)
    if t > 0:
        return _T1_POS
    if t < 0:
        return _T1_NEG
    return _T1_ZERO


def unpack_t1(bits: int) -> Trit:
    b = bits & 0b11
    if b == _T1_POS:
        return 1
    if b == _T1_NEG:
        return -1
    if b == _T1_ZERO:
        return 0
    raise ValueError(f"illegal T1 pattern {bin(b)}")


def pack_trits(trits: Sequence[Trit]) -> int:
    """Pack little-endian trit list into an int carrier (2 bits each)."""
    acc = 0
    for i, t in enumerate(trits):
        acc |= pack_t1(t) << (2 * i)
    return acc


def unpack_trits(word: int, n: int) -> List[Trit]:
    return [unpack_t1(word >> (2 * i)) for i in range(n)]


def pack_codon(codon: str) -> int:
    return pack_trits(list(codon_primary(codon)))


@dataclass
class TritWord:
    """Bare-metal-oriented word: n trits + integer carrier for transport."""

    n: int
    pack: int

    @classmethod
    def from_trits(cls, trits: Sequence[Trit]) -> "TritWord":
        ts = [as_trit(t) for t in trits]
        return cls(n=len(ts), pack=pack_trits(ts))

    def trits(self) -> List[Trit]:
        return unpack_trits(self.pack, self.n)

    def to_dict(self) -> Dict[str, Any]:
        return {"n": self.n, "pack": self.pack, "trits": self.trits()}


def quantize_features_to_trits(features: Sequence[float], n: int | None = None) -> List[Trit]:
    """
    Sensory edge: map real features → trit stream (threshold at 0).
    Future: multi-level ADC → native trinary cells.
    """
    vals = list(features)
    if n is not None:
        if len(vals) < n:
            vals = vals + [0.0] * (n - len(vals))
        else:
            vals = vals[:n]
    return [as_trit(v) for v in vals]


def torch_from_S(S: torch.Tensor, lo: float = -0.4, hi: float = 0.4) -> torch.Tensor:
    out = torch.zeros_like(S, dtype=torch.int8)
    out = torch.where(S < lo, torch.full_like(out, -1), out)
    out = torch.where(S > hi, torch.full_like(out, 1), out)
    return out


def self_test() -> Dict[str, Any]:
    errors: List[str] = []
    # ops
    if pair(1, -1) != -1:
        errors.append("pair")
    if sum_sat(1, 1) != 1:
        errors.append("sum_sat")
    if consensus(1, 1) != 1 or consensus(1, -1) != 0:
        errors.append("consensus")
    # packing round-trip
    for t in (-1, 0, 1):
        if unpack_t1(pack_t1(t)) != t:
            errors.append(f"t1 {t}")
    trip = codon_primary("ATG")
    if unpack_trits(pack_trits(list(trip)), 3) != list(trip):
        errors.append("codon pack")
    # AT
    for codon in ("ATG", "TTT", "AAA", "CCC"):
        p = codon_primary(codon)
        if len(p) != 3 or any(x not in (-1, 1) for x in p):
            # primary has no 0 for ACGT
            if any(x not in (-1, 0, 1) for x in p):
                errors.append(codon)
    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "substrate": "trinary",
        "carrier_note": "integer pack is transport only; ontology is T={-1,0,+1}",
        "sample_ATG": list(codon_primary("ATG")),
        "sample_word": TritWord.from_trits([1, -1, 0, 1]).to_dict(),
    }
