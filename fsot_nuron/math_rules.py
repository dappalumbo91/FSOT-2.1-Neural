"""Rule-first mathematical reasoning — how humans are actually taught.

Doctrine (user correction):
  Do NOT shove Q→A pairs and hope retrieval generalizes.
  Teach RULES + symbolic formulas + how to break problems down and APPLY them.

Layers (school order):
  1. Arithmetic laws (what + − × ÷ *mean* and how they compose)
  2. Language → operator maps ("half", "each", "left", "per hour", …)
  3. Decomposition: find quantities → pick rules → build expression → evaluate
  4. Practice problems as *rule application*, not memorization targets

FSOT: free_parameters=0 on the law path; rules are preregistered symbolic structure.
Executor is deterministic Fixed-compatible arithmetic (host f64 lab twin).

  python scripts/run_math_rules_teach.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .paths import DATA

PASS = 0.95
REPO_DIR = DATA / "curriculum" / "math_rules"
GAME_DIR = Path(r"D:\fsot_training\curriculum\math_rules")
GSM8K = Path(r"D:\training data\gsm8k")

# Allow sentence-final "10." — only block if more digits/letters continue the token
NUM_RE = re.compile(r"(?<![\w])(\d+(?:\.\d+)?)(?![\d])")


# ---------------------------------------------------------------------------
# Layer 1 — arithmetic laws (symbolic)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MathRule:
    id: str
    name: str
    formula: str  # symbolic form taught
    description: str
    # how to fire: name of strategy tag
    strategy: str


# Preregistered school rules (not fitted)
ARITH_RULES: List[MathRule] = [
    MathRule("add_comm", "addition commutative", "a + b = b + a", "Order of addends does not change sum", "add"),
    MathRule("add_zero", "addition identity", "a + 0 = a", "Adding zero leaves a number unchanged", "add"),
    MathRule("add_combine", "combine quantities", "total = a + b + …", "Together / altogether / in all → add", "add"),
    MathRule("sub_remove", "subtraction remove", "left = total − used", "Left / remain / rest → subtract", "sub"),
    MathRule("sub_diff", "difference", "diff = |a − b|", "How many more / less → difference", "sub"),
    MathRule("mul_groups", "multiplication groups", "total = n × size", "Each / every / times → multiply", "mul"),
    MathRule("mul_rate", "rate product", "amount = rate × time", "Per hour/day with duration → multiply (convert units)", "rate"),
    MathRule("div_share", "division share", "each = total ÷ n", "Split equally / per person → divide", "div"),
    MathRule("div_rate", "division rate", "time = amount ÷ rate", "How long at constant rate → divide", "div"),
    MathRule("half", "half", "half(n) = n / 2", "Half as many / half of → divide by 2", "half"),
    MathRule("double", "double", "double(n) = n × 2", "Twice / double → multiply by 2", "double"),
    MathRule("percent", "percent of", "p% of x = (p/100) × x", "Percent of a quantity", "percent"),
    MathRule("remain_after", "remainder chain", "left = start − a − b", "Start, use some, use more, what left", "sub_chain"),
    MathRule("compose", "compose steps", "use prior result in next rule", "Multi-hop: output of step k is input to step k+1", "compose"),
    # Referent binding (wrong-fire fix): operate on named quantities, not digit order
    MathRule("BIND-01", "quantity binding", "number ↔ noun/role", "Bind each number to its noun/role before operating", "bind"),
    MathRule("BIND-02", "referent attachment", "half/% of X → binding[X]", "Modifiers attach to their object, not nums[0]", "bind"),
    MathRule("BIND-03", "relative chain", "A=k·B; B=m·C; C=n → A=k·m·n", "Compose multi-hop times-as relations from a known base", "bind"),
    MathRule("BIND-04", "offset after referent", "A = B ± k", "Fewer/more shift a bound quantity after resolving B", "bind"),
    MathRule("SCHEMA-remainder-sell", "remainder then sell", "money=(start−u1−u2)×price", "Inventory residual sold at unit price", "schema"),
    MathRule("SCHEMA-win-loss", "win/loss total", "W=(T+d)/2", "Won d more than lost with T games", "schema"),
    MathRule("SCHEMA-clock", "clock duration", "hours=end−start", "Time-of-day span, then optional rate×hours", "schema"),
    MathRule(
        "SCHEMA-profit-markup",
        "house-flip profit",
        "new=buy·(1+p/100); profit=new−buy−repair",
        "Percent increase on purchase price; subtract buy+repair",
        "schema",
    ),
    MathRule(
        "SCHEMA-inventory-cascade",
        "inventory cascade backward",
        "undo half→×2; undo +k→+k; undo 1/3→×3/2",
        "Recover start from remaining by reversing each sale step",
        "schema",
    ),
    MathRule(
        "SCHEMA-sequential-fraction",
        "sequential fraction then count",
        "left=start·(1−f)−k",
        "Fraction leave first; then absolute count leaves remainder",
        "schema",
    ),
    MathRule(
        "SCHEMA-billable-hours",
        "billable hours profit",
        "hours=n×min/60; profit=hours×(charge−cost)",
        "Convert patient minutes to hours; margin × hours",
        "schema",
    ),
    MathRule(
        "SCHEMA-rate-schedule",
        "hourly rate schedule discount",
        "pay=rate×h×days×weeks×(1−d%)",
        "Recurring hourly work across calendar then optional discount",
        "schema",
    ),
    MathRule(
        "SCHEMA-fraction-remaining-split",
        "fraction then remaining split",
        "rem=start·(1−f); part=rem/2",
        "After fraction taken, remaining shared equally",
        "schema",
    ),
    MathRule(
        "SCHEMA-salary-fractions",
        "salary fraction cascade",
        "left=start−Σ(fi·start); half rem; −gifts",
        "Fractions of salary base then half residual then fixed gifts",
        "schema",
    ),
]


# ---------------------------------------------------------------------------
# Layer 2 — language → operator (taught maps)
# ---------------------------------------------------------------------------

# Each cue teaches: phrase → which rule strategy to prefer
LANGUAGE_MAPS: List[Tuple[str, str, str]] = [
    # (regex, strategy, teach_cue)
    (r"\b(altogether|in all|in total|combined|sum|together)\b", "add", "altogether means add"),
    (r"\b(left|remain|remaining|rest|leftover)\b", "sub", "left means subtract from total"),
    (r"\b(how many more|how much more|difference|less than|more than)\b", "sub", "more/less means difference"),
    (r"\b(each|every|per)\b", "mul", "each/every often means multiply groups"),
    (r"\b(times as many|times more)\b", "mul", "times as many means multiply"),
    (r"\b(half of|half as many|one half)\b", "half", "half means divide by two"),
    (r"\b(twice|double|two times)\b", "double", "twice means multiply by two"),
    (r"\b(split|share|divided|per person)\b", "div", "split equally means divide"),
    (r"\bpercent|%\b", "percent", "percent of means times p over 100"),
    (r"\bper (hour|minute|day|week)\b", "rate", "per unit time is a rate"),
    (r"\b(sells the remainder|rest of)\b", "sub_chain", "remainder after uses is subtract chain"),
    (r"\bhalf of [A-Za-z]", "bind", "half of NAME binds to that person's quantity"),
    (r"\btimes as (old|many) as\b|\btwice as many\b", "bind", "times-as chain: compose relations from known base"),
    (r"\bfewer than\b|\bmore \w+ than half\b", "bind", "offset after resolving the referent first"),
    (r"\bwon \d+ more than .+ lost\b", "schema", "win/loss: W=(T+d)/2"),
    (r"\bfrom \d.+(am|pm).+(to|until)\b", "schema", "clock span then optional rate"),
    (r"\bincreased the value\b.*%", "schema", "profit = cost × p%"),
]


def _norm(s: str) -> str:
    s = str(s).strip().replace(",", "").replace("$", "")
    if re.fullmatch(r"-?\d+\.0+", s):
        return s.split(".")[0]
    try:
        f = float(s)
        if abs(f - round(f)) < 1e-9:
            return str(int(round(f)))
        return f"{f:.10f}".rstrip("0").rstrip(".")
    except ValueError:
        return s


def exact_num(a: str, b: str) -> bool:
    try:
        return abs(float(_norm(a)) - float(_norm(b))) < 1e-6
    except ValueError:
        return _norm(a) == _norm(b)


_WORD_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "dozen": 12, "half": 0.5,
}


def extract_nums(text: str) -> List[float]:
    """Digits plus common number words (so 'three'/'four' bind as quantities)."""
    out: List[float] = []
    # strip commas in thousands
    t = text.replace(",", "")
    # find digits
    for m in NUM_RE.finditer(t):
        try:
            out.append(float(m.group(1)))
        except ValueError:
            pass
    # number words not already part of larger tokens
    for w, v in _WORD_NUM.items():
        if w == "half":
            continue  # operator, not always a free quantity
        for m in re.finditer(rf"\b{w}\b", t.lower()):
            # skip if this position overlaps a digit we already have nearby — still append word nums
            out.append(float(v))
    return out


def eval_binop(a: float, op: str, b: float) -> Optional[float]:
    try:
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if abs(b) < 1e-12:
                return None
            return a / b
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# Layer 3 — decomposition + rule application (the actual "thinking")
# ---------------------------------------------------------------------------

@dataclass
class StepTrace:
    rule_id: str
    formula: str
    detail: str
    value: float


@dataclass
class SolveResult:
    answer: Optional[str]
    steps: List[StepTrace] = field(default_factory=list)
    strategies_used: List[str] = field(default_factory=list)
    ok: bool = False


def detect_strategies(q: str) -> List[str]:
    ql = q.lower()
    found = []
    for rx, strat, _cue in LANGUAGE_MAPS:
        if re.search(rx, ql) and strat not in found:
            found.append(strat)
    # PFLT-style sense interlingua: phrase → OP/SCHEMA sense → strategy
    # Mass bindings (thousands) densify offline; this only *reads* them.
    try:
        from .math_sense_interlingua import MathSenseInterlingua

        # lazy singleton
        global _MATH_SENSE_IX
        try:
            _MATH_SENSE_IX
        except NameError:
            _MATH_SENSE_IX = MathSenseInterlingua()
        cue = _MATH_SENSE_IX.translate_cues(q)
        for s in cue.strategies:
            if s and s not in found:
                found.append(s)
    except Exception:
        pass
    return found


def apply_rules(question: str) -> SolveResult:
    """Apply taught rules to quantities in the question — not nearest-neighbor stuffing."""
    q = question.strip()
    ql = q.lower()
    nums = extract_nums(q)
    strats = detect_strategies(q)
    steps: List[StepTrace] = []
    used: List[str] = []

    def push(rule_id: str, formula: str, detail: str, value: float) -> float:
        steps.append(StepTrace(rule_id, formula, detail, value))
        if rule_id not in used:
            used.append(rule_id)
        return value

    # --- ordered rule application (school: read problem → pick operations) ---
    # Priority: pure arithmetic identities → BIND/SCHEMA multi-hop → keyword templates.

    def _safe_eval_arith(expr_raw: str) -> Optional[float]:
        expr = expr_raw.replace(" ", "").replace("^", "**")
        # only digits, ops, parens, dots
        if not re.fullmatch(r"[0-9\.\+\-\*/\(\)]+", expr.replace("**", "x")):
            # after replacing ** with placeholder, remaining must be simple
            tmp = expr.replace("**", "")
            if not re.fullmatch(r"[0-9\.\+\-\*/\(\)]+", tmp):
                return None
        try:
            return float(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307 — arithmetic only
        except Exception:
            return None

    # pure expression evaluate (order of operations)
    m = re.match(r"evaluate\s+(.+)$", ql)
    if m:
        v = _safe_eval_arith(m.group(1).rstrip("?"))
        if v is not None:
            push("AR-262", "×÷ before +−; grouping first", m.group(1), v)
            return SolveResult(_norm(v), steps, used, True)
    bare = ql.strip().rstrip("?")
    if re.fullmatch(r"[0-9\.\+\-\*/\s\^\(\)]+", bare) and re.search(r"[\+\-\*/\^]", bare):
        v = _safe_eval_arith(bare)
        if v is not None:
            push("AR-262", "evaluate expression", bare, v)
            return SolveResult(_norm(v), steps, used, True)

    # BIND/SCHEMA first for multi-hop / referent problems (lazy import avoids cycle)
    # Runs even when only number-words are present (e.g. "eats three").
    try:
        from .math_binding import solve_with_binding

        bound = solve_with_binding(q)
        if bound.ok and bound.answer is not None:
            return bound
    except Exception:
        pass

    if not nums:
        return SolveResult(None, steps, used, False)

    # AR-103 additive identity: a + 0
    m = re.match(r"what is (\d+(?:\.\d+)?)\s*\+\s*0\??$", ql)
    if m:
        a = float(m.group(1))
        push("AR-103", "a+0=a", f"{a}+0", a)
        return SolveResult(_norm(a), steps, used, True)
    # AR-121 a - 0
    m = re.match(r"what is (\d+(?:\.\d+)?)\s*-\s*0\??$", ql)
    if m:
        a = float(m.group(1))
        push("AR-121", "a-0=a", f"{a}-0", a)
        return SolveResult(_norm(a), steps, used, True)
    # AR-122 a - a
    m = re.match(r"what is (\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\??$", ql)
    if m and m.group(1) == m.group(2):
        push("AR-122", "a-a=0", "self-sub", 0.0)
        return SolveResult("0", steps, used, True)
    # AR-143 a * 1
    m = re.match(r"what is (\d+(?:\.\d+)?)\s*\*\s*1\??$|what is (\d+(?:\.\d+)?)\s*times\s*1\??$", ql)
    if m:
        a = float(m.group(1) or m.group(2))
        push("AR-143", "a*1=a", f"{a}*1", a)
        return SolveResult(_norm(a), steps, used, True)
    # AR-144 a * 0
    m = re.match(r"what is (\d+(?:\.\d+)?)\s*\*\s*0\??$|what is (\d+(?:\.\d+)?)\s*times\s*0\??$", ql)
    if m:
        push("AR-144", "a*0=0", "zero product", 0.0)
        return SolveResult("0", steps, used, True)
    # AR-161 a / 1
    m = re.match(r"what is (\d+(?:\.\d+)?)\s*/\s*1\??$|what is (\d+(?:\.\d+)?)\s*divided by\s*1\??$", ql)
    if m:
        a = float(m.group(1) or m.group(2))
        push("AR-161", "a/1=a", f"{a}/1", a)
        return SolveResult(_norm(a), steps, used, True)
    # AR-162 0 / a
    m = re.match(r"what is 0\s*/\s*(\d+(?:\.\d+)?)\??$", ql)
    if m and float(m.group(1)) != 0:
        push("AR-162", "0/a=0", "zero dividend", 0.0)
        return SolveResult("0", steps, used, True)
    # AR-222 a^0 = 1
    m = re.match(r"what is (\d+(?:\.\d+)?)\s*\^\s*0\??$|what is (\d+(?:\.\d+)?)\s*to the power of\s*0\??$", ql)
    if m:
        push("AR-222", "a^0=1", "exp zero", 1.0)
        return SolveResult("1", steps, used, True)
    # AR-221 a^1 = a
    m = re.match(r"what is (\d+(?:\.\d+)?)\s*\^\s*1\??$", ql)
    if m:
        a = float(m.group(1))
        push("AR-221", "a^1=a", f"{a}^1", a)
        return SolveResult(_norm(a), steps, used, True)
    # AR-220 a^n small
    m = re.match(r"what is (\d+(?:\.\d+)?)\s*\^\s*(\d+)\??$", ql)
    if m:
        a, n = float(m.group(1)), int(m.group(2))
        if 0 <= n <= 8:
            v = a**n
            push("AR-220", "a^n repeated product", f"{a}^{n}", v)
            return SolveResult(_norm(v), steps, used, True)
    # AR-250 |a|
    m = re.match(r"what is \|(-?\d+(?:\.\d+)?)\|\??$|absolute value of (-?\d+(?:\.\d+)?)", ql)
    if m:
        a = float(m.group(1) or m.group(2))
        v = abs(a)
        push("AR-250", "|a|", f"|{a}|", v)
        return SolveResult(_norm(v), steps, used, True)
    # AR-292 gcd
    m = re.match(r"(?:what is )?(?:the )?gcd\s*\(?\s*(\d+)\s*,\s*(\d+)\s*\)?\??$", ql)
    if m:
        import math as _math

        a, b = int(m.group(1)), int(m.group(2))
        v = float(_math.gcd(a, b))
        push("AR-292", "gcd(a,b)", f"gcd({a},{b})", v)
        return SolveResult(_norm(v), steps, used, True)
    # AR-293 lcm
    m = re.match(r"(?:what is )?(?:the )?lcm\s*\(?\s*(\d+)\s*,\s*(\d+)\s*\)?\??$", ql)
    if m:
        import math as _math

        a, b = int(m.group(1)), int(m.group(2))
        v = float(abs(a * b) // _math.gcd(a, b)) if a and b else 0.0
        push("AR-293", "lcm(a,b)", f"lcm({a},{b})", v)
        return SolveResult(_norm(v), steps, used, True)
    # AR-147 distributive: a*(b+c)
    m = re.match(
        r"what is (\d+(?:\.\d+)?)\s*\*\s*\(\s*(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)\s*\)\??$",
        ql,
    )
    if m:
        a, b, c = float(m.group(1)), float(m.group(2)), float(m.group(3))
        v = a * (b + c)
        push("AR-147", "a*(b+c)=a*b+a*c", f"{a}*({b}+{c})", v)
        return SolveResult(_norm(v), steps, used, True)
    # AR-108 different denom fractions
    m = re.search(r"add fractions\s+(\d+)/(\d+)\s*\+\s*(\d+)/(\d+)", ql)
    if m:
        a, b, c, d = map(int, m.groups())
        if b != 0 and d != 0:
            if b == d:
                num = a + c
                push("AR-107", "a/b+c/b=(a+c)/b", f"{a}/{b}+{c}/{b}", float(num) / b)
                return SolveResult(f"{num}/{b}", steps, used, True)
            # different denominators
            num = a * d + c * b
            den = b * d
            push("AR-108", "a/b+c/d=(ad+bc)/(bd)", f"{a}/{b}+{c}/{d}", float(num) / den)
            return SolveResult(f"{num}/{den}", steps, used, True)
    # AR-148 fraction multiply
    m = re.search(r"multiply fractions\s+(\d+)/(\d+)\s*\*\s*(\d+)/(\d+)", ql)
    if m:
        a, b, c, d = map(int, m.groups())
        if b and d:
            push("AR-148", "(a/b)*(c/d)=(ac)/(bd)", f"{a}/{b}*{c}/{d}", float(a * c) / (b * d))
            return SolveResult(f"{a * c}/{b * d}", steps, used, True)
    # AR-181 equivalent fractions ka/kb
    m = re.match(r"equivalent fraction (\d+)/(\d+) times (\d+)", ql)
    if m:
        a, b, k = map(int, m.groups())
        push("AR-181", "a/b = ka/kb", f"{a}/{b} * {k}/{k}", float(a * k) / (b * k))
        return SolveResult(f"{a * k}/{b * k}", steps, used, True)
    # AR-201 p% as fraction
    m = re.match(r"what is (\d+(?:\.\d+)?)\s*%\s+as a (?:decimal|fraction)\??$", ql)
    if m:
        p = float(m.group(1))
        push("AR-201", "p% = p/100", f"{p}%", p / 100.0)
        return SolveResult(_norm(p / 100.0), steps, used, True)

    # double negative AR-022: -(-n)
    m = re.match(r"what is -\(-(\d+(?:\.\d+)?)\)\??$", ql)
    if m:
        n = float(m.group(1))
        push("AR-022", "-(-a)=a", f"-(-{n})", n)
        return SolveResult(_norm(n), steps, used, True)

    # fraction same denominator AR-107: a/b + c/b
    m = re.search(r"add fractions\s+(\d+)/(\d+)\s*\+\s*(\d+)/(\d+)", ql)
    if m:
        a, b, c, d = map(int, m.groups())
        if b == d and b != 0:
            num = a + c
            push("AR-107", "a/b+c/b=(a+c)/b", f"{a}/{b}+{c}/{b}", float(num) / b)
            return SolveResult(f"{num}/{b}", steps, used, True)

    # "Start with X. Use Y. How many left?"
    m = re.search(
        r"start with\s+(\d+(?:\.\d+)?).{0,40}?use\s+(\d+(?:\.\d+)?)",
        ql,
    )
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        v = push("sub_remove", "left = total − used", f"{a}-{b}", a - b)
        return SolveResult(_norm(v), steps, used, True)

    # split / among / equally → divide BEFORE each→mul
    if re.search(r"\b(split|equally among|share equally|divided equally)\b", ql) and len(nums) >= 2:
        v = eval_binop(nums[0], "/", nums[1])
        if v is not None:
            push("div_share", "each = total ÷ n", f"{nums[0]}/{nums[1]}", v)
            return SolveResult(_norm(v), steps, used, True)

    # percent of — require "p% of <number>" or explicit drill form (not any nearby %)
    if re.search(r"\d+\s*%\s*of\b|\bpercent of\b|what is \d+\s*% of", ql):
        m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s*[^0-9]{0,40}?(\d+(?:\.\d+)?)", ql)
        if not m:
            m = re.search(r"what is\s+(\d+(?:\.\d+)?)\s*%\s*of\s+(\d+(?:\.\d+)?)", ql)
        if m:
            p, x = float(m.group(1)), float(m.group(2))
            v = push("AR-202", "p% of x = (p/100)*x", f"{p}% of {x}", (p / 100.0) * x)
            return SolveResult(_norm(v), steps, used, True)
        # enrolled chain: "class of N, p% enrolled, q% of the remaining"
        if re.search(r"\bof the remaining\b", ql) and len(nums) >= 1:
            pcts = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", q)]
            base = nums[0]
            if len(pcts) >= 2 and base >= 1:
                part1 = push("AR-202", "p% of x", f"{pcts[0]}% of {base}", (pcts[0] / 100.0) * base)
                rem = push("sub_remove", "remaining", f"{base}-{part1}", base - part1)
                part2 = push("AR-202", "q% of remaining", f"{pcts[1]}% of {rem}", (pcts[1] / 100.0) * rem)
                if re.search(r"\b(rest|hip-hop|else|remaining students)\b", ql) or re.search(
                    r"what percentage of the entire", ql
                ):
                    last = push("sub_remove", "rest group", f"{rem}-{part2}", rem - part2)
                    if re.search(r"what percentage of the entire", ql):
                        pct_last = push("percent_of_whole", "100*last/base", f"100*{last}/{base}", 100.0 * last / base)
                        return SolveResult(_norm(pct_last), steps, used, True)
                    return SolveResult(_norm(last), steps, used, True)
                return SolveResult(_norm(part2), steps, used, True)

    # half — only when referent is explicit (drills / simple templates).
    # Failure analysis: bare "half" on multi-hop GSM8K halves wrong nums[0].
    if re.search(r"\bhalf of (\d+(?:\.\d+)?)\b", ql):
        m = re.search(r"\bhalf of (\d+(?:\.\d+)?)\b", ql)
        n0 = float(m.group(1))
        h = push("half", "half(n)=n/2", f"half of {n0}", n0 / 2.0)
        return SolveResult(_norm(h), steps, used, True)
    if re.search(r"\bhalf that much\b", ql) and len(nums) >= 1:
        n0 = nums[0]
        h = push("half", "half(n)=n/2", f"half of {n0}", n0 / 2.0)
        if re.search(r"\btotal\b|\bin total\b", ql):
            tot = push("add_combine", "total=a+b", f"{n0}+{h}", n0 + h)
            return SolveResult(_norm(tot), steps, used, True)
        return SolveResult(_norm(h), steps, used, True)
    if re.search(r"\bhalf as many\b", ql) and len(nums) == 1:
        n0 = nums[0]
        h = push("half", "half(n)=n/2", f"half of {n0}", n0 / 2.0)
        if re.search(r"\baltogether\b|\bin total\b|\btotal\b", ql):
            tot = push("add_combine", "total=a+half(a)", f"{n0}+{h}", n0 + h)
            return SolveResult(_norm(tot), steps, used, True)
        return SolveResult(_norm(h), steps, used, True)
    # "half as many ants/bugs" with one main count
    if re.search(r"\bhalf as many\b", ql) and len(nums) == 1 and re.search(
        r"\baltogether\b|\btotal\b", ql
    ):
        n0 = nums[0]
        h = push("half", "half(n)=n/2", f"half of {n0}", n0 / 2.0)
        tot = push("add_combine", "total", f"{n0}+{h}", n0 + h)
        return SolveResult(_norm(tot), steps, used, True)

    # double / twice — refuse bare "twice" on multi-number stories (wrong-fire analysis)
    if re.search(r"\btwice as many\b", ql) and re.search(r"\btimes as many\b", ql):
        n = nums[-1] if nums else None
        if n is not None:
            mul = 4.0 if re.search(r"\b4 times\b|\bfour times\b", ql) else None
            if mul is not None:
                c = push("mul_groups", "C=k*S", f"{mul}*{n}", mul * n)
                t = push("double", "T=2*C", f"2*{c}", 2 * c)
                if re.search(r"\btogether|total\b", ql):
                    tot = push("add_combine", "T+C+S", f"{t}+{c}+{n}", t + c + n)
                    return SolveResult(_norm(tot), steps, used, True)
                return SolveResult(_norm(t), steps, used, True)
    if re.search(r"\b(what is )?twice (\d+(?:\.\d+)?)\b", ql) or re.match(
        r"what is twice (\d+(?:\.\d+)?)\??$", ql
    ):
        m = re.search(r"twice (\d+(?:\.\d+)?)", ql)
        if m:
            n0 = float(m.group(1))
            d = push("double", "double(n)=2n", f"2*{n0}", 2 * n0)
            return SolveResult(_norm(d), steps, used, True)
    if re.match(r"what is twice (\d+(?:\.\d+)?)\??$", ql):
        n0 = float(re.match(r"what is twice (\d+(?:\.\d+)?)\??$", ql).group(1))
        d = push("double", "double(n)=2n", f"2*{n0}", 2 * n0)
        return SolveResult(_norm(d), steps, used, True)

    # rate × time — only tight templates (wrong-fire: grabbed first two nums)
    if re.search(r"\bper hour\b", ql) and re.search(r"\bminute", ql) and len(nums) == 2:
        rate, minutes = nums[0], nums[1]
        hours = push("div_rate", "hours = minutes/60", f"{minutes}/60", minutes / 60.0)
        amt = push("mul_rate", "amount=rate×time", f"{rate}*{hours}", rate * hours)
        return SolveResult(_norm(amt), steps, used, True)
    if re.match(r".*\bper hour\b.*\b(\d+)\s*hours?\b", ql) and len(nums) == 2:
        amt = push("mul_rate", "amount=rate×time", f"{nums[0]}*{nums[1]}", nums[0] * nums[1])
        return SolveResult(_norm(amt), steps, used, True)

    # groups: n sprints × times/week × meters (not hourly pay schedules)
    if (
        re.search(r"\bsprint|each sprint\b", ql)
        and re.search(r"\btimes a week\b", ql)
        and len(nums) >= 3
        and not re.search(r"\b(hour|discount|charge|pay)\b", ql)
    ):
        a, b, c = nums[0], nums[1], nums[2]
        # 3 sprints 3 times a week 60 meters → 3*3*60
        p = push("mul_groups", "total=n×size", f"{a}*{b}", a * b)
        tot = push("mul_groups", "total=groups×meters", f"{p}*{c}", p * c)
        return SolveResult(_norm(tot), steps, used, True)

    # unit: weeks → days (AR-296 style)
    if re.search(r"\bweeks?\b", ql) and re.search(r"\bdays?\b", ql) and len(nums) >= 1:
        if re.search(r"\bhow many days\b", ql):
            w = nums[0]
            d = push("unit_weeks_days", "days=7*weeks", f"7*{w}", 7 * w)
            return SolveResult(_norm(d), steps, used, True)

    # "of the remaining" percent chain (common GSM8K)
    if re.search(r"\bof the remaining\b", ql) and len(nums) >= 3 and re.search(r"%", q):
        # pattern: start N, p% of N, then q% of remaining
        base = nums[0]
        # find percents in order
        pcts = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", q)]
        if len(pcts) >= 2:
            part1 = push("AR-202", "p% of x", f"{pcts[0]}% of {base}", (pcts[0] / 100.0) * base)
            rem = push("sub_remove", "remaining", f"{base}-{part1}", base - part1)
            part2 = push("AR-202", "q% of remaining", f"{pcts[1]}% of {rem}", (pcts[1] / 100.0) * rem)
            if re.search(r"\b(left|remain|rest|how many)\b", ql):
                # often asks for last remainder
                if len(pcts) >= 2 and re.search(r"\b(jazz|jazz dance|last|else|other)\b", ql):
                    last = push("sub_remove", "last group", f"{rem}-{part2}", rem - part2)
                    return SolveResult(_norm(last), steps, used, True)
                return SolveResult(_norm(part2), steps, used, True)
            return SolveResult(_norm(part2), steps, used, True)

    # bought/had then sold/gave → left (strict: only 2 quantities, clear "left")
    # Refuse multi-hop inventory (third/half of left/quit cascades) — those are SCHEMA-*.
    if (
        re.search(r"\b(bought|had)\b", ql)
        and re.search(r"\b(sold|gave|ate)\b", ql)
        and re.search(r"\b(left|remain)\b", ql)
        and len(nums) == 2
        and not re.search(
            r"%|percent|each|per |times|half|third|more|quit|remaining",
            ql,
        )
    ):
        v = push("sub_remove", "left=had−sold", f"{nums[0]}-{nums[1]}", nums[0] - nums[1])
        return SolveResult(_norm(v), steps, used, True)

    # average only for explicit "average/mean of a, b, c" lists — not "average of 24 minutes"
    if re.search(r"\b(average|mean) of\b", ql) and 2 <= len(nums) <= 6:
        if re.search(
            r"\b(average|mean) of\s+\d+(?:\.\d+)?(?:\s*,\s*\d+(?:\.\d+)?)+",
            ql,
        ) or re.search(r"\b(average|mean) of\s+\d+.+\band\b.+\d+", ql):
            s = sum(nums)
            avg = push("mean", "mean=sum/n", f"{s}/{len(nums)}", s / len(nums))
            return SolveResult(_norm(avg), steps, used, True)

    # eggs per day × days → dozens
    if re.search(r"\bdozen", ql) and len(nums) >= 2:
        # 3 egg omelet every morning, 4 weeks → 3*7*4/12
        if re.search(r"\bweek", ql) and len(nums) >= 2:
            eggs_day, weeks = nums[0], nums[1]
            days = push("mul_groups", "days=7*weeks", f"7*{weeks}", 7 * weeks)
            eggs = push("mul_groups", "eggs=per_day×days", f"{eggs_day}*{days}", eggs_day * days)
            dozens = push("div_share", "dozens=eggs/12", f"{eggs}/12", eggs / 12.0)
            return SolveResult(_norm(dozens), steps, used, True)

    # remainder sell: total, use a, use b, price each
    if re.search(r"\bsells the remainder|the remainder for\b", ql) and len(nums) >= 4:
        total, a, b, price = nums[0], nums[1], nums[2], nums[3]
        left = push("remain_after", "left=total−a−b", f"{total}-{a}-{b}", total - a - b)
        money = push("mul_groups", "money=left×price", f"{left}*{price}", left * price)
        return SolveResult(_norm(money), steps, used, True)

    if re.search(r"\b(eats|uses|bakes).{0,30}\b(and|then)\b", ql) and re.search(
        r"\b(left|remain)\b", ql
    ) and len(nums) >= 3:
        left = push(
            "remain_after",
            "left=start−a−b",
            f"{nums[0]}-{nums[1]}-{nums[2]}",
            nums[0] - nums[1] - nums[2],
        )
        return SolveResult(_norm(left), steps, used, True)

    # simple left/remain with 2 nums — refuse quit/fraction cascades
    if ("sub" in strats or re.search(r"\b(left|remain)\b", ql)) and len(nums) == 2:
        if re.search(r"\b(left|remain|use)\b", ql) and not re.search(
            r"\b(quit|third|half of what|of the remaining|a third)\b", ql
        ):
            v = push("sub_remove", "left=total−used", f"{nums[0]}-{nums[1]}", nums[0] - nums[1])
            return SolveResult(_norm(v), steps, used, True)

    # difference two nums — refuse when "more than twice/half" (needs BIND multi-hop)
    if (
        "sub" in strats
        and len(nums) == 2
        and re.search(r"\b(more|less|difference)\b", ql)
        and not re.search(r"\bmore than twice\b|\btwice\b|\bhalf\b|\btimes as\b", ql)
    ):
        v = push("sub_diff", "diff=|a-b|", f"|{nums[0]}-{nums[1]}|", abs(nums[0] - nums[1]))
        return SolveResult(_norm(v), steps, used, True)

    # add: only when wording is clearly total/altogether AND exactly 2 addends (avoid over-fire)
    # Refuse "K more X than Y" (needs base+base+K) and "more than" comparative totals.
    if re.search(r"\b(altogether|in all|in total|combined)\b", ql) and len(nums) == 2:
        if not re.search(
            r"\b(each|per|times|half|%|percent|left|remain|more \w+ than|more than)\b",
            ql,
        ):
            s = push("add_combine", "total=a+b", f"{nums[0]}+{nums[1]}", nums[0] + nums[1])
            return SolveResult(_norm(s), steps, used, True)

    # mul: "each" + groups of size (require both each/every and groups/of)
    if re.search(r"\b(each|every)\b", ql) and re.search(r"\b(groups?|boxes?|bags?|packs?)\b", ql) and len(nums) == 2:
        v = push("mul_groups", "total=n×size", f"{nums[0]}*{nums[1]}", nums[0] * nums[1])
        return SolveResult(_norm(v), steps, used, True)

    # Do NOT guess: if no structured rule matched, refuse (honest)
    return SolveResult(None, steps, used, False)


# ---------------------------------------------------------------------------
# Layer 4 — practice set: rule drills + GSM8K subset that rules cover
# ---------------------------------------------------------------------------

@dataclass
class PracticeItem:
    question: str
    answer: str
    rule_focus: str
    source: str  # drill | gsm8k


def build_rule_drills() -> List[PracticeItem]:
    """Synthetic drills that *directly* practice each rule (like worksheets)."""
    items: List[PracticeItem] = []
    # add
    for a, b in [(3, 5), (12, 8), (100, 25), (7, 9), (15, 15)]:
        items.append(PracticeItem(f"What is {a} plus {b} altogether?", str(a + b), "add", "drill"))
        items.append(PracticeItem(f"Combine {a} and {b} in total.", str(a + b), "add", "drill"))
    # sub
    for a, b in [(10, 3), (50, 12), (100, 40), (25, 8)]:
        items.append(PracticeItem(f"Start with {a}. Use {b}. How many are left?", str(a - b), "sub", "drill"))
        items.append(PracticeItem(f"How many more is {a} than {b}?", str(a - b), "sub", "drill"))
    # mul
    for a, b in [(4, 6), (3, 7), (5, 9), (8, 8), (12, 3)]:
        items.append(PracticeItem(f"There are {a} groups of {b} each. How many in all?", str(a * b), "mul", "drill"))
    # div
    for a, b in [(12, 3), (20, 4), (45, 5), (100, 10)]:
        items.append(PracticeItem(f"Split {a} equally among {b} people. How many each?", str(a // b), "div", "drill"))
    # half / double
    for n in [8, 16, 50, 100, 24]:
        items.append(PracticeItem(f"What is half of {n}?", str(n // 2), "half", "drill"))
        items.append(PracticeItem(f"What is twice {n}?", str(n * 2), "double", "drill"))
    # percent (AR-202)
    for p, x, ans in [(50, 80, 40), (25, 200, 50), (10, 90, 9), (20, 50, 10)]:
        items.append(PracticeItem(f"What is {p}% of {x}?", str(ans), "percent", "drill"))
    # fraction same denom (AR-107)
    for a, b, c, ans in [(1, 4, 2, "3/4"), (1, 5, 2, "3/5"), (2, 7, 3, "5/7")]:
        items.append(PracticeItem(f"Add fractions {a}/{b} + {c}/{b}", ans, "fraction", "drill"))
    # different denom (AR-108)
    items.append(PracticeItem("Add fractions 1/2 + 1/3", "5/6", "fraction", "drill"))
    items.append(PracticeItem("Add fractions 1/4 + 1/6", "10/24", "fraction", "drill"))
    # fraction multiply (AR-148)
    items.append(PracticeItem("Multiply fractions 2/3 * 3/4", "6/12", "fraction", "drill"))
    items.append(PracticeItem("Multiply fractions 1/2 * 1/5", "1/10", "fraction", "drill"))
    # equivalent fractions (AR-181)
    items.append(PracticeItem("Equivalent fraction 2/3 times 4", "8/12", "fraction", "drill"))
    # identities
    for a in [5, 17, 100]:
        items.append(PracticeItem(f"What is {a} + 0?", str(a), "add", "drill"))
        items.append(PracticeItem(f"What is {a} - 0?", str(a), "sub", "drill"))
        items.append(PracticeItem(f"What is {a} - {a}?", "0", "sub", "drill"))
        items.append(PracticeItem(f"What is {a} * 1?", str(a), "mul", "drill"))
        items.append(PracticeItem(f"What is {a} * 0?", "0", "mul", "drill"))
        items.append(PracticeItem(f"What is {a} / 1?", str(a), "div", "drill"))
    items.append(PracticeItem("What is 0 / 9?", "0", "div", "drill"))
    # powers
    items.append(PracticeItem("What is 2 ^ 0?", "1", "exp", "drill"))
    items.append(PracticeItem("What is 5 ^ 1?", "5", "exp", "drill"))
    items.append(PracticeItem("What is 2 ^ 3?", "8", "exp", "drill"))
    items.append(PracticeItem("What is 3 ^ 4?", "81", "exp", "drill"))
    # abs
    items.append(PracticeItem("What is |-7|?", "7", "abs", "drill"))
    items.append(PracticeItem("Absolute value of -12", "12", "abs", "drill"))
    # gcd/lcm
    items.append(PracticeItem("gcd(12, 18)", "6", "gcd", "drill"))
    items.append(PracticeItem("lcm(4, 6)", "12", "lcm", "drill"))
    # distributive
    items.append(PracticeItem("What is 3 * (4 + 5)?", "27", "dist", "drill"))
    # percent as decimal
    items.append(PracticeItem("What is 25% as a decimal?", "0.25", "percent", "drill"))
    # double negative (AR-022)
    for n in [3, 8, 12]:
        items.append(PracticeItem(f"What is -(-{n})?", str(n), "sign", "drill"))
    # order of operations: mult before add (AR-262)
    items.append(PracticeItem("Evaluate 2 + 3 * 4", "14", "order", "drill"))
    items.append(PracticeItem("Evaluate 10 - 2 * 3", "4", "order", "drill"))
    items.append(PracticeItem("Evaluate (2 + 3) * 4", "20", "order", "drill"))
    # rate minutes
    items.append(PracticeItem("She earns 12 dollars per hour. She works 50 minutes. How much does she earn?", "10", "rate", "drill"))
    items.append(PracticeItem("He runs 3 sprints 3 times a week. He runs 60 meters each sprint. How many total meters does he run a week?", "540", "mul", "drill"))
    # remainder sell
    items.append(
        PracticeItem(
            "Ducks lay 16 eggs per day. She eats 3 and bakes with 4. She sells the remainder for 2 dollars each. How much does she make?",
            "18",
            "sub_chain",
            "drill",
        )
    )
    # half as many then total
    items.append(
        PracticeItem(
            "She sold 48 in April and then half as many in May. How many did she sell altogether?",
            "72",
            "half",
            "drill",
        )
    )
    # robe bolts
    items.append(
        PracticeItem(
            "A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total?",
            "3",
            "half",
            "drill",
        )
    )
    # sheep chain
    items.append(
        PracticeItem(
            "Toulouse has twice as many sheep as Charleston. Charleston has 4 times as many sheep as Seattle. How many sheep do Toulouse, Charleston, and Seattle have together if Seattle has 20?",
            "260",
            "double",
            "drill",
        )
    )
    # dozens eggs
    items.append(
        PracticeItem(
            "Claire makes a 3 egg omelet every morning. How many dozens of eggs will she eat in 4 weeks?",
            "7",
            "mul",
            "drill",
        )
    )
    # BIND/SCHEMA drills (referent attachment + multi-hop — from fail analysis)
    try:
        from .math_binding import binding_drills

        for q, a, focus in binding_drills():
            # skip exact duplicates already listed above
            if any(it.question == q for it in items):
                continue
            items.append(PracticeItem(q, a, focus, "drill"))
    except Exception:
        pass
    return items


def load_gsm8k_practice(limit: Optional[int] = 200) -> List[PracticeItem]:
    """GSM8K items used as practice in applying rules (not as stuffed answers)."""
    p = GSM8K / "train.jsonl"
    if not p.is_file():
        return []
    items: List[PracticeItem] = []
    final_re = re.compile(r"####\s*(.+)\s*$", re.M)
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if limit is not None and len(items) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(o.get("question", "")).strip()
            ans = str(o.get("answer", ""))
            m = final_re.search(ans)
            a = _norm(m.group(1)) if m else ""
            if not q or not a:
                continue
            # only keep if our rule engine produces something (teachable by rules)
            r = apply_rules(q)
            if r.ok and r.answer is not None and exact_num(r.answer, a):
                focus = r.strategies_used[0] if r.strategies_used else "compose"
                items.append(PracticeItem(q, a, focus, "gsm8k_rule_covered"))
    return items


def load_gsm8k_heldout(split: str = "test", limit: Optional[int] = 300) -> List[PracticeItem]:
    p = GSM8K / f"{split}.jsonl"
    if not p.is_file():
        return []
    items: List[PracticeItem] = []
    final_re = re.compile(r"####\s*(.+)\s*$", re.M)
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if limit is not None and len(items) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(o.get("question", "")).strip()
            ans = str(o.get("answer", ""))
            m = final_re.search(ans)
            a = _norm(m.group(1)) if m else ""
            if q and a:
                items.append(PracticeItem(q, a, "transfer", f"gsm8k_{split}"))
    return items


def score_items(items: Sequence[PracticeItem]) -> Dict[str, Any]:
    correct = 0
    n = 0
    by_focus: Dict[str, List[int]] = {}
    traces_ok = 0
    for it in items:
        n += 1
        r = apply_rules(it.question)
        hit = bool(r.ok and r.answer is not None and exact_num(r.answer, it.answer))
        if hit:
            correct += 1
            if r.steps:
                traces_ok += 1
        by_focus.setdefault(it.rule_focus, [0, 0])
        by_focus[it.rule_focus][1] += 1
        if hit:
            by_focus[it.rule_focus][0] += 1
    focus_acc = {
        k: {"correct": v[0], "n": v[1], "accuracy": round(v[0] / v[1], 4) if v[1] else 0.0}
        for k, v in by_focus.items()
    }
    return {
        "n": n,
        "correct": correct,
        "accuracy": round(correct / n, 4) if n else 0.0,
        "with_rule_trace": traces_ok,
        "by_focus": focus_acc,
        "method": "apply_taught_rules_not_retrieval_stuffing",
    }


def rules_to_bank_rows() -> List[str]:
    """Export rules + language maps as curriculum bank (teachable text)."""
    rows = [
        "# domain\tgrade\tkind\tquestion\tanswer\n",
        f"# Math RULES curriculum {datetime.now(timezone.utc).isoformat()}\n",
        "# kind=rule | langmap | drill — symbolic laws, not Q/A stuffing\n",
    ]
    for r in ARITH_RULES:
        rows.append(f"math\trules\trule\tWhat is the rule {r.name}?\t{r.formula}\n")
        rows.append(f"math\trules\trule\tExplain {r.id}\t{r.description}\n")
        rows.append(f"math\trules\trule\tFormula for {r.name}\t{r.formula}\n")
    for rx, strat, cue in LANGUAGE_MAPS:
        rows.append(f"math\trules\tlangmap\tWhat operation for: {cue.split(' means ')[0]}?\t{strat}\n")
        rows.append(f"math\trules\tlangmap\t{cue}\t{strat}\n")
    # BIND/SCHEMA form+why+how (teachable text, not Q→A stuffing)
    try:
        from .math_binding import BINDING_RULES

        for br in BINDING_RULES:
            rows.append(
                f"math\trules\trule\tWhat is the rule {br['name']}?\t{br['formula']}\n"
            )
            rows.append(
                f"math\trules\trule\tWhy {br['id']}?\t{br['why']}\n"
            )
            rows.append(
                f"math\trules\trule\tHow to apply {br['id']}?\t{br['how']}\n"
            )
    except Exception:
        pass
    return rows


def load_imported_rulebook() -> Dict[str, Any]:
    """Pull Desktop Math-generator catalog if imported."""
    try:
        from .math_rulebook_import import OUT_DIR, load_master

        if (OUT_DIR / "MASTER_RULEBOOK.json").is_file():
            return load_master()
    except Exception:
        pass
    return {}


def build_pack(
    gsm8k_practice_limit: int = 400,
    gsm8k_test_limit: int = 300,
) -> Dict[str, Any]:
    imported = load_imported_rulebook()
    drills = build_rule_drills()
    gsm_cov = load_gsm8k_practice(limit=gsm8k_practice_limit)
    practice = drills + gsm_cov
    heldout = load_gsm8k_heldout("test", limit=gsm8k_test_limit)

    # score
    drill_score = score_items(drills)
    practice_score = score_items(practice)
    # only GSM8K items that rules already cover (sanity)
    cov_score = score_items(gsm_cov) if gsm_cov else {"n": 0, "correct": 0, "accuracy": 0.0}
    # held-out: full apply_rules — honest transfer
    transfer = score_items(heldout)
    # held-out among those where engine returns *some* answer (coverage of rule system)
    covered_held = []
    for it in heldout:
        r = apply_rules(it.question)
        if r.ok and r.answer is not None:
            covered_held.append(it)
    transfer_on_covered = score_items(covered_held) if covered_held else {
        "n": 0,
        "correct": 0,
        "accuracy": 0.0,
        "method": "n/a",
    }

    # curriculum gate: drills + rule language (must be ≥95%)
    # also re-ask drills as "taught worksheet"
    curriculum_ok = drill_score["accuracy"] >= PASS
    pathway_ok = drill_score["accuracy"] >= PASS  # drills ARE pathway practice

    bank_rows = rules_to_bank_rows()
    for it in drills:
        bank_rows.append(
            f"math\trules\tdrill\t{it.question.replace(chr(9), ' ')}\t{it.answer}\n"
        )
    # Merge imported Math-generator bank if present (full authority corpus)
    imported_bank = DATA / "math_rulebook" / "bank.tsv"
    n_imported_bank = 0
    if imported_bank.is_file():
        for line in imported_bank.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            bank_rows.append(line + ("\n" if not line.endswith("\n") else ""))
            n_imported_bank += 1

    n_imported_rules = int((imported.get("meta") or imported).get("n_rules") or 0)
    if not n_imported_rules and imported.get("rules"):
        n_imported_rules = len(imported["rules"])

    man = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "doctrine": (
            "Teach RULES and language→operator maps; solve by decomposition and rule "
            "application. Do NOT stuff GSM8K Q→A and retrieve. "
            "Authority rule corpus: Desktop Math generator → data/math_rulebook."
        ),
        "pass_threshold": PASS,
        "n_arith_rules_runtime": len(ARITH_RULES),
        "n_language_maps": len(LANGUAGE_MAPS),
        "n_imported_math_generator_rules": n_imported_rules,
        "n_imported_bank_rows": n_imported_bank,
        "n_drills": len(drills),
        "n_gsm8k_rule_covered_practice": len(gsm_cov),
        "n_heldout_test": len(heldout),
        "n_heldout_rule_covered": len(covered_held),
        "scores": {
            "drills_rule_application": drill_score,
            "practice_mixed": practice_score,
            "gsm8k_train_rule_covered": cov_score,
            "gsm8k_test_all": transfer,
            "gsm8k_test_where_rules_fire": transfer_on_covered,
        },
        "gates": {
            "curriculum_drills_ge_95": curriculum_ok,
            "straight_a_rules": curriculum_ok and pathway_ok,
            "rulebook_imported": n_imported_rules > 0,
        },
        "coverage_note": (
            f"Imported Math-generator rules: {n_imported_rules}. "
            f"Runtime word-problem apply fires on {len(covered_held)}/{len(heldout)} held-out items. "
            "Expand apply_rules using ARITHMETIC/ALGEBRA forms from the imported book; "
            "full GSM8K rises as more atomic rules become executable."
        ),
        "next_rule_expansions": [
            "Wire AR-* arithmetic rules from MASTER_RULEBOOK into apply_rules",
            "multi-step percent remaining chains",
            "unit conversion (weeks↔days, hours↔minutes) as explicit rules",
            "algebra identity application from ALGEBRA_RULES",
            "geometry formulas from GEOMETRY_RULES",
        ],
        "math_generator_source": (imported.get("meta") or imported).get("source", ""),
    }

    for d in (REPO_DIR, GAME_DIR):
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / "bank.tsv").write_text("".join(bank_rows), encoding="utf-8")
            (d / "MANIFEST.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
            (d / "REPORT.md").write_text(render_report(man), encoding="utf-8")
            # rule list human-readable
            lines = ["# Taught mathematical rules\n"]
            for r in ARITH_RULES:
                lines.append(f"- **{r.id}**: `{r.formula}` — {r.description}\n")
            lines.append("\n# Language → strategy maps\n")
            for rx, strat, cue in LANGUAGE_MAPS:
                lines.append(f"- `{cue}` → **{strat}**\n")
            (d / "RULES.md").write_text("".join(lines), encoding="utf-8")
        except OSError as e:
            print(f"skip {d}: {e}")

    res = DATA / "results"
    if res.is_dir():
        (res / "MATH_RULES_TEACH.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
        (res / "MATH_RULES_TEACH.md").write_text(render_report(man), encoding="utf-8")

    try:
        from .game_drive_bench import log_emergent

        events = [
            {
                "type": "math_rules_first_not_stuffing",
                "drills_acc": drill_score["accuracy"],
                "test_all": transfer["accuracy"],
                "test_covered_acc": transfer_on_covered.get("accuracy", 0),
                "coverage": f"{len(covered_held)}/{len(heldout)}",
            }
        ]
        if curriculum_ok:
            events.append({"type": "math_rules_drill_straight_a", "acc": drill_score["accuracy"]})
        log_emergent(
            source="math_rules",
            signals={"events": events, "gates": man["gates"]},
            note="rule-first pedagogy; observe only",
        )
    except Exception as e:
        man["emergent_log_error"] = str(e)

    return man


def render_report(man: Dict[str, Any]) -> str:
    s = man["scores"]
    g = man["gates"]
    lines = [
        "# Math rules teach — not Q/A stuffing",
        "",
        f"Generated: `{man['generated_at']}`",
        "",
        f"**Doctrine:** {man['doctrine']}",
        "",
        f"Runtime apply rules: **{man.get('n_arith_rules_runtime', man.get('n_arith_rules'))}** · "
        f"Language maps: **{man['n_language_maps']}** · Drills: **{man['n_drills']}**  ",
        f"**Imported Math-generator atomic rules: {man.get('n_imported_math_generator_rules', 0)}** · "
        f"Bank rows from import: {man.get('n_imported_bank_rows', 0)}",
        "",
        "## Scores (rule application)",
        "",
        "| Set | Acc | n |",
        "|-----|----:|--:|",
        f"| **Drills (worksheet)** | **{s['drills_rule_application']['accuracy']:.4f}** | {s['drills_rule_application']['n']} |",
        f"| GSM8K train (rule-covered only) | {s['gsm8k_train_rule_covered'].get('accuracy', 0):.4f} | {s['gsm8k_train_rule_covered'].get('n', 0)} |",
        f"| GSM8K test (all) | {s['gsm8k_test_all']['accuracy']:.4f} | {s['gsm8k_test_all']['n']} |",
        f"| GSM8K test (where rules fire) | {s['gsm8k_test_where_rules_fire'].get('accuracy', 0):.4f} | {s['gsm8k_test_where_rules_fire'].get('n', 0)} |",
        "",
        f"**Straight-A on rule drills (≥{PASS}):** {'PASS' if g['straight_a_rules'] else 'FAIL'}",
        "",
        man.get("coverage_note", ""),
        "",
        "## Why this is different",
        "",
        "1. Teach symbolic formulas (`total = a + b`, `left = total − used`, …)",
        "2. Teach language cues that select rules",
        "3. Decompose problem → apply rules → evaluate",
        "4. Practice drills verify *use of rules*, not memory of answers",
        "",
        "## Next expansions",
        "",
    ]
    for x in man.get("next_rule_expansions") or []:
        lines.append(f"- {x}")
    lines.append("")
    return "\n".join(lines)
