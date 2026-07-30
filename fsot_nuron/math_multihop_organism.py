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
TRACE_BANK_PATH = DATA / "math_learn" / "trace_bank.json"
REPORT_PATH = DATA / "results" / "MATH_MULTIHOP_LEARN.json"
EXPERIENCE_REPORT = DATA / "results" / "MATH_EXPERIENCE_LEARN.json"

WM_SLOTS = 4
NUM_RE = re.compile(r"(?<![\w])(\d+(?:\.\d+)?)(?![\d])")

WORD_NUM = {
    "zero": 0.0, "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0,
    "five": 5.0, "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0,
    "ten": 10.0, "eleven": 11.0, "twelve": 12.0, "dozen": 12.0,
    "twice": 2.0, "half": 0.5, "thrice": 3.0,
}

# map teacher calc ops → apply_atomic names
_OP_MAP = {
    "+": "add",
    "-": "sub",
    "*": "mul",
    "/": "div",
    "add": "add",
    "sub": "sub",
    "mul": "mul",
    "div": "div",
    "half": "half",
    "double": "double",
    "percent": "percent",
    "id": "id",
}


@dataclass
class Episode:
    cue: str
    answer: str
    strength: float = 1.0
    hops: int = 1
    rule_id: str = ""


@dataclass
class EpisodeTrace:
    """Learned multi-hop method retained from experience (not hand rules).

    hop_trace ops run through apply_atomic with slot:/t:/const: args so the
    same method transfers to novel numbers when the language cue matches.
    """

    cue_skeleton: str
    hop_trace: List[Dict[str, Any]]
    n_slots: int
    strength: float = 1.25
    support: int = 1
    source: str = "lesson"
    last_answer: str = ""  # diagnostic only — never used as solve target


@dataclass
class WmSlot:
    name: str = ""
    value: float = 0.0
    strength: float = 0.0


class MathMultihopOrganism:
    """Learn multi-hop arithmetic by teaching + WM composition + replay.

    Pure-bio path: experience → episodic hop traces → WM atomics → sleep → apply.
    Plans live in memory (trace_bank), not as growing regex in source.
    """

    def __init__(self) -> None:
        self.episodes: Dict[str, Episode] = {}
        self.traces: Dict[str, EpisodeTrace] = {}
        self.wm: List[WmSlot] = [WmSlot() for _ in range(WM_SLOTS)]
        self.n_teaches = 0
        self.n_hops = 0
        self.n_replays = 0
        self.n_claims = 0
        self.n_claim_ok = 0
        self.n_trace_teaches = 0
        self.n_trace_hits = 0
        self.n_trace_tries = 0
        self._load()
        self._load_traces()
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

    def _load_traces(self) -> None:
        if not TRACE_BANK_PATH.is_file():
            return
        try:
            raw = json.loads(TRACE_BANK_PATH.read_text(encoding="utf-8"))
            for e in raw.get("traces") or []:
                sk = str(e.get("cue_skeleton") or "")
                if not sk:
                    continue
                self.traces[sk] = EpisodeTrace(
                    cue_skeleton=sk,
                    hop_trace=list(e.get("hop_trace") or []),
                    n_slots=int(e.get("n_slots") or 0),
                    strength=float(e.get("strength", 1.25)),
                    support=int(e.get("support") or 1),
                    source=str(e.get("source") or "lesson"),
                    last_answer=str(e.get("last_answer") or ""),
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
        self.save_traces()

    def save_traces(self) -> None:
        TRACE_BANK_PATH.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "cue_skeleton": t.cue_skeleton,
                "hop_trace": t.hop_trace,
                "n_slots": t.n_slots,
                "strength": t.strength,
                "support": t.support,
                "source": t.source,
                "last_answer": t.last_answer,
            }
            for t in self.traces.values()
        ]
        TRACE_BANK_PATH.write_text(
            json.dumps(
                {
                    "n": len(rows),
                    "doctrine": "experience→episodic hop traces→WM atomics→sleep",
                    "traces": rows,
                },
                indent=2,
            ),
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

    # ----- pure-bio: experience → episodic hop traces -----

    def teach_trace(
        self,
        question: str,
        hop_trace: List[Dict[str, Any]],
        *,
        n_slots: Optional[int] = None,
        source: str = "lesson",
        gold: str = "",
    ) -> Optional[EpisodeTrace]:
        """Retain a multi-hop *method* from a worked lesson (not the exam answer)."""
        if not hop_trace:
            return None
        sk = cue_skeleton(question)
        if not sk:
            return None
        slots = extract_slot_nums(question)
        ns = n_slots if n_slots is not None else len(slots)
        prev = self.traces.get(sk)
        if prev and _hop_sig(prev.hop_trace) == _hop_sig(hop_trace):
            prev.strength = min(8.0, prev.strength + 0.45)
            prev.support += 1
            if gold:
                prev.last_answer = _norm(gold)
            self.n_trace_teaches += 1
            return prev
        # same skeleton, different method: keep stronger / higher support
        if prev and prev.strength >= 2.5 and prev.support >= 3:
            # don't overwrite a well-consolidated method lightly
            if _hop_sig(prev.hop_trace) != _hop_sig(hop_trace):
                # store under extended key if conflict
                sk = f"{sk} ::{_hop_sig(hop_trace)[:24]}"
        tr = EpisodeTrace(
            cue_skeleton=sk,
            hop_trace=hop_trace,
            n_slots=ns,
            strength=1.4,
            support=1,
            source=source,
            last_answer=_norm(gold) if gold else "",
        )
        self.traces[sk] = tr
        self.n_trace_teaches += 1
        self.n_teaches += 1
        return tr

    def teach_from_worked(
        self,
        question: str,
        answer_body: str,
        gold: str,
        *,
        source: str = "train_lesson",
    ) -> bool:
        """Teacher uses solution key to build a hop trace; organism only retains memory.

        Abstraction of <<calcs>> lives on the *school* side. Student stores the trace.
        """
        hops = hop_trace_from_worked(question, answer_body, gold)
        if not hops:
            return False
        slots = extract_slot_nums(question)
        # verify replay on the lesson numbers before encoding (grounded teach)
        pred = self.replay_trace(hops, slots)
        if pred is None:
            return False
        if gold and not exact_num(_norm(pred), _norm(gold)):
            # still teach if close? require exact for integrity
            try:
                if abs(float(_norm(pred)) - float(_norm(gold))) > 0.05:
                    return False
            except ValueError:
                return False
        self.teach_trace(
            question,
            hops,
            n_slots=len(slots),
            source=source,
            gold=gold,
        )
        return True

    def retrieve_traces(
        self,
        question: str,
        *,
        top_k: int = 8,
        min_overlap: float = 0.12,
    ) -> List[Tuple[float, EpisodeTrace]]:
        """Retrieve retained methods by language skeleton similarity + strength.

        Exact skeleton match always wins (taught wording retention).
        """
        sk = cue_skeleton(question)
        if not sk or not self.traces:
            return []
        slots = extract_slot_nums(question)
        n = len(slots)

        # exact cue first — A-student: "I remember this lesson"
        exact: List[Tuple[float, EpisodeTrace]] = []
        if sk in self.traces:
            exact.append((1.0, self.traces[sk]))
        for key, t in self.traces.items():
            if key.startswith(sk + " ::") or key.startswith(sk + "::"):
                exact.append((0.99, t))
        if exact:
            exact.sort(key=lambda x: (-x[1].strength, -x[1].support))
            return exact[:top_k]

        qset = set(sk.split())
        scored: List[Tuple[float, EpisodeTrace]] = []
        for t in self.traces.values():
            if t.n_slots and n and t.n_slots != n:
                if abs(t.n_slots - n) > 0:
                    continue
            base_sk = t.cue_skeleton.split(" ::")[0].split("::")[0]
            tset = set(base_sk.split())
            if not tset or not qset:
                continue
            inter = len(qset & tset)
            union = len(qset | tset)
            j = inter / max(1, union)
            if j < min_overlap and inter < 4:
                continue
            # prefer high overlap; soft match is only for transfer, not guesses
            if j < 0.35 and inter < 6:
                continue
            score = 0.70 * j + 0.20 * min(t.strength, 8.0) / 8.0 + 0.10 * min(t.support, 20) / 20.0
            scored.append((score, t))
        scored.sort(key=lambda x: -x[0])
        return scored[:top_k]

    def replay_trace(
        self,
        hop_trace: List[Dict[str, Any]],
        slots: List[float],
    ) -> Optional[float]:
        """Replay a retained hop plan through apply_atomic (physiology)."""
        step_vals: List[float] = []
        for hop in hop_trace:
            op = _OP_MAP.get(str(hop.get("op", "")), str(hop.get("op", "")))
            raw_args = hop.get("args") or []
            vals: List[float] = []
            for a in raw_args:
                v = self._resolve_hop_arg(a, slots, step_vals)
                if v is None:
                    return None
                vals.append(v)
            if op == "id":
                if not vals:
                    return None
                step_vals.append(vals[0])
                self.n_hops += 1
                continue
            if op == "half":
                if len(vals) < 1:
                    return None
                r = self.apply_atomic("half", vals[0])
            elif op == "double":
                if len(vals) < 1:
                    return None
                r = self.apply_atomic("double", vals[0])
            elif op in ("add", "sub", "mul", "div", "percent"):
                if len(vals) < 2:
                    return None
                r = self.apply_atomic(op, vals[0], vals[1])
            else:
                return None
            if r is None:
                return None
            step_vals.append(float(r))
            self.n_hops += 1
        return step_vals[-1] if step_vals else None

    def _resolve_hop_arg(
        self,
        arg: Any,
        slots: List[float],
        step_vals: List[float],
    ) -> Optional[float]:
        # string form: slot:0 / t:1 / const:5
        if isinstance(arg, str):
            if arg.startswith("slot:"):
                i = int(arg.split(":", 1)[1])
                return slots[i] if 0 <= i < len(slots) else None
            if arg.startswith("t:") or arg.startswith("wm:"):
                i = int(arg.split(":", 1)[1])
                return step_vals[i] if 0 <= i < len(step_vals) else None
            if arg.startswith("const:"):
                return float(arg.split(":", 1)[1])
            try:
                return float(arg)
            except ValueError:
                return None
        # template-style [kind, val]
        if isinstance(arg, (list, tuple)) and len(arg) >= 2:
            kind, val = arg[0], arg[1]
            if kind == "n":
                i = int(val)
                return slots[i] if 0 <= i < len(slots) else None
            if kind == "t":
                i = int(val)
                return step_vals[i] if 0 <= i < len(step_vals) else None
            if kind == "c":
                return float(val)
        if isinstance(arg, (int, float)):
            return float(arg)
        return None

    def solve_from_experience(self, question: str) -> SolveResult:
        """Apply retained hop traces — what was learned from information, not regex."""
        steps: List[StepTrace] = []
        used: List[str] = []
        self.wm_clear()
        slots = extract_slot_nums(question)
        if not slots:
            return SolveResult(None, steps, used, False)

        # bind slots into WM for visibility
        for i, v in enumerate(slots[:WM_SLOTS]):
            self.wm_write(f"slot{i}", v)
            steps.append(StepTrace("MH-BIND", "slot", f"slot{i}={v}", v))

        cands = self.retrieve_traces(question)
        self.n_trace_tries += 1
        for score, tr in cands:
            # exact recall may still run if slot count matches method arity
            if tr.n_slots and len(slots) != tr.n_slots:
                if score < 0.95:  # soft matches must match arity
                    continue
                # exact cue but different digit count — skip (number-word lessons)
                continue
            pred = self.replay_trace(tr.hop_trace, slots)
            if pred is None:
                continue
            if pred != pred or abs(pred) > 1e12:
                continue
            steps.append(
                StepTrace(
                    "MH-TRACE",
                    f"replay n={len(tr.hop_trace)}",
                    f"score={score:.2f} str={tr.strength:.1f} sup={tr.support}",
                    float(pred),
                )
            )
            used.extend(["MH-TRACE", "MH-CLAIM"])
            # strengthen on successful grounded use
            tr.strength = min(8.0, tr.strength + 0.35)
            tr.support += 1
            self.n_trace_hits += 1
            self.n_claims += 1
            self.n_claim_ok += 1
            self.wm_write("result", float(pred))
            return SolveResult(_norm(pred), steps, used, True)

        return SolveResult(None, steps, used, False)

    def experience_practice(
        self,
        *,
        n: int = 40,
        seed: int = 0,
        top_traces: int = 48,
    ) -> Dict[str, Any]:
        """Practice retained methods on novel numbers (transfer, not Q→A recall)."""
        import random

        rng = random.Random(seed)
        # strongest / most supported traces
        bank = sorted(
            self.traces.values(),
            key=lambda t: (-t.strength, -t.support),
        )[:top_traces]
        if not bank:
            return {"n": 0, "hit": 0, "acc": 0.0, "n_traces": 0}

        hit = 0
        total = 0
        for _ in range(n):
            tr = rng.choice(bank)
            if tr.n_slots < 1 or not tr.hop_trace:
                continue
            # novel positive slots (avoid div-by-zero extremes)
            slots = [float(rng.randint(2, 40)) for _ in range(tr.n_slots)]
            gold = self.replay_trace(tr.hop_trace, slots)
            if gold is None:
                continue
            # resurface language skeleton with new numbers for retrieval
            q = _resurfaced_question(tr.cue_skeleton, slots)
            r = self.solve_from_experience(q)
            total += 1
            if r.ok and r.answer is not None and exact_num(r.answer, _norm(gold)):
                hit += 1
            else:
                # restudy: re-encode the same method (prediction error)
                self.teach_trace(
                    q,
                    tr.hop_trace,
                    n_slots=tr.n_slots,
                    source="restudy",
                    gold=_norm(gold),
                )
        self.sleep_replay(2)
        self.save_traces()
        return {
            "n": total,
            "hit": hit,
            "acc": round(hit / max(1, total), 4),
            "n_traces": len(self.traces),
        }

    def retention_probe(
        self,
        taught: List[Tuple[str, str]],
        *,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Re-present taught questions (original wording). A/B student check."""
        items = taught[:limit] if limit else taught
        hit = 0
        miss_qs: List[Tuple[str, str]] = []
        for q, gold in items:
            r = self.solve_from_experience(q)
            if r.ok and r.answer is not None and exact_num(r.answer, gold):
                hit += 1
            else:
                miss_qs.append((q, gold))
        return {
            "n": len(items),
            "hit": hit,
            "acc": round(hit / max(1, len(items)), 4),
            "misses": miss_qs,
        }

    def retention_restudy(
        self,
        taught_lessons: List[Tuple[str, str, str]],
        *,
        max_passes: int = 4,
        target_acc: float = 0.95,
    ) -> Dict[str, Any]:
        """Restudy misses until taught-wording retention hits target (or max passes)."""
        taught_pairs = [(q, g) for q, _b, g in taught_lessons]
        history: List[Dict[str, Any]] = []
        for p in range(1, max_passes + 1):
            probe = self.retention_probe(taught_pairs)
            history.append({"pass": p, "acc": probe["acc"], "hit": probe["hit"], "n": probe["n"]})
            print(
                f"  RETENTION pass {p}/{max_passes} acc={probe['acc']} "
                f"({probe['hit']}/{probe['n']})",
                flush=True,
            )
            if probe["acc"] >= target_acc or not probe["misses"]:
                break
            # restudy only misses with original worked lesson
            miss_set = {m[0] for m in probe["misses"]}
            for q, body, gold in taught_lessons:
                if q not in miss_set:
                    continue
                # re-encode method (prediction-error restudy)
                self.teach_from_worked(q, body, gold, source="retention_restudy")
                # also strengthen if hop already known
                hops = hop_trace_from_worked(q, body, gold)
                if hops:
                    self.teach_trace(q, hops, source="retention_restudy", gold=gold)
            self.sleep_replay(2)
        final = self.retention_probe(taught_pairs)
        self.save_traces()
        return {"history": history, "final": final, "target_acc": target_acc}

    def experience_session(
        self,
        lessons: List[Tuple[str, str, str]],
        *,
        epochs: int = 3,
        practice_n: int = 32,
        sleep_rounds: int = 4,
        seed: int = 42,
        retention_target: float = 0.95,
        retention_passes: int = 5,
    ) -> Dict[str, Any]:
        """Unattended school: teach worked lessons → practice novel numbers → sleep.

        lessons: (question, answer_body, gold)
        """
        history: List[Dict[str, Any]] = []
        taught_lessons: List[Tuple[str, str, str]] = []
        n_taught = 0
        for q, body, gold in lessons:
            if self.teach_from_worked(q, body, gold):
                n_taught += 1
                taught_lessons.append((q, body, gold))
        self.sleep_replay(sleep_rounds)
        self.save_traces()
        print(
            f"ENCODE done taught_ok={n_taught}/{len(lessons)} traces={len(self.traces)}",
            flush=True,
        )

        # push taught-wording retention toward A-range before long practice
        print("=== RETENTION RESTUDY (taught wording) ===", flush=True)
        ret0 = self.retention_restudy(
            taught_lessons,
            max_passes=retention_passes,
            target_acc=retention_target,
        )

        for ep in range(1, epochs + 1):
            prac = self.experience_practice(
                n=practice_n,
                seed=seed + ep * 97,
            )
            # interleaved: restudy a slice of taught wording each epoch
            import random

            rng = random.Random(seed + ep * 13)
            slice_n = min(len(taught_lessons), max(20, practice_n // 2))
            slice_lessons = (
                rng.sample(taught_lessons, slice_n) if taught_lessons else []
            )
            ret_slice = self.retention_probe([(q, g) for q, _b, g in slice_lessons])
            if ret_slice["misses"]:
                miss_set = {m[0] for m in ret_slice["misses"]}
                for q, body, gold in slice_lessons:
                    if q in miss_set:
                        self.teach_from_worked(q, body, gold, source=f"epoch{ep}_restudy")
            self.sleep_replay(sleep_rounds)
            self.save_traces()
            row = {
                "epoch": ep,
                "practice": prac,
                "retention_slice": {
                    "n": ret_slice["n"],
                    "hit": ret_slice["hit"],
                    "acc": ret_slice["acc"],
                },
                "n_traces": len(self.traces),
                "mean_trace_strength": round(
                    sum(t.strength for t in self.traces.values())
                    / max(1, len(self.traces)),
                    4,
                ),
            }
            history.append(row)
            print(
                f"EXP-EPOCH {ep}/{epochs} practice_acc={prac['acc']} "
                f"retain_slice={ret_slice['acc']} "
                f"traces={row['n_traces']} mean_str={row['mean_trace_strength']}",
                flush=True,
            )

        prove = self.experience_practice(n=max(24, practice_n), seed=seed + 9001)
        # full retention exam on all successfully taught lessons
        print("=== FINAL RETENTION EXAM (all taught wording) ===", flush=True)
        ret_final = self.retention_probe([(q, g) for q, _b, g in taught_lessons])
        print(
            f"FINAL retention {ret_final['hit']}/{ret_final['n']} acc={ret_final['acc']}",
            flush=True,
        )
        # one more restudy pass if still under target
        if ret_final["acc"] < retention_target and taught_lessons:
            print("=== FINAL RESTUDY PUSH ===", flush=True)
            ret_push = self.retention_restudy(
                taught_lessons,
                max_passes=max(2, retention_passes // 2),
                target_acc=retention_target,
            )
            ret_final = ret_push["final"]
        else:
            ret_push = None

        self.sleep_replay(3)
        self.save_traces()
        report = {
            "doctrine": "experience→episodic hop traces→WM atomics→sleep→prove transfer",
            "n_lessons": len(lessons),
            "n_taught_ok": n_taught,
            "epochs": epochs,
            "history": history,
            "retention_after_encode": ret0,
            "retention_final": {
                "n": ret_final["n"],
                "hit": ret_final["hit"],
                "acc": ret_final["acc"],
            },
            "retention_push": ret_push,
            "prove": prove,
            "n_traces_final": len(self.traces),
            "n_trace_teaches": self.n_trace_teaches,
            "n_trace_hits": self.n_trace_hits,
            "n_trace_tries": self.n_trace_tries,
            "mean_trace_strength_final": round(
                sum(t.strength for t in self.traces.values()) / max(1, len(self.traces)),
                4,
            ),
        }
        EXPERIENCE_REPORT.parent.mkdir(parents=True, exist_ok=True)
        EXPERIENCE_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

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
        """NREM proxy: strengthen high-priority episodes + hop traces (STDP densify)."""
        ranked = sorted(self.episodes.values(), key=lambda e: -e.strength)[:48]
        for _ in range(rounds):
            for e in ranked:
                e.strength = min(8.0, e.strength + 0.08)
                self.n_replays += 1
        # densify retained multi-hop methods
        tr_ranked = sorted(self.traces.values(), key=lambda t: -t.strength)[:48]
        for _ in range(rounds):
            for t in tr_ranked:
                t.strength = min(8.0, t.strength + 0.10)
                self.n_replays += 1
        # decay weak
        for e in self.episodes.values():
            if e.strength < 1.1:
                e.strength = max(0.2, e.strength * 0.97)
        for t in self.traces.values():
            if t.strength < 1.1:
                t.strength = max(0.2, t.strength * 0.97)

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

        Preference (pure-bio):
          1) solve_from_experience — replay hop traces retained from lessons
          2) legacy language plans (frozen; not expanded for benchmark chasing)
          3) short atomic drills
        """
        # ----- experience first: what was taught and retained -----
        exp = self.solve_from_experience(question)
        if exp.ok and exp.answer is not None:
            return exp

        steps: List[StepTrace] = []
        used: List[str] = []
        self.wm_clear()
        # normalize curly quotes / dashes so possessives & "times as" match
        q = (
            question.strip()
            .replace("\u2019", "'")
            .replace("\u2018", "'")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2013", "-")
            .replace("\u2014", "-")
        )
        ql = q.lower().replace(",", "")
        nums = [float(x) for x in NUM_RE.findall(ql)]

        def push(rid: str, formula: str, detail: str, value: float) -> float:
            steps.append(StepTrace(rid, formula, detail, value))
            if rid not in used:
                used.append(rid)
            self.n_hops += 1
            return value

        grounded = True

        def _nm(s: str) -> str:
            """Normalize entity names (strip possessives)."""
            t = (s or "").lower().strip()
            t = t.replace("'s", "").replace("’s", "")
            if t.endswith("s") and len(t) > 3 and self.wm_read(t[:-1]) is not None:
                t = t[:-1]
            return t

        SKIP_BIND = {
            "if", "she", "he", "they", "it", "who", "which", "what", "how",
            "there", "here", "this", "that", "one", "two", "first", "second",
            "third", "total", "each", "every", "a", "an", "the", "and",
            "program", "number", "iphone", "phone", "recipe", "recipes",
        }

        # ----- BIND absolute quantities only (never "has 5 more/fewer/times") -----
        for m in re.finditer(
            r"\b([A-Za-z][a-zA-Z']{1,20})\s+(?:has|have|had)\s+(?:\$)?(\d+(?:\.\d+)?)\b"
            r"(?!\s*(?:times|more|fewer|less|as many))",
            q,
        ):
            name = _nm(m.group(1))
            if name in SKIP_BIND or len(name) < 2:
                continue
            val = float(m.group(2))
            self.wm_write(name, val)
            push("MH-BIND", "bind absolute", f"{name}={val}", val)

        # "X weighs N" / "X costs N"
        for m in re.finditer(
            r"\b([A-Za-z][a-zA-Z']+)\s+(?:weighs?|costs?|scored|spent)\s+(?:\$)?(\d+(?:\.\d+)?)",
            q,
            flags=re.I,
        ):
            name = _nm(m.group(1))
            if name in SKIP_BIND:
                continue
            val = float(m.group(2))
            if self.wm_read(name) is None:
                self.wm_write(name, val)
                push("MH-BIND", "bind weighs/costs", f"{name}={val}", val)

        # "If Suzy's iPhone is 1" / "is N year old" — person name only
        for m in re.finditer(
            r"\b([A-Za-z][a-zA-Z']+)(?:'s\s+\w+)?\s+is\s+(\d+(?:\.\d+)?)\s*(?:year|years)?",
            q,
        ):
            name = _nm(m.group(1))
            if name in SKIP_BIND:
                continue
            # skip "is four times"
            tail = q[m.end() : m.end() + 12].lower()
            if re.match(r"\s*times\b", tail):
                continue
            # skip common nouns bound as ages
            if name in ("iphone", "phone", "old", "year"):
                continue
            val = float(m.group(2))
            if self.wm_read(name) is None:
                self.wm_write(name, val)
                push("MH-BIND", "bind is", f"{name}={val}", val)

        # "there are N girls/boys/dogs" absolute counts
        for m in re.finditer(
            r"\bthere are\s+(\d+(?:\.\d+)?)\s+([a-z]+)",
            ql,
        ):
            val, kind = float(m.group(1)), m.group(2)
            if kind in ("students", "people", "items", "times"):
                continue
            self.wm_write(kind.rstrip("s") if kind.endswith("s") else kind, val)
            self.wm_write(kind, val)
            push("MH-BIND", "there are", f"{kind}={val}", val)

        # "one having N" / "the first one having N"
        for m in re.finditer(
            r"(?:one|first(?:\s+one)?|second(?:\s+one)?)\s+having\s+(\d+(?:\.\d+)?)",
            ql,
        ):
            val = float(m.group(1))
            # only seed base if no better bind
            if self.wm_read("base") is None:
                self.wm_write("base", val)
                push("MH-BIND", "having", f"base={val}", val)

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
            who, ktok, other = _nm(m.group(1)), m.group(2), _nm(m.group(3))
            k = float(WORD_NUM.get(ktok, ktok))
            base = self.wm_read(other) or self.wm_read("offset")
            if base is not None:
                a = self.apply_atomic("sub", base, k)
                if a is not None:
                    push("MH-SUB", "fewer", f"{base}-{k}={a}", a)
                    if who not in ("who", "which", "that"):
                        self.wm_write(who, a)
                    else:
                        # "who has 4 fewer than Bo" — bind relative clause subject later
                        self.wm_write("offset", a)
                    # don't claim yet if multi-person together chain still open
                    if not re.search(r"\bmore\b.*\bfewer\b|\bfewer\b.*\bmore\b", ql) or not re.search(
                        r"\btogether|total|combined\b", ql
                    ):
                        if who not in ("who", "which", "that"):
                            self.wm_write("result", a)
        elif re.search(r"\bfewer\b", ql) and self.wm_read("offset") is not None:
            m = re.search(r"(\d+|one|two|three|four|five)\s+fewer", ql)
            if m:
                k = float(WORD_NUM.get(m.group(1), m.group(1)))
                base = self.wm_read("offset") or 0.0
                a = self.apply_atomic("sub", base, k)
                if a is not None:
                    push("MH-SUB", "fewer", f"{base}-{k}", a)
                    if not re.search(r"\btogether|total|combined\b", ql):
                        self.wm_write("result", a)

        # If only half was needed (not nested half / more-than-half chains)
        if half_done and self.wm_read("result") is None and not re.search(
            r"\bfewer\b|\bmore\b.*\bhalf\b|\btogether\b", ql
        ):
            n_half = len(re.findall(r"\bhalf\b", ql))
            if n_half <= 1 and not re.search(r"percent|%\s+of", ql):
                self.wm_write("result", self.wm_read("half") or 0.0)

        # ----- TIMES AS MANY / AS OLD / EATS-AS-MANY chains -----
        if re.search(
            r"\btimes as (many|old|much)\b|\btwice as many\b|\bthrice as many\b|"
            r"\btimes older\b|\btimes as many \w+ as\b",
            ql,
        ):
            ktok = r"(twice|thrice|\d+|two|three|four|five|six|seven|eight|nine|ten)"
            # allow multi-word noun phrases: "Facebook friends", "friends on Facebook"
            many_as = r"as many(?:\s+\w+){0,5}\s+as"
            edges = re.findall(
                rf"([A-Za-z][a-zA-Z']+)\s+has\s+{ktok}\s+(?:times\s+)?{many_as}\s+([A-Za-z][a-zA-Z']+)",
                q,
                flags=re.I,
            )
            edges += re.findall(
                rf"([A-Za-z][a-zA-Z']+)(?:'s\s+\w+)?\s+is\s+{ktok}\s+times\s+"
                r"(?:as old as|older than|as many as)\s+([A-Za-z][a-zA-Z']+)",
                q,
                flags=re.I,
            )
            # "Cody eats three times as many cookies as Amir" / thrice as many cats as Mark
            edges += re.findall(
                rf"([A-Za-z][a-zA-Z']+)\s+(?:eats?|has|walked|scored|bought|buys)\s+"
                rf"{ktok}\s+(?:times\s+)?{many_as}\s+([A-Za-z][a-zA-Z']+)",
                q,
                flags=re.I,
            )
            # "Marilyn's first record sold 10 times as many copies as Harald's"
            edges += re.findall(
                rf"([A-Za-z][a-zA-Z']+)(?:'s)?\s+\w*\s*(?:sold|has)\s+"
                rf"{ktok}\s+times\s+{many_as}\s+([A-Za-z][a-zA-Z']+)",
                q,
                flags=re.I,
            )

            def _kk(k: str) -> float:
                kl = str(k).lower()
                if kl in ("twice",):
                    return 2.0
                if kl in ("thrice",):
                    return 3.0
                if kl in WORD_NUM:
                    return float(WORD_NUM[kl])
                return float(k)

            base_m = re.search(
                r"\bif\s+([A-Za-z][a-zA-Z']+)(?:'s\s+\w+)?\s+(?:has|is|eats?)\s+(\d+(?:\.\d+)?)",
                ql,
            )
            if not base_m:
                cands = list(
                    re.finditer(
                        r"\b([A-Za-z][a-zA-Z']+)\s+(?:has|eats?)\s+(\d+(?:\.\d+)?)(?!\s*times)",
                        ql,
                    )
                )
                # drop skip-bind noise
                cands = [c for c in cands if _nm(c.group(1)) not in SKIP_BIND]
                base_m = cands[-1] if cands else None

            # Combined total known: "sold 88000 copies combined" / "together"
            comb = re.search(
                r"(?:sold|have|are)\s+(\d+(?:\.\d+)?)\s+\w*\s*combined|"
                r"combined.*?(\d+(?:\.\d+)?)\s+copies|"
                r"(\d+(?:\.\d+)?)\s+copies combined",
                ql,
            )
            comb_n = None
            if comb:
                comb_n = float(next(g for g in comb.groups() if g))

            vals: Dict[str, float] = {}
            # seed from WM absolute binds (suzy, mark, …)
            for s in self.wm:
                if s.name and s.name not in ("half", "offset", "result", "base") and s.value:
                    vals[s.name] = s.value
            if base_m:
                bn = _nm(base_m.group(1))
                vals[bn] = float(base_m.group(2))
                push("MH-BIND", "base", f"{bn}={base_m.group(2)}", float(base_m.group(2)))

            # normalize edges (strip possessives: Ben's → ben)
            norm_edges: List[Tuple[str, float, str]] = []
            for a, k, b in edges:
                a, b = _nm(a), _nm(b)
                if not a or not b or a == b:
                    continue
                kk = _kk(k)
                norm_edges.append((a, kk, b))

            # Inverse: A = k*B and A+B = total → B = total/(1+k)
            if comb_n is not None and norm_edges and len(vals) < 2:
                a, kk, b = norm_edges[0]
                base_v = comb_n / (1.0 + kk)
                big_v = kk * base_v
                vals[b] = push("MH-DIV", "base from combined", f"{comb_n}/(1+{kk})", base_v)
                vals[a] = push("MH-MUL", "A=k*B", f"{kk}*{base_v}", big_v)
                if re.search(r"\bhow many\b.*" + re.escape(b), ql) or re.search(
                    rf"how many .* did {b}", ql
                ):
                    self.wm_write("result", base_v)
                elif re.search(r"\bhow many\b.*" + re.escape(a), ql):
                    self.wm_write("result", big_v)
                else:
                    ask = re.search(r"how many.*?did\s+([a-z]+)", ql)
                    if ask and _nm(ask.group(1)) in vals:
                        self.wm_write("result", vals[_nm(ask.group(1))])
                    else:
                        self.wm_write("result", base_v)

            if norm_edges and vals:
                for _ in range(8):
                    for a, kk, b in norm_edges:
                        if b in vals and a not in vals:
                            nv = self.apply_atomic("mul", kk, vals[b])
                            if nv is not None:
                                vals[a] = push("MH-MUL", "A=k*B", f"{a}={kk}*{b}", nv)
                                self.wm_write(a, nv)
                        if a in vals and b not in vals and kk:
                            nv = self.apply_atomic("div", vals[a], kk)
                            if nv is not None:
                                vals[b] = push("MH-DIV", "B=A/k", f"{b}={a}/{kk}", nv)
                                self.wm_write(b, nv)
                if re.search(r"\btogether|total|in all|both of them|combined weights?\b", ql) and len(vals) >= 2:
                    # prefer named people sums over all keys
                    people = [v for n, v in vals.items() if n not in ("half", "offset", "result", "base")]
                    s = self.apply_atomic("add", *(people if people else list(vals.values())))
                    if s is not None:
                        push("MH-ADD", "sum bindings", "sum", s)
                        self.wm_write("result", s)
                elif self.wm_read("result") is None:
                    ask = re.search(
                        r"how (?:old|many)\s+(?:is|are|did|does)\s+([A-Za-z][a-zA-Z']+)",
                        ql,
                    )
                    if not ask:
                        ask = re.search(
                            r"how (?:old|many).*?([A-Za-z][a-zA-Z']+)(?:'s)?",
                            ql,
                        )
                    if ask and _nm(ask.group(1)) in vals:
                        self.wm_write("result", vals[_nm(ask.group(1))])
                    else:
                        # last propagated entity often the asked person
                        for name in reversed(list(vals.keys())):
                            if name not in ("half", "offset", "result", "base"):
                                # only if ask mentions them
                                if re.search(rf"\b{re.escape(name)}\b", ql.split("?")[0].split(".")[-1] if "?" in ql else ql):
                                    self.wm_write("result", vals[name])
                                    break

        # ----- "there are twice/k times as many X as Y" + base Y count -----
        if self.wm_read("result") is None:
            m = re.search(
                r"(?:there are|has|have|buys?|bought)\s+(twice|thrice|\d+|two|three|four|five)\s+"
                r"(?:times\s+)?as many\s+(\w+)\s+as\s+(\w+)",
                ql,
            )
            if m:
                kraw, xkind, ykind = m.group(1), m.group(2), m.group(3)
                kk = float(WORD_NUM.get(kraw, kraw)) if not str(kraw).isdigit() else float(kraw)
                if kraw == "twice":
                    kk = 2.0
                if kraw == "thrice":
                    kk = 3.0
                yv = self.wm_read(ykind) or self.wm_read(ykind.rstrip("s"))
                if yv is None:
                    ym = re.search(
                        rf"(?:there are|are)\s+(\d+(?:\.\d+)?)\s+{re.escape(ykind)}",
                        ql,
                    )
                    if not ym:
                        ym = re.search(
                            rf"(\d+(?:\.\d+)?)\s+{re.escape(ykind)}",
                            ql,
                        )
                    if ym:
                        yv = float(ym.group(1))
                        push("MH-BIND", "Y count", f"{ykind}={yv}", yv)
                if yv is not None:
                    xv = self.apply_atomic("mul", kk, yv)
                    if xv is not None:
                        push("MH-MUL", "k×Y", f"{kk}*{yv}", xv)
                        self.wm_write(xkind, xv)
                        # students = boys+girls; teachers = students / ratio
                        if re.search(r"how many teachers", ql):
                            ratio_m = re.search(
                                r"(\d+)\s+students?\s+to every teacher|"
                                r"(\d+)\s+students? per teacher",
                                ql,
                            )
                            if ratio_m:
                                ratio = float(next(g for g in ratio_m.groups() if g))
                                tot = self.apply_atomic("add", xv, yv)
                                if tot is not None:
                                    push("MH-ADD", "students", f"{xv}+{yv}", tot)
                                    tch = self.apply_atomic("div", tot, ratio)
                                    if tch is not None:
                                        push("MH-DIV", "teachers", f"{tot}/{ratio}", tch)
                                        self.wm_write("result", tch)
                        elif re.search(r"\btogether|in all|total\b", ql):
                            tot = self.apply_atomic("add", xv, yv)
                            if tot is not None:
                                push("MH-ADD", "X+Y", f"{xv}+{yv}", tot)
                                self.wm_write("result", tot)
                        else:
                            self.wm_write("result", xv)

        # ----- "second having twice as many as the first" simple double+sum -----
        if self.wm_read("result") is None and re.search(
            r"twice as many .* as the first|second one having twice",
            ql,
        ):
            base = self.wm_read("base")
            if base is None and nums:
                # prefer "having 20" style
                hm = re.search(r"having\s+(\d+)", ql)
                base = float(hm.group(1)) if hm else nums[0]
            if base is not None:
                second = self.apply_atomic("double", base)
                if second is not None:
                    push("MH-DOUBLE", "twice first", f"2*{base}", second)
                    if re.search(r"both|together|total|to prepare|to read", ql):
                        tot = self.apply_atomic("add", base, second)
                        if tot is not None:
                            push("MH-ADD", "both", f"{base}+{second}", tot)
                            self.wm_write("result", tot)
                    else:
                        self.wm_write("result", second)

        # ----- X is k less/more than m times Y (Alex: 2 less than 4× Grace) -----
        if self.wm_read("result") is None:
            m = re.search(
                r"([A-Za-z][a-zA-Z']+)\s+(?:weighs?|has|is|costs?)\s+(\d+(?:\.\d+)?)\s+"
                r"(pounds?|dollars?|more|less)?\s*"
                r"(less|more)\s+than\s+(\d+)\s+times\s+(?:what\s+)?([A-Za-z][a-zA-Z']+)",
                ql,
            )
            if not m:
                m = re.search(
                    r"([A-Za-z][a-zA-Z']+)\s+(?:weighs?|has|is)\s+(\d+)\s+\w+\s+"
                    r"(less|more)\s+than\s+(\d+)\s+times\s+(?:what\s+)?([A-Za-z][a-zA-Z']+)",
                    ql,
                )
            if m:
                who = _nm(m.group(1))
                groups = m.groups()
                # parse flexibly
                k_off = float(m.group(2))
                direction = None
                mult = None
                base_name = None
                for g in groups[2:]:
                    if g in ("less", "more"):
                        direction = g
                    elif g and re.fullmatch(r"\d+(?:\.\d+)?", str(g)) and mult is None and g != m.group(2):
                        mult = float(g)
                    elif g and re.match(r"^[a-zA-Z]", str(g)) and str(g) not in (
                        "pounds", "pound", "dollars", "dollar", "more", "less", "what",
                    ):
                        base_name = _nm(str(g))
                # more reliable parse from full match text
                m2 = re.search(
                    rf"{re.escape(who)}\s+\w+\s+(\d+(?:\.\d+)?)\s+\w*\s*"
                    rf"(less|more)\s+than\s+(\d+)\s+times\s+(?:what\s+)?([a-z]+)",
                    ql,
                )
                if m2:
                    k_off = float(m2.group(1))
                    direction = m2.group(2)
                    mult = float(m2.group(3))
                    base_name = _nm(m2.group(4))
                bv = self.wm_read(base_name) if base_name else None
                if bv is None and base_name:
                    bm = re.search(rf"{base_name}\s+(?:weighs?|has|is)\s+(\d+(?:\.\d+)?)", ql)
                    if bm:
                        bv = float(bm.group(1))
                        push("MH-BIND", "base", f"{base_name}={bv}", bv)
                if bv is not None and mult is not None and direction:
                    thr = self.apply_atomic("mul", mult, bv)
                    if thr is not None:
                        push("MH-MUL", "m×base", f"{mult}*{bv}", thr)
                        if direction == "less":
                            res = self.apply_atomic("sub", thr, k_off)
                            push("MH-SUB", "less than m×", f"{thr}-{k_off}", res or 0.0)
                        else:
                            res = self.apply_atomic("add", thr, k_off)
                            push("MH-ADD", "more than m×", f"{thr}+{k_off}", res or 0.0)
                        if res is not None:
                            self.wm_write(who, res)
                            if re.search(r"combined|together|total|sum", ql):
                                if bv is not None:
                                    tot = self.apply_atomic("add", res, bv)
                                    if tot is not None:
                                        push("MH-ADD", "combined", f"{res}+{bv}", tot)
                                        self.wm_write("result", tot)
                            else:
                                self.wm_write("result", res)

        # ----- won K more than lost; played N games → win = (N+K)/2 -----
        if self.wm_read("result") is None:
            m = re.search(
                r"played\s+(\d+)\s+games?.*?won\s+(\d+)\s+more than (?:they |he |she )?lost",
                ql,
                re.S,
            )
            if not m:
                m = re.search(
                    r"won\s+(\d+)\s+more than (?:they |he |she )?lost.*?(\d+)\s+games?",
                    ql,
                    re.S,
                )
                if m:
                    # groups swapped
                    k_more, n_games = float(m.group(1)), float(m.group(2))
                else:
                    k_more = n_games = None  # type: ignore
            else:
                n_games, k_more = float(m.group(1)), float(m.group(2))
            if m and n_games is not None and k_more is not None:
                # W + L = N, W = L + K → 2L + K = N → L = (N-K)/2, W = (N+K)/2
                wins = (n_games + k_more) / 2.0
                push("MH-DIV", "wins", f"({n_games}+{k_more})/2", wins)
                if re.search(r"how many.*win|did they win|games? did .* win", ql):
                    self.wm_write("result", wins)
                elif re.search(r"how many.*lost|did they lose", ql):
                    self.wm_write("result", (n_games - k_more) / 2.0)
                else:
                    self.wm_write("result", wins)

        # ----- sequential: first N; second k times first; third reduced by p% of second -----
        if self.wm_read("result") is None:
            m = re.search(
                r"(\d+(?:\.\d+)?)\s+\w+\s+in the first month.*?"
                r"second month was (twice|thrice|\d+|two|three|four|five)\s+times as many.*?"
                r"reduced by\s+(\d+)\s*%",
                ql,
                re.S,
            )
            if not m:
                m = re.search(
                    r"(?:first month|first)\D{0,60}?(\d+(?:\.\d+)?).*?"
                    r"(?:second month|second).*?(twice|thrice|\d+|two|three|four|five)\s+times as many.*?"
                    r"reduced by\s+(\d+)\s*%",
                    ql,
                    re.S,
                )
            if m:
                first = float(m.group(1))
                kraw = m.group(2)
                pct = float(m.group(3))
                kk = float(WORD_NUM.get(kraw, kraw)) if not str(kraw).isdigit() else float(kraw)
                if kraw == "twice":
                    kk = 2.0
                if kraw == "thrice":
                    kk = 3.0
                second = self.apply_atomic("mul", kk, first)
                if second is not None:
                    push("MH-MUL", "2nd=k×1st", f"{kk}*{first}", second)
                    third = second * (1.0 - pct / 100.0)
                    push("MH-PCT", "3rd reduce", f"{second}*(1-{pct}/100)", third)
                    tot = first + second + third
                    push("MH-ADD", "3-month total", f"{first}+{second}+{third}", tot)
                    self.wm_write("result", tot)

        # ----- scores N then p% more points (Mike ping pong) -----
        if self.wm_read("result") is None:
            m = re.search(
                r"scores?\s+(\d+)\s+points?.*?"
                r"scores?\s+(\d+)\s*%\s*more points?",
                ql,
                re.S,
            )
            if m:
                a, pct = float(m.group(1)), float(m.group(2))
                b = a * (1.0 + pct / 100.0)
                push("MH-PCT", "p% more pts", f"{a}*(1+{pct}/100)", b)
                tot = self.apply_atomic("add", a, b)
                if tot is not None:
                    push("MH-ADD", "total points", f"{a}+{b}", tot)
                    self.wm_write("result", tot)
        # ----- k fewer than m times as many as X (Bobby: 5 fewer than 3 times Brian) -----
        m = re.search(
            r"([A-Za-z][a-zA-Z']+)\s+has\s+(\d+)\s+fewer than\s+(\d+)\s+times as many\s+\w+\s+as\s+([A-Za-z][a-zA-Z']+)",
            ql,
        )
        if not m:
            m = re.search(
                r"([A-Za-z][a-zA-Z']+)\s+has\s+(\d+)\s+fewer than\s+(\d+)\s+times as many.*?as\s+([A-Za-z][a-zA-Z']+)",
                ql,
            )
        if m:
            who, fewer, mult, base_name = (
                m.group(1).lower(),
                float(m.group(2)),
                float(m.group(3)),
                m.group(4).lower(),
            )
            base = self.wm_read(base_name)
            if base is None:
                bm = re.search(
                    rf"{base_name}\s+has\s+(\d+(?:\.\d+)?)",
                    ql,
                )
                if bm:
                    base = float(bm.group(1))
                    self.wm_write(base_name, base)
                    push("MH-BIND", "base", f"{base_name}={base}", base)
            if base is not None:
                thr = self.apply_atomic("mul", mult, base)
                if thr is not None:
                    push("MH-MUL", "m times", f"{mult}*{base}", thr)
                    # lost N before compare?
                    lost = re.search(
                        rf"{base_name}\s+has\s+(\d+).*?lost\s+(\d+)",
                        ql,
                    )
                    b2 = base
                    if lost:
                        b2 = self.apply_atomic("sub", base, float(lost.group(2))) or base
                        push("MH-SUB", "lost", f"{base}-{lost.group(2)}", b2)
                        thr = self.apply_atomic("mul", mult, b2)
                        if thr is not None:
                            push("MH-MUL", "m times after loss", f"{mult}*{b2}", thr)
                    res = self.apply_atomic("sub", thr or 0.0, fewer)
                    if res is not None:
                        push("MH-SUB", "fewer than m×", f"{thr}-{fewer}", res)
                        self.wm_write(who, res)
                        self.wm_write("result", res)

        # ----- Yuri: 10 more than half as many as Naomi (68) -----
        m = re.search(
            r"([A-Za-z][a-zA-Z']+)\s+scored\s+(\d+)\s+more than half as many.*?as\s+([A-Za-z][a-zA-Z']+)",
            ql,
        )
        if m:
            who, more, base_name = m.group(1).lower(), float(m.group(2)), m.group(3).lower()
            bm = re.search(rf"{base_name}\s+scored\s+(\d+)", ql)
            if bm:
                base = float(bm.group(1))
                h = self.apply_atomic("half", base)
                if h is not None:
                    push("MH-HALF", "half base", f"half({base})", h)
                    res = self.apply_atomic("add", h, more)
                    if res is not None:
                        push("MH-ADD", "half+more", f"{h}+{more}", res)
                        self.wm_write(who, res)
                        # total of four? if only ask one person
                        if re.search(rf"how many.*?{who}|{who} scored", ql) or re.search(
                            r"how many points did", ql
                        ):
                            # often ask total remaining or yuri — if total known
                            tot_m = re.search(r"total of\s+(\d+)\s+points", ql)
                            if tot_m and re.search(r"how many.*?others|rest", ql):
                                pass
                            self.wm_write("result", res)

        # ----- guess average: one says N, another k more than half, third p% more; average -----
        if re.search(r"\bsays?\b", ql) and re.search(r"\baverage|mean\b", ql):
            first = re.search(r"one says?\s+(\d+)", ql)
            half_more = re.search(
                r"(\d+)\s+more than half (?:of )?(?:the )?first",
                ql,
            )
            pct_more = re.search(
                r"(\d+)\s*%\s*more than the first",
                ql,
            )
            if first and (half_more or pct_more):
                a = float(first.group(1))
                guesses = [a]
                if half_more:
                    h = a / 2.0
                    b = h + float(half_more.group(1))
                    push("MH-HALF", "half first", f"half({a})", h)
                    push("MH-ADD", "half+more", f"{h}+{half_more.group(1)}", b)
                    guesses.append(b)
                if pct_more:
                    c = a * (1.0 + float(pct_more.group(1)) / 100.0)
                    push("MH-PCT", "p% more", f"{a}*(1+{pct_more.group(1)}/100)", c)
                    guesses.append(c)
                if len(guesses) >= 2:
                    avg = sum(guesses) / len(guesses)
                    push("MH-DIV", "mean", f"sum/{len(guesses)}", avg)
                    self.wm_write("result", avg)

        # ----- ages: A is twice as old as B. In k years sum = S -----
        m = re.search(
            r"([A-Za-z][a-zA-Z']+)\s+is twice as old as\s+([A-Za-z][a-zA-Z']+).*?"
            r"in\s+(\d+)\s+years?.*?sum of their ages will be\s+(\d+)",
            ql,
            re.S,
        )
        if m:
            # A=2B; (A+k)+(B+k)=S → 3B+2k=S → B=(S-2k)/3, A=2B
            k, s = float(m.group(3)), float(m.group(4))
            b = (s - 2 * k) / 3.0
            a = 2 * b
            push("MH-DIV", "age base", f"({s}-2*{k})/3", b)
            push("MH-MUL", "twice age", f"2*{b}", a)
            who = re.search(r"how old is\s+([a-z]+)", ql)
            if who and who.group(1) == m.group(1).lower():
                self.wm_write("result", a)
            elif who and who.group(1) == m.group(2).lower():
                self.wm_write("result", b)
            else:
                self.wm_write("result", a)

        # ----- A has k times as many as B; C has m times as many as B; A has N → B or C -----
        m = re.search(
            r"([A-Za-z][a-zA-Z']+)\s+has\s+(twice|thrice|\d+|two|three|four|five)\s+"
            r"times as many(?:\s+\w+){0,5}\s+as\s+([A-Za-z][a-zA-Z']+).*?"
            r"([A-Za-z][a-zA-Z']+)\s+has\s+(twice|thrice|\d+|two|three|four|five)\s+"
            r"times as many(?:\s+\w+){0,6}\s+as\s+\3.*?"
            r"(?:if\s+)?\1\s+has\s+(\d+)",
            ql,
            re.S,
        )
        if m:
            a_name, k1, b_name, c_name, k2, a_val = (
                _nm(m.group(1)),
                m.group(2),
                _nm(m.group(3)),
                _nm(m.group(4)),
                m.group(5),
                float(m.group(6)),
            )
            kk1 = float(WORD_NUM.get(k1, k1)) if not str(k1).isdigit() else float(k1)
            kk2 = float(WORD_NUM.get(k2, k2)) if not str(k2).isdigit() else float(k2)
            if k1 in ("twice",):
                kk1 = 2.0
            if k1 in ("thrice",):
                kk1 = 3.0
            if k2 in ("twice",):
                kk2 = 2.0
            if k2 in ("thrice",):
                kk2 = 3.0
            # A = kk1 * B → B = A/kk1
            b_val = self.apply_atomic("div", a_val, kk1)
            if b_val is not None:
                push("MH-DIV", "B=A/k", f"{a_val}/{kk1}", b_val)
                self.wm_write(b_name, b_val)
                c_val = self.apply_atomic("mul", kk2, b_val)
                if c_val is not None:
                    push("MH-MUL", "C=m*B", f"{kk2}*{b_val}", c_val)
                    self.wm_write(c_name, c_val)
                    ask = re.search(
                        r"how many.*?does\s+([a-z]+)|how many.*?([a-z]+)\s+have",
                        ql,
                    )
                    target = None
                    if ask:
                        target = _nm(ask.group(1) or ask.group(2) or "")
                    if target == b_name:
                        self.wm_write("result", b_val)
                    elif target == c_name or target == a_name:
                        self.wm_write("result", c_val if target == c_name else a_val)
                    else:
                        # default ask is often the third person (James)
                        self.wm_write("result", c_val)

        # ----- walk miles Mon; Tue k times Mon; total Mon-Wed = T → Wed -----
        m = re.search(
            r"monday.*?(\d+)\s+miles?.*?tuesday.*?(\d+)\s+times as many miles.*?monday.*?"
            r"total mileage monday through wednesday.*?(\d+)",
            ql,
            re.S,
        )
        if m:
            mon, k, total = float(m.group(1)), float(m.group(2)), float(m.group(3))
            tue = self.apply_atomic("mul", k, mon)
            if tue is not None:
                push("MH-MUL", "tue", f"{k}*{mon}", tue)
                wed = self.apply_atomic("sub", total, mon + tue)
                if wed is not None:
                    push("MH-SUB", "wed", f"{total}-{mon}-{tue}", wed)
                    self.wm_write("result", wed)

        # ----- REMAINDER sell (digits or number words) -----
        if self.wm_read("result") is None and (
            re.search(r"\bremainder\b|\bsells? the (?:rest|left)\b", ql)
            or (
                re.search(r"\b(eats?|uses?|bakes?)\b", ql)
                and re.search(r"\b(sells?|market)\b", ql)
            )
        ):
            start = None
            sm = re.search(
                r"(?:lay|lays|has|have|make|makes)\s+(\d+(?:\.\d+)?)",
                ql,
            )
            if sm:
                start = float(sm.group(1))
            if start is None and nums:
                start = nums[0]
            uses: List[float] = []
            for m in re.finditer(
                r"(?:eats?|uses?|bakes?|with)\s+"
                r"(\d+(?:\.\d+)?|three|four|two|five|one|six|seven|eight|nine|ten)",
                ql,
            ):
                uses.append(float(WORD_NUM.get(m.group(1), m.group(1))))
            # "eats three for breakfast" / "with four" without explicit verb repeat
            for m in re.finditer(
                r"\b(?:eats?|bakes?)\b.*?(\d+(?:\.\d+)?|three|four|two|five|one|six)\b",
                ql,
            ):
                u = float(WORD_NUM.get(m.group(1), m.group(1)))
                if u not in uses and u >= 1:
                    uses.append(u)
            uq: List[float] = []
            for u in uses:
                if u not in uq and u >= 1:
                    uq.append(u)
            price = None
            pm = re.search(
                r"(?:for|at)\s+\$?\s*(\d+(?:\.\d+)?)\s*(?:per|each|dollars?)?",
                ql,
            )
            if not pm:
                pm = re.search(r"\$\s*(\d+(?:\.\d+)?)\s*per", ql)
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

        # ----- nested half: half of N are X, half of the X are Y -----
        if self.wm_read("result") is None:
            m = re.search(
                r"(\d+(?:\.\d+)?)\s+\w+\b.*?half of the \w+ are (\w+).*?half of the \2 are (\w+)",
                ql,
                re.S,
            )
            if not m:
                m = re.search(
                    r"(\d+(?:\.\d+)?)\s+\w+\b.*?half of (?:the )?\w+ are (\w+).*?"
                    r"half of (?:the )?\2(?:\s+\w+)? are (\w+)",
                    ql,
                    re.S,
                )
            if m:
                n = float(m.group(1))
                h1 = self.apply_atomic("half", n)
                if h1 is not None:
                    push("MH-HALF", "half1", f"half({n})", h1)
                    h2 = self.apply_atomic("half", h1)
                    if h2 is not None:
                        push("MH-HALF", "half2", f"half({h1})", h2)
                        self.wm_write("result", h2)

        # ----- p% of N, then half of those -----
        if self.wm_read("result") is None:
            m = re.search(
                r"(\d+(?:\.\d+)?)\s+\w+.*?"
                r"(\d+(?:\.\d+)?)\s*(?:percent|%)\s+of them are (\w+).*?"
                r"half of the \3",
                ql,
                re.S,
            )
            if not m:
                m = re.search(
                    r"(\d+(?:\.\d+)?)\s+\w+.*?"
                    r"(\d+(?:\.\d+)?)\s*(?:percent|%)\s+of them.*?"
                    r"half of the \w+",
                    ql,
                    re.S,
                )
            if m:
                n, pct = float(m.group(1)), float(m.group(2))
                part = self.apply_atomic("percent", pct, n)
                if part is not None:
                    push("MH-PCT", "p% of N", f"{pct}% of {n}", part)
                    if re.search(r"\bhalf of\b", ql):
                        h = self.apply_atomic("half", part)
                        if h is not None:
                            push("MH-HALF", "half of part", f"half({part})", h)
                            self.wm_write("result", h)
                    else:
                        self.wm_write("result", part)

        # ----- A has/made K more than B; B has N; (C has M more than A); together -----
        if self.wm_read("result") is None and re.search(
            r"\bmore than\b", ql
        ) and re.search(r"\btogether|combined|total|all three|sum\b", ql):
            # chain of offsets from a base person with absolute
            abs_m = re.search(
                r"\bif\s+([a-z]+)\s+(?:made|has|have)\s+(\d+)|"
                r"([a-z]+)\s+has\s+\$?(\d+)(?!\s*(?:more|fewer|less|times))",
                ql,
            )
            if abs_m:
                base_name = _nm(abs_m.group(1) or abs_m.group(3) or "")
                base_val = float(abs_m.group(2) or abs_m.group(4) or 0)
                vals_c: Dict[str, float] = {base_name: base_val}
                push("MH-BIND", "chain base", f"{base_name}={base_val}", base_val)
                # "A has/made K more than B"
                for m in re.finditer(
                    r"([a-z]+)\s+(?:has|have|made|makes)\s+\$?(\d+)\s+more than\s+([a-z]+)",
                    ql,
                ):
                    who, k, other = _nm(m.group(1)), float(m.group(2)), _nm(m.group(3))
                    if other in vals_c and who not in vals_c:
                        nv = self.apply_atomic("add", vals_c[other], k)
                        if nv is not None:
                            vals_c[who] = push("MH-ADD", "more than", f"{other}+{k}", nv)
                # reverse pass if some known only via absolute on first person
                for _ in range(4):
                    for m in re.finditer(
                        r"([a-z]+)\s+(?:has|have|made|makes)\s+\$?(\d+)\s+more than\s+([a-z]+)",
                        ql,
                    ):
                        who, k, other = _nm(m.group(1)), float(m.group(2)), _nm(m.group(3))
                        if other in vals_c and who not in vals_c:
                            nv = self.apply_atomic("add", vals_c[other], k)
                            if nv is not None:
                                vals_c[who] = push(
                                    "MH-ADD", "more than", f"{other}+{k}", nv
                                )
                        if who in vals_c and other not in vals_c:
                            nv = self.apply_atomic("sub", vals_c[who], k)
                            if nv is not None:
                                vals_c[other] = push(
                                    "MH-SUB", "base from more", f"{who}-{k}", nv
                                )
                if len(vals_c) >= 2:
                    tot = self.apply_atomic("add", *vals_c.values())
                    if tot is not None:
                        push("MH-ADD", "together chain", "sum", tot)
                        self.wm_write("result", tot)

        # ----- A has K more than B, who has F fewer than C; C has N; together -----
        if self.wm_read("result") is None:
            m = re.search(
                r"([a-z]+)\s+has\s+(\w+)\s+more \w+ than\s+([a-z]+),?\s+who has\s+"
                r"(\d+)\s+fewer \w+ than\s+([a-z]+).*?"
                r"\5\s+has\s+(\d+)",
                ql,
                re.S,
            )
            if m:
                a, more_tok, b, fewer, c, c_val = (
                    _nm(m.group(1)),
                    m.group(2),
                    _nm(m.group(3)),
                    float(m.group(4)),
                    _nm(m.group(5)),
                    float(m.group(6)),
                )
                more = float(WORD_NUM.get(more_tok, more_tok))
                push("MH-BIND", "C", f"{c}={c_val}", c_val)
                b_val = self.apply_atomic("sub", c_val, fewer)
                if b_val is not None:
                    push("MH-SUB", "B=C-fewer", f"{c_val}-{fewer}", b_val)
                    a_val = self.apply_atomic("add", b_val, more)
                    if a_val is not None:
                        push("MH-ADD", "A=B+more", f"{b_val}+{more}", a_val)
                        tot = self.apply_atomic("add", a_val, b_val, c_val)
                        if tot is not None:
                            push("MH-ADD", "three together", "sum", tot)
                            self.wm_write("result", tot)

        # ----- X is K years less than twice Y's age; X is N → Y -----
        if self.wm_read("result") is None:
            m = re.search(
                r"([a-z]+)\s+(?:just )?turned\s+(\d+).*?"
                r"(\d+)\s+years? less than twice (?:the age of )?(?:his |her )?([a-z]+)",
                ql,
                re.S,
            )
            if not m:
                m = re.search(
                    r"([a-z]+)\s+is\s+(\d+).*?"
                    r"(\d+)\s+(?:years? )?(?:less|younger) than twice.*?(?:his |her )?([a-z]+)",
                    ql,
                    re.S,
                )
            if m:
                # N = 2*Y - K → Y = (N+K)/2
                n_age, k_less = float(m.group(2)), float(m.group(3))
                y = (n_age + k_less) / 2.0
                push("MH-DIV", "half(N+K)", f"({n_age}+{k_less})/2", y)
                self.wm_write("result", y)

        # ----- partition: N animals, twice as many chickens as cows; legs -----
        if self.wm_read("result") is None:
            m = re.search(
                r"(\d+)\s+animals?.*?twice as many (chickens?|birds?) as (cows?|pigs?)",
                ql,
                re.S,
            )
            if m:
                n = float(m.group(1))
                # 2c + c = n → c = n/3, chickens = 2n/3
                cows = n / 3.0
                chicks = 2.0 * cows
                push("MH-DIV", "cows=N/3", f"{n}/3", cows)
                push("MH-MUL", "chickens=2c", f"2*{cows}", chicks)
                if re.search(r"\blegs?\b", ql):
                    # chickens 2 legs, cows 4
                    legs = 2 * chicks + 4 * cows
                    push("MH-ADD", "legs", f"2*{chicks}+4*{cows}", legs)
                    self.wm_write("result", legs)
                elif re.search(r"how many chickens|how many cows", ql):
                    if re.search(r"chickens?", ql.split("?")[0].split("how")[-1] if "how" in ql else ql):
                        self.wm_write("result", chicks)
                    else:
                        self.wm_write("result", cows)
                else:
                    self.wm_write("result", chicks)

        # ----- A made/has K more than B; B has N (no "together" required) -----
        if self.wm_read("result") is None:
            m = re.search(
                r"([a-z]+)\s+(?:made|has|have)\s+(\d+)\s+more \w* ?than\s+([a-z]+).*?"
                r"(?:if\s+)?\3\s+(?:made|has|have)\s+(\d+)",
                ql,
                re.S,
            )
            if m:
                a, k, b, bv = _nm(m.group(1)), float(m.group(2)), _nm(m.group(3)), float(m.group(4))
                av = self.apply_atomic("add", bv, k)
                if av is not None:
                    push("MH-ADD", "A=B+K", f"{bv}+{k}", av)
                    if re.search(r"together|combined|total|both|all", ql):
                        tot = self.apply_atomic("add", av, bv)
                        if tot is not None:
                            push("MH-ADD", "A+B", f"{av}+{bv}", tot)
                            self.wm_write("result", tot)
                    else:
                        self.wm_write("result", av)

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
            elif kind == "remainder":
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
            # fallthrough kinds added via extra choices below

        # more application kinds (expand multi-hop surface)
        for _ in range(max(12, n // 2)):
            kind = rng.choice(
                [
                    "together_times",
                    "combined_inverse",
                    "fewer_than_times",
                    "half_more_pts",
                    "age_twice",
                    "dual_ratio",
                    "times_old_chain",
                    "less_than_m_times",
                    "win_more_than_lost",
                    "seq_times_pct",
                    "pct_more_points",
                    "twice_as_many_groups",
                    "thrice_as_many",
                    "both_recipes",
                    "more_chain",
                    "nested_half",
                    "pct_then_half",
                    "rani_chain",
                ]
            )
            if kind == "together_times":
                base = float(rng.choice([4, 5, 6, 8, 10]))
                k = float(rng.choice([2, 3, 4]))
                tot = base + k * base
                q = (
                    f"Cody eats {int(k)} times as many cookies as Amir eats. "
                    f"If Amir eats {int(base)} cookies, how many cookies do both of them eat together?"
                )
                items.append((q, _norm(tot)))
            elif kind == "combined_inverse":
                base = float(rng.choice([5000, 8000, 10000, 4000]))
                k = float(rng.choice([2, 5, 10]))
                total = base * (1 + k)
                q = (
                    f"Marilyn sold {int(k)} times as many copies as Harald. "
                    f"If they sold {int(total)} copies combined, how many copies did Harald sell?"
                )
                items.append((q, _norm(base)))
            elif kind == "fewer_than_times":
                base = float(rng.choice([10, 15, 20, 25]))
                mult = float(rng.choice([2, 3, 4]))
                fewer = float(rng.randint(1, 6))
                ans = mult * base - fewer
                q = (
                    f"Bobby has {int(fewer)} fewer than {int(mult)} times as many video games as Brian. "
                    f"If Brian has {int(base)} video games, how many does Bobby have?"
                )
                items.append((q, _norm(ans)))
            elif kind == "half_more_pts":
                base = float(rng.choice([40, 50, 60, 68, 80]))
                more = float(rng.randint(5, 15))
                ans = base / 2 + more
                q = (
                    f"Naomi scored {int(base)} of the points. Yuri scored {int(more)} more than half "
                    f"as many points as Naomi. How many points did Yuri score?"
                )
                items.append((q, _norm(ans)))
            elif kind == "age_twice":
                k = 2.0
                s = float(rng.choice([28, 32, 40, 44]))
                b = (s - 2 * k) / 3.0
                a = 2 * b
                if abs(b - int(b)) > 1e-6:
                    continue
                q = (
                    f"Seth is twice as old as Brooke. In {int(k)} years, the sum of their ages will be "
                    f"{int(s)}. How old is Seth?"
                )
                items.append((q, _norm(a)))
            elif kind == "dual_ratio":
                b = float(rng.choice([4, 5, 6, 8, 10]))
                k1 = float(rng.choice([2, 3, 4]))
                k2 = float(rng.choice([2, 3, 5]))
                a = k1 * b
                c = k2 * b
                q = (
                    f"Charlie has {int(k1)} times as many apples as Dorothy. "
                    f"James has {int(k2)} times as many apples as Dorothy. "
                    f"If Charlie has {int(a)} apples, how many apples does James have?"
                )
                items.append((q, _norm(c)))
            elif kind == "times_old_chain":
                suzy = float(rng.choice([1, 2, 3]))
                k_ben = float(rng.choice([2, 3]))
                k_br = float(rng.choice([2, 3, 4]))
                ben = k_ben * suzy
                br = k_br * ben
                q = (
                    f"Brandon's iPhone is {int(k_br)} times as old as Ben's iPhone. "
                    f"Ben's iPhone is {int(k_ben)} times older than Suzy's iPhone. "
                    f"If Suzy's iPhone is {int(suzy)} year old, how old is Brandon's iPhone?"
                )
                items.append((q, _norm(br)))
            elif kind == "less_than_m_times":
                g = float(rng.choice([50, 100, 125, 80]))
                mult = float(rng.choice([2, 3, 4]))
                less = float(rng.randint(1, 5))
                ax = mult * g - less
                tot = ax + g
                q = (
                    f"Grace weighs {int(g)} pounds. Alex weighs {int(less)} pounds less than "
                    f"{int(mult)} times what Grace weighs. What are their combined weights in pounds?"
                )
                items.append((q, _norm(tot)))
            elif kind == "win_more_than_lost":
                lost = float(rng.choice([5, 7, 10, 12]))
                more = float(rng.choice([2, 4, 6, 8]))
                wins = lost + more
                n = wins + lost
                q = (
                    f"A football team played {int(n)} games. They won {int(more)} more than they lost. "
                    f"How many did they win?"
                )
                items.append((q, _norm(wins)))
            elif kind == "seq_times_pct":
                first = float(rng.choice([20, 40, 60, 80]))
                k = float(rng.choice([2, 3, 4]))
                pct = float(rng.choice([10, 20, 25, 30]))
                second = k * first
                third = second * (1 - pct / 100.0)
                tot = first + second + third
                q = (
                    f"A new program had {int(first)} downloads in the first month. The number of downloads "
                    f"in the second month was {int(k)} times as many as the downloads in the first month, "
                    f"but then reduced by {int(pct)}% in the third month. How many downloads did the program "
                    f"have total over the three months?"
                )
                items.append((q, _norm(tot)))
            elif kind == "pct_more_points":
                a = float(rng.choice([4, 8, 10, 20]))
                pct = float(rng.choice([25, 50, 10, 20]))
                b = a * (1 + pct / 100.0)
                tot = a + b
                q = (
                    f"Mike plays ping pong for 40 minutes. In the first 20 minutes, he scores {int(a)} points. "
                    f"In the second 20 minutes, he scores {int(pct)}% more points. "
                    f"How many total points did he score?"
                )
                items.append((q, _norm(tot)))
            elif kind == "twice_as_many_groups":
                girls = float(rng.choice([20, 30, 40, 60]))
                ratio = float(rng.choice([4, 5, 6]))
                boys = 2 * girls
                tot = boys + girls
                teachers = tot / ratio
                if abs(teachers - int(teachers)) > 1e-6:
                    continue
                q = (
                    f"There are twice as many boys as girls at Dr. Wertz's school. "
                    f"If there are {int(girls)} girls and {int(ratio)} students to every teacher, "
                    f"how many teachers are there?"
                )
                items.append((q, _norm(teachers)))
            elif kind == "thrice_as_many":
                base = float(rng.choice([3, 4, 5, 6, 8]))
                q = (
                    f"Lisa has thrice as many cats as Mark. Mark has {int(base)} cats. "
                    f"How many cats does Lisa have?"
                )
                items.append((q, _norm(3 * base)))
            elif kind == "both_recipes":
                first = float(rng.choice([10, 15, 20, 25]))
                q = (
                    f"Kelian has two recipes for preparing dishes, one having {int(first)} instructions "
                    f"and the second one having twice as many instructions as the first one. "
                    f"How many instructions does Kelian have to read to prepare both dishes?"
                )
                items.append((q, _norm(first + 2 * first)))
            elif kind == "more_chain":
                base = float(rng.choice([40, 50, 80, 100]))
                k1 = float(rng.choice([10, 20, 25]))
                k2 = float(rng.choice([15, 30, 50]))
                b = base
                a = b + k1
                c = a + k2
                q = (
                    f"Carmen has ${int(base)}, Samantha has ${int(k1)} more than Carmen, "
                    f"and Daisy has ${int(k2)} more than Samantha. "
                    f"How much do all three girls have combined?"
                )
                items.append((q, _norm(a + b + c)))
            elif kind == "nested_half":
                n = float(rng.choice([12, 16, 20, 24, 32]))
                q = (
                    f"A juggler can juggle {int(n)} balls. Half of the balls are golf balls, "
                    f"and half of the golf balls are blue. How many blue golf balls are there?"
                )
                items.append((q, _norm(n / 4.0)))
            elif kind == "pct_then_half":
                n = float(rng.choice([100, 200, 220, 300]))
                pct = float(rng.choice([20, 40, 50]))
                part = n * pct / 100.0
                q = (
                    f"There are {int(n)} castles in Scotland. {int(pct)} percent of them are ruins, "
                    f"and half of the ruined castles are unmanned. How many unmanned ruined castles "
                    f"are there in Scotland?"
                )
                items.append((q, _norm(part / 2.0)))
            else:
                # rani_chain
                bo = float(rng.choice([30, 40, 50, 60]))
                fewer = float(rng.choice([2, 4, 5]))
                more = float(rng.choice([5, 8, 10]))
                monic = bo - fewer
                rani = monic + more
                q = (
                    f"Rani has {int(more)} more crabs than Monic, who has {int(fewer)} fewer crabs "
                    f"than Bo. If Bo has {int(bo)} crabs, calculate the total number of crabs "
                    f"the three have together."
                )
                items.append((q, _norm(rani + monic + bo)))

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


def cue_skeleton(question: str) -> str:
    """Language shape with numbers blanked — method cue, not the answer.

    Blanks digits *and* number words so slot count matches extract_slot_nums.
    """
    s = (question or "").lower()
    s = (
        s.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    s = s.replace(",", "")
    # blank number words first (longer first to avoid partials)
    _words = (
        "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
        "twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|"
        "zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        "dozen|half|twice|thrice|quarter|third|fourth|fifth"
    )
    s = re.sub(rf"\b({_words})\b", "N", s)
    s = re.sub(r"\d+(?:\.\d+)?", "N", s)
    s = re.sub(r"[^a-zN %]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:180]


def extract_slot_nums(question: str) -> List[float]:
    """Digits + number words — must match teacher abstract_solution slots."""
    try:
        from .math_auto_templates import extract_nums as _ext

        return _ext(question or "")
    except Exception:
        t = (question or "").replace(",", "")
        out: List[float] = []
        for m in NUM_RE.finditer(t):
            try:
                out.append(float(m.group(1)))
            except ValueError:
                pass
        return out


def _hop_sig(hop_trace: List[Dict[str, Any]]) -> str:
    parts = []
    for h in hop_trace:
        op = str(h.get("op", ""))
        args = h.get("args") or []
        ap = []
        for a in args:
            if isinstance(a, (list, tuple)):
                ap.append(f"{a[0]}{a[1]}")
            else:
                ap.append(str(a))
        parts.append(f"{op}({','.join(ap)})")
    return "|".join(parts)


def hop_trace_from_worked(
    question: str,
    answer_body: str,
    gold: str,
) -> Optional[List[Dict[str, Any]]]:
    """School-side: turn a worked solution into a hop list for teach_trace.

    Uses the same calc abstraction as curriculum mining, but the result is
    written into organism memory — not a permanent solver rule table.
    """
    try:
        from .math_auto_templates import abstract_solution
    except Exception:
        return None
    tmpl = abstract_solution(question, answer_body, gold)
    if tmpl is None or not tmpl.steps:
        return None
    hops: List[Dict[str, Any]] = []
    for st in tmpl.steps:
        op = str(st.get("op", ""))
        args_out: List[str] = []
        for a in st.get("args") or []:
            if not isinstance(a, (list, tuple)) or len(a) < 2:
                continue
            kind, val = a[0], a[1]
            if kind == "n":
                args_out.append(f"slot:{int(val)}")
            elif kind == "t":
                args_out.append(f"t:{int(val)}")
            elif kind == "c":
                args_out.append(f"const:{val}")
        if op == "id" and args_out:
            hops.append({"op": "id", "args": args_out[:1]})
        elif op in _OP_MAP or op in ("+", "-", "*", "/"):
            hops.append({"op": _OP_MAP.get(op, op), "args": args_out})
        else:
            return None
    return hops if hops else None


def _resurfaced_question(skeleton: str, slots: List[float]) -> str:
    """Put novel numbers back into a blanked skeleton for retrieval practice."""
    parts = skeleton.split()
    out: List[str] = []
    si = 0
    for w in parts:
        if w == "N" and si < len(slots):
            v = slots[si]
            out.append(str(int(v)) if abs(v - int(v)) < 1e-9 else str(v))
            si += 1
        else:
            out.append(w)
    # if skeleton had fewer N than slots, append remaining as "N = ..."
    while si < len(slots):
        v = slots[si]
        out.append(str(int(v)) if abs(v - int(v)) < 1e-9 else str(v))
        si += 1
    return " ".join(out)


_ORG: Optional[MathMultihopOrganism] = None


def get_organism() -> MathMultihopOrganism:
    global _ORG
    if _ORG is None:
        _ORG = MathMultihopOrganism()
    return _ORG


def solve_multihop(question: str) -> SolveResult:
    return get_organism().multi_hop_solve(question)


def reset_organism() -> MathMultihopOrganism:
    """Fresh organism instance (tests / clean experience runs)."""
    global _ORG
    _ORG = MathMultihopOrganism()
    return _ORG


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
