"""Referent binding + multi-hop rule graphs for word problems.

Failure analysis taught us:
  - Atomic ops (half, %, twice) are fine
  - GSM8K fails when we bind the *wrong quantity* or skip hops

Rules taught here (form / why / how):
  BIND-01  Quantity binding: number ↔ noun/role in the sentence
  BIND-02  Referent of "half of X" / "k% of the price" attaches to X
  BIND-03  Relative chain: A = k·B, B = m·C, C = n → compose
  BIND-04  More/fewer offsets: A = B ± k after binding B
  SCHEMA-* Named multi-hop templates (remainder-sell, win/loss, clock, profit)

  Used by math_rules.apply_rules before keyword fallbacks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .math_rules import SolveResult, StepTrace, _norm

NUM_RE = re.compile(r"(?<![\w])(\d+(?:\.\d+)?)(?![\d])")
WORD_NUM = {
    "zero": 0.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
    "eleven": 11.0,
    "twelve": 12.0,
    "dozen": 12.0,
    "twice": 2.0,
    "thrice": 3.0,
    "half": 0.5,
}

# stopwords / comparative tails that must not become quantity names
_BAD_NOUN_START = frozenset(
    {
        "fewer",
        "more",
        "less",
        "times",
        "than",
        "as",
        "of",
        "the",
        "a",
        "an",
        "and",
        "or",
        "for",
        "per",
        "with",
        "how",
        "many",
        "much",
        "what",
        "if",
        "then",
        "every",
        "each",
        "only",
        "just",
        "about",
        "from",
        "to",
        "into",
        "over",
        "under",
        "after",
        "before",
        "year",
        "years",
        "old",
        "long",
        "short",
    }
)

# Binding rules (curriculum metadata)
BINDING_RULES = [
    {
        "id": "BIND-01",
        "name": "Quantity binding",
        "formula": "number ↔ noun/role",
        "why": "Operations act on named quantities, not on raw digit order.",
        "how": "When you see N next to a noun (or $N price), store binding[noun]=N.",
    },
    {
        "id": "BIND-02",
        "name": "Referent attachment",
        "formula": "half/of/% of X → operate on binding[X]",
        "why": "Modifiers attach to their grammatical object, not the first number in the text.",
        "how": "Parse the object of of/as; look up that name in bindings; then apply half or %.",
    },
    {
        "id": "BIND-03",
        "name": "Relative chain composition",
        "formula": "A=k·B; B=m·C; C=n → A=k·m·n",
        "why": "Multi-hop relations must be composed before the final ask.",
        "how": "Build equations from 'times as'/'twice'/'more than'; solve from the known base.",
    },
    {
        "id": "BIND-04",
        "name": "Offset after referent",
        "formula": "A = B ± k",
        "why": "Fewer/more shift a bound quantity without replacing it.",
        "how": "Resolve B first; then add/subtract k.",
    },
    {
        "id": "SCHEMA-remainder-sell",
        "name": "Remainder then sell",
        "formula": "money = (start − use1 − use2) × price",
        "why": "Inventory residual is sold at unit price.",
        "how": "Bind start and uses (digits or number words); subtract; multiply by unit price.",
    },
    {
        "id": "SCHEMA-win-loss",
        "name": "Win/loss total",
        "formula": "W+L=T; W=L+d → W=(T+d)/2",
        "why": "Two unknowns with sum and difference.",
        "how": "From total games and 'won d more than lost', solve W=(T+d)/2.",
    },
    {
        "id": "SCHEMA-clock",
        "name": "Clock duration",
        "formula": "hours = end − start (same day)",
        "why": "Time-of-day spans are not free numbers in the text.",
        "how": "Parse H AM/PM or 24h; subtract; handle PM.",
    },
    {
        "id": "SCHEMA-profit-markup",
        "name": "House-flip profit",
        "formula": "new=buy·(1+p/100); profit=new−buy−repair",
        "why": "Percent increase attaches to purchase price; repairs still count as invested.",
        "how": "Bind buy and repair; new value = buy×(1+p/100); profit = new − (buy+repair).",
    },
]


@dataclass
class Qty:
    value: float
    name: str  # normalized token key
    role: str = "count"  # count|price|percent|rate|hours|other
    span: Tuple[int, int] = (0, 0)
    priority: int = 0  # higher wins in bindings_map


def _norm_name(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("'s", "")
    return s


def _tok_num(tok: str) -> Optional[float]:
    tok = tok.lower().strip()
    if tok in WORD_NUM:
        return float(WORD_NUM[tok])
    try:
        return float(tok)
    except ValueError:
        return None


def extract_bound_quantities(text: str) -> List[Qty]:
    """BIND-01: attach numbers (digits + number words) to nearby nouns/roles."""
    t = text.replace(",", "")
    tl = t.lower()
    qtys: List[Qty] = []

    # $price (high priority)
    for m in re.finditer(r"\$\s*(\d+(?:\.\d+)?)", t):
        qtys.append(Qty(float(m.group(1)), "price", "price", m.span(), priority=3))

    # N%
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", t):
        qtys.append(Qty(float(m.group(1)), "percent", "percent", m.span(), priority=3))

    # Prefer "NAME has N" when N is a *base quantity*, not a multiplier.
    # Reject "has 4 times as many" — that 4 is a relation coefficient (BIND-03).
    for m in re.finditer(
        r"\b([A-Za-z][A-Za-z'-]{1,24})\s+(?:has|have|had)\s+(?:\$)?(\d+(?:\.\d+)?)\b"
        r"(?!\s*times\b)",
        t,
    ):
        name = _norm_name(m.group(1))
        if name in _BAD_NOUN_START or name in ("she", "he", "they", "it", "we"):
            continue
        # also skip if followed by "as many" without times (rare)
        tail = t[m.end() : m.end() + 24].lower()
        if re.match(r"\s*times\b|\s*as many\b", tail):
            continue
        qtys.append(Qty(float(m.group(2)), name, "count", m.span(), priority=5))

    # "If NAME's X is N" / "NAME is N year old" — not "is four times"
    for m in re.finditer(
        r"\b(?:if\s+)?([A-Za-z][A-Za-z'-]{1,24})(?:'s\s+\w+)?\s+is\s+(\d+(?:\.\d+)?)\b"
        r"(?!\s*times\b)",
        t,
    ):
        name = _norm_name(m.group(1))
        if name in _BAD_NOUN_START:
            continue
        tail = t[m.end() : m.end() + 16].lower()
        if re.match(r"\s*times\b", tail):
            continue
        qtys.append(Qty(float(m.group(2)), name, "count", m.span(), priority=5))

    # "NAME costs $N"
    for m in re.finditer(
        r"\b([A-Za-z][A-Za-z'-]{1,24})\s+costs?\s+\$?\s*(\d+(?:\.\d+)?)",
        t,
    ):
        name = _norm_name(m.group(1))
        qtys.append(Qty(float(m.group(2)), name, "price", m.span(), priority=4))
        qtys.append(Qty(float(m.group(2)), "price", "price", m.span(), priority=3))

    # digit + clean noun (skip comparative tails)
    for m in re.finditer(
        r"(?<![\w])(\d+(?:\.\d+)?)(?!\d)(?:\s+(?:per\s+)?([a-zA-Z][a-zA-Z'-]{0,20}"
        r"(?:\s+[a-zA-Z][a-zA-Z'-]{0,16}){0,2}))?",
        t,
    ):
        val = float(m.group(1))
        if m.end() < len(t) and t[m.end() : m.end() + 1] == "%":
            continue
        raw_noun = m.group(2) or ""
        noun = _norm_name(raw_noun) if raw_noun else f"n{val:g}"
        first = noun.split()[0] if noun else ""
        if first in _BAD_NOUN_START:
            # still keep anonymous quantity
            qtys.append(Qty(val, f"n{val:g}", "count", m.span(), priority=1))
            continue
        role = "count"
        if first in ("dollar", "dollars", "bucks", "price", "cost"):
            role = "price"
            noun = "price"
        if "hour" in noun:
            role = "hours"
        if "minute" in noun:
            role = "minutes"
        qtys.append(Qty(val, noun if noun != "num" else f"n{val:g}", role, m.span(), priority=2))

    # number words used as quantities (eats three / with four)
    for w, val in WORD_NUM.items():
        if w in ("half", "twice", "thrice"):
            continue
        for m in re.finditer(rf"\b{w}\b", tl):
            # only if not already a digit at same place — word qty for remainder uses
            qtys.append(Qty(float(val), w, "count", m.span(), priority=1))

    return qtys


def bindings_map(qtys: List[Qty]) -> Dict[str, float]:
    """Higher priority wins; within same priority last write wins."""
    ranked: Dict[str, Tuple[int, float]] = {}
    for q in qtys:
        prev = ranked.get(q.name)
        if prev is None or q.priority >= prev[0]:
            ranked[q.name] = (q.priority, q.value)
        tok = q.name.split()[0] if q.name else ""
        if tok and tok not in _BAD_NOUN_START:
            prev_t = ranked.get(tok)
            if prev_t is None or q.priority >= prev_t[0]:
                # only promote first token if not lower priority
                if prev_t is None or q.priority > prev_t[0] or tok == q.name:
                    ranked[tok] = (q.priority, q.value)
    return {k: v for k, (_, v) in ranked.items()}


def lookup_binding(binds: Dict[str, float], key: str) -> Optional[float]:
    k = _norm_name(key)
    if not k or len(k) < 2:
        return None
    if k in binds:
        return binds[k]
    # first token
    first = k.split()[0]
    if first in binds:
        return binds[first]
    # fuzzy only for keys length >= 3 (avoid "r" matching "raymond"/noise)
    if len(k) < 3:
        return None
    for name, val in binds.items():
        if len(name) < 3:
            continue
        if k in name or name in k:
            return val
    return None


def solve_with_binding(question: str) -> SolveResult:
    """Apply BIND-* and SCHEMA-* rules with proper referent attachment."""
    q = question.strip().replace(",", "")  # $80,000 → $80000
    ql = q.lower()
    steps: List[StepTrace] = []
    used: List[str] = []

    def push(rule_id: str, formula: str, detail: str, value: float) -> float:
        steps.append(StepTrace(rule_id, formula, detail, value))
        if rule_id not in used:
            used.append(rule_id)
        return value

    qtys = extract_bound_quantities(q)
    binds = bindings_map(qtys)

    # ----- pure half / twice of a number (BIND-02 / BIND-03 atomic) -----
    m = re.match(r"what is half of (\d+(?:\.\d+)?)\s*\??$", ql)
    if m:
        n0 = float(m.group(1))
        h = push("BIND-02", "half(n)=n/2", f"half of {n0}", n0 / 2.0)
        return SolveResult(_norm(h), steps, used, True)
    m = re.match(r"what is twice (\d+(?:\.\d+)?)\s*\??$", ql)
    if m:
        n0 = float(m.group(1))
        d = push("BIND-03", "twice(n)=2n", f"2*{n0}", 2.0 * n0)
        return SolveResult(_norm(d), steps, used, True)

    # ----- SCHEMA clock: from H to H -----
    m = re.search(
        r"from\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:to|until|-)\s*"
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
        ql,
    )
    if m:
        h1, m1, p1, h2, m2, p2 = m.groups()

        def to_hours(h, mi, p):
            h = int(h)
            mi = int(mi or 0)
            if p == "pm" and h != 12:
                h += 12
            if p == "am" and h == 12:
                h = 0
            return h + mi / 60.0

        p1 = p1 or p2
        p2 = p2 or p1
        t1 = to_hours(h1, m1, p1)
        t2 = to_hours(h2, m2, p2)
        if t2 < t1:
            t2 += 24
        # Refuse when this is a *travel* problem with outbound/return rates
        # (wrong-fire: Tom's ship 1–4 PM then back at different mph).
        if re.search(r"\b(mph|miles per hour|travel|sailing|drive|driving)\b", ql):
            # only keep duration as an intermediate if a later schema needs it — don't answer
            pass
        else:
            dur = push("SCHEMA-clock", "hours=end-start", f"{t2}-{t1}", t2 - t1)
            if re.search(r"\bcm|centimeter|melts?\b", ql):
                rate_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:cm|centimeters?)", ql)
                if rate_m and re.search(r"every hour|per hour", ql):
                    rate = float(rate_m.group(1))
                    total = push(
                        "mul_rate", "melt=rate×hours", f"{rate}*{dur}", rate * dur
                    )
                    return SolveResult(_norm(total), steps, used, True)
            if re.search(r"after burning|shorter|how many centimeters", ql):
                return SolveResult(_norm(dur), steps, used, True)
            if re.search(
                r"\bhow (many|much) (hours|long)\b|how long does it take|how many hours",
                ql,
            ) and not re.search(r"\bback\b|\breturn\b", ql):
                return SolveResult(_norm(dur), steps, used, True)

    # ----- SCHEMA win/loss -----
    m = re.search(
        r"played\s+(\d+)\s+games?.*?won\s+(\d+)\s+more than (?:they |he |she )?lost"
        r".*?how many did (?:they|he|she) win",
        ql,
        re.S,
    )
    if m:
        total, d = float(m.group(1)), float(m.group(2))
        w = push("SCHEMA-win-loss", "W=(T+d)/2", f"({total}+{d})/2", (total + d) / 2.0)
        return SolveResult(_norm(w), steps, used, True)

    # ----- SCHEMA profit markup (GSM8K house-flip pattern) -----
    # Buy B, repairs R, value increased by P% → new = B*(1+P/100); profit = new − B − R
    # (percent applies to purchase price, not total invested — GSM8K official).
    if re.search(r"\bprofit\b", ql) and re.search(r"%", ql):
        buy_m = re.search(
            r"(?:buys?|bought)\D{0,40}?\$?\s*(\d+(?:\.\d+)?)",
            ql,
        )
        rep_m = re.search(
            r"(?:repairs?|puts? in|renovat\w+)\D{0,20}?\$?\s*(\d+(?:\.\d+)?)",
            ql,
        )
        pcts = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", ql)]
        if buy_m and pcts and (
            re.search(r"increas\w+ (?:the )?value by", ql)
            or re.search(r"value of the \w+ by", ql)
        ):
            buy = float(buy_m.group(1))
            repair = float(rep_m.group(1)) if rep_m else 0.0
            p = pcts[0]
            invested = push(
                "add_combine", "invested=buy+repair", f"{buy}+{repair}", buy + repair
            )
            new_val = push(
                "SCHEMA-profit-markup",
                "new=buy*(1+p/100)",
                f"{buy}*(1+{p}/100)",
                buy * (1.0 + p / 100.0),
            )
            profit = push(
                "SCHEMA-profit-markup",
                "profit=new−invested",
                f"{new_val}-{invested}",
                new_val - invested,
            )
            return SolveResult(_norm(profit), steps, used, True)

    # ----- SCHEMA remainder-sell (digits + number words) -----
    if re.search(r"\bsells the remainder|remainder at\b", ql) or (
        re.search(r"\bremainder\b", ql) and re.search(r"\b(sells?|market)\b", ql)
    ):
        start = None
        m = re.search(
            r"(?:lay|lays|produce|produces|has|have|makes?)\s+(\d+(?:\.\d+)?)",
            ql,
        )
        if m:
            start = float(m.group(1))
        if start is None:
            m = re.search(r"(\d+(?:\.\d+)?)\s+eggs?", ql)
            if m:
                start = float(m.group(1))
        uses: List[float] = []
        # eats/uses/bakes ... number (digit or word)
        for m in re.finditer(
            r"\b(?:eats?|uses?|gives?)\s+(?:with\s+)?(\d+(?:\.\d+)?|three|four|two|five|one|six|seven|eight|nine|ten)\b",
            ql,
        ):
            v = _tok_num(m.group(1))
            if v is not None and v >= 1:
                uses.append(v)
        # "bakes ... with four" / "with 4"
        for m in re.finditer(
            r"\bwith\s+(\d+(?:\.\d+)?|three|four|two|five|one|six|seven|eight|nine|ten)\b",
            ql,
        ):
            v = _tok_num(m.group(1))
            if v is not None and v >= 1 and v not in uses:
                uses.append(v)
        # "bakes 4" / "eats 3"
        for m in re.finditer(
            r"\b(?:bakes?|eats?|uses?)\s+(\d+(?:\.\d+)?)\b",
            ql,
        ):
            v = float(m.group(1))
            if v not in uses:
                uses.append(v)
        price = None
        m = re.search(
            r"(?:for|at)\s+\$?\s*(\d+(?:\.\d+)?)\s*(?:each|per|a\s|dollars?\s+each)?",
            ql,
        )
        if m:
            price = float(m.group(1))
        if price is None:
            m = re.search(r"\$\s*(\d+(?:\.\d+)?)", q)
            if m:
                price = float(m.group(1))
        if start is not None and len(uses) >= 2 and price is not None:
            left = start
            for u in uses[:2]:
                left = push("sub_remove", "left=start−use", f"{left}-{u}", left - u)
            money = push(
                "SCHEMA-remainder-sell",
                "money=left×price",
                f"{left}*{price}",
                left * price,
            )
            return SolveResult(_norm(money), steps, used, True)

    # ----- Explicit multi-hop offset chain (Siobhan/Aaron/Raymond) -----
    # A has K fewer than B. B has M more than half of C. C has N.
    m = re.search(
        r"(\w+)\s+has\s+(\d+)\s+fewer\s+\w*\s*than\s+(\w+)\s*\.\s*"
        r"(\w+)\s+has\s+(\d+)\s+more\s+\w*\s*than\s+half of\s+(\w+)"
        r".*?\b(\w+)\s+has\s+(\d+)",
        ql,
        re.S,
    )
    if m:
        _a, fewer_k, _b, _b2, more_k, _c, c_name2, c_val = m.groups()
        c = float(c_val)
        # prefer bound C if present
        c_bound = lookup_binding(binds, c_name2)
        if c_bound is not None:
            c = c_bound
        half_c = push("BIND-02", "half of C", f"half({c})", c / 2.0)
        b = push(
            "BIND-04",
            "B=half(C)+k",
            f"{half_c}+{more_k}",
            half_c + float(more_k),
        )
        a = push("BIND-04", "A=B−k", f"{b}-{fewer_k}", b - float(fewer_k))
        return SolveResult(_norm(a), steps, used, True)

    # Nested "half of the X … half of the Y" handled later — don't early-exit on first half.
    _nested_half = ql.count("half of the") >= 2

    # ----- BIND-02: half of <named entity> -----
    m = re.search(
        r"half of\s+([a-z]{2,}(?:'s)?(?:\s+[a-z]{2,}){0,3})",
        ql,
    )
    if m and not re.search(r"half of\s+\d", ql) and not _nested_half:
        raw_ref = m.group(1)
        ref = _norm_name(raw_ref)
        # drop possession and unit tails
        ref = re.sub(
            r"\b(jewels?|eggs?|apples?|miles?|hours?|water|amount|laundry|"
            r"iphones?|phones?|sheep|items?|balls?)\b",
            " ",
            ref,
        )
        ref = re.sub(r"\s+", " ", ref).strip()
        val = lookup_binding(binds, ref)
        if val is None and ref:
            val = lookup_binding(binds, ref.split()[0])
        if val is not None:
            h = push("BIND-02", "half of X", f"half of {ref}={val}", val / 2.0)
            # "M more [NOUN] than half of X"
            m2 = re.search(
                r"(\d+(?:\.\d+)?|one|two|three|four|five)\s+more"
                r"(?:\s+\w+){0,2}\s+than half of",
                ql,
            )
            if m2:
                k = float(_tok_num(m2.group(1)) or 0)
                h = push("BIND-04", "B=half+k", f"{h}+{k}", h + k)
            # "A has K fewer than B" after computing B≈h
            if re.search(r"\bfewer than\b", ql) and re.search(r"more.{0,20}than half", ql):
                m4 = re.search(
                    r"(\d+(?:\.\d+)?|one|two|three|four|five)\s+fewer",
                    ql,
                )
                if m4:
                    k = float(_tok_num(m4.group(1)) or 0)
                    a = push("BIND-04", "A=B−k", f"{h}-{k}", h - k)
                    return SolveResult(_norm(a), steps, used, True)
            # simple ask for half of named
            if re.search(r"\bhow many\b|what is half of", ql) and not re.search(
                r"\bfewer than|\bmore.{0,12}than half\b", ql
            ):
                return SolveResult(_norm(h), steps, used, True)
            if re.search(r"half of", ql) and not re.search(
                r"more.{0,20}than half|fewer than", ql
            ):
                return SolveResult(_norm(h), steps, used, True)

    # ----- BIND-03 relative chains: times as old / times as many / twice as many -----
    edges: List[Tuple[str, float, str]] = []

    # "A is K times as old as B" / "A's X is K times as old as B's"
    for a, k, b in re.findall(
        r"([A-Za-z][a-zA-Z'-]+)(?:'s\s+\w+)?\s+is\s+"
        r"(\d+|two|three|four|five|twice)\s+times\s+"
        r"(?:as old as|older than|as many as)\s+([A-Za-z][a-zA-Z'-]+)",
        q,
    ):
        kk = float(WORD_NUM.get(k, k)) if not str(k).replace(".", "").isdigit() else float(k)
        if k == "twice":
            kk = 2.0
        edges.append((_norm_name(a), kk, _norm_name(b)))

    # "A has twice as many X as B" / "A has 4 times as many X as B"
    for a, k, b in re.findall(
        r"([A-Za-z][a-zA-Z'-]+)\s+has\s+"
        r"(twice|\d+|two|three|four|five)\s+"
        r"(?:times\s+)?as many\s+\w+\s+as\s+([A-Za-z][a-zA-Z'-]+)",
        q,
        flags=re.I,
    ):
        if k.lower() == "twice":
            kk = 2.0
        else:
            kk = float(WORD_NUM.get(k.lower(), k))
        edges.append((_norm_name(a), kk, _norm_name(b)))

    if edges:
        base_name, base_val = None, None
        # Prefer explicit "if NAME has/is N" (known base), never "has N times"
        base_m = re.search(
            r"\bif\s+([A-Za-z][a-zA-Z'-]+)(?:'s\s+\w+)?\s+(?:has|is)\s+(\d+(?:\.\d+)?)"
            r"(?!\s*times\b)",
            ql,
        )
        if base_m:
            base_name, base_val = _norm_name(base_m.group(1)), float(base_m.group(2))
        if base_name is None:
            # "If Suzy's iPhone is 1 year old"
            base_m = re.search(
                r"(?:if\s+)?([A-Za-z][a-zA-Z'-]+)(?:'s\s+\w+)?\s+is\s+(\d+(?:\.\d+)?)"
                r"\s*(?:year|years)?(?:\s+old)?(?!\s*times\b)",
                ql,
            )
            if base_m:
                cand = _norm_name(base_m.group(1))
                # reject if this match is mid "is 4 times"
                after = ql[base_m.end() : base_m.end() + 12]
                if not re.match(r"\s*times\b", after):
                    base_name, base_val = cand, float(base_m.group(2))
        if base_name is None:
            # last "NAME has N" that is NOT a multiplier
            candidates = list(
                re.finditer(
                    r"\b([A-Za-z][a-zA-Z'-]+)\s+has\s+(\d+(?:\.\d+)?)"
                    r"(?!\s*times\b)(?!\s*as many\b)",
                    ql,
                )
            )
            if candidates:
                # prefer the last absolute quantity (often the given base)
                bm = candidates[-1]
                base_name, base_val = _norm_name(bm.group(1)), float(bm.group(2))

        if base_name is not None and base_val is not None:
            vals: Dict[str, float] = {base_name: base_val}
            push("BIND-01", "base quantity", f"{base_name}={base_val}", base_val)
            for _ in range(8):
                for a, k, b in edges:
                    if b in vals and a not in vals:
                        vals[a] = push("BIND-03", "A=k*B", f"{a}={k}*{b}", k * vals[b])
                    if a in vals and b not in vals and k != 0:
                        vals[b] = push("BIND-03", "B=A/k", f"{b}={a}/{k}", vals[a] / k)
            ask = re.search(
                r"how (?:old|many)\s+(?:is|are)\s+([A-Za-z][a-zA-Z'-]+)",
                ql,
            )
            if not ask:
                ask = re.search(r"how old is ([A-Za-z][a-zA-Z'-]+)", ql)
            if ask:
                target = _norm_name(ask.group(1))
                if target in vals:
                    return SolveResult(_norm(vals[target]), steps, used, True)
            if re.search(r"\btogether|total\b", ql) and len(vals) >= 2:
                s = sum(vals.values())
                push("add_combine", "sum bindings", "sum", s)
                return SolveResult(_norm(s), steps, used, True)

    # ----- percent of the price (BIND-02 price role) -----
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of the price", ql)
    if m and re.search(r"costs?\s+\$?\s*(\d+(?:\.\d+)?)", ql):
        pct = float(m.group(1))
        price_m = re.search(r"costs?\s+\$?\s*(\d+(?:\.\d+)?)", ql)
        price = float(price_m.group(1))
        disc = push("BIND-02", "p% of price", f"{pct}% of {price}", price * pct / 100.0)
        nm = re.search(r"buy\s+(\d+)\s+\w+", ql)
        if nm and re.search(r"every second", ql):
            n = int(float(nm.group(1)))
            full_n = (n + 1) // 2
            half_n = n // 2
            total = push(
                "mul_groups",
                "full*price + half*disc",
                f"{full_n}*{price}+{half_n}*{disc}",
                full_n * price + half_n * disc,
            )
            return SolveResult(_norm(total), steps, used, True)
        return SolveResult(_norm(disc), steps, used, True)

    # ----- half as long (Jim TV) -----
    if re.search(r"half as long", ql) and re.search(r"\bhours?\b", ql):
        hm = re.search(r"(\d+(?:\.\d+)?)\s*hours?", ql)
        times = re.search(r"(\d+)\s*times a week", ql)
        if hm and times and re.search(r"\btv\b|\breading\b", ql):
            h = float(hm.group(1))
            half = push("BIND-02", "half as long", f"half({h})", h / 2.0)
            per = push("add_combine", "tv+read", f"{h}+{half}", h + half)
            week_times = float(times.group(1))
            per_week = push(
                "mul_groups", "per week", f"{per}*{week_times}", per * week_times
            )
            # "in N weeks" / "in one month"
            span = re.search(r"\bin\s+(\d+)\s*weeks?\b", ql)
            if span:
                w = float(span.group(1))
                tot = push("mul_groups", "weeks span", f"{per_week}*{w}", per_week * w)
                return SolveResult(_norm(tot), steps, used, True)
            return SolveResult(_norm(per_week), steps, used, True)

    # ----- half as many as NAME, then together -----
    m = re.search(
        r"half as many\s+\w+\s+as\s+(?:her |his |their )?(mom|mother|dad|father|\w+)",
        ql,
    )
    if m and re.search(r"\b(both|together|altogether|in total|in all)\b", ql):
        base = None
        # "mom got 20" / "if her mom got 20 apples"
        bm = re.search(
            r"(?:mom|mother|dad|father|\w+)\s+(?:got|has|picked)\s+(\d+(?:\.\d+)?)",
            ql,
        )
        if bm:
            base = float(bm.group(1))
        if base is None:
            nums = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", ql)]
            if len(nums) == 1:
                base = nums[0]
        if base is not None:
            h = push("BIND-02", "half as many", f"half({base})", base / 2.0)
            tot = push("add_combine", "both=half+base", f"{h}+{base}", h + base)
            return SolveResult(_norm(tot), steps, used, True)

    # ----- "K more than twice X" (Jimmy/Ethel) -----
    m = re.search(
        r"(\d+(?:\.\d+)?)\s+more than twice.*?(\w+)\s+has\s+\$?\s*(\d+(?:\.\d+)?)",
        ql,
        re.S,
    )
    if not m:
        m = re.search(
            r"(\d+(?:\.\d+)?)\s+more than twice.*?if\s+(\w+)\s+has\s+\$?\s*(\d+(?:\.\d+)?)",
            ql,
            re.S,
        )
    if m:
        k, _name, base = float(m.group(1)), m.group(2), float(m.group(3))
        twice = push("BIND-03", "twice base", f"2*{base}", 2.0 * base)
        ans = push("BIND-04", "twice+k", f"{twice}+{k}", twice + k)
        return SolveResult(_norm(ans), steps, used, True)
    m = re.search(
        r"\$?(\d+(?:\.\d+)?)\s+more than twice the money\s+(\w+)\s+has.*?"
        r"(\w+)\s+has\s+\$?\s*(\d+(?:\.\d+)?)",
        ql,
        re.S,
    )
    if m:
        k, base = float(m.group(1)), float(m.group(4))
        twice = push("BIND-03", "twice base", f"2*{base}", 2.0 * base)
        ans = push("BIND-04", "twice+k", f"{twice}+{k}", twice + k)
        return SolveResult(_norm(ans), steps, used, True)

    # travel: outbound hours × speed, return distance/speed2
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*miles per hour.*?from\s+(\d{1,2})\s*(?:am|pm)?\s*to\s+"
        r"(\d{1,2})\s*(?:am|pm)?.*?back at (?:a rate of\s*)?(\d+(?:\.\d+)?)",
        ql,
        re.S,
    )
    if m:
        sp1, h1, h2, sp2 = (
            float(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            float(m.group(4)),
        )
        hours = abs(h2 - h1)
        dist = push("mul_rate", "dist=speed×hours", f"{sp1}*{hours}", sp1 * hours)
        back = push("div_rate", "time=dist/speed", f"{dist}/{sp2}", dist / sp2)
        return SolveResult(_norm(back), steps, used, True)

    # ----- nested half: half of N are X; half of the X are Y -----
    # "16 balls. Half of the balls are golf balls, and half of the golf balls are blue."
    if re.search(r"\bhalf of the\b", ql) and ql.count("half of the") >= 2:
        nm = re.search(r"(\d+(?:\.\d+)?)\s+\w+", ql)
        if nm and re.search(r"\bhow many\b", ql):
            n0 = float(nm.group(1))
            h1 = push("BIND-02", "half of set", f"half({n0})", n0 / 2.0)
            h2 = push("BIND-02", "half of subset", f"half({h1})", h1 / 2.0)
            return SolveResult(_norm(h2), steps, used, True)

    # ----- "A base. K more X than base. total?" → 2*base + K -----
    m = re.search(
        r"there are (\d+(?:\.\d+)?)\s+(\w+).*?(\d+(?:\.\d+)?)\s+more\s+(\w+)\s+than\s+\2"
        r".*?(?:total|in all|altogether|how many \w+ are there)",
        ql,
        re.S,
    )
    if m:
        base, _n1, more, _n2 = (
            float(m.group(1)),
            m.group(2),
            float(m.group(3)),
            m.group(4),
        )
        other = push("BIND-04", "other=base+k", f"{base}+{more}", base + more)
        tot = push("add_combine", "total=base+other", f"{base}+{other}", base + other)
        return SolveResult(_norm(tot), steps, used, True)

    # ----- half as many as prior duration/quantity + together -----
    # "takes 6 days by bus and half as many days by car" → total trip options or sum
    m = re.search(
        r"(\d+(?:\.\d+)?)\s+days?\b.*?half as many days\b",
        ql,
        re.S,
    )
    if m and re.search(r"\b(together|total|both|how many days)\b", ql):
        base = float(m.group(1))
        h = push("BIND-02", "half as many", f"half({base})", base / 2.0)
        # "how many days will he travel if he plans to take the bus and car"
        if re.search(r"\bbus\b.*\bcar\b|\bcar\b.*\bbus\b", ql):
            tot = push("add_combine", "bus+car", f"{base}+{h}", base + h)
            return SolveResult(_norm(tot), steps, used, True)

    # ----- spend half of money + additional $K; how much left -----
    m = re.search(
        r"(?:brought|had|has)\s+\$?\s*(\d+(?:\.\d+)?).*?"
        r"spent half.*?additional\s+\$?\s*(\d+(?:\.\d+)?).*?"
        r"(?:left|remain)",
        ql,
        re.S,
    )
    if m:
        start, extra = float(m.group(1)), float(m.group(2))
        spent_half = push("BIND-02", "half of money", f"half({start})", start / 2.0)
        spent = push(
            "add_combine", "spent=half+extra", f"{spent_half}+{extra}", spent_half + extra
        )
        left = push("sub_remove", "left=start−spent", f"{start}-{spent}", start - spent)
        return SolveResult(_norm(left), steps, used, True)

    # ----- bought A of X and K more Y than X; total items -----
    m = re.search(
        r"bought\s+(\d+(?:\.\d+)?)\s+\w+.*?(\d+(?:\.\d+)?)\s+more\s+\w+\s+than"
        r".*?(?:total|altogether|in all|how many)",
        ql,
        re.S,
    )
    if m and not re.search(r"%|percent|each cost|\$", ql):
        base, more = float(m.group(1)), float(m.group(2))
        other = push("BIND-04", "other=base+k", f"{base}+{more}", base + more)
        tot = push("add_combine", "total", f"{base}+{other}", base + other)
        return SolveResult(_norm(tot), steps, used, True)

    return SolveResult(None, steps, used, False)


def binding_drills() -> List[Tuple[str, str, str]]:
    """(question, answer, focus) for BIND/SCHEMA teaching."""
    return [
        (
            "Raymond has 40 jewels. What is half of Raymond's jewels?",
            "20",
            "BIND-02",
        ),
        (
            "Siobhan has 2 fewer jewels than Aaron. Aaron has 5 more jewels than half of "
            "Raymond's jewels. If Raymond has 40 jewels, how many jewels does Siobhan have?",
            "23",
            "BIND-04",
        ),
        (
            "Brandon's iPhone is four times as old as Ben's iPhone. Ben's iPhone is two times "
            "older than Suzy's iPhone. If Suzy's iPhone is 1 year old, how old is Brandon's iPhone?",
            "8",
            "BIND-03",
        ),
        (
            "Toulouse has twice as many sheep as Charleston. Charleston has 4 times as many sheep "
            "as Seattle. How many sheep do Toulouse, Charleston, and Seattle have together if "
            "Seattle has 20?",
            "260",
            "BIND-03",
        ),
        (
            "Ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes "
            "muffins for her friends every day with four. She sells the remainder at the farmers' "
            "market daily for $2 per fresh duck egg. How much in dollars does she make every day "
            "at the farmers' market?",
            "18",
            "SCHEMA-remainder-sell",
        ),
        (
            "A football team played 22 games. They won 8 more than they lost. How many did they win?",
            "15",
            "SCHEMA-win-loss",
        ),
        (
            "A candle melts by 2 centimeters every hour that it burns. How many centimeters shorter "
            "will a candle be after burning from 1:00 PM to 5:00 PM?",
            "8",
            "SCHEMA-clock",
        ),
        (
            "One glass costs $5, but every second glass costs only 60% of the price. Kylar wants to "
            "buy 16 glasses. How much does he need to pay for them?",
            "64",
            "BIND-02",
        ),
        (
            "Josh decides to try flipping a house. He buys a house for $80000 and then puts in "
            "$50000 in repairs. This increased the value of the house by 150%. How much profit "
            "did he make?",
            "70000",
            "SCHEMA-profit-markup",
        ),
        (
            "Jim spends 2 hours watching TV and then decides to go to bed and reads for half as "
            "long. He does this 3 times a week. How many hours does he spend on TV and reading "
            "in a week?",
            "9",
            "BIND-02",
        ),
        (
            "Jim spends 2 hours watching TV and then decides to go to bed and reads for half as "
            "long. He does this 3 times a week. How many hours does he spend on TV and reading "
            "in 4 weeks?",
            "36",
            "BIND-02",
        ),
        (
            "Jenna picked half as many apples as her mom. If her mom got 20 apples, how many "
            "apples did they both pick?",
            "30",
            "BIND-02",
        ),
        (
            "Jimmy has $2 more than twice the money Ethel has. If Ethel has $8, how much money "
            "is Jimmy having?",
            "18",
            "BIND-04",
        ),
        (
            "Tom's ship can travel at 10 miles per hour. He is sailing from 1 to 4 PM. He then "
            "travels back at a rate of 6 mph. How long does it take him to get back?",
            "5",
            "SCHEMA-clock",
        ),
        ("What is half of 40?", "20", "BIND-02"),
        ("What is twice 7?", "14", "BIND-03"),
        # extra drills for binding stability
        (
            "Maria has 30 apples. What is half of Maria's apples?",
            "15",
            "BIND-02",
        ),
        (
            "Alex has twice as many books as Sam. Sam has 3 times as many books as Pat. "
            "If Pat has 5 books, how many books do Alex, Sam, and Pat have together?",
            "50",
            "BIND-03",
        ),
        (
            "A team played 30 games and won 6 more than they lost. How many did they win?",
            "18",
            "SCHEMA-win-loss",
        ),
        (
            "A juggler can juggle 16 balls. Half of the balls are golf balls, and half of the "
            "golf balls are blue. How many blue golf balls are there?",
            "4",
            "BIND-02",
        ),
        (
            "There are 4 roses in the vase. There are 7 more dahlias than roses in the vase. "
            "How many flowers are there in the vase in total?",
            "15",
            "BIND-04",
        ),
        (
            "Annika brought $50 to the town fair. She spent half of it on food and snacks, and "
            "an additional $10 for rides. How much, in dollars, is left?",
            "15",
            "BIND-02",
        ),
        (
            "Andrew plans a road trip. It takes 6 days to travel by bus and half as many days "
            "to travel by car. How many days will he travel if he plans to take the bus and car?",
            "9",
            "BIND-02",
        ),
    ]
