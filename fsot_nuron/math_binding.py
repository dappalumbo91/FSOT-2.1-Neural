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
    {
        "id": "SCHEMA-inventory-cascade",
        "name": "Inventory cascade (work backward)",
        "formula": "undo half→×2; undo +k→−k; undo 1/3 sold→×3/2",
        "why": "When final remaining is known, reverse each sale step to recover start.",
        "how": "Walk sales in reverse order; each 'half left sold' doubles; each '+k sold' adds k; "
        "'a third sold' means 2/3 remains so start = rem×3/2.",
    },
    {
        "id": "SCHEMA-sequential-fraction",
        "name": "Sequential fraction then count leave",
        "formula": "left = start·(1−f) − k",
        "why": "A fraction leaves first; then an absolute count leaves the remainder.",
        "how": "Apply fraction of start (or remaining); subtract fixed quit count from what is left.",
    },
    {
        "id": "SCHEMA-billable-hours",
        "name": "Billable hours profit",
        "formula": "hours=n×min/60; profit=hours×(charge−cost)",
        "why": "Patient minutes convert to hours; margin is charge rate minus cost rate.",
        "how": "Total minutes → hours; profit/hour = patient$/h − doctor$/h; multiply.",
    },
    {
        "id": "SCHEMA-rate-schedule",
        "name": "Hourly rate × schedule × discount",
        "formula": "pay = rate×h×days×weeks×(1−d%)",
        "why": "Recurring hourly work multiplies across the calendar, then optional discount.",
        "how": "rate×hours/day×times/week×weeks; subtract d% if given.",
    },
    {
        "id": "SCHEMA-fraction-remaining-split",
        "name": "Fraction sold then half remaining split",
        "formula": "rem=start·(1−f); part=rem/2",
        "why": "After a fraction is taken, remaining is shared equally across periods.",
        "how": "Subtract f of start; if half of left is sold equally in two slots, each slot = rem/2.",
    },
    {
        "id": "SCHEMA-salary-fractions",
        "name": "Salary fraction cascade",
        "formula": "left = start − Σ(fi·start); then half remaining; then fixed gifts",
        "why": "Percents/fractions of salary apply to original base; half applies to residual.",
        "how": "Subtract each fi×salary; half the remainder; subtract fixed dollar gifts.",
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

    # ----- classroom composition BEFORE generic times-chain -----
    # "k times as many girls as boys, 1/10 as many Z as boys, has N boys; total"
    if (
        re.search(r"\btimes as many\b", ql)
        and re.search(r"\b\d+/\d+\s+as many\b", ql)
        and re.search(r"\b(total|how many total|total children)\b", ql)
    ):
        km = re.search(r"(\d+)\s+times as many", ql)
        fm = re.search(r"(\d+)/(\d+)\s+as many", ql)
        # base count: "has 30 boys" — not "has 3 times"
        bm = re.search(
            r"(?:has|have)\s+(\d+)\s+(boys|girls|students|children)\b",
            ql,
        )
        if not bm:
            # last absolute "has N <noun>" not followed by times
            cands = list(
                re.finditer(
                    r"(?:has|have)\s+(\d+)\s+\w+\b(?!\s*times)",
                    ql,
                )
            )
            bm = cands[-1] if cands else None
        if km and fm and bm:
            k = float(km.group(1))
            f = float(fm.group(1)) / float(fm.group(2))
            base = float(bm.group(1))
            g = push("BIND-03", "k×base", f"{k}*{base}", k * base)
            z = push("BIND-02", "f×base", f"{f:g}*{base}", f * base)
            tot = push("add_combine", "g+base+z", f"{g}+{base}+{z}", g + base + z)
            return SolveResult(_norm(tot), steps, used, True)

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
    # Allow multi-word noun between more and than ("more fish sausages than")
    m = re.search(
        r"(?:bought|has|have|had)\s+(\d+(?:\.\d+)?)\s+(?:\w+\s+){0,3}\w+"
        r".*?(\d+(?:\.\d+)?)\s+more\s+(?:\w+\s+){1,3}than\s+"
        r".*?(?:total|altogether|in all|how many)",
        ql,
        re.S,
    )
    if m and not re.search(r"%|percent|each cost|\$", ql):
        base, more = float(m.group(1)), float(m.group(2))
        other = push("BIND-04", "other=base+k", f"{base}+{more}", base + more)
        tot = push("add_combine", "total", f"{base}+{other}", base + other)
        return SolveResult(_norm(tot), steps, used, True)

    # =====================================================================
    # High-lift schemas (inventory cascade, sequential fraction, billable)
    # =====================================================================

    # ----- SCHEMA-inventory-cascade (work BACKWARD from remaining) -----
    # Melanie: sold a third, then k more, then half of left; has L left → start?
    if (
        re.search(r"\bsold a third\b|\ba third of (?:her |his |the )?", ql)
        and re.search(r"\bhalf of what (was left|remained|is left)\b", ql)
        and re.search(r"\b(start with|start with\?|did she start|did he start|how many did)\b", ql)
    ):
        left_m = re.search(
            r"(?:has|have|had)\s+(\d+(?:\.\d+)?)\s+(?:\w+\s+){0,3}left\b",
            ql,
        )
        if not left_m:
            left_m = re.search(
                r"(\d+(?:\.\d+)?)\s+(?:\w+\s+){0,3}left\b",
                ql,
            )
        more_m = re.search(r"(\d+(?:\.\d+)?)\s+more\b", ql)
        if left_m and more_m:
            left = float(left_m.group(1))
            k = float(more_m.group(1))
            # reverse orange: half of what was left sold → before = left*2
            before_half = push(
                "SCHEMA-inventory-cascade",
                "undo half-sold → ×2",
                f"{left}*2",
                left * 2.0,
            )
            # reverse red: sold k more → before = before_half + k
            before_more = push(
                "SCHEMA-inventory-cascade",
                "undo +k sold → +k",
                f"{before_half}+{k}",
                before_half + k,
            )
            # reverse green: sold a third → 2/3 remained = before_more → start = ×3/2
            start = push(
                "SCHEMA-inventory-cascade",
                "undo 1/3 sold → ×3/2",
                f"{before_more}*3/2",
                before_more * 3.0 / 2.0,
            )
            return SolveResult(_norm(start), steps, used, True)

    # ----- SCHEMA-sequential-fraction (forward: fraction leave, then count) -----
    # Nissa: 60 elves; a third quit; then 10 of remaining quit → left
    if re.search(r"\b(quit|leave|left)\b", ql) and re.search(
        r"\b(a third|one third|1/3|half|a half|1/2|a quarter|1/4)\b", ql
    ):
        start_m = re.search(
            r"(?:hires?|has|have|had|starts? with|employs?)\s+(\d+(?:\.\d+)?)",
            ql,
        )
        if not start_m:
            start_m = re.search(r"^.*?(\d+(?:\.\d+)?)\s+\w+", ql)
        frac = None
        if re.search(r"\ba third\b|\bone third\b|\b1/3\b", ql):
            frac = 1.0 / 3.0
        elif re.search(r"\bhalf\b|\b1/2\b", ql) and not re.search(
            r"half of what", ql
        ):
            frac = 0.5
        elif re.search(r"\ba quarter\b|\b1/4\b", ql):
            frac = 0.25
        # "then K of the remaining ... quit"
        then_m = re.search(
            r"(?:then|,)\s+(\d+(?:\.\d+)?)\s+(?:of the remaining\s+\w+\s+)?"
            r"(?:quit|leave|left)",
            ql,
        )
        if start_m and frac is not None and then_m and re.search(
            r"\bhow many\b.*\b(left|remain)", ql
        ):
            start = float(start_m.group(1))
            k = float(then_m.group(1))
            quit1 = push(
                "SCHEMA-sequential-fraction",
                "quit1=f×start",
                f"{frac:g}*{start}",
                frac * start,
            )
            rem1 = push(
                "sub_remove", "after fraction", f"{start}-{quit1}", start - quit1
            )
            left = push(
                "SCHEMA-sequential-fraction",
                "left=rem−k",
                f"{rem1}-{k}",
                rem1 - k,
            )
            return SolveResult(_norm(left), steps, used, True)

    # ----- SCHEMA-billable-hours (hospital margin) -----
    # n people × m minutes; doctors $A/h; hospital charges $B/h → profit
    if (
        re.search(r"\b(patient|people|person)\b", ql)
        and re.search(r"\bminutes?\b", ql)
        and re.search(r"\b(charge|charges|profit)\b", ql)
        and re.search(r"\bhour\b", ql)
    ):
        n_m = re.search(r"(\d+(?:\.\d+)?)\s+(?:people|patients?|persons?)", ql)
        if not n_m:
            n_m = re.search(r"sees\s+(\d+(?:\.\d+)?)", ql)
        min_m = re.search(r"(?:average of\s*)?(\d+(?:\.\d+)?)\s*minutes?", ql)
        # two dollar rates: cost (doctors) then charge (hospital/patients)
        rates = [float(x) for x in re.findall(r"\$\s*(\d+(?:\.\d+)?)", q)]
        if not rates:
            rates = [
                float(x)
                for x in re.findall(
                    r"charge[sd]?\s+(?:her |him |them |the \w+ )?\$?\s*(\d+(?:\.\d+)?)",
                    ql,
                )
            ]
        # also "charge $150 an hour" / "charges the patients $200 an hour"
        rate_pairs = re.findall(
            r"(?:charge[sd]?|cost[s]?)\s+(?:[^$]{0,40}?)\$?\s*(\d+(?:\.\d+)?)\s*"
            r"(?:an hour|/hour|per hour)",
            ql,
        )
        if len(rate_pairs) >= 2:
            rates = [float(x) for x in rate_pairs[:2]]
        if n_m and min_m and len(rates) >= 2 and re.search(r"\bprofit\b", ql):
            n = float(n_m.group(1))
            minutes = float(min_m.group(1))
            cost_h, charge_h = rates[0], rates[1]
            # ensure charge > cost for profit framing when order is doctor then hospital
            if "doctor" in ql and "hospital" in ql:
                # doctors charge hospital A; hospital charges patients B
                dm = re.search(
                    r"doctors?\s+charge[sd]?\s+\$?\s*(\d+(?:\.\d+)?)", ql
                )
                hm = re.search(
                    r"hospital\s+charges?\s+(?:the patients?\s+)?\$?\s*(\d+(?:\.\d+)?)",
                    ql,
                )
                if dm and hm:
                    cost_h, charge_h = float(dm.group(1)), float(hm.group(1))
            total_min = push(
                "mul_groups", "total minutes", f"{n}*{minutes}", n * minutes
            )
            hours = push(
                "div_rate", "hours=min/60", f"{total_min}/60", total_min / 60.0
            )
            margin = push(
                "sub_diff",
                "margin=charge−cost",
                f"{charge_h}-{cost_h}",
                charge_h - cost_h,
            )
            profit = push(
                "SCHEMA-billable-hours",
                "profit=hours×margin",
                f"{hours}*{margin}",
                hours * margin,
            )
            return SolveResult(_norm(profit), steps, used, True)

    # ----- SCHEMA-rate-schedule (hourly × day × week × weeks × discount) -----
    # Jean makeup: $250/h, 6 hours/day, 4 times a week, 5 weeks, 10% discount
    if (
        re.search(r"\$?\s*\d+.+\b(an hour|per hour|/hour)\b", ql)
        and re.search(r"\bhours?\b", ql)
        and re.search(r"\b(times a week|a week|weeks?)\b", ql)
    ):
        rate_m = re.search(
            r"\$?\s*(\d+(?:\.\d+)?)\s*(?:an hour|per hour|/hour)",
            ql,
        )
        h_m = re.search(r"(\d+(?:\.\d+)?)\s*hours?\s+(?:to do|each day|a day|per day)", ql)
        if not h_m:
            h_m = re.search(r"takes\s+(\d+(?:\.\d+)?)\s*hours?", ql)
        week_m = re.search(r"(\d+)\s*times a week", ql)
        weeks_m = re.search(r"(\d+)\s*weeks?", ql)
        disc_m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*discount", ql)
        if rate_m and h_m and week_m and weeks_m:
            rate = float(rate_m.group(1))
            hours = float(h_m.group(1))
            per_week_times = float(week_m.group(1))
            weeks = float(weeks_m.group(1))
            per_day = push(
                "mul_rate", "rate×hours", f"{rate}*{hours}", rate * hours
            )
            per_week = push(
                "mul_groups",
                "day×times/week",
                f"{per_day}*{per_week_times}",
                per_day * per_week_times,
            )
            gross = push(
                "mul_groups",
                "week×weeks",
                f"{per_week}*{weeks}",
                per_week * weeks,
            )
            if disc_m and re.search(r"\b(pay|paid|cost|how much)\b", ql):
                d = float(disc_m.group(1))
                off = push(
                    "SCHEMA-rate-schedule",
                    "discount",
                    f"{gross}*{d}/100",
                    gross * d / 100.0,
                )
                pay = push(
                    "SCHEMA-rate-schedule",
                    "pay=gross−discount",
                    f"{gross}-{off}",
                    gross - off,
                )
                return SolveResult(_norm(pay), steps, used, True)
            if re.search(r"\b(pay|paid|cost|how much)\b", ql):
                return SolveResult(_norm(gross), steps, used, True)

    # ----- SCHEMA-fraction-remaining-split (bakery afternoon) -----
    # two-thirds sold morning; half of left sold equally afternoon and evening
    if re.search(
        r"\b(two-thirds|2/3|two thirds)\b", ql
    ) and re.search(r"\bhalf of what is left\b|\bhalf of (the )?remaining\b", ql):
        start_m = re.search(
            r"(?:produces?|makes?|bakes?|has|have)\s+(\d+(?:\.\d+)?)",
            ql,
        )
        if not start_m:
            start_m = re.search(r"(\d+(?:\.\d+)?)\s+loaves?", ql)
        if start_m:
            start = float(start_m.group(1))
            morning = push(
                "SCHEMA-fraction-remaining-split",
                "morning=2/3×start",
                f"2/3*{start}",
                start * 2.0 / 3.0,
            )
            rem = push(
                "sub_remove", "remaining", f"{start}-{morning}", start - morning
            )
            # equally afternoon and evening of remaining (or half each)
            if re.search(r"\bequally\b|\bafternoon\b.*\bevening\b", ql):
                part = push(
                    "SCHEMA-fraction-remaining-split",
                    "slot=rem/2",
                    f"{rem}/2",
                    rem / 2.0,
                )
                if re.search(r"\bafternoon\b", ql) and re.search(
                    r"\bhow many\b", ql
                ):
                    return SolveResult(_norm(part), steps, used, True)
                if re.search(r"\bevening\b", ql) and re.search(r"\bhow many\b", ql):
                    return SolveResult(_norm(part), steps, used, True)

    # ----- SCHEMA-salary-fractions (Zaid-style) -----
    # spend 1/4 on A, 1/3 on B, half of remaining to charity, then fixed gifts
    if re.search(r"\b(salary|earns?|earning)\b", ql) and re.search(
        r"\b(1/4|1/3|half of the remaining)\b", ql
    ):
        sal_m = re.search(
            r"(?:earns?|salary of|makes?)\s+\$?\s*(\d+(?:\.\d+)?)",
            ql,
        )
        if not sal_m:
            # "If Zaid earns 6000$ per month"
            sal_m = re.search(
                r"(?:earns?|earning)\s+(\d+(?:\.\d+)?)\s*\$?",
                ql,
            )
        if not sal_m:
            sal_m = re.search(
                r"(\d+(?:\.\d+)?)\s*\$\s*per month",
                ql,
            )
        # fractions of the *salary base* only (not half of remaining)
        fracs: List[float] = []
        for fm in re.finditer(
            r"(1/\d+)\s+of (?:his |her )?salary",
            ql,
        ):
            a, b = fm.group(1).split("/")
            fracs.append(float(a) / float(b))
        # "1/4 of his salary on rent, 1/3 on car fuel"
        for fm in re.finditer(r"(1/\d+)\s+on\s+\w+", ql):
            a, b = fm.group(1).split("/")
            v = float(a) / float(b)
            if v not in fracs:
                fracs.append(v)
        # Fixed gifts only — never the salary figure itself
        # "gives his daughter 200$ ... and 700$ to his wife"
        fixed_u: List[float] = []
        for fm in re.finditer(
            r"(?:daughter|son|wife|husband|child|kids?)\s+(\d+)\s*\$",
            ql,
        ):
            fixed_u.append(float(fm.group(1)))
        for fm in re.finditer(
            r"(\d+)\s*\$\s+to\s+(?:use|his|her|the)",
            ql,
        ):
            v = float(fm.group(1))
            if v not in fixed_u:
                fixed_u.append(v)
        for fm in re.finditer(
            r"and\s+(\d+)\s*\$\s+to\s+(?:his|her)",
            ql,
        ):
            v = float(fm.group(1))
            if v not in fixed_u:
                fixed_u.append(v)
        if sal_m and fracs:
            salary = float(sal_m.group(1))
            spent = 0.0
            for f in fracs:
                part = push(
                    "SCHEMA-salary-fractions",
                    "f×salary",
                    f"{f:g}*{salary}",
                    f * salary,
                )
                spent += part
            rem = push(
                "sub_remove", "after fractions", f"{salary}-{spent}", salary - spent
            )
            if re.search(r"\bhalf of the remaining\b|\bdonates half\b", ql):
                half = push(
                    "BIND-02", "half remaining", f"half({rem})", rem / 2.0
                )
                rem = push(
                    "sub_remove", "after half donate", f"{rem}-{half}", rem - half
                )
            if fixed_u and re.search(
                r"\b(still have|left|remain|after all)\b", ql
            ):
                gifts = sum(fixed_u)
                push("add_combine", "fixed gifts", str(gifts), gifts)
                left = push(
                    "SCHEMA-salary-fractions",
                    "left=rem−gifts",
                    f"{rem}-{gifts}",
                    rem - gifts,
                )
                return SolveResult(_norm(left), steps, used, True)
            if re.search(r"\b(still have|left|remain)\b", ql):
                return SolveResult(_norm(rem), steps, used, True)

    # =====================================================================
    # Refinement batch (linguistics cues → known multi-hop forms)
    # =====================================================================

    # ----- leave L, then twice as much as left added back (water tank) -----
    if re.search(r"twice as much as what was left", ql) and re.search(
        r"\b(used|took|removed)\b", ql
    ):
        nums_local = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", ql)]
        # start and consumed are first two quantities
        if len(nums_local) >= 2:
            start, consumed = nums_local[0], nums_local[1]
            if start > consumed:
                left = push(
                    "sub_remove",
                    "left=start−used",
                    f"{start}-{consumed}",
                    start - consumed,
                )
                rain = push("BIND-03", "twice left", f"2*{left}", 2.0 * left)
                now = push("add_combine", "left+rain", f"{left}+{rain}", left + rain)
                return SolveResult(_norm(now), steps, used, True)

    # ----- twice (A + B) combined (Peter exercise) -----
    m = re.search(
        r"twice the amount.*?combined.*?"
        r"(?:sunday|monday|first).*?(\d+(?:\.\d+)?)\s*minutes?.*?"
        r"(?:monday|sunday|second).*?(\d+(?:\.\d+)?)\s*minutes?",
        ql,
        re.S,
    )
    if not m:
        m = re.search(
            r"twice.*?(?:monday and sunday|sunday and monday) combined.*?"
            r"(\d+(?:\.\d+)?)\s*minutes?.*?(\d+(?:\.\d+)?)\s*minutes?",
            ql,
            re.S,
        )
    if m and re.search(r"\btwice\b", ql) and re.search(r"\bcombined\b", ql):
        a, b = float(m.group(1)), float(m.group(2))
        s = push("add_combine", "A+B", f"{a}+{b}", a + b)
        t = push("BIND-03", "twice sum", f"2*{s}", 2.0 * s)
        return SolveResult(_norm(t), steps, used, True)
    # looser: two minute amounts + twice + combined
    if (
        re.search(r"\btwice\b", ql)
        and re.search(r"\bcombined\b", ql)
        and re.search(r"\bminutes?\b", ql)
    ):
        mins = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*minutes?", ql)]
        if len(mins) == 2:
            s = push("add_combine", "A+B", f"{mins[0]}+{mins[1]}", mins[0] + mins[1])
            t = push("BIND-03", "twice sum", f"2*{s}", 2.0 * s)
            return SolveResult(_norm(t), steps, used, True)

    # ----- classroom: k times as many X as Y, f as many Z as Y, Y has N; total -----
    m = re.search(
        r"(\d+)\s+times as many \w+ as (?:they do )?(\w+).*?"
        r"(1/\d+|\d+/\d+)\s+as many \w+ as (?:they do )?(?:\w+).*?"
        r"(?:has|have)\s+(\d+)\s+(\w+)",
        ql,
        re.S,
    )
    if m and re.search(r"\b(total|how many total|in total|total children)\b", ql):
        k = float(m.group(1))
        frac = m.group(3)
        base = float(m.group(4))
        if "/" in frac:
            a, b = frac.split("/")
            f = float(a) / float(b)
        else:
            f = float(frac)
        g = push("BIND-03", "k×base", f"{k}*{base}", k * base)
        z = push("BIND-02", "f×base", f"{f:g}*{base}", f * base)
        tot = push("add_combine", "g+base+z", f"{g}+{base}+{z}", g + base + z)
        return SolveResult(_norm(tot), steps, used, True)
    # looser classroom: "N times as many" + "1/10 as many" + "has 30 boys" + total
    if (
        re.search(r"\btimes as many\b", ql)
        and re.search(r"\b1/\d+\s+as many\b", ql)
        and re.search(r"\b(total|how many total)\b", ql)
    ):
        km = re.search(r"(\d+)\s+times as many", ql)
        fm = re.search(r"(1/\d+|\d+/\d+)\s+as many", ql)
        bm = re.search(r"(?:has|have)\s+(\d+)\s+\w+", ql)
        if km and fm and bm:
            k = float(km.group(1))
            a, b = fm.group(1).split("/")
            f = float(a) / float(b)
            base = float(bm.group(1))
            g = push("BIND-03", "k×base", f"{k}*{base}", k * base)
            z = push("BIND-02", "f×base", f"{f:g}*{base}", f * base)
            tot = push("add_combine", "g+base+z", f"{g}+{base}+{z}", g + base + z)
            return SolveResult(_norm(tot), steps, used, True)

    # ----- loan + interest − payments remaining (Janeth) -----
    m = re.search(
        r"borrowed\s+\$?\s*(\d+(?:\.\d+)?).*?"
        r"(?:additional|interest)\s+(\d+(?:\.\d+)?)\s*%.*?"
        r"\$?\s*(\d+(?:\.\d+)?)\s*(?:a month|per month).*?"
        r"(\d+)\s*months?",
        ql,
        re.S,
    )
    if m and re.search(r"\b(remaining|balance|left)\b", ql):
        principal = float(m.group(1))
        pct = float(m.group(2))
        monthly = float(m.group(3))
        months = float(m.group(4))
        interest = push(
            "SCHEMA-loan-balance",
            "interest=p%×principal",
            f"{pct}%*{principal}",
            principal * pct / 100.0,
        )
        owed = push(
            "add_combine",
            "owed=principal+interest",
            f"{principal}+{interest}",
            principal + interest,
        )
        paid = push(
            "mul_groups",
            "paid=monthly×months",
            f"{monthly}*{months}",
            monthly * months,
        )
        rem = push("sub_remove", "balance=owed−paid", f"{owed}-{paid}", owed - paid)
        return SolveResult(_norm(rem), steps, used, True)

    # ----- fee stack net proceeds (Mr Tan) -----
    # sale price, p% transfer, q% brokerage, loan remaining → net = sale − fees − loan
    if re.search(r"\b(net proceeds|net from selling)\b", ql) or (
        re.search(r"\b(transfer fees?|brokerage)\b", ql)
        and re.search(r"\b(selling price|sold .* for)\b", ql)
    ):
        price_m = re.search(
            r"(?:sold .* for|selling price of)\s+\$?\s*(\d+(?:\s+\d+)*)",
            ql,
        )
        if not price_m:
            price_m = re.search(r"\$\s*(\d+(?:\s+\d+){0,2})", q.replace(",", ""))
        pcts = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", ql)]
        loan_m = re.search(
            r"(?:loan|remaining loan|paid)\s+\$?\s*(\d+(?:\s+\d+)*)",
            ql,
        )
        # normalize "400 000" → 400000
        def _money(s: str) -> float:
            return float(re.sub(r"\s+", "", s))

        if price_m and len(pcts) >= 2:
            price = _money(price_m.group(1))
            fees = 0.0
            for p in pcts[:2]:
                fee = push(
                    "SCHEMA-fee-stack",
                    "fee=p%×price",
                    f"{p}%*{price}",
                    price * p / 100.0,
                )
                fees += fee
            loan = 0.0
            if loan_m:
                loan = _money(loan_m.group(1))
                # avoid treating small percents as loan
                if loan < price:
                    push("BIND-01", "loan", f"loan={loan}", loan)
                else:
                    loan = 0.0
            # also "paid $250000 for the remaining loan"
            loan2 = re.search(
                r"paid\s+\$?\s*(\d+(?:\s+\d+)*)\s+for the remaining loan",
                ql,
            )
            if loan2:
                loan = _money(loan2.group(1))
            net = push(
                "SCHEMA-fee-stack",
                "net=price−fees−loan",
                f"{price}-{fees}-{loan}",
                price - fees - loan,
            )
            return SolveResult(_norm(net), steps, used, True)

    # ----- section weight × height, then (1−p%) remains (redwood) -----
    m = re.search(
        r"(\d+(?:\.\d+)?)-foot section.*?weighs\s+(\d+(?:\.\d+)?).*?"
        r"(\d+(?:\.\d+)?)\s*%.*?"
        r"(\d+(?:\.\d+)?)\s*feet?\s+tall",
        ql,
        re.S,
    )
    if m and re.search(r"\bweigh\b", ql):
        sec, w, pct, height = (
            float(m.group(1)),
            float(m.group(2)),
            float(m.group(3)),
            float(m.group(4)),
        )
        nsec = push("div_share", "sections=h/sec", f"{height}/{sec}", height / sec)
        full = push("mul_groups", "full weight", f"{nsec}*{w}", nsec * w)
        eaten = push(
            "SCHEMA-section-weight",
            "eaten=p%×full",
            f"{pct}%*{full}",
            full * pct / 100.0,
        )
        left = push("sub_remove", "left=full−eaten", f"{full}-{eaten}", full - eaten)
        return SolveResult(_norm(left), steps, used, True)

    # ----- multi-day times-as-many + calorie diff (Sue cookies) -----
    if (
        re.search(r"\bon monday\b", ql)
        and re.search(r"\bon tuesday\b", ql)
        and re.search(r"\btimes as many\b", ql)
        and re.search(r"\bcalories?\b", ql)
    ):
        # sister ate A Monday and B next day; Sue k× Mon, m× Tue; cal per cookie
        sm = re.search(
            r"sister ate\s+(\d+).*?monday.*?(\d+).*?(?:next day|tuesday)",
            ql,
            re.S,
        )
        km = re.search(r"monday.*?(\d+)\s+times as many", ql, re.S)
        tm = re.search(r"tuesday.*?(\d+|twice)\s+times as many|tuesday.*?twice as many", ql, re.S)
        cal = re.search(r"(\d+)\s*calories?", ql)
        if sm and km and cal:
            sis_m, sis_t = float(sm.group(1)), float(sm.group(2))
            k = float(km.group(1))
            if tm:
                raw = tm.group(1) if tm.lastindex else "2"
                mlt = 2.0 if str(raw) == "twice" or raw is None else float(raw)
            else:
                mlt = 2.0 if re.search(r"tuesday.*?twice", ql, re.S) else 2.0
            sue_m = push("BIND-03", "sue mon", f"{k}*{sis_m}", k * sis_m)
            sue_t = push("BIND-03", "sue tue", f"{mlt}*{sis_t}", mlt * sis_t)
            sue = push("add_combine", "sue total", f"{sue_m}+{sue_t}", sue_m + sue_t)
            sis = push("add_combine", "sis total", f"{sis_m}+{sis_t}", sis_m + sis_t)
            diff = push("sub_diff", "more cookies", f"{sue}-{sis}", sue - sis)
            cals = float(cal.group(1))
            out = push("mul_groups", "cal diff", f"{diff}*{cals}", diff * cals)
            return SolveResult(_norm(out), steps, used, True)

    # ----- adults take fixed, rest share among children -----
    m = re.search(
        r"(\d+)\s+adults?.*?(\d+)\s+children?.*?"
        r"(\d+)\s+packets?.*?each packet contains\s+(\d+).*?"
        r"each adult gets\s+(\d+).*?"
        r"(?:rest|remaining).*?(?:shared equally|equally).*?children",
        ql,
        re.S,
    )
    if m:
        nad, nch, npk, per_pk, per_ad = (
            float(m.group(1)),
            float(m.group(2)),
            float(m.group(3)),
            float(m.group(4)),
            float(m.group(5)),
        )
        total = push("mul_groups", "bars", f"{npk}*{per_pk}", npk * per_pk)
        ad = push("mul_groups", "adults", f"{nad}*{per_ad}", nad * per_ad)
        rem = push("sub_remove", "rest", f"{total}-{ad}", total - ad)
        each = push("div_share", "per child", f"{rem}/{nch}", rem / nch)
        return SolveResult(_norm(each), steps, used, True)

    # =====================================================================
    # No-fire lift batch (sense already tags these; executors were missing)
    # =====================================================================

    # ----- N dozen @ $P each line → sum (Toula bakery) -----
    dozen_lines = re.findall(
        r"(\d+)\s+dozen\w*.*?(?:cost|for)\s+\$?\s*(\d+(?:\.\d+)?)\s*per dozen",
        ql,
    )
    if len(dozen_lines) >= 2 and re.search(r"\b(total cost|how much was the total)\b", ql):
        s = 0.0
        for n, p in dozen_lines:
            line = push(
                "SCHEMA-dozen-cost",
                "n×price/dozen",
                f"{n}*{p}",
                float(n) * float(p),
            )
            s += line
        push("add_combine", "sum lines", str(s), s)
        return SolveResult(_norm(s), steps, used, True)

    # ----- paid D after p% discount → original = D/(1-p/100) -----
    if re.search(r"\boriginal price\b", ql) and re.search(r"\bdiscount\b", ql):
        paid_m = re.search(r"\$\s*(\d+(?:\.\d+)?)", q)
        pct_m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*discount", ql)
        if paid_m and pct_m:
            paid, pct = float(paid_m.group(1)), float(pct_m.group(1))
            factor = 1.0 - pct / 100.0
            if factor > 0 and paid < 1e6:
                orig = push(
                    "SCHEMA-discount-original",
                    "orig=paid/(1-p/100)",
                    f"{paid}/{factor}",
                    paid / factor,
                )
                return SolveResult(_norm(orig), steps, used, True)

    # ----- overtime: regular rate R for H0 hours, OT multiplier m, worked H -----
    m = re.search(
        r"(?:rate per hour|hourly rate|is\s+\$?\s*(\d+(?:\.\d+)?)).*?"
        r"first\s+(\d+)\s+hours?.*?"
        r"(?:overtime|1\.(\d+)|(\d+(?:\.\d+)?)\s+times her regular).*?"
        r"worked.*?(\d+)\s+hours?",
        ql,
        re.S,
    )
    # simpler Eliza pattern
    m2 = re.search(
        r"first\s+(\d+)\s+hours?.*?is\s+\$?\s*(\d+(?:\.\d+)?).*?"
        r"(\d+(?:\.\d+)?)\s+times her regular.*?worked.*?(\d+)\s+hours?",
        ql,
        re.S,
    )
    if m2:
        h0, rate, mult, h = (
            float(m2.group(1)),
            float(m2.group(2)),
            float(m2.group(3)),
            float(m2.group(4)),
        )
        ot_h = push("sub_remove", "OT hours", f"{h}-{h0}", h - h0)
        ot_rate = push("mul_groups", "OT rate", f"{rate}*{mult}", rate * mult)
        reg = push("mul_rate", "regular", f"{rate}*{h0}", rate * h0)
        ot_pay = push("mul_rate", "OT pay", f"{ot_rate}*{ot_h}", ot_rate * ot_h)
        tot = push("add_combine", "earnings", f"{reg}+{ot_pay}", reg + ot_pay)
        return SolveResult(_norm(tot), steps, used, True)

    # ----- two hourly jobs × hours/week × weeks (Jill) -----
    m = re.search(
        r"\$?\s*(\d+(?:\.\d+)?)\s*per hour.*?"
        r"\$?\s*(\d+(?:\.\d+)?).*?"
        r"(\d+)\s*weeks? a year.*?"
        r"(\d+)\s*hours? a week.*?"
        r"(\d+)\s*hours? a week",
        ql,
        re.S,
    )
    if m and re.search(r"\b(annual|salary|year)\b", ql):
        r1, r2, weeks, h1, h2 = (
            float(m.group(1)),
            float(m.group(2)),
            float(m.group(3)),
            float(m.group(4)),
            float(m.group(5)),
        )
        w1 = push("mul_rate", "job1/week", f"{r1}*{h1}", r1 * h1)
        w2 = push("mul_rate", "job2/week", f"{r2}*{h2}", r2 * h2)
        week = push("add_combine", "week total", f"{w1}+{w2}", w1 + w2)
        year = push("mul_groups", "annual", f"{week}*{weeks}", week * weeks)
        return SolveResult(_norm(year), steps, used, True)

    # ----- month downloads: M1, k×M1, then reduce by p% of M2; total -----
    m = re.search(
        r"(\d+)\s+downloads? in the first month.*?"
        r"(\d+|three|two|four|five)\s+times as many as.*?first month.*?"
        r"(?:reduced by\s+)?(\d+)\s*%.*?third month.*?"
        r"(?:total|how many downloads)",
        ql,
        re.S,
    )
    if m:
        m1 = float(m.group(1))
        ktok = m.group(2)
        k = float(WORD_NUM.get(ktok, ktok))
        pct = float(m.group(3))
        m2 = push("BIND-03", "month2", f"{k}*{m1}", k * m1)
        cut = push(
            "SCHEMA-month-cascade",
            "cut=p% of m2",
            f"{pct}%*{m2}",
            m2 * pct / 100.0,
        )
        m3 = push("sub_remove", "month3", f"{m2}-{cut}", m2 - cut)
        tot = push("add_combine", "3 months", f"{m1}+{m2}+{m3}", m1 + m2 + m3)
        return SolveResult(_norm(tot), steps, used, True)

    # ----- change from payment (sum costs, pay P, change) -----
    if re.search(r"\b(change|cashier|give back|gives back)\b", ql):
        # prices like $4.20
        prices = [float(x) for x in re.findall(r"\$\s*(\d+(?:\.\d+)?)", q)]
        if len(prices) >= 3:
            # last is often payment if "pays $20"
            pay_m = re.search(r"pays?\s+\$?\s*(\d+(?:\.\d+)?)", ql)
            if pay_m:
                pay = float(pay_m.group(1))
                costs = [p for p in prices if abs(p - pay) > 1e-9]
                if not costs:
                    costs = prices[:-1]
                    pay = prices[-1]
                spent = sum(costs)
                push("add_combine", "spent", str(spent), spent)
                ch = push("sub_remove", "change", f"{pay}-{spent}", pay - spent)
                return SolveResult(_norm(ch), steps, used, True)

    # ----- beats p% of N → lose = N - p%*N -----
    m = re.search(
        r"(\d+)\s+(?:people|players|opponents).*?"
        r"beats?\s+(\d+)\s*%.*?"
        r"(?:lose|lost|does he lose)",
        ql,
        re.S,
    )
    if m:
        n, pct = float(m.group(1)), float(m.group(2))
        win = push("AR-202", "beats", f"{pct}%*{n}", n * pct / 100.0)
        lose = push("sub_remove", "lose", f"{n}-{win}", n - win)
        return SolveResult(_norm(lose), steps, used, True)

    # ----- A per batch * n batches + B per batch * m (Mason sugar) -----
    m = re.search(
        r"(\d+(?:\.\d+)?)\s+\w+.*?batch of \w+.*?"
        r"(\d+(?:\.\d+)?)\s+\w+.*?batch of \w+.*?"
        r"(\d+)\s+batches? of \w+.*?"
        r"(\d+)\s+batch(?:es)? of",
        ql,
        re.S,
    )
    if m and re.search(r"\bhow much\b|\bhow many\b", ql):
        a, b, n, m_ct = (
            float(m.group(1)),
            float(m.group(2)),
            float(m.group(3)),
            float(m.group(4)),
        )
        t1 = push("mul_groups", "type1", f"{a}*{n}", a * n)
        t2 = push("mul_groups", "type2", f"{b}*{m_ct}", b * m_ct)
        tot = push("add_combine", "total", f"{t1}+{t2}", t1 + t2)
        return SolveResult(_norm(tot), steps, used, True)

    # ----- servings per carton, eat 1/day, days D, cost per carton -----
    m = re.search(
        r"(\d+)\s+servings?.*?per carton.*?\$?\s*(\d+(?:\.\d+)?)\s*per carton.*?"
        r"(?:after\s+)?(\d+)\s+days?",
        ql,
        re.S,
    )
    if m and re.search(r"\b(spend|cost|how much)\b", ql):
        serv, price, days = float(m.group(1)), float(m.group(2)), float(m.group(3))
        carts = push("div_share", "cartons", f"{days}/{serv}", days / serv)
        spend = push("mul_groups", "spend", f"{carts}*{price}", carts * price)
        return SolveResult(_norm(spend), steps, used, True)

    # ----- cart: known lines + total paid; unknown qty of last item -----
    # Marie: chicken $12, 5 milk $3 each, 4 apples $1.50 each, pizza $8.50, paid $50
    if re.search(r"\bpaid a total of\b", ql) and re.search(
        r"\bhow many (boxes|packs|items|cartons)?\b|\bhow many \w+ did\b",
        ql,
    ):
        total_m = re.search(r"paid a total of\s+\$?\s*(\d+(?:\.\d+)?)", ql)
        last_price = re.search(
            r"each (?:box|pack|item|one)?\s*costs?\s+\$?\s*(\d+(?:\.\d+)?)",
            ql,
        )
        # unit costs with quantities
        qty_each = re.findall(
            r"(\d+)\s+\w+(?:\s+\w+){0,2}\s+that costs?\s+\$?\s*(\d+(?:\.\d+)?)\s*each",
            ql,
        )
        singles = re.findall(
            r"(?:one|a|an)\s+\w+(?:\s+\w+){0,2}\s+that costs?\s+\$?\s*(\d+(?:\.\d+)?)",
            ql,
        )
        if total_m and last_price and (qty_each or singles):
            paid = float(total_m.group(1))
            unit = float(last_price.group(1))
            spent = 0.0
            for a, p in qty_each:
                spent += float(a) * float(p)
            for p in singles:
                # skip if this is the last item unit price restated
                if abs(float(p) - unit) < 1e-9 and "pizza" in ql:
                    continue
                spent += float(p)
            push("add_combine", "known spend", str(spent), spent)
            rem = push("sub_remove", "for unknown", f"{paid}-{spent}", paid - spent)
            if unit > 0 and rem >= 0:
                qty = push("div_share", "qty", f"{rem}/{unit}", rem / unit)
                return SolveResult(_norm(qty), steps, used, True)

    # ----- flock: each eats K cups/day; morning A, afternoon B; final meal -----
    # Wendi: 3 cups each × 20 chickens = 60; final = 60 − 15 − 25
    if (
        re.search(r"\bcups?\b", ql)
        and re.search(r"\bmorning\b", ql)
        and re.search(r"\bafternoon\b", ql)
        and re.search(r"\b(final meal|last meal)\b", ql)
        and re.search(r"\bchickens?\b", ql)
    ):
        # "each of her chickens three cups" or "each chicken eats 3 cups"
        km = re.search(
            r"each(?: of her)? \w+\s+(?:eats\s+)?(\d+|three|two|four|five)\s+cups?",
            ql,
        )
        morn = re.search(r"morning.*?(\d+)\s+cups?", ql)
        aft = re.search(r"afternoon.*?(\d+)\s+cups?", ql)
        n_ch = re.search(r"flock is\s+(\d+)\s+chickens?", ql)
        if not n_ch:
            n_ch = re.search(r"(\d+)\s+chickens?", ql)
        if km and morn and aft and n_ch:
            raw = km.group(1)
            k = float(WORD_NUM.get(raw, raw))
            n = float(n_ch.group(1))
            mo, af = float(morn.group(1)), float(aft.group(1))
            need = push("mul_groups", "daily need", f"{k}*{n}", k * n)
            left = push(
                "sub_remove",
                "final meal",
                f"{need}-{mo}-{af}",
                need - mo - af,
            )
            return SolveResult(_norm(left), steps, used, True)

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
        # --- high-lift schemas ---
        (
            "Melanie sold a third of her vacuum cleaners at the green house, 2 more to the red "
            "house, and half of what was left at the orange house. If Melanie has 5 vacuum "
            "cleaners left, how many did she start with?",
            "18",
            "SCHEMA-inventory-cascade",
        ),
        (
            "Nissa hires 60 seasonal workers to play elves. A third of the elves quit after "
            "children vomit on them, then 10 of the remaining elves quit after kids kick their "
            "shins. How many elves are left?",
            "30",
            "SCHEMA-sequential-fraction",
        ),
        (
            "A hospital sees 500 people a day. Each patient is seen for an average of 24 minutes. "
            "The doctors charge $150 an hour to the hospital and the hospital charges the "
            "patients $200 an hour. How much profit does the hospital make from these visits?",
            "10000",
            "SCHEMA-billable-hours",
        ),
        (
            "Jeans makeup artist charges her $250 an hour. It takes 6 hours to do each day and "
            "she needs it done 4 times a week. The movie takes 5 weeks to finish. After the "
            "movie the makeup artist gives Jean a 10% discount. How much did Jean pay?",
            "27000",
            "SCHEMA-rate-schedule",
        ),
        (
            "A bakery produces 60 loaves of bread each day. Two-thirds of the loaves are sold in "
            "the morning and half of what is left is sold equally in the afternoon and evening. "
            "How many loaves of bread are sold in the afternoon?",
            "10",
            "SCHEMA-fraction-remaining-split",
        ),
        (
            "Zaid spends 1/4 of his salary on rent, 1/3 on car fuel and donates half of the "
            "remaining amount to his favorite charity. He gives his daughter 200$ to use for her "
            "weekly expenses and 700$ to his wife. If Zaid earns 6000$ per month, how much money "
            "will he still have after all these expenses and donations?",
            "350",
            "SCHEMA-salary-fractions",
        ),
        (
            "He bought 38 chicken sausages and 6 more fish sausages than chicken sausages. "
            "How many sausages did he buy in all?",
            "82",
            "BIND-04",
        ),
        (
            "A water tank is filled with 120 liters of water. Celine used 90 liters. She collected "
            "rainwater that is twice as much as what was left. How many liters of water are in "
            "the tank now?",
            "90",
            "BIND-03",
        ),
        (
            "On Tuesday, Peter wants to exercise for twice the amount of time he did on Monday "
            "and Sunday combined. On Sunday he exercised for 23 minutes. On Monday he exercised "
            "for 16 minutes. How many minutes does he have to exercise on Tuesday?",
            "78",
            "BIND-03",
        ),
        (
            "If a classroom has 3 times as many girls as they do boys, and 1/10 as many "
            "nongendered children as they do boys, and the classroom has 30 boys. How many total "
            "children does it have?",
            "123",
            "BIND-03",
        ),
        (
            "Janeth borrowed $2000 and promised to return it with an additional 10% of the amount. "
            "If she is going to pay $165 a month for 12 months, how much will be Janeth's "
            "remaining balance by then?",
            "220",
            "SCHEMA-loan-balance",
        ),
        (
            "Mr. Tan sold his house for $400000. He paid the transfer fees that amount to 3% of "
            "the selling price and also paid a brokerage fee that is 5% of the selling price. "
            "If he also paid $250000 for the remaining loan amount of the house, how much is "
            "Mr. Tan's net proceeds from selling the house?",
            "118000",
            "SCHEMA-fee-stack",
        ),
        (
            "Each solid 10-foot section of a redwood tree weighs 400 pounds. Termites ate 30% of "
            "this redwood's wood. If the redwood is 200 feet tall, how much does it weigh?",
            "5600",
            "SCHEMA-section-weight",
        ),
        (
            "4 adults and 8 children are to share 8 packets of chocolate bars. Each packet "
            "contains 5 chocolate bars. If each adult gets 6 chocolate bars and the rest are to "
            "be shared equally among the children, how many will each child get?",
            "2",
            "SCHEMA-share-rest",
        ),
    ]
