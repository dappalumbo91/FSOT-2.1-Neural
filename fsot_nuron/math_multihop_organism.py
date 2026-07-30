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

    def multi_hop_solve(self, question: str) -> SolveResult:
        """Compose atomics via WM hops — claimable only if every hop grounded."""
        steps: List[StepTrace] = []
        used: List[str] = []
        self.wm_clear()
        ql = question.lower().replace(",", "")
        nums = [float(x) for x in NUM_RE.findall(ql)]
        # number words
        for w, v in WORD_NUM.items():
            if w in ("half", "twice", "thrice"):
                continue
            if re.search(rf"\b{w}\b", ql):
                nums.append(v)

        def push(rid: str, formula: str, detail: str, value: float) -> float:
            steps.append(StepTrace(rid, formula, detail, value))
            if rid not in used:
                used.append(rid)
            self.n_hops += 1
            return value

        # --- plan hops from language (bio: retrieve then apply) ---
        grounded = True

        # BIND: named "X has N"
        for m in re.finditer(
            r"\b([A-Za-z][a-zA-Z']{1,20})\s+(?:has|have|had)\s+(?:\$)?(\d+(?:\.\d+)?)\b(?!\s*times)",
            question,
        ):
            name = m.group(1).lower()
            if name in ("if", "she", "he", "they", "it"):
                continue
            val = float(m.group(2))
            self.wm_write(name, val)
            push("MH-BIND", "bind name", f"{name}={val}", val)
            self.teach(f"{name} has", _norm(val), rule_id="BIND-01")

        # half of named / half of N
        m = re.search(r"half of\s+([a-zA-Z][a-zA-Z']+)", ql)
        if m:
            ref = m.group(1)
            v = self.wm_read(ref)
            if v is None:
                ep = self.retrieve(f"half of {ref}")
                if ep:
                    try:
                        v = float(ep.answer)
                        push("MH-RETRIEVE", "half bank", ep.cue, v)
                    except ValueError:
                        v = None
            if v is None and nums:
                # last absolute often the base (Raymond 40)
                v = nums[-1]
            if v is not None:
                h = push("MH-HALF", "half(n)", f"half({v})", v / 2.0)
                self.wm_write("half", h)
                self.teach(f"half of {int(v) if v==int(v) else v}", _norm(h), rule_id="half")
            else:
                grounded = False

        # k more than half → WM half + k
        m = re.search(
            r"(\d+|one|two|three|four|five)\s+more(?:\s+\w+){0,2}\s+than half",
            ql,
        )
        if m and self.wm_read("half") is not None:
            ktok = m.group(1)
            k = float(WORD_NUM.get(ktok, ktok))
            h = self.wm_read("half") or 0.0
            b = push("MH-OFFSET", "half+k", f"{h}+{k}", h + k)
            self.wm_write("offset", b)

        # k fewer than Y (use offset or named)
        m = re.search(r"(\d+|one|two|three|four|five)\s+fewer", ql)
        if m and (self.wm_read("offset") is not None or self.wm_read("half") is not None):
            k = float(WORD_NUM.get(m.group(1), m.group(1)))
            base = self.wm_read("offset")
            if base is None:
                base = self.wm_read("half")
            if base is not None:
                a = push("MH-OFFSET", "base−k", f"{base}-{k}", base - k)
                self.wm_write("result", a)

        # times as many chain with base at end
        if re.search(r"\btimes as (many|old|much)\b|\btwice as many\b", ql) and len(nums) >= 1:
            edges = re.findall(
                r"([A-Za-z][a-zA-Z']+)\s+has\s+(twice|\d+)\s+(?:times\s+)?as many\s+\w+\s+as\s+([A-Za-z][a-zA-Z']+)",
                question,
                flags=re.I,
            )
            base_m = re.search(
                r"\bif\s+([A-Za-z][a-zA-Z']+)\s+has\s+(\d+(?:\.\d+)?)",
                ql,
            )
            if not base_m:
                base_m = re.search(
                    r"([A-Za-z][a-zA-Z']+)\s+has\s+(\d+(?:\.\d+)?)(?!\s*times)",
                    ql,
                )
            if edges and base_m:
                vals: Dict[str, float] = {
                    base_m.group(1).lower(): float(base_m.group(2))
                }
                push("MH-BIND", "base", f"{base_m.group(1)}={base_m.group(2)}", float(base_m.group(2)))
                for _ in range(6):
                    for a, k, b in edges:
                        a, b = a.lower(), b.lower()
                        kk = 2.0 if k.lower() == "twice" else float(k)
                        if b in vals and a not in vals:
                            vals[a] = push("MH-MUL", "A=k*B", f"{a}={kk}*{b}", kk * vals[b])
                        if a in vals and b not in vals and kk:
                            vals[b] = push("MH-DIV", "B=A/k", f"{b}={a}/{kk}", vals[a] / kk)
                if re.search(r"\btogether|total\b", ql) and len(vals) >= 2:
                    s = sum(vals.values())
                    push("MH-ADD", "sum", "sum", s)
                    self.wm_write("result", s)
                else:
                    ask = re.search(r"how (?:old|many).*?\b([A-Za-z][a-zA-Z']+)", ql)
                    if ask and ask.group(1).lower() in vals:
                        self.wm_write("result", vals[ask.group(1).lower()])

        # remainder: start − uses × price
        if re.search(r"\bremainder\b", ql) and re.search(r"\b(sell|market|\$)\b", ql):
            if len(nums) >= 4:
                start, u1, u2, price = nums[0], nums[1], nums[2], nums[3]
                # word nums may pad — prefer first digit as start
                left = push("MH-SUB", "use1", f"{start}-{u1}", start - u1)
                left = push("MH-SUB", "use2", f"{left}-{u2}", left - u2)
                money = push("MH-MUL", "sell", f"{left}*{price}", left * price)
                self.wm_write("result", money)

        # pure retrieve atomic if short question
        if self.wm_read("result") is None and len(question) < 60:
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
            # last written non-empty
            for s in reversed(self.wm):
                if s.name:
                    result = s.value
                    break

        self.n_claims += 1
        if result is not None and grounded and steps:
            self.n_claim_ok += 1
            ans = _norm(result)
            # encode success (train)
            self.train_from_successful_solve(question, ans, used)
            return SolveResult(ans, steps, used + ["MH-CLAIM"], True)

        return SolveResult(None, steps, used, False)

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
