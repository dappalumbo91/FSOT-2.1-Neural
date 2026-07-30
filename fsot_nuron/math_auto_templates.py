"""Curriculum-scale template mining from GSM8K *train* solutions.

Doctrine:
  - Learn HOW to compute from school solutions (formulas + number slots)
  - Never store test Q→A pairs (no stuffing)
  - Templates are: keyword bag + n_slots + RPN/ops over slots

This is how you cover hundreds of no-fires without hand-writing 20 regexes/turn.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .math_rules import SolveResult, StepTrace, _norm, exact_num
from .paths import DATA

TRAIN_PATHS = [
    Path(r"D:\training data\gsm8k\train.jsonl"),
    Path(r"D:\fsot_training\gsm8k\train.jsonl"),
]
PACK_PATH = DATA / "math_templates" / "TRAIN_TEMPLATES.json"
REPORT_PATH = DATA / "results" / "MATH_AUTO_TEMPLATES.json"

NUM_RE = re.compile(r"(?<![\w])(\d+(?:\.\d+)?)(?![\d])")
CALC_RE = re.compile(r"<<([^>]+)>>")
FINAL_RE = re.compile(r"####\s*(.+)\s*$", re.M)
# tokenize formula into numbers and ops
TOK_RE = re.compile(r"\d+(?:\.\d+)?|[+\-*/()]")

# language cues for matching (cheap bag)
CUE_WORDS = (
    "each every per total together left remain remaining half twice times "
    "percent discount more less fewer ratio dozen week day hour mile cost "
    "price buy bought sold spend pay change average how many how much "
    "first second third after before then of the and plus minus "
    "adult child share split equal morning afternoon final year month "
    "teacher student chicken egg pie slice bag ticket fee tip tax "
    "interest loan profit original water tank train mile gallon"
).split()


def extract_nums(text: str) -> List[float]:
    t = text.replace(",", "")
    out: List[float] = []
    for m in NUM_RE.finditer(t):
        try:
            out.append(float(m.group(1)))
        except ValueError:
            pass
    return out


def cue_set(text: str) -> Set[str]:
    tl = text.lower()
    return {w for w in CUE_WORDS if w in tl}


def number_roles(text: str) -> List[str]:
    """Nearest content word before each number — role signature for matching."""
    t = text.replace(",", "")
    roles: List[str] = []
    for m in NUM_RE.finditer(t):
        start = m.start()
        left = t[max(0, start - 40) : start].lower()
        words = re.findall(r"[a-z]{3,}", left)
        role = words[-1] if words else "num"
        # normalize
        if role in {"costs", "costing", "priced"}:
            role = "cost"
        if role in {"hours", "hour"}:
            role = "hour"
        if role in {"days", "day"}:
            role = "day"
        if role in {"weeks", "week"}:
            role = "week"
        if role in {"miles", "mile", "km"}:
            role = "mile"
        if role.endswith("s") and len(role) > 4:
            role = role[:-1]
        roles.append(role)
    return roles


def _safe_eval(expr: str) -> Optional[float]:
    expr = expr.replace(" ", "")
    if not re.fullmatch(r"[0-9\.\+\-\*/\(\)]+", expr):
        return None
    try:
        return float(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307
    except Exception:
        return None


def parse_calc(step: str) -> Optional[Tuple[str, float]]:
    """'3*20=60' or '3*20' → (lhs, rhs)."""
    step = step.strip().replace(" ", "")
    if "=" in step:
        lhs, rhs = step.split("=", 1)
        try:
            return lhs, float(rhs)
        except ValueError:
            v = _safe_eval(rhs)
            if v is None:
                return None
            return lhs, v
    v = _safe_eval(step)
    if v is None:
        return None
    return step, v


@dataclass
class Template:
    """One curriculum solution shape."""

    id: str
    n_slots: int
    # sequence of steps: each is ("op", [arg...]) where arg is ("n", i) or ("t", step_idx) or ("c", const)
    steps: List[Dict[str, Any]]
    cues: List[str]
    support: int = 1  # how many train problems abstracted to this
    # fingerprint for clustering
    op_sig: str = ""
    roles: List[str] = field(default_factory=list)


def _leaf_to_ref(
    val: float,
    q_nums: List[float],
    intermediates: Dict[float, int],
    *,
    tol: float = 1e-6,
) -> Optional[Tuple[str, float]]:
    """Map a numeric leaf to slot or intermediate step index."""
    # prefer intermediates first (multi-hop)
    for iv, idx in intermediates.items():
        if abs(iv - val) < tol:
            return ("t", float(idx))
    # then unique slot
    hits = [i for i, n in enumerate(q_nums) if abs(n - val) < tol]
    if len(hits) == 1:
        return ("n", float(hits[0]))
    if len(hits) > 1:
        # ambiguous — take first unused? use first
        return ("n", float(hits[0]))
    # constant not in question (e.g. 12 inches/foot, 7 days, 100 for %)
    return ("c", val)


def abstract_solution(
    question: str,
    answer_body: str,
    gold: str,
) -> Optional[Template]:
    q_nums = extract_nums(question)
    if not q_nums or len(q_nums) > 12:
        return None
    calcs = CALC_RE.findall(answer_body)
    if not calcs:
        return None
    steps_out: List[Dict[str, Any]] = []
    intermediates: Dict[float, int] = {}
    op_parts: List[str] = []

    for si, raw in enumerate(calcs):
        parsed = parse_calc(raw)
        if not parsed:
            return None
        lhs, rhs = parsed
        # tokenize lhs for simple binops a op b or a op b op c
        # only handle binary + - * / with two sides maybe parenthesized simple
        # strip outer parens
        e = lhs
        # percent style: 80*1.25 or 200*40*.01
        # find operator at top level
        depth = 0
        main_op = None
        main_i = -1
        for i, ch in enumerate(e):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif depth == 0 and ch in "+-*/" and i > 0:
                # rightmost top-level for left-assoc chain: take last
                main_op = ch
                main_i = i
        if main_op is None or main_i < 0:
            # single number?
            try:
                v = float(e)
                ref = _leaf_to_ref(v, q_nums, intermediates)
                if ref is None:
                    return None
                steps_out.append({"op": "id", "args": [list(ref)], "out": rhs})
                intermediates[rhs] = len(steps_out) - 1
                op_parts.append("id")
                continue
            except ValueError:
                return None
        left_s, right_s = e[:main_i], e[main_i + 1 :]
        # if left still has ops, eval left as nested by recursive simple: only allow left to be number or known
        def resolve_side(s: str) -> Optional[Tuple[str, float]]:
            s = s.strip()
            if not s:
                return None
            # try as expression of already-known structure: if pure number
            try:
                v = float(s)
                return _leaf_to_ref(v, q_nums, intermediates)
            except ValueError:
                pass
            # try eval if only numbers and ops matching intermediates — fold by eval leaves
            # replace numbers with values and eval
            vv = _safe_eval(s)
            if vv is None:
                return None
            return _leaf_to_ref(vv, q_nums, intermediates)

        # For chains like a*b*c, right is last factor, left is a*b — resolve left as intermediate value
        lv = _safe_eval(left_s)
        rv = _safe_eval(right_s)
        if lv is None or rv is None:
            # try single-op only
            la = resolve_side(left_s)
            ra = resolve_side(right_s)
            if la is None or ra is None:
                return None
        else:
            la = _leaf_to_ref(lv, q_nums, intermediates)
            ra = _leaf_to_ref(rv, q_nums, intermediates)
            if la is None or ra is None:
                return None
        # verify
        a = _eval_ref(la, q_nums, [s.get("out", 0) for s in steps_out])
        b = _eval_ref(ra, q_nums, [s.get("out", 0) for s in steps_out])
        if a is None or b is None:
            return None
        if main_op == "+":
            pred = a + b
        elif main_op == "-":
            pred = a - b
        elif main_op == "*":
            pred = a * b
        elif main_op == "/":
            if abs(b) < 1e-12:
                return None
            pred = a / b
        else:
            return None
        if abs(pred - rhs) > 1e-3 * max(1.0, abs(rhs)):
            # allow float noise
            if abs(pred - rhs) > 0.05:
                return None
        steps_out.append(
            {"op": main_op, "args": [list(la), list(ra)], "out": rhs}
        )
        intermediates[rhs] = len(steps_out) - 1
        op_parts.append(main_op)

    if not steps_out:
        return None
    # final must match gold
    try:
        g = float(str(gold).replace(",", ""))
    except ValueError:
        return None
    last = steps_out[-1]["out"]
    if abs(float(last) - g) > 1e-3 * max(1.0, abs(g)) and abs(float(last) - g) > 0.05:
        return None

    cues = sorted(cue_set(question))
    roles = number_roles(question)
    sig = "".join(op_parts)
    tid = f"T{len(q_nums)}_{sig}_{abs(hash(tuple(cues)+tuple(roles)))%10**8:08d}"
    return Template(
        id=tid,
        n_slots=len(q_nums),
        steps=steps_out,
        cues=cues,
        support=1,
        op_sig=sig,
        roles=roles,
    )


def _eval_ref(
    ref: Tuple[str, float],
    slots: List[float],
    step_vals: List[float],
) -> Optional[float]:
    kind, val = ref[0], ref[1]
    if kind == "n":
        i = int(val)
        if 0 <= i < len(slots):
            return slots[i]
        return None
    if kind == "t":
        i = int(val)
        if 0 <= i < len(step_vals):
            return float(step_vals[i])
        return None
    if kind == "c":
        return float(val)
    return None


def execute_template(tmpl: Template, slots: List[float]) -> Optional[float]:
    if len(slots) != tmpl.n_slots:
        return None
    step_vals: List[float] = []
    for st in tmpl.steps:
        op = st["op"]
        args = st["args"]
        if op == "id":
            v = _eval_ref(tuple(args[0]), slots, step_vals)
            if v is None:
                return None
            step_vals.append(v)
            continue
        if len(args) < 2:
            return None
        a = _eval_ref(tuple(args[0]), slots, step_vals)
        b = _eval_ref(tuple(args[1]), slots, step_vals)
        if a is None or b is None:
            return None
        if op == "+":
            step_vals.append(a + b)
        elif op == "-":
            step_vals.append(a - b)
        elif op == "*":
            step_vals.append(a * b)
        elif op == "/":
            if abs(b) < 1e-12:
                return None
            step_vals.append(a / b)
        else:
            return None
    return step_vals[-1] if step_vals else None


def template_key(t: Template) -> Tuple:
    """Cluster key for merging identical structure + role signature."""
    # normalize steps without out values
    norm_steps = []
    for s in t.steps:
        norm_steps.append((s["op"], tuple(tuple(a) for a in s["args"])))
    # roles stabilize which slot is "price" vs "count"
    return (t.n_slots, t.op_sig, tuple(norm_steps), tuple(t.roles))


def mine_train(
    *,
    limit: Optional[int] = None,
    min_support: int = 1,
) -> Dict[str, Any]:
    path = next((p for p in TRAIN_PATHS if p.is_file()), None)
    if path is None:
        return {"error": "no train.jsonl", "n_templates": 0}

    raw: List[Template] = []
    n_rows = 0
    n_ok = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if limit is not None and n_rows >= limit:
                break
            n_rows += 1
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(o.get("question", ""))
            ans = str(o.get("answer", ""))
            m = FINAL_RE.search(ans)
            if not m:
                continue
            gold = m.group(1).strip()
            t = abstract_solution(q, ans, gold)
            if t is None:
                continue
            # verify re-exec
            slots = extract_nums(q)
            pred = execute_template(t, slots)
            if pred is None or not exact_num(_norm(pred), _norm(gold)):
                continue
            n_ok += 1
            raw.append(t)

    # merge by structure
    buckets: Dict[Tuple, Template] = {}
    cue_union: Dict[Tuple, Set[str]] = defaultdict(set)
    for t in raw:
        k = template_key(t)
        cue_union[k].update(t.cues)
        if k not in buckets:
            buckets[k] = t
        else:
            buckets[k].support += 1

    templates: List[Dict[str, Any]] = []
    for k, t in buckets.items():
        if t.support < min_support:
            continue
        t.cues = sorted(cue_union[k])
        templates.append(
            {
                "id": t.id,
                "n_slots": t.n_slots,
                "steps": t.steps,
                "cues": t.cues,
                "support": t.support,
                "op_sig": t.op_sig,
                "roles": t.roles,
            }
        )

    # sort by support desc
    templates.sort(key=lambda x: (-x["support"], -len(x["cues"])))

    pack = {
        "source": str(path),
        "n_train_rows_scanned": n_rows,
        "n_abstracted_ok": n_ok,
        "n_templates": len(templates),
        "min_support": min_support,
        "templates": templates,
        "doctrine": "Train-mined solution templates only; no test Q→A stuffing.",
    }
    PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    PACK_PATH.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "n_templates": pack["n_templates"],
                "n_abstracted_ok": n_ok,
                "n_train_rows_scanned": n_rows,
                "top_support": [
                    {"id": t["id"], "support": t["support"], "sig": t["op_sig"], "n": t["n_slots"]}
                    for t in templates[:30]
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return pack


_CACHE: Optional[List[Template]] = None
_BY_SLOTS: Optional[Dict[int, List[Template]]] = None


def load_templates() -> List[Template]:
    global _CACHE, _BY_SLOTS
    if _CACHE is not None:
        return _CACHE
    if not PACK_PATH.is_file():
        _CACHE = []
        _BY_SLOTS = {}
        return _CACHE
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    out: List[Template] = []
    for t in pack.get("templates") or []:
        out.append(
            Template(
                id=t["id"],
                n_slots=int(t["n_slots"]),
                steps=t["steps"],
                cues=list(t.get("cues") or []),
                support=int(t.get("support") or 1),
                op_sig=str(t.get("op_sig") or ""),
                roles=list(t.get("roles") or []),
            )
        )
    _CACHE = out
    _BY_SLOTS = defaultdict(list)
    for t in out:
        _BY_SLOTS[t.n_slots].append(t)
    # prefer high support
    for n in _BY_SLOTS:
        _BY_SLOTS[n].sort(key=lambda x: -x.support)
    return _CACHE


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 0.0
    u = a | b
    if not u:
        return 0.0
    return len(a & b) / len(u)


def solve_with_templates(
    question: str,
    *,
    min_jaccard: float = 0.15,
    max_try: int = 40,
) -> SolveResult:
    """Apply best matching train-mined templates."""
    load_templates()
    assert _BY_SLOTS is not None
    slots = extract_nums(question)
    if not slots:
        return SolveResult(None, [], [], False)
    cset = cue_set(question)
    cands = list(_BY_SLOTS.get(len(slots), []))
    if not cands:
        return SolveResult(None, [], [], False)

    scored: List[Tuple[float, Template]] = []
    for t in cands:
        tc = set(t.cues)
        sc = jaccard(cset, tc)
        # boost support
        sc = sc + 0.01 * min(t.support, 20)
        if sc >= min_jaccard or (not cset and t.support >= 3):
            scored.append((sc, t))
    scored.sort(key=lambda x: -x[0])

    steps: List[StepTrace] = []
    # try top templates; require that if multiple fire different answers, pick highest score only
    for sc, t in scored[:max_try]:
        pred = execute_template(t, slots)
        if pred is None:
            continue
        # sanity: finite
        if pred != pred or abs(pred) > 1e12:
            continue
        steps.append(
            StepTrace(
                "AUTO-TMPL",
                t.op_sig or "train template",
                f"{t.id} support={t.support} j={sc:.2f}",
                float(pred),
            )
        )
        return SolveResult(_norm(pred), steps, ["AUTO-TMPL", t.id], True)

    return SolveResult(None, steps, [], False)


def role_score(q_roles: List[str], t_roles: List[str]) -> float:
    if not q_roles or not t_roles or len(q_roles) != len(t_roles):
        return 0.0
    hit = sum(1 for a, b in zip(q_roles, t_roles) if a == b)
    return hit / len(q_roles)


def solve_with_templates_strict(
    question: str,
    *,
    min_jaccard: float = 0.25,
    min_support: int = 1,
    margin: float = 0.05,
    min_role: float = 1.0,
) -> SolveResult:
    """Match train-mined templates by *exact* number-role signature + cues.

    Exact roles (same skeleton: each/cost/day/…) allow bulk curriculum transfer
    without loose bag-of-words wrong-fire.
    """
    load_templates()
    assert _BY_SLOTS is not None
    slots = extract_nums(question)
    if not slots or len(slots) < 3:
        return SolveResult(None, [], [], False)
    cset = cue_set(question)
    q_roles = number_roles(question)
    if len(cset) < 2 or not q_roles:
        return SolveResult(None, [], [], False)
    cands = [t for t in _BY_SLOTS.get(len(slots), []) if t.support >= min_support]
    scored: List[Tuple[float, Template, float]] = []
    for t in cands:
        if not t.roles or len(t.roles) != len(q_roles):
            continue
        rs = role_score(q_roles, t.roles)
        if rs < min_role:
            continue
        sc = jaccard(cset, set(t.cues))
        # still want some language overlap
        if sc < 0.15 and len(cset & set(t.cues)) < 2:
            continue
        pred = execute_template(t, slots)
        if pred is None or pred != pred or abs(pred) > 1e12:
            continue
        score = 0.55 * rs + 0.35 * sc + 0.10 * min(t.support, 30) / 30.0
        scored.append((score, t, pred))
    if not scored:
        return SolveResult(None, [], [], False)
    scored.sort(key=lambda x: -x[0])
    sc1, t1, p1 = scored[0]
    # Vote: among exact-role hits, pick the answer with most template agreement
    # (bulk-safe: only fire when curriculum programs cluster on one value)
    votes: Dict[str, List[Tuple[float, Template]]] = defaultdict(list)
    for sc, t, p in scored:
        key = _norm(p)
        votes[key].append((sc, t))
    best_ans = None
    best_vote = 0
    best_sc = -1.0
    best_t = None
    for ans, lst in votes.items():
        v = len(lst)
        top_sc = max(x[0] for x in lst)
        if v > best_vote or (v == best_vote and top_sc > best_sc):
            best_vote = v
            best_sc = top_sc
            best_ans = ans
            best_t = max(lst, key=lambda x: x[0])[1]
    if best_ans is None or best_t is None:
        return SolveResult(None, [], [], False)
    # require agreement of ≥2 templates OR (support≥3 and strong score)
    if best_vote < 2 and best_t.support < 3:
        return SolveResult(None, [], [], False)
    if best_sc < 0.50:
        return SolveResult(None, [], [], False)
    try:
        pred_f = float(best_ans)
    except ValueError:
        return SolveResult(None, [], [], False)
    steps = [
        StepTrace(
            "AUTO-TMPL",
            best_t.op_sig,
            f"{best_t.id} votes={best_vote} support={best_t.support} score={best_sc:.2f}",
            pred_f,
        )
    ]
    return SolveResult(_norm(pred_f), steps, ["AUTO-TMPL", best_t.id], True)
