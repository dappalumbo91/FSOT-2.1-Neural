"""
ITU-grade Morse codec — letters, digits, punctuation, prosigns, math tokens.

This is the *interpretation layer* for reservoir signals: lossless round-trip
on the symbolic path (encode text → Morse units → ternary → decode).
Reservoir dynamics remain the fluid substrate; Morse is how we read it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paths import ROOT

DATA_PATH = ROOT / "data" / "itu_morse.json"


def load_itu_table(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or DATA_PATH
    return json.loads(p.read_text(encoding="utf-8"))


class ITUMorseCodec:
    """Full encode/decode with timing units (dit=1)."""

    def __init__(self, table: Optional[Dict[str, Any]] = None):
        self.table = table or load_itu_table()
        self.char_to_morse: Dict[str, str] = {}
        self.morse_to_char: Dict[str, str] = {}
        for section in ("letters", "digits", "punctuation"):
            for ch, code in self.table.get(section, {}).items():
                self.char_to_morse[ch.upper() if len(ch) == 1 else ch] = code
                # Prefer letters over colliding punctuation when decoding
                if code not in self.morse_to_char or section == "letters":
                    self.morse_to_char[code] = ch.upper() if len(ch) == 1 and ch.isalpha() else ch
        for name, code in self.table.get("prosigns", {}).items():
            self.char_to_morse[f"<{name}>"] = code
            if code not in self.morse_to_char:
                self.morse_to_char[code] = f"<{name}>"
        for name, code in self.table.get("math_tokens", {}).items():
            self.char_to_morse[f"[{name}]"] = code

    def encode_char(self, ch: str) -> str:
        if ch == " ":
            return " "
        key = ch.upper() if ch.isalpha() else ch
        if key not in self.char_to_morse:
            raise KeyError(f"no ITU Morse mapping for {ch!r}")
        return self.char_to_morse[key]

    def encode_text(self, text: str, *, strict: bool = False) -> str:
        """Return Morse string with / between words, spaces between letters."""
        words = text.strip().split()
        out_words: List[str] = []
        for w in words:
            letters: List[str] = []
            for ch in w:
                key = ch.upper() if ch.isalpha() else ch
                if key in self.char_to_morse:
                    letters.append(self.char_to_morse[key])
                elif strict:
                    raise KeyError(f"unmapped character {ch!r}")
                # skip unmapped in non-strict
            if letters:
                out_words.append(" ".join(letters))
        return " / ".join(out_words)

    def decode_morse_string(self, morse: str) -> str:
        words = [w.strip() for w in morse.split(" / ")]
        decoded_words: List[str] = []
        for w in words:
            if not w:
                continue
            letters = []
            for tok in w.split():
                letters.append(self.morse_to_char.get(tok, "?"))
            decoded_words.append("".join(letters))
        return " ".join(decoded_words)

    # --- unit / ternary timing path (lossless when clean) ---

    def text_to_units(self, text: str) -> List[int]:
        """
        On/off keying stream: 1 = mark (carrier), 0 = space.
        dit mark=1, dah mark=111, intra-element gap=0, letter gap=000, word=0000000
        """
        stream: List[int] = []
        words = text.strip().split()
        for wi, w in enumerate(words):
            if wi:
                stream.extend([0] * 7)
            first_letter = True
            for ch in w:
                key = ch.upper() if ch.isalpha() else ch
                code = self.char_to_morse.get(key)
                if not code:
                    continue
                if not first_letter:
                    stream.extend([0] * 3)
                first_letter = False
                for ei, el in enumerate(code):
                    if ei:
                        stream.append(0)  # intra-char gap
                    stream.extend([1] * (1 if el == "." else 3))
        return stream

    def units_to_ternary(self, units: Sequence[int]) -> List[int]:
        """
        Map OOK units → FSOT trinary:
          mark run len 1 → -1 (dit / damped short)
          mark run len ≥2 → +1 (dah / emergent long)
          space → 0
        """
        tern: List[int] = []
        i = 0
        n = len(units)
        while i < n:
            if units[i] == 0:
                tern.append(0)
                i += 1
                continue
            j = i
            while j < n and units[j] == 1:
                j += 1
            run = j - i
            tern.append(-1 if run <= 1 else 1)
            # expand to run length for temporal alignment with reservoir T
            for _ in range(run - 1):
                tern.append(tern[-1])
            i = j
        return tern

    def ternary_to_units_approx(self, ternary: Sequence[int]) -> List[int]:
        """Inverse of units_to_ternary (best-effort on noisy streams)."""
        units: List[int] = []
        i = 0
        n = len(ternary)
        while i < n:
            v = int(ternary[i])
            if v == 0:
                units.append(0)
                i += 1
                continue
            j = i
            while j < n and int(ternary[j]) == v:
                j += 1
            run = j - i
            if v == 1:
                # dah
                units.extend([1] * max(3, run if run >= 2 else 3))
            else:
                units.extend([1] * 1)
            i = j
        return units

    def units_to_morse_string(self, units: Sequence[int]) -> str:
        """Parse OOK unit stream → Morse letter string (ITU timing)."""
        # Find mark runs and space runs
        tokens: List[str] = []
        i = 0
        n = len(units)
        letter_elems: List[str] = []
        while i < n:
            if units[i] == 1:
                j = i
                while j < n and units[j] == 1:
                    j += 1
                run = j - i
                letter_elems.append("." if run <= 1 else "-")
                i = j
            else:
                j = i
                while j < n and units[j] == 0:
                    j += 1
                gap = j - i
                i = j
                if gap >= 7:
                    if letter_elems:
                        tokens.append("".join(letter_elems))
                        letter_elems = []
                    tokens.append("/")  # word gap marker
                elif gap >= 3:
                    if letter_elems:
                        tokens.append("".join(letter_elems))
                        letter_elems = []
                # gap==1: intra-element, continue letter
        if letter_elems:
            tokens.append("".join(letter_elems))

        # Build morse string
        parts: List[str] = []
        word: List[str] = []
        for t in tokens:
            if t == "/":
                if word:
                    parts.append(" ".join(word))
                    word = []
            else:
                word.append(t)
        if word:
            parts.append(" ".join(word))
        return " / ".join(parts)

    def ternary_to_text(self, ternary: Sequence[int]) -> Tuple[str, str]:
        """Noisy-tolerant: ternary → units → morse → text."""
        # Compress runs for parsing
        compressed: List[int] = []
        units: List[int] = []
        i = 0
        n = len(ternary)
        while i < n:
            v = int(ternary[i])
            j = i
            while j < n and int(ternary[j]) == v:
                j += 1
            run = j - i
            if v == 0:
                # map long zeros to letter/word gaps
                if run >= 6:
                    units.extend([0] * 7)
                elif run >= 3:
                    units.extend([0] * 3)
                else:
                    units.extend([0] * max(1, run))
            elif v == 1:
                units.extend([1] * (3 if run >= 2 else 1))
                units.append(0)  # intra
            else:  # -1 dit
                units.extend([1])
                units.append(0)
            i = j
        morse = self.units_to_morse_string(units)
        text = self.decode_morse_string(morse.replace(" / ", " / "))
        return text, morse

    def roundtrip_accuracy(self, text: str) -> Dict[str, Any]:
        """Lossless symbolic path check (no reservoir)."""
        # Normalize: uppercase alnum + spaces + known punct
        norm = []
        for ch in text.upper():
            if ch == " " or ch in self.char_to_morse or ch.isalpha() or ch.isdigit():
                if ch.isalpha() or ch.isdigit() or ch in self.char_to_morse or ch == " ":
                    norm.append(ch)
        cleaned = "".join(norm)
        # collapse spaces
        cleaned = " ".join(cleaned.split())
        morse = self.encode_text(cleaned)
        decoded = self.decode_morse_string(morse)
        units = self.text_to_units(cleaned)
        morse2 = self.units_to_morse_string(units)
        decoded2 = self.decode_morse_string(morse2)
        # character accuracy
        def acc(a: str, b: str) -> float:
            n = max(len(a), len(b), 1)
            m = min(len(a), len(b))
            match = sum(1 for i in range(m) if a[i] == b[i])
            return match / n

        return {
            "input_normalized": cleaned,
            "morse": morse,
            "decoded_from_morse": decoded,
            "decoded_from_units": decoded2,
            "exact_morse_path": decoded == cleaned,
            "exact_units_path": decoded2 == cleaned,
            "char_accuracy_morse": acc(decoded, cleaned),
            "char_accuracy_units": acc(decoded2, cleaned),
        }


def verify_morse_tables() -> Dict[str, Any]:
    """Self-test: every letter/digit round-trips."""
    c = ITUMorseCodec()
    fails = []
    for ch, code in list(c.table["letters"].items()) + list(c.table["digits"].items()):
        enc = c.encode_text(ch)
        dec = c.decode_morse_string(enc)
        if dec != ch.upper() and dec != ch:
            fails.append({"ch": ch, "enc": enc, "dec": dec})
    # phrase
    phrase = "FSOT 2.1"
    # strip unsupported if any
    rt = c.roundtrip_accuracy("HELLO WORLD 123")
    return {
        "table_entries": len(c.char_to_morse),
        "letter_digit_fails": fails,
        "letter_digit_ok": len(fails) == 0,
        "phrase_test": rt,
        "standard": c.table.get("standard"),
    }
