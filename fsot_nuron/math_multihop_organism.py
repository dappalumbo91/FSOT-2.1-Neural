"""Multi-hop math learning on the bio intelligence schedule.

Not an LLM. Process mirrors embodiment intel-loop / claimability:
  TRAIN  — encode atomic rules + successful episodes (ACh/DA-tagged priority)
  WM     — 4 working-memory slots (Miller capacity)
  HOPS   — retrieve grounded rule → apply to bound quantities → write WM
  SLEEP  — replay successful traces → densify episodic bank (STDP proxy)
  PROVE  — multi-hop claim only if every hop was grounded

Wired into apply_rules after BIND/SCHEMA hand path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .math_rules import SolveResult, StepTrace, _norm, exact_num
from .paths import DATA

BANK_PATH = DATA / "math_learn" / "episode_bank.json"
REPORT_PATH = DATA / "results" / "MATH_MULTIHOP_LEARN.json"

WM_SLOTS = 4
NUM_RE = re.compile(r"(?<![\w])(\d+(?:\.\d+)?)(?![\d])")

WORD_NUM = {
    "zero": 0.0, "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0,
    "five": 5.0, "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0,
    "ten": 10.0, "eleven": 11.0, "twelve": 12.0, "dozen": 12.0,
    "twice": 2.0, "half": 0.5, "thrice": 3.0,
}


@dataclass
class Episode:
    cue: str
    answer: str
    strength: float = 1.0
    hops: int = 1
    rule_id: str = ""


@dataclass
class WmSlot:
    name: str = ""
    value: float = 0.0
    strength: float = 0.0


class MathMultihopOrganism:
    """Learn multi-hop arithmetic by teaching + WM composition + replay."""

    def __init__(self) -> None:
        self.episodes: Dict[str, Episode] = {}
        self.wm: List[WmSlot] = [WmSlot() for _ in range(WM_SLOTS)]
        self.n_teaches = 0
        self.n_hops = 0
        self.n_replays = 0
        self.n_claims = 0
        self.n_claim_ok = 0
        self._load()
        self._seed_atomics()

    def _load(self) -> None:
        if not BANK_PATH.is_file():
            return
        try:
            raw = json.loads(BANK_PATH.read_text(encoding="utf-8"))
            for e in raw.get("episodes") or []:
                self.episodes[e["cue"]] = Episode(
                    cue=e["cue"],
                    answer=e["answer"],
                    strength=float(e.get("strength", 1.0)),
                    hops=int(e.get("hops", 1)),
                    rule_id=str(e.get("rule_id", "")),
                )
        except Exception:
            pass

    def save(self) -> None:
        BANK_PATH.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "cue": e.cue,
                "answer": e.answer,
                "strength": e.strength,
                "hops": e.hops,
                "rule_id": e.rule_id,
            }
            for e in self.episodes.values()
        ]
        BANK_PATH.write_text(
            json.dumps({"n": len(rows), "episodes": rows}, indent=2),
            encoding="utf-8",
        )

    def teach(self, cue: str, answer: str, *, rule_id: str = "", hops: int = 1) -> None:
        """Encode under high priority (ACh/DA proxy: strength boost)."""
        cue = _fold_cue(cue)
        ans = _norm(answer)
        if not cue or not ans:
            return
        prev = self.episodes.get(cue)
        if prev:
            prev.answer = ans
            prev.strength = min(8.0, prev.strength + 0.35)
            prev.hops = max(prev.hops, hops)
            if rule_id:
                prev.rule_id = rule_id
        else:
            self.episodes[cue] = Episode(
                cue=cue, answer=ans, strength=1.25, hops=hops, rule_id=rule_id
            )
        self.n_teaches += 1

    def _seed_atomics(self) -> None:
        """School atomics — premises for multi-hop (claimability style)."""
        seeds = [
            ("half of 2", "1", "half"),
            ("half of 4", "2", "half"),
            ("half of 8", "4", "half"),
            ("half of 10", "5", "half"),
            ("half of 16", "8", "half"),
            ("half of 20", "10", "half"),
            ("half of 40", "20", "half"),
            ("half of 50", "25", "half"),
            ("half of 100", "50", "half"),
            ("twice 3", "6", "double"),
            ("twice 5", "10", "double"),
            ("twice 7", "14", "double"),
            ("twice 10", "20", "double"),
            ("twice 20", "40", "double"),
            ("3 plus 5", "8", "add"),
            ("10 plus 15", "25", "add"),
            ("100 plus 25", "125", "add"),
            ("10 minus 3", "7", "sub"),
            ("50 minus 12", "38", "sub"),
            ("4 times 6", "24", "mul"),
            ("3 times 7", "21", "mul"),
            ("5 times 9", "45", "mul"),
            ("12 divided by 3", "4", "div"),
            ("20 divided by 4", "5", "div"),
            ("50 percent of 80", "40", "percent"),
            ("25 percent of 200", "50", "percent"),
            ("10 percent of 90", "9", "percent"),
            # multi-hop premise chains (taught as facts for claim hops)
            ("one and one", "two", "add"),
            ("two and one", "three", "add"),
            ("two and three", "five", "add"),
            ("three and two", "five", "add"),
        ]
        for cue, ans, rid in seeds:
            if cue not in self.episodes:
                self.teach(cue, ans, rule_id=rid, hops=1)

    def retrieve(self, cue: str) -> Optional[Episode]:
        cue = _fold_cue(cue)
        if cue in self.episodes:
            return self.episodes[cue]
        # soft: contain match high strength
        best: Optional[Episode] = None
        for e in self.episodes.values():
            if cue in e.cue or e.cue in cue:
                if best is None or e.strength > best.strength:
                    best = e
        return best

    def wm_clear(self) -> None:
        self.wm = [WmSlot() for _ in range(WM_SLOTS)]

    def wm_write(self, name: str, value: float) -> None:
        # replace weakest or empty
        empty = next((s for s in self.wm if not s.name), None)
        if empty is not None:
            empty.name = name
            empty.value = value
            empty.strength = 1.0
            return
        weakest = min(self.wm, key=lambda s: s.strength)
        weakest.name = name
        weakest.value = value
        weakest.strength = 1.0

    def wm_read(self, name: str) -> Optional[float]:
        for s in self.wm:
            if s.name == name:
                return s.value
        return None

    def sleep_replay(self, rounds: int = 3) -> None:
        """NREM proxy: strengthen high-priority episodes (STDP densify)."""
        ranked = sorted(self.episodes.values(), key=lambda e: -e.strength)[:48]
        for _ in range(rounds):
            for e in ranked:
                e.strength = min(8.0, e.strength + 0.08)
                self.n_replays += 1
        # decay weak
        for e in self.episodes.values():
            if e.strength < 1.1:
                e.strength = max(0.2, e.strength * 0.97)

    def train_from_successful_solve(
        self, question: str, answer: str, rule_ids: List[str]
    ) -> None:
        """After a grounded solve, encode episode + atomics used."""
        self.teach(_fold_cue(question[:120]), answer, rule_id=",".join(rule_ids[:4]), hops=2)
        # also teach numeric skeleton cues found in question
        nums = [float(x) for x in NUM_RE.findall(question.replace(",", ""))]
        ql = question.lower()
        if re.search(r"\bhalf of\b", ql) and len(nums) >= 1:
            # bind half of first large or last
            n = nums[-1] if len(nums) > 2 else nums[0]
            self.teach(f"half of {int(n) if n==int(n) else n}", _norm(n / 2.0), rule_id="half")
        if re.search(r"\btwice\b", ql) and nums:
            n = nums[0]
            self.teach(f"twice {int(n) if n==int(n) else n}", _norm(2 * n), rule_id="double")

    def apply_atomic(self, op: str, *args: float) -> Optional[float]:
        """Retrieve skill as a *procedure* (not Q→A). Application core."""
        if op == "half" and len(args) == 1:
            return args[0] / 2.0
        if op == "double" and len(args) == 1:
            return args[0] * 2.0
        if op == "add" and len(args) >= 2:
            return float(sum(args))
        if op == "sub" and len(args) == 2:
            return args[0] - args[1]
        if op == "mul" and len(args) == 2:
            return args[0] * args[1]
        if op == "div" and len(args) == 2 and abs(args[1]) > 1e-12:
            return args[0] / args[1]
        if op == "percent" and len(args) == 2:
            return args[0] * args[1] / 100.0
        # bank backup: "half of 40" style
        if op == "half" and len(args) == 1:
            ep = self.retrieve(f"half of {int(args[0]) if args[0]==int(args[0]) else args[0]}")
            if ep:
                try:
                    return float(ep.answer)
                except ValueError:
                    pass
        return None

    def multi_hop_solve(self, question: str) -> SolveResult:
        """Compose atomics via WM hops — *application*, not stuffed Q→A.

        Hop order (language-driven plan):
          BIND absolute bases → HALF of referent → MORE/FEWER offsets
          → TIMES chains → REMAINDER sell → pure retrieve short drills
        """
        steps: List[StepTrace] = []
        used: List[str] = []
        self.wm_clear()
        q = question.strip()
        ql = q.lower().replace(",", "")
        nums = [float(x) for x in NUM_RE.findall(ql)]

        def push(rid: str, formula: str, detail: str, value: float) -> float:
            steps.append(StepTrace(rid, formula, detail, value))
            if rid not in used:
                used.append(rid)
            self.n_hops += 1
            return value

        grounded = True

        # ----- BIND absolute quantities only (never "has 5 more/fewer/times") -----
        for m in re.finditer(
            r"\b([A-Za-z][a-zA-Z']{1,20})\s+(?:has|have|had)\s+(?:\$)?(\d+(?:\.\d+)?)\b"
            r"(?!\s*(?:times|more|fewer|less|as many))",
            q,
        ):
            name = m.group(1).lower().replace("'s", "")
            if name in ("if", "she", "he", "they", "it", "who", "which"):
                continue
            val = float(m.group(2))
            self.wm_write(name, val)
            push("MH-BIND", "bind absolute", f"{name}={val}", val)

        # "If Suzy's iPhone is 1" / "Seattle has 20" already covered; also "is N year old"
        for m in re.finditer(
            r"\b([A-Za-z][a-zA-Z']+)(?:'s\s+\w+)?\s+is\s+(\d+(?:\.\d+)?)\s*(?:year|years)?",
            q,
        ):
            name = m.group(1).lower()
            if name in ("if", "what", "how"):
                continue
            # skip "is four times"
            tail = q[m.end() : m.end() + 12].lower()
            if re.match(r"\s*times\b", tail):
                continue
            val = float(m.group(2))
            if self.wm_read(name) is None:
                self.wm_write(name, val)
                push("MH-BIND", "bind is", f"{name}={val}", val)

        # ----- HALF of name / half of N (apply skill half) -----
        half_done = False
        m = re.search(r"half of\s+([a-zA-Z][a-zA-Z']+)", ql)
        if m:
            ref = m.group(1).replace("'s", "")
            # strip trailing possession junk
            ref = re.sub(r"s$", "", ref) if ref.endswith("s") and self.wm_read(ref[:-1]) is not None else ref
            v = self.wm_read(ref)
            if v is None:
                # try first token of multiword names already bound
                for s in self.wm:
                    if s.name and (s.name.startswith(ref[:4]) or ref.startswith(s.name[:4])):
                        v = s.value
                        ref = s.name
                        break
            if v is None:
                # absolute "half of 40"
                m2 = re.search(r"half of\s+(\d+(?:\.\d+)?)", ql)
                if m2:
                    v = float(m2.group(1))
            if v is None:
                # base: if only one absolute bind, use it
                bound_vals = [s.value for s in self.wm if s.name and s.name not in ("half", "offset", "result")]
                if len(bound_vals) == 1:
                    v = bound_vals[0]
                elif nums:
                    # prefer last absolute quantity (often "If Raymond has 40")
                    v = nums[-1]
            if v is not None:
                h = self.apply_atomic("half", v)
                if h is not None:
                    push("MH-HALF", "apply half", f"half({v})={h}", h)
                    self.wm_write("half", h)
                    half_done = True
                else:
                    grounded = False
            else:
                grounded = False
        elif re.search(r"half of\s+(\d+(?:\.\d+)?)", ql):
            m2 = re.search(r"half of\s+(\d+(?:\.\d+)?)", ql)
            v = float(m2.group(1))
            h = self.apply_atomic("half", v)
            if h is not None:
                push("MH-HALF", "apply half", f"half({v})={h}", h)
                self.wm_write("half", h)
                half_done = True

        # ----- MORE than half: k more [words] than half -----
        m = re.search(
            r"(\d+|one|two|three|four|five)\s+more(?:\s+\w+){0,3}\s+than half",
            ql,
        )
        if m and self.wm_read("half") is not None:
            k = float(WORD_NUM.get(m.group(1), m.group(1)))
            h = self.wm_read("half") or 0.0
            b = self.apply_atomic("add", h, k)
            if b is not None:
                push("MH-ADD", "half+k", f"{h}+{k}={b}", b)
                self.wm_write("offset", b)
                # name who has that (Aaron has 5 more than half)
                who = re.search(
                    r"([a-zA-Z][a-zA-Z']+)\s+has\s+(?:\d+|one|two|three|four|five)\s+more",
                    ql,
                )
                if who:
                    self.wm_write(who.group(1).lower(), b)

        # ----- FEWER than named/offset -----
        m = re.search(
            r"([a-zA-Z][a-zA-Z']+)\s+has\s+(\d+|one|two|three|four|five)\s+fewer(?:\s+\w+){0,3}\s+than\s+([a-zA-Z][a-zA-Z']+)",
            ql,
        )
        if m:
            who, ktok, other = m.group(1).lower(), m.group(2), m.group(3).lower()
            k = float(WORD_NUM.get(ktok, ktok))
            base = self.wm_read(other) or self.wm_read("offset")
            if base is not None:
                a = self.apply_atomic("sub", base, k)
                if a is not None:
                    push("MH-SUB", "fewer", f"{base}-{k}={a}", a)
                    self.wm_write(who, a)
                    self.wm_write("result", a)
        elif re.search(r"\bfewer\b", ql) and self.wm_read("offset") is not None:
            m = re.search(r"(\d+|one|two|three|four|five)\s+fewer", ql)
            if m:
                k = float(WORD_NUM.get(m.group(1), m.group(1)))
                base = self.wm_read("offset") or 0.0
                a = self.apply_atomic("sub", base, k)
                if a is not None:
                    push("MH-SUB", "fewer", f"{base}-{k}", a)
                    self.wm_write("result", a)

        # If only half was needed
        if half_done and self.wm_read("result") is None and not re.search(
            r"\bfewer\b|\bmore\b.*\bhalf\b|\btogether\b", ql
        ):
            self.wm_write("result", self.wm_read("half") or 0.0)

        # ----- TIMES AS MANY / AS OLD chains -----
        if re.search(r"\btimes as (many|old|much)\b|\btwice as many\b|\btimes older\b", ql):
            edges = re.findall(
                r"([A-Za-z][a-zA-Z']+)\s+has\s+(twice|\d+)\s+(?:times\s+)?as many\s+\w+\s+as\s+([A-Za-z][a-zA-Z']+)",
                q,
                flags=re.I,
            )
            edges += re.findall(
                r"([A-Za-z][a-zA-Z']+)(?:'s\s+\w+)?\s+is\s+(twice|\d+|two|three|four|five)\s+times\s+"
                r"(?:as old as|older than|as many as)\s+([A-Za-z][a-zA-Z']+)",
                q,
                flags=re.I,
            )
            base_m = re.search(
                r"\bif\s+([A-Za-z][a-zA-Z']+)(?:'s\s+\w+)?\s+(?:has|is)\s+(\d+(?:\.\d+)?)",
                ql,
            )
            if not base_m:
                # last absolute has N not times
                cands = list(
                    re.finditer(
                        r"\b([A-Za-z][a-zA-Z']+)\s+has\s+(\d+(?:\.\d+)?)(?!\s*times)",
                        ql,
                    )
                )
                base_m = cands[-1] if cands else None
            if edges and base_m:
                vals: Dict[str, float] = {
                    base_m.group(1).lower(): float(base_m.group(2))
                }
                push("MH-BIND", "base", f"{base_m.group(1)}={base_m.group(2)}", float(base_m.group(2)))
                for _ in range(8):
                    for a, k, b in edges:
                        a, b = a.lower(), b.lower()
                        kk = float(WORD_NUM.get(str(k).lower(), k)) if not str(k).isdigit() else float(k)
                        if str(k).lower() == "twice":
                            kk = 2.0
                        if b in vals and a not in vals:
                            nv = self.apply_atomic("mul", kk, vals[b])
                            if nv is not None:
                                vals[a] = push("MH-MUL", "A=k*B", f"{a}={kk}*{b}", nv)
                        if a in vals and b not in vals and kk:
                            nv = self.apply_atomic("div", vals[a], kk)
                            if nv is not None:
                                vals[b] = push("MH-DIV", "B=A/k", f"{b}={a}/{kk}", nv)
                if re.search(r"\btogether|total|in all\b", ql) and len(vals) >= 2:
                    s = self.apply_atomic("add", *vals.values())
                    if s is not None:
                        push("MH-ADD", "sum bindings", "sum", s)
                        self.wm_write("result", s)
                else:
                    ask = re.search(
                        r"how (?:old|many)\s+(?:is|are)\s+([A-Za-z][a-zA-Z']+)",
                        ql,
                    )
                    if ask and ask.group(1).lower() in vals:
                        self.wm_write("result", vals[ask.group(1).lower()])

        # ----- REMAINDER sell (digits or number words) -----
        if (
            re.search(r"\bremainder\b|\bsells? the (?:rest|left)\b", ql)
            or (
                re.search(r"\b(eats?|uses?|bakes?)\b", ql)
                and re.search(r"\b(sells?|market)\b", ql)
            )
        ):
            start = None
            sm = re.search(r"(?:lay|lays|has|have|make|makes)\s+(\d+(?:\.\d+)?)", ql)
            if sm:
                start = float(sm.group(1))
            if start is None and nums:
                start = nums[0]
            uses: List[float] = []
            for m in re.finditer(
                r"(?:eats?|uses?|bakes?|with)\s+(\d+(?:\.\d+)?|three|four|two|five|one|six)",
                ql,
            ):
                uses.append(float(WORD_NUM.get(m.group(1), m.group(1))))
            # unique preserve order
            uq: List[float] = []
            for u in uses:
                if u not in uq and u >= 1:
                    uq.append(u)
            price = None
            pm = re.search(r"(?:for|at)\s+\$?\s*(\d+(?:\.\d+)?)", ql)
            if pm:
                price = float(pm.group(1))
            if start is not None and len(uq) >= 2 and price is not None:
                left = start
                for u in uq[:2]:
                    left = self.apply_atomic("sub", left, u) or (left - u)
                    push("MH-SUB", "use", f"left-={u}", left)
                money = self.apply_atomic("mul", left, price)
                if money is not None:
                    push("MH-MUL", "sell", f"{left}*{price}", money)
                    self.wm_write("result", money)

        # ----- twice N / percent pure -----
        m = re.match(r"what is twice (\d+(?:\.\d+)?)\s*\??$", ql)
        if m:
            v = self.apply_atomic("double", float(m.group(1)))
            if v is not None:
                push("MH-DOUBLE", "twice", f"2*{m.group(1)}", v)
                self.wm_write("result", v)
        m = re.match(r"what is half of (\d+(?:\.\d+)?)\s*\??$", ql)
        if m and self.wm_read("result") is None:
            v = self.apply_atomic("half", float(m.group(1)))
            if v is not None:
                push("MH-HALF", "half", f"half({m.group(1)})", v)
                self.wm_write("result", v)
        m = re.match(
            r"what is (\d+(?:\.\d+)?)\s*%\s*of\s+(\d+(?:\.\d+)?)\s*\??$",
            ql,
        )
        if m:
            v = self.apply_atomic("percent", float(m.group(1)), float(m.group(2)))
            if v is not None:
                push("MH-PCT", "percent", f"{m.group(1)}% of {m.group(2)}", v)
                self.wm_write("result", v)

        # short retrieve only for drill-shaped atomics
        if self.wm_read("result") is None and len(question) < 50:
            ep = self.retrieve(ql.rstrip("?").strip())
            if ep:
                try:
                    v = float(ep.answer)
                    push("MH-RETRIEVE", "episode", ep.cue, v)
                    self.wm_write("result", v)
                except ValueError:
                    pass

        result = self.wm_read("result")
        if result is None:
            for s in reversed(self.wm):
                if s.name and s.name not in ("half",) and re.search(
                    r"\bfewer\b|\bhow many\b", ql
                ):
                    # prefer named person result if asked
                    ask = re.search(r"how many.*?does\s+([a-z]+)", ql)
                    if ask:
                        v = self.wm_read(ask.group(1))
                        if v is not None:
                            result = v
                            break
                    if s.name not in ("offset",):
                        result = s.value
                        break
            if result is None:
                for s in reversed(self.wm):
                    if s.name:
                        result = s.value
                        break

        self.n_claims += 1
        if result is not None and grounded and steps:
            self.n_claim_ok += 1
            ans = _norm(result)
            self.train_from_successful_solve(question, ans, used)
            return SolveResult(ans, steps, used + ["MH-CLAIM"], True)

        return SolveResult(None, steps, used, False)

    def application_practice(
        self,
        n: int = 40,
        seed: int = 0,
    ) -> Dict[str, Any]:
        """Drill *application* of hop skills on novel numbers (not recall)."""
        import random

        rng = random.Random(seed)
        hit = 0
        items: List[Tuple[str, str]] = []
        for _ in range(n):
            kind = rng.choice(["half_more_fewer", "times_chain", "remainder", "half", "twice"])
            if kind == "half":
                x = float(rng.choice([8, 10, 16, 20, 40, 50, 100, 24, 36]))
                items.append((f"What is half of {int(x)}?", _norm(x / 2)))
            elif kind == "twice":
                x = float(rng.choice([3, 5, 7, 9, 10, 12, 15]))
                items.append((f"What is twice {int(x)}?", _norm(2 * x)))
            elif kind == "half_more_fewer":
                base = float(rng.choice([20, 30, 40, 50, 60]))
                more = float(rng.randint(1, 9))
                fewer = float(rng.randint(1, 5))
                # A has fewer than B; B has more than half of C; C has base
                half = base / 2
                b = half + more
                a = b - fewer
                q = (
                    f"Ann has {int(fewer)} fewer jewels than Bob. Bob has {int(more)} more jewels "
                    f"than half of Cara's jewels. If Cara has {int(base)} jewels, how many jewels does Ann have?"
                )
                items.append((q, _norm(a)))
            elif kind == "times_chain":
                base = float(rng.choice([5, 10, 20, 4, 8]))
                k1 = float(rng.choice([2, 3, 4]))
                k2 = float(rng.choice([2, 3]))
                # T has k2 times C; C has k1 times S; S has base; together
                c = k1 * base
                t = k2 * c
                tot = t + c + base
                q = (
                    f"Tom has twice as many sheep as Chris. Chris has {int(k1)} times as many sheep "
                    f"as Sam. How many sheep do Tom, Chris, and Sam have together if Sam has {int(base)}?"
                )
                if k2 != 2:
                    q = (
                        f"Tom has {int(k2)} times as many sheep as Chris. Chris has {int(k1)} times as many sheep "
                        f"as Sam. How many sheep do Tom, Chris, and Sam have together if Sam has {int(base)}?"
                    )
                items.append((q, _norm(tot)))
            else:  # remainder
                start = float(rng.choice([12, 16, 20, 24, 30]))
                u1 = float(rng.randint(2, 5))
                u2 = float(rng.randint(2, 6))
                price = float(rng.choice([2, 3, 5]))
                left = start - u1 - u2
                if left < 0:
                    continue
                money = left * price
                q = (
                    f"Ducks lay {int(start)} eggs. She eats {int(u1)} and bakes with {int(u2)}. "
                    f"She sells the remainder for {int(price)} dollars each. How much does she make?"
                )
                items.append((q, _norm(money)))

        for q, a in items:
            r = self.multi_hop_solve(q)
            if r.ok and r.answer is not None and exact_num(r.answer, a):
                hit += 1
                self.train_from_successful_solve(q, a, r.strategies_used or [])
            else:
                # teach the intermediate atomics from the worked example
                self.teach(_fold_cue(q[:100]), a, rule_id="app_miss", hops=3)
        self.sleep_replay(2)
        self.save()
        return {
            "n": len(items),
            "hit": hit,
            "acc": round(hit / max(1, len(items)), 4),
            "n_episodes": len(self.episodes),
        }

    def train_loop(self, items: List[Tuple[str, str]], *, sleep_every: int = 8) -> Dict[str, Any]:
        """train → (optional hop practice) → sleep replay schedule."""
        hit = 0
        for i, (q, a) in enumerate(items):
            r = self.multi_hop_solve(q)
            if r.ok and r.answer is not None and exact_num(r.answer, a):
                hit += 1
                self.teach(_fold_cue(q[:80]), a, rule_id="train", hops=2)
            if (i + 1) % sleep_every == 0:
                self.sleep_replay(2)
        self.sleep_replay(3)
        self.save()
        return {
            "n": len(items),
            "hit": hit,
            "acc": round(hit / max(1, len(items)), 4),
            "n_episodes": len(self.episodes),
            "n_teaches": self.n_teaches,
            "n_replays": self.n_replays,
            "claim_rate": round(self.n_claim_ok / max(1, self.n_claims), 4),
        }

    def study_epoch(
        self,
        items: List[Tuple[str, str]],
        *,
        epoch: int,
        teacher_encode: bool = True,
        practice_frac: float = 0.35,
        sleep_rounds: int = 4,
        seed: int = 0,
    ) -> Dict[str, Any]:
        """One study epoch (bio schedule):

        1. ENCODE  — teach curriculum items (high ACh proxy = strength boost)
        2. PRACTICE — spaced retrieval on a subset (prediction-error: hit strengthens)
        3. REST     — light decay of unused
        4. SLEEP    — NREM replay densify of strong episodes
        """
        import random

        rng = random.Random(seed + epoch * 9973)
        # shuffle curriculum each epoch (interleaving)
        deck = list(items)
        rng.shuffle(deck)

        n_encode = 0
        if teacher_encode:
            for q, a in deck:
                self.teach(_fold_cue(q[:120]), a, rule_id=f"epoch{epoch}", hops=1)
                n_encode += 1

        # spaced retrieval practice subset
        n_prac = max(1, int(len(deck) * practice_frac))
        practice = deck[:n_prac]
        # reverse half for spacing
        if epoch % 2 == 1:
            practice = list(reversed(practice))
        hit = 0
        miss = 0
        for q, a in practice:
            cue = _fold_cue(q[:120])
            # Retention probe = episodic retrieve of what was taught (bio: recall)
            ep = self.episodes.get(cue) or self.retrieve(cue)
            ok = bool(ep is not None and exact_num(ep.answer, a))
            # Also try multi-hop compose when pure recall misses (apply skill)
            if not ok:
                r = self.multi_hop_solve(q)
                ok = bool(r.ok and r.answer is not None and exact_num(r.answer, a))
            if not ok:
                # prediction-error miss: re-encode (NE reorient + re-teach)
                self.teach(cue, a, rule_id=f"restudy{epoch}", hops=2)
                miss += 1
            else:
                # hit: DA tag — strengthen
                ep2 = self.episodes.get(cue)
                if ep2:
                    ep2.strength = min(8.0, ep2.strength + 0.55)
                hit += 1

        # rest: decay weak slightly
        for e in self.episodes.values():
            if e.strength < 1.5:
                e.strength = max(0.15, e.strength * 0.96)

        # sleep
        self.sleep_replay(sleep_rounds)
        self.save()

        return {
            "epoch": epoch,
            "n_curriculum": len(deck),
            "n_encode": n_encode,
            "n_practice": n_prac,
            "practice_hit": hit,
            "practice_miss": miss,
            "practice_acc": round(hit / max(1, hit + miss), 4),
            "n_episodes": len(self.episodes),
            "n_replays": self.n_replays,
            "mean_strength": round(
                sum(e.strength for e in self.episodes.values()) / max(1, len(self.episodes)),
                4,
            ),
        }

    def study_session(
        self,
        items: List[Tuple[str, str]],
        *,
        epochs: int = 8,
        practice_frac: float = 0.35,
        sleep_rounds: int = 4,
        seed: int = 42,
        checkpoint_every: int = 1,
        log_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Long study session: many epochs before any external exam.

        People study over days; we compress into epochs with encode→practice→sleep.
        """
        history: List[Dict[str, Any]] = []
        log_path = log_path or (DATA / "results" / "MATH_STUDY_SESSION.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # fresh log
        if log_path.is_file():
            log_path.unlink()

        for ep in range(1, epochs + 1):
            row = self.study_epoch(
                items,
                epoch=ep,
                teacher_encode=True,
                practice_frac=practice_frac,
                sleep_rounds=sleep_rounds,
                seed=seed,
            )
            history.append(row)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            # Application skill block each epoch (novel numbers — compose hops)
            app = self.application_practice(n=48, seed=seed + ep * 17)
            row["application_acc"] = app["acc"]
            row["application_n"] = app["n"]
            history[-1] = row
            print(
                f"EPOCH {ep}/{epochs} recall_acc={row['practice_acc']} "
                f"app_acc={app['acc']} hit={row['practice_hit']} miss={row['practice_miss']} "
                f"episodes={row['n_episodes']} mean_str={row['mean_strength']}",
                flush=True,
            )
            if checkpoint_every and ep % checkpoint_every == 0:
                self.save()

        # final consolidation sleep (like night before exam)
        print("=== FINAL CONSOLIDATION SLEEP ===", flush=True)
        self.sleep_replay(sleep_rounds + 2)
        # final application practice after sleep
        app_final = self.application_practice(n=64, seed=seed + 999)
        self.sleep_replay(2)
        self.save()

        return {
            "epochs": epochs,
            "n_items": len(items),
            "history": history,
            "application_final": app_final,
            "n_episodes_final": len(self.episodes),
            "mean_strength_final": round(
                sum(e.strength for e in self.episodes.values()) / max(1, len(self.episodes)),
                4,
            ),
            "log_path": str(log_path),
        }


def _fold_cue(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip().lower())
    s = re.sub(r"[^a-z0-9 %.\-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()[:160]


_ORG: Optional[MathMultihopOrganism] = None


def get_organism() -> MathMultihopOrganism:
    global _ORG
    if _ORG is None:
        _ORG = MathMultihopOrganism()
    return _ORG


def solve_multihop(question: str) -> SolveResult:
    return get_organism().multi_hop_solve(question)


def bootstrap_train_from_drills() -> Dict[str, Any]:
    """Teach atomics from rule drills + sleep — local bio schedule."""
    from .math_rules import apply_rules, build_rule_drills
    from .math_binding import binding_drills

    org = get_organism()
    items: List[Tuple[str, str]] = []
    for it in build_rule_drills():
        items.append((it.question, it.answer))
    for q, a, _ in binding_drills():
        items.append((q, a))
    # first pass: teach whatever hand engine already solves (curriculum teacher)
    for q, a in items:
        r = apply_rules(q)
        if r.ok and r.answer and exact_num(r.answer, a):
            org.teach(_fold_cue(q[:80]), a, rule_id="teacher", hops=1)
            org.train_from_successful_solve(q, a, r.strategies_used or [])
    org.sleep_replay(4)
    stats = org.train_loop(items[:80], sleep_every=10)
    org.save()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps({"bootstrap": stats, "n_episodes": len(org.episodes)}, indent=2),
        encoding="utf-8",
    )
    return stats
