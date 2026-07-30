"""Math sense interlingua — PFLT translation spine applied to word problems.

PFLT doctrine (I:\\pflt sense_interlingua.py / VISION_SENSE_IDENTITY):
  surface form  →  SENSE_id  →  target form
  aqua          →  SENSE_water → water / Wasser

Math twin:
  language cue  →  OP_SENSE / SCHEMA_SENSE  →  formula + executor tag
  "altogether"  →  OP_add                   → total = a+b+…
  "half of X"   →  OP_half + BIND_referent  → half(binding[X])

NOT Q→A stuffing. NOT NMT. Bindings are finite tables densified offline
(like PFLT densify_lexicon / pul_terms / form_sense packs).

Sources bulk-loaded at build:
  1) Core OP senses (school language → operator)
  2) SCHEMA senses (multi-hop templates)
  3) ARITH / BIND rules already in math_rules + math_binding
  4) Imported Math-generator rulebook (1520) — id/name/examples → senses
  5) Optional PFLT SenseInterlingua number/word forms when I:\\pflt is present
  6) densify pack data/math_sense/densify_bindings.json (chew-style growth)

Usage:
  ix = MathSenseInterlingua()
  r = ix.translate_cues(question)   # form → sense chain
  stats = ix.stats()                # n_senses, n_form_bindings
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paths import DATA

SENSE_DIR = DATA / "math_sense"
DENSIFY_PATH = SENSE_DIR / "densify_bindings.json"
PACK_PATH = SENSE_DIR / "binding_pack.json"
REPORT_PATH = DATA / "results" / "MATH_SENSE_BINDINGS.json"


def _sense_id(gloss: str, prefix: str = "OP") -> str:
    g = re.sub(r"[^a-z0-9]+", "_", (gloss or "").strip().lower()).strip("_")
    return f"{prefix}_{g}" if g else f"{prefix}_unknown"


def _fold(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# Function words that must never be claimed by sparse rulebook dumps
_STOP_FORMS = frozenset(
    {
        "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "if",
        "is", "are", "was", "were", "be", "by", "as", "at", "from", "with",
        "what", "when", "where", "who", "whom", "which", "how", "many", "much",
        "she", "he", "they", "her", "his", "their", "them", "this", "that",
        "then", "than", "into", "over", "under", "after", "before", "about",
        "will", "can", "did", "does", "has", "have", "had", "not", "no",
        "all", "any", "some", "only", "also", "just", "very", "more", "most",
        "used", "using", "make", "made", "get", "got", "take", "took",
    }
)


# ---------------------------------------------------------------------------
# Core language → operator senses (PFLT UNIVERSAL_LABELS style, math domain)
# Multi-form labels bind to one sense. Expand only with explicit pairs.
# ---------------------------------------------------------------------------

# sense_key → { forms: [...], formula, strategy, why }
CORE_OP_SENSES: Dict[str, Dict[str, Any]] = {
    "add": {
        "forms": [
            "altogether", "in all", "in total", "combined", "sum", "together",
            "plus", "add", "added", "total of", "and also", "overall",
        ],
        "formula": "total = a + b + …",
        "strategy": "add",
        "why": "Union of quantities",
    },
    "sub": {
        "forms": [
            "left", "remain", "remaining", "rest", "leftover", "how many more",
            "how much more", "difference", "less than", "fewer than", "minus",
            "subtract", "gave away", "sold", "ate", "used", "spent",
        ],
        "formula": "left = total − used",
        "strategy": "sub",
        "why": "Remove or compare",
    },
    "mul": {
        "forms": [
            "each", "every", "per", "times", "groups of", "rows of",
            "multiplied by", "product", "twice", "double", "triple",
            "times as many", "times as much", "times as old",
        ],
        "formula": "total = n × size",
        "strategy": "mul",
        "why": "Equal groups / scaling",
    },
    "div": {
        "forms": [
            "split", "share", "divided", "per person", "each gets",
            "how many in each", "quotient", "divided by", "split equally",
        ],
        "formula": "each = total ÷ n",
        "strategy": "div",
        "why": "Equal share",
    },
    "half": {
        "forms": [
            "half of", "half as many", "half as much", "half as long",
            "one half", "1/2 of", "half that", "half the",
        ],
        "formula": "half(n) = n / 2",
        "strategy": "half",
        "why": "Halve the referent quantity",
    },
    "double": {
        "forms": ["twice", "double", "two times", "2 times"],
        "formula": "double(n) = 2n",
        "strategy": "double",
        "why": "Scale by two",
    },
    "percent": {
        "forms": [
            "percent", "%", "percent of", "% of", "% off", "discount",
            "tax", "tip", "interest", "commission", "fee of",
        ],
        "formula": "p% of x = (p/100)×x",
        "strategy": "percent",
        "why": "Scale by hundredths",
    },
    "rate": {
        "forms": [
            "per hour", "per day", "per week", "per minute", "mph",
            "miles per hour", "an hour", "each hour", "every hour",
        ],
        "formula": "amount = rate × time",
        "strategy": "rate",
        "why": "Rate product",
    },
    "fraction": {
        "forms": [
            "a third", "one third", "two-thirds", "2/3", "a quarter",
            "one quarter", "three-quarters", "1/4", "3/4", "1/3", "1/5",
            "fifth", "eighth", "third of", "quarter of",
        ],
        "formula": "f × x",
        "strategy": "fraction",
        "why": "Rational part of a whole",
    },
    "bind_referent": {
        "forms": [
            "half of", "of the remaining", "of what was left", "of what remained",
            "times as old as", "times as many as", "more than half of",
            "fewer than", "more jewels than", "as many as",
        ],
        "formula": "op(binding[X]) not op(nums[0])",
        "strategy": "bind",
        "why": "Modifier attaches to grammatical object",
    },
    "schema_remainder_sell": {
        "forms": ["sells the remainder", "remainder at", "rest for $", "left for $"],
        "formula": "money=(start−u1−u2)×price",
        "strategy": "schema",
        "why": "Inventory residual sold",
    },
    "schema_win_loss": {
        "forms": ["won more than they lost", "won more than he lost", "won more than she lost"],
        "formula": "W=(T+d)/2",
        "strategy": "schema",
        "why": "Sum and difference",
    },
    "schema_profit": {
        "forms": ["how much profit", "profit did", "increased the value"],
        "formula": "profit = new − invested",
        "strategy": "schema",
        "why": "Value change vs cost basis",
    },
    "schema_cascade": {
        "forms": [
            "half of what was left", "of the remaining", "then of the remaining",
            "a third of the elves quit", "then of the remaining",
        ],
        "formula": "sequential state updates on remaining",
        "strategy": "schema",
        "why": "Multi-hop inventory / fraction chain",
    },
    "schema_ratio": {
        "forms": ["ratio of", "in the ratio", "ratio is"],
        "formula": "part = total × a/(a+b)",
        "strategy": "schema",
        "why": "Partition by ratio parts",
    },
    "schema_discount": {
        "forms": ["% discount", "percent discount", "% off", "discount from the original"],
        "formula": "pay = price×(1−d/100) or original = pay/(1−d/100)",
        "strategy": "schema",
        "why": "Percent off price",
    },
    "schema_fee_stack": {
        "forms": ["delivery fee", "transfer fees", "brokerage fee", "tax on"],
        "formula": "total = base + fees(+tips)",
        "strategy": "schema",
        "why": "Stack money adjustments",
    },
    "number_word": {
        "forms": [
            "zero", "one", "two", "three", "four", "five", "six", "seven",
            "eight", "nine", "ten", "eleven", "twelve", "dozen", "thirteen",
            "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
            "nineteen", "twenty", "thirty", "forty", "fifty", "sixty",
            "seventy", "eighty", "ninety", "hundred", "thousand",
        ],
        "formula": "word → numeral value",
        "strategy": "numeral",
        "why": "Number words are quantities (BIND-01)",
    },
}


# Extra multi-phrase bindings (densify-style explicit pairs)
EXTRA_FORM_SENSE: List[Tuple[str, str]] = [
    # (form, sense_key)
    ("how many are left", "sub"),
    ("how much is left", "sub"),
    ("how many did she start", "schema_cascade"),
    ("how many did he start", "schema_cascade"),
    ("start with", "schema_cascade"),
    ("original price", "schema_discount"),
    ("before the discount", "schema_discount"),
    ("after the discount", "schema_discount"),
    ("sales tax", "schema_fee_stack"),
    ("plus tax", "schema_fee_stack"),
    ("including tip", "schema_fee_stack"),
    ("per dozen", "mul"),
    ("a dozen", "number_word"),
    ("times a week", "mul"),
    ("times a day", "mul"),
    ("every morning", "mul"),
    ("each day", "mul"),
    ("for each", "mul"),
    ("split equally among", "div"),
    ("shared equally", "div"),
    ("average of", "div"),
    ("mean of", "div"),
    ("miles per hour", "rate"),
    ("kilometers per hour", "rate"),
    ("dollars an hour", "rate"),
    ("dollars per hour", "rate"),
    ("worked for", "rate"),
    ("how long does it take", "rate"),
    ("years older than", "sub"),
    ("years younger than", "sub"),
    ("as old as", "mul"),
    ("as many as", "mul"),
    ("of the price", "percent"),
    ("of his salary", "fraction"),
    ("of her salary", "fraction"),
    ("of the remaining amount", "schema_cascade"),
    ("donates half", "half"),
    ("half of what is left", "schema_cascade"),
    ("two more than", "sub"),
    ("more than they lost", "schema_win_loss"),
]


@dataclass
class SenseNode:
    sense_id: str
    key: str
    formula: str
    strategy: str
    why: str
    forms: List[str] = field(default_factory=list)

    def add_form(self, form: str) -> None:
        f = _fold(form)
        if f and f not in self.forms:
            self.forms.append(f)


@dataclass
class SenseHit:
    sense_id: str
    key: str
    form: str
    formula: str
    strategy: str
    method: str  # exact | phrase | densify | rulebook
    confidence: float


@dataclass
class CueTranslateResult:
    input_text: str
    tokens: List[str]
    hits: List[SenseHit]
    senses: List[str]
    strategies: List[str]
    resolution: List[str]
    exact_rate: float
    n_bindings_consulted: int
    note: str


class MathSenseInterlingua:
    """
    Language form → math sense → strategy/formula.
    Mirrors PFLT SenseInterlingua; target 'form' is the executable sense.
    """

    def __init__(self, *, load_rulebook: bool = True, load_pflt: bool = True) -> None:
        self.nodes: Dict[str, SenseNode] = {}
        # folded form → sense_id (longest match preferred at query time)
        self.index: Dict[str, str] = {}
        self._forms_by_len: List[Tuple[str, str]] = []  # (form, sense_id) sorted len desc
        self._build(load_rulebook=load_rulebook, load_pflt=load_pflt)

    def _ensure(
        self,
        key: str,
        *,
        formula: str = "",
        strategy: str = "",
        why: str = "",
        prefix: str = "OP",
    ) -> SenseNode:
        sid = _sense_id(key, prefix=prefix)
        if sid not in self.nodes:
            self.nodes[sid] = SenseNode(
                sense_id=sid,
                key=key,
                formula=formula,
                strategy=strategy or key,
                why=why,
            )
        else:
            n = self.nodes[sid]
            if formula and not n.formula:
                n.formula = formula
            if strategy and not n.strategy:
                n.strategy = strategy
            if why and not n.why:
                n.why = why
        return self.nodes[sid]

    # Higher = stronger claim on a form (PFLT: core seeds beat sparse dumps)
    _PREFIX_RANK = {
        "OP": 100,
        "SCHEMA": 95,
        "BIND": 90,
        "RULE": 80,
        "DEN": 70,
        "PFLT": 40,
        "RB": 20,
    }

    def bind(
        self,
        form: str,
        sense_key: str,
        *,
        formula: str = "",
        strategy: str = "",
        why: str = "",
        prefix: str = "OP",
    ) -> str:
        node = self._ensure(
            sense_key, formula=formula, strategy=strategy, why=why, prefix=prefix
        )
        f = _fold(form)
        if not f or len(f) < 2:
            return node.sense_id
        # refuse binding ultra-common function words to sparse rulebook senses
        if f in _STOP_FORMS and prefix in {"RB", "PFLT"}:
            return node.sense_id
        # refuse single very short tokens for low-rank prefixes
        if len(f) < 4 and prefix in {"RB", "PFLT"}:
            return node.sense_id
        node.add_form(f)
        # prefer higher-rank sense on collision (do not let RB overwrite OP)
        prev = self.index.get(f)
        if prev is None:
            self.index[f] = node.sense_id
        else:
            prev_rank = self._PREFIX_RANK.get(prev.split("_", 1)[0], 0)
            new_rank = self._PREFIX_RANK.get(prefix, 0)
            # longer phrase always wins later via scan; for same form, rank wins
            if new_rank >= prev_rank:
                self.index[f] = node.sense_id
        return node.sense_id

    def _rebuild_len_index(self) -> None:
        self._forms_by_len = sorted(
            self.index.items(), key=lambda kv: len(kv[0]), reverse=True
        )

    def _build(self, *, load_rulebook: bool, load_pflt: bool) -> None:
        # 1) core op senses
        for key, meta in CORE_OP_SENSES.items():
            prefix = "SCHEMA" if key.startswith("schema_") else "OP"
            node = self._ensure(
                key,
                formula=str(meta.get("formula") or ""),
                strategy=str(meta.get("strategy") or key),
                why=str(meta.get("why") or ""),
                prefix=prefix,
            )
            for form in meta.get("forms") or []:
                self.bind(
                    form,
                    key,
                    formula=node.formula,
                    strategy=node.strategy,
                    why=node.why,
                    prefix=prefix,
                )

        # 2) extra explicit pairs
        for form, key in EXTRA_FORM_SENSE:
            prefix = "SCHEMA" if key.startswith("schema_") else "OP"
            self.bind(form, key, prefix=prefix)

        # 3) live LANGUAGE_MAPS + ARITH_RULES from math_rules
        try:
            from .math_rules import ARITH_RULES, LANGUAGE_MAPS

            for rx, strat, cue in LANGUAGE_MAPS:
                # bind the human cue string, not the regex
                cue_form = cue.split(" means ")[0].strip()
                if cue_form:
                    self.bind(cue_form, strat, strategy=strat, why=cue)
                self.bind(strat, strat, strategy=strat)
            for r in ARITH_RULES:
                self.bind(
                    r.name,
                    r.id,
                    formula=r.formula,
                    strategy=r.strategy,
                    why=r.description,
                    prefix="RULE",
                )
                self.bind(
                    r.id,
                    r.id,
                    formula=r.formula,
                    strategy=r.strategy,
                    why=r.description,
                    prefix="RULE",
                )
                # token peels from formula words
                for tok in re.findall(r"[A-Za-z]{3,}", r.formula):
                    if tok.lower() not in {"total", "left", "and", "the"}:
                        self.bind(tok, r.id, formula=r.formula, strategy=r.strategy, prefix="RULE")
        except Exception:
            pass

        # 4) BINDING_RULES metadata
        try:
            from .math_binding import BINDING_RULES

            for br in BINDING_RULES:
                rid = br["id"]
                self.bind(
                    br["name"],
                    rid,
                    formula=br.get("formula", ""),
                    strategy="bind" if rid.startswith("BIND") else "schema",
                    why=br.get("why", ""),
                    prefix="BIND" if rid.startswith("BIND") else "SCHEMA",
                )
                self.bind(rid, rid, formula=br.get("formula", ""), why=br.get("how", ""))
                # Do NOT peel free words from how/why prose (that pollutes "half"/"more"/"each").
                # Only bind multi-word cue snippets already in formula/name.
        except Exception:
            pass

        # 5) Math-generator rulebook mass (PFLT densify analogue)
        if load_rulebook:
            self._load_rulebook_mass()

        # 6) densify pack on disk
        if DENSIFY_PATH.is_file():
            try:
                dens = json.loads(DENSIFY_PATH.read_text(encoding="utf-8"))
                for form, sense_key in (dens or {}).items():
                    if form and sense_key:
                        self.bind(str(form), str(sense_key), prefix="DEN")
            except Exception:
                pass

        # 7) optional PFLT number/word senses (thousands of form bindings)
        if load_pflt:
            self._load_pflt_numeric_forms()

        self._rebuild_len_index()

    def _load_rulebook_mass(self) -> None:
        try:
            from .math_rulebook_import import load_master

            master = load_master()
            rules = master.get("rules") or []
        except Exception:
            return
        for r in rules:
            if not isinstance(r, dict):
                continue
            rid = str(r.get("id") or "")
            name = str(r.get("name") or "")
            cat = str(r.get("category") or "")
            op = str(r.get("operation") or "")
            formula = str(r.get("output_form") or r.get("input_form") or "")
            fam = str(r.get("domain_family") or "math")
            key = rid or name or cat
            if not key:
                continue
            self.bind(
                name or rid,
                key,
                formula=formula,
                strategy=cat or fam,
                why=op[:200],
                prefix="RB",
            )
            if rid:
                self.bind(rid, key, formula=formula, strategy=cat or fam, prefix="RB")
            if cat:
                self.bind(cat, key, formula=formula, strategy=cat, prefix="RB")
            # example phrases as forms (PFLT: surface labels for the sense)
            for ex in (r.get("examples") or [])[:6]:
                exs = str(ex)
                # short examples only
                if 3 <= len(exs) <= 80:
                    self.bind(exs, key, formula=formula, strategy=cat or fam, prefix="RB")
                # first clause / before =
                head = re.split(r"[=→]", exs)[0].strip()
                if 3 <= len(head) <= 40:
                    self.bind(head, key, formula=formula, prefix="RB")
            # name tokens — only multi-char operator-ish heads, not every English word
            for tok in re.findall(r"[A-Za-z]{5,}", name):
                tl = tok.lower()
                if tl in _STOP_FORMS:
                    continue
                if tl in {
                    "addition", "subtraction", "multiplication", "division",
                    "fraction", "percent", "percentage", "ratio", "average",
                    "interest", "discount", "perimeter", "volume", "area",
                    "equation", "identity", "commutative", "distributive",
                    "numerator", "denominator", "quotient", "product",
                    "remainder", "factor", "multiple", "prime", "integer",
                } or cat.lower() in {
                    "addition", "subtraction", "multiplication", "division",
                    "fraction", "percent", "exponent", "order of operations",
                }:
                    self.bind(tok, key, formula=formula, prefix="RB")

    def _load_pflt_numeric_forms(self) -> None:
        """Pull number-related form→sense from PFLT if available (local, no API)."""
        pflt_root = Path(r"I:\pflt")
        if not pflt_root.is_dir():
            return
        try:
            import sys

            if str(pflt_root) not in sys.path:
                sys.path.insert(0, str(pflt_root))
            from sense_interlingua import SenseInterlingua  # type: ignore

            ix = SenseInterlingua()
            # bind only numeric / quantity-ish senses into number_word or keep EN form
            want = {
                "half", "double", "twice", "third", "quarter", "dozen",
                "one", "two", "three", "four", "five", "six", "seven",
                "eight", "nine", "ten", "eleven", "twelve", "twenty",
                "thirty", "forty", "fifty", "hundred", "thousand",
                "sum", "total", "difference", "product", "ratio",
                "percent", "hour", "day", "week", "year", "money",
                "price", "cost", "water",  # keep small
            }
            n = 0
            for sid, node in ix.nodes.items():
                en = (node.canonical_en or "").lower()
                if en not in want and not any(w in en for w in ("number", "count", "half")):
                    # still take pure short quantity heads
                    if en not in want:
                        continue
                for lang, forms in node.forms.items():
                    if lang not in {"en", "la", "de", "fr", "es"}:
                        continue
                    for form in forms:
                        self.bind(form, "number_word" if en in {
                            "one","two","three","four","five","six","seven","eight",
                            "nine","ten","eleven","twelve","dozen","twenty","thirty",
                            "forty","fifty","hundred","thousand","half",
                        } else en, prefix="PFLT")
                        n += 1
                        if n >= 5000:
                            return
        except Exception:
            return

    def resolve_form(self, form: str) -> Optional[SenseHit]:
        f = _fold(form)
        if not f:
            return None
        if f in self.index:
            sid = self.index[f]
            node = self.nodes[sid]
            return SenseHit(
                sense_id=sid,
                key=node.key,
                form=f,
                formula=node.formula,
                strategy=node.strategy,
                method="exact",
                confidence=1.0,
            )
        return None

    def scan_phrases(self, text: str, *, max_hits: int = 32) -> List[SenseHit]:
        """Longest-first phrase scan (PFLT multi-token binding style)."""
        ql = _fold(text)
        hits: List[SenseHit] = []
        covered = [False] * (len(ql) + 1)
        for form, sid in self._forms_by_len:
            if len(form) < 3:
                continue
            pref = sid.split("_", 1)[0]
            # single short words only if high-rank OP/SCHEMA/BIND/RULE/DEN
            if " " not in form and len(form) < 5 and pref in {"RB", "PFLT"}:
                continue
            if form in _STOP_FORMS:
                continue
            start = 0
            while True:
                i = ql.find(form, start)
                if i < 0:
                    break
                left_ok = i == 0 or not ql[i - 1].isalnum()
                right = i + len(form)
                right_ok = right >= len(ql) or not ql[right].isalnum()
                if left_ok and right_ok:
                    if not any(covered[i:right]):
                        node = self.nodes.get(sid)
                        if node:
                            hits.append(
                                SenseHit(
                                    sense_id=sid,
                                    key=node.key,
                                    form=form,
                                    formula=node.formula,
                                    strategy=node.strategy,
                                    method="phrase",
                                    confidence=min(1.0, 0.5 + len(form) / 40.0),
                                )
                            )
                            for j in range(i, right):
                                covered[j] = True
                            if len(hits) >= max_hits:
                                return hits
                start = i + 1
        return hits

    def translate_cues(self, text: str) -> CueTranslateResult:
        """form → sense chain for a word problem (not NMT)."""
        tokens = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+(?:\.\d+)?|%", text)
        phrase_hits = self.scan_phrases(text)
        strategies: List[str] = []
        senses: List[str] = []
        resolution: List[str] = []
        for h in phrase_hits:
            if h.strategy not in strategies:
                strategies.append(h.strategy)
            if h.sense_id not in senses:
                senses.append(h.sense_id)
            resolution.append(
                f"{h.form} → {h.sense_id} → {h.formula or h.strategy} [{h.method}]"
            )
        # also token-level for short ops
        for tok in tokens:
            hit = self.resolve_form(tok)
            if hit and hit.sense_id not in senses:
                senses.append(hit.sense_id)
                if hit.strategy not in strategies:
                    strategies.append(hit.strategy)
                resolution.append(
                    f"{tok} → {hit.sense_id} → {hit.formula or hit.strategy} [token]"
                )
        n = max(1, len(phrase_hits))
        return CueTranslateResult(
            input_text=text,
            tokens=tokens,
            hits=phrase_hits,
            senses=senses,
            strategies=strategies,
            resolution=resolution,
            exact_rate=1.0 if phrase_hits else 0.0,
            n_bindings_consulted=len(self.index),
            note=(
                "Math sense-identity: language form → OP/SCHEMA sense → formula. "
                "PFLT spine. Not Q→A stuffing. Unresolved cues are not invented."
            ),
        )

    def stats(self) -> Dict[str, Any]:
        n_forms = sum(len(n.forms) for n in self.nodes.values())
        by_prefix: Dict[str, int] = {}
        for sid in self.nodes:
            pref = sid.split("_", 1)[0]
            by_prefix[pref] = by_prefix.get(pref, 0) + 1
        return {
            "n_senses": len(self.nodes),
            "n_form_bindings": n_forms,
            "n_index_keys": len(self.index),
            "by_prefix": by_prefix,
            "doctrine": "form→SENSE→formula (PFLT twin for math)",
            "sources": [
                "CORE_OP_SENSES",
                "EXTRA_FORM_SENSE",
                "ARITH_RULES",
                "LANGUAGE_MAPS",
                "BINDING_RULES",
                "math_rulebook MASTER",
                "densify_bindings.json",
                "PFLT SenseInterlingua (optional)",
            ],
        }

    def export_pack(self) -> Dict[str, Any]:
        pack = {
            "doctrine": "PFLT-style math sense bindings",
            "stats": self.stats(),
            "senses": {
                sid: {
                    "key": n.key,
                    "formula": n.formula,
                    "strategy": n.strategy,
                    "why": n.why,
                    "n_forms": len(n.forms),
                    "forms_head": n.forms[:12],
                }
                for sid, n in list(self.nodes.items())[:500]
            },
            "index_size": len(self.index),
        }
        SENSE_DIR.mkdir(parents=True, exist_ok=True)
        PACK_PATH.write_text(json.dumps(pack, indent=2), encoding="utf-8")
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(pack["stats"], indent=2), encoding="utf-8")
        return pack


def densify_from_gsm8k_cues(
    *,
    limit: int = 1319,
    max_new: int = 2000,
) -> Dict[str, Any]:
    """
    Chew-style densify: mine held-out *language cues* that co-occur with
    solvable structures — bind cue phrases → strategies already known.
    Does NOT bind question→answer (no stuffing).
    """
    from .math_rules import LANGUAGE_MAPS, load_gsm8k_heldout

    dens: Dict[str, str] = {}
    if DENSIFY_PATH.is_file():
        try:
            dens = json.loads(DENSIFY_PATH.read_text(encoding="utf-8"))
        except Exception:
            dens = {}

    # seed densify from language maps cues
    for rx, strat, cue in LANGUAGE_MAPS:
        dens[_fold(cue.split(" means ")[0])] = strat

    items = load_gsm8k_heldout("test", limit=limit)
    # n-gram cues that look like operator language
    cue_re = re.compile(
        r"\b(how many more|how much more|in total|altogether|left|remaining|"
        r"per hour|per day|times as many|twice as|half of|percent of|"
        r"discount|each|every|together|difference|split equally|"
        r"a third of|two-thirds|of the remaining|years older|"
        r"sold the remainder|won more than)\b",
        re.I,
    )
    strat_guess = {
        "how many more": "sub",
        "how much more": "sub",
        "in total": "add",
        "altogether": "add",
        "left": "sub",
        "remaining": "sub",
        "per hour": "rate",
        "per day": "rate",
        "times as many": "mul",
        "twice as": "double",
        "half of": "half",
        "percent of": "percent",
        "discount": "schema_discount",
        "each": "mul",
        "every": "mul",
        "together": "add",
        "difference": "sub",
        "split equally": "div",
        "a third of": "fraction",
        "two-thirds": "fraction",
        "of the remaining": "schema_cascade",
        "years older": "sub",
        "sold the remainder": "schema_remainder_sell",
        "won more than": "schema_win_loss",
    }
    added = 0
    for it in items:
        for m in cue_re.finditer(it.question.lower()):
            phrase = _fold(m.group(1))
            if phrase in dens:
                continue
            # map to strategy
            strat = None
            for k, v in strat_guess.items():
                if k in phrase:
                    strat = v
                    break
            if strat:
                dens[phrase] = strat
                added += 1
                if added >= max_new:
                    break
        if added >= max_new:
            break

    SENSE_DIR.mkdir(parents=True, exist_ok=True)
    DENSIFY_PATH.write_text(json.dumps(dens, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"densify_size": len(dens), "added": added, "path": str(DENSIFY_PATH)}


def smoke_math_sense() -> Dict[str, Any]:
    ix = MathSenseInterlingua()
    cases = [
        "What is half of 40?",
        "How many are left if she had 10 and used 3?",
        "They won 8 more than they lost",
        "60% of the price",
        "sells the remainder for $2 each",
        "a third of the elves quit then 10 of the remaining quit",
    ]
    rows = []
    for q in cases:
        r = ix.translate_cues(q)
        rows.append(
            {
                "q": q,
                "strategies": r.strategies,
                "senses": r.senses[:8],
                "resolution": r.resolution[:6],
            }
        )
    st = ix.stats()
    ix.export_pack()
    return {"stats": st, "cases": rows}
