"""GSM8K teach pack — first high-impact external benchmark (grade-school math reasoning).

Why GSM8K first (doctrine):
  • Industry flagship for *emerging* multi-hop arithmetic reasoning in LLMs
  • Literally grade-school math — natural extension of PK→G8, not college MMLU
  • Our cold baseline was ~5% (worst open-answer offender)
  • Solutions already encode pathways: <<expr=value>> steps → teachable hops

Same spirit as open curriculum:
  teach premises + intermediate calc hops + final answer
  hold out test questions
  score final numeric + pathway coverage

  python scripts/run_gsm8k_teach.py
  python scripts/run_gsm8k_teach.py --limit-train 400 --limit-test 100
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paths import DATA

# Sources
DEFAULT_GSM8K = Path(r"D:\training data\gsm8k")
# Outputs
REPO_DIR = DATA / "curriculum" / "gsm8k"
GAME_DIR = Path(r"D:\fsot_training\curriculum\gsm8k")

STEP_RE = re.compile(r"<<([^>=]+)=([^>]+)>>")
FINAL_RE = re.compile(r"####\s*(.+)\s*$", re.MULTILINE)


@dataclass
class Step:
    expr: str
    value: str


@dataclass
class Problem:
    question: str
    answer_final: str
    steps: List[Step] = field(default_factory=list)
    solution_raw: str = ""
    split: str = "train"


def _norm_num(s: str) -> str:
    s = s.strip().replace(",", "").replace("$", "")
    s = s.replace("%", "")
    # fraction leave as-is if /
    if re.fullmatch(r"-?\d+\.0+", s):
        s = s.split(".")[0]
    return s.strip()


def parse_problem(obj: Dict[str, Any], split: str) -> Optional[Problem]:
    q = str(obj.get("question", "")).strip()
    ans = str(obj.get("answer", "")).strip()
    if not q or not ans:
        return None
    m = FINAL_RE.search(ans)
    final = _norm_num(m.group(1)) if m else _norm_num(ans.split("\n")[-1])
    steps: List[Step] = []
    for expr, val in STEP_RE.findall(ans):
        e = expr.strip().replace(" ", "")
        v = _norm_num(val)
        if e and v:
            steps.append(Step(expr=e, value=v))
    return Problem(question=q, answer_final=final, steps=steps, solution_raw=ans, split=split)


def load_split(root: Path, name: str, limit: Optional[int] = None) -> List[Problem]:
    p = root / f"{name}.jsonl"
    if not p.is_file():
        return []
    out: List[Problem] = []
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if limit is not None and len(out) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            pr = parse_problem(o, name)
            if pr:
                out.append(pr)
    return out


def _q_clean(s: str, n: int = 220) -> str:
    s = s.replace("\t", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


def problem_to_bank_rows(pr: Problem, grade: str = "gsm8k") -> List[str]:
    """Pathway teach rows: arithmetic hops + final Q→A."""
    rows: List[str] = []
    # 1) each calc hop as math fact (pathway atom)
    for st in pr.steps:
        # several cue forms for the same hop
        rows.append(f"math\t{grade}\tcalc\t{st.expr}\t{st.value}\n")
        # verbalize simple ops when clear
        m = re.fullmatch(r"(-?\d+\.?\d*)([+\-*/])(-?\d+\.?\d*)", st.expr)
        if m:
            a, op, b = m.group(1), m.group(2), m.group(3)
            opw = {"+": "plus", "-": "minus", "*": "times", "/": "divided by"}.get(op, op)
            rows.append(f"math\t{grade}\tcalc\t{a} {opw} {b}\t{st.value}\n")
    # 2) full question → final (composition target)
    rows.append(f"math\t{grade}\tword\t{_q_clean(pr.question)}\t{pr.answer_final}\n")
    # 3) last hop → final (bridge)
    if pr.steps:
        last = pr.steps[-1]
        rows.append(f"math\t{grade}\tbridge\tlast step {last.expr}\t{pr.answer_final}\n")
        rows.append(f"math\t{grade}\tbridge\tresult of {last.expr}\t{pr.answer_final}\n")
    return rows


def pathway_chain(pr: Problem) -> Dict[str, Any]:
    """Multi-hop chain for claimability-style scoring."""
    hops = []
    for st in pr.steps:
        hops.append({"cue": st.expr, "answer": st.value})
    hops.append({"cue": _q_clean(pr.question, 160), "answer": pr.answer_final})
    return {
        "question": pr.question,
        "final": pr.answer_final,
        "n_hops": len(hops),
        "hops": hops,
    }


# --- retrieval score (same family as grade depth / game_drive) ---

_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "in", "on", "for",
    "and", "or", "what", "which", "who", "how", "many", "do", "does", "did", "you",
    "we", "i", "it", "she", "he", "her", "his", "their", "them", "this", "that", "with",
    "from", "as", "at", "by", "if", "her", "him", "has", "have", "had", "just", "only",
}


def _tokens(s: str) -> List[str]:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s\.\-\+]", " ", s)
    return [t for t in s.split() if t and t not in _STOP]


def build_bank_index(rows: Sequence[str]) -> List[Tuple[set, str]]:
    idx: List[Tuple[set, str]] = []
    for line in rows:
        if line.startswith("#") or not line.strip():
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 5:
            continue
        q, a = parts[3], parts[4]
        idx.append((set(_tokens(q)), _norm_num(a)))
    return idx


def retrieve(q: str, index: List[Tuple[set, str]]) -> str:
    qt = set(_tokens(q))
    if not qt:
        return ""
    best_s, best_a = -1.0, ""
    for toks, ans in index:
        if not toks:
            continue
        inter = len(qt & toks)
        if inter == 0:
            continue
        score = inter / ((len(qt) * len(toks)) ** 0.5 + 1e-9)
        # boost exact expr match
        if q.replace(" ", "") == "".join(sorted(toks)) or q.replace(" ", "") in "".join(toks):
            score += 0.5
        if score > best_s:
            best_s = score
            best_a = ans
    return best_a


def exact_num(pred: str, gold: str) -> bool:
    p, g = _norm_num(pred), _norm_num(gold)
    if not p or not g:
        return False
    if p == g:
        return True
    try:
        return abs(float(p) - float(g)) < 1e-6
    except ValueError:
        return p in g or g in p


def score_final(index: List[Tuple[set, str]], problems: Sequence[Problem]) -> Dict[str, Any]:
    correct = 0
    n = 0
    for pr in problems:
        n += 1
        # try direct question retrieve
        pred = retrieve(pr.question, index)
        # also try last step expr if any
        if not exact_num(pred, pr.answer_final) and pr.steps:
            pred2 = retrieve(pr.steps[-1].expr, index)
            if exact_num(pred2, pr.answer_final):
                pred = pred2
            elif exact_num(pred2, pr.steps[-1].value):
                # pathway: got last hop value — check if equals final
                if exact_num(pred2, pr.answer_final):
                    pred = pred2
        if exact_num(pred, pr.answer_final):
            correct += 1
    return {
        "n": n,
        "correct": correct,
        "accuracy": round(correct / n, 4) if n else 0.0,
        "method": "bank_retrieve_final",
    }


def score_pathways(index: List[Tuple[set, str]], problems: Sequence[Problem]) -> Dict[str, Any]:
    """Fraction of intermediate <<steps>> retrievable + final."""
    hop_ok = 0
    hop_n = 0
    full_ok = 0
    full_n = 0
    for pr in problems:
        full_n += 1
        steps_hit = 0
        for st in pr.steps:
            hop_n += 1
            pred = retrieve(st.expr, index)
            if exact_num(pred, st.value):
                hop_ok += 1
                steps_hit += 1
            else:
                # try verbal form
                pred2 = retrieve(st.expr.replace("*", " times ").replace("/", " divided by "), index)
                if exact_num(pred2, st.value):
                    hop_ok += 1
                    steps_hit += 1
        fin = retrieve(pr.question, index)
        fin_ok = exact_num(fin, pr.answer_final)
        if fin_ok:
            hop_ok += 1
        hop_n += 1
        # full pathway claimable if all steps + final
        if pr.steps and steps_hit == len(pr.steps) and fin_ok:
            full_ok += 1
        elif not pr.steps and fin_ok:
            full_ok += 1
    return {
        "hop_n": hop_n,
        "hop_correct": hop_ok,
        "hop_accuracy": round(hop_ok / hop_n, 4) if hop_n else 0.0,
        "full_pathway_n": full_n,
        "full_pathway_correct": full_ok,
        "full_pathway_accuracy": round(full_ok / full_n, 4) if full_n else 0.0,
        "method": "pathway_hops_plus_final",
    }


def build_pack(
    gsm8k_root: Path = DEFAULT_GSM8K,
    limit_train: int = 500,
    limit_test: int = 150,
    out_dirs: Optional[Sequence[Path]] = None,
) -> Dict[str, Any]:
    train = load_split(gsm8k_root, "train", limit_train)
    test = load_split(gsm8k_root, "test", limit_test)
    if not train:
        raise FileNotFoundError(f"No GSM8K train at {gsm8k_root}")

    bank_rows: List[str] = [
        "# domain\tgrade\tkind\tquestion\tanswer\n",
        f"# GSM8K teach pack generated {datetime.now(timezone.utc).isoformat()}\n",
        "# kinds: calc=hop atom, word=full Q, bridge=last-step→final\n",
    ]
    # also harvest unique calc atoms across train (pathway alphabet)
    calc_seen = set()
    for pr in train:
        for st in pr.steps:
            key = (st.expr, st.value)
            if key in calc_seen:
                continue
            calc_seen.add(key)
        bank_rows.extend(problem_to_bank_rows(pr))

    exam_rows: List[str] = [
        "# domain\tgrade\tkind\tquestion\tanswer\n",
        "# GSM8K held-out test questions (final answer only)\n",
    ]
    chains: List[Dict[str, Any]] = []
    for pr in test:
        exam_rows.append(f"math\tgsm8k\tword\t{_q_clean(pr.question)}\t{pr.answer_final}\n")
        chains.append(pathway_chain(pr))

    dirs = list(out_dirs) if out_dirs else [REPO_DIR, GAME_DIR]
    written = []
    for d in dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / "bank.tsv").write_text("".join(bank_rows), encoding="utf-8")
            (d / "exam.tsv").write_text("".join(exam_rows), encoding="utf-8")
            (d / "pathways.jsonl").write_text(
                "\n".join(json.dumps(c, ensure_ascii=False) for c in chains) + "\n",
                encoding="utf-8",
            )
            written.append(str(d))
        except OSError as e:
            print(f"skip write {d}: {e}")

    # index from bank (skip headers)
    index = build_bank_index(bank_rows)

    # baselines
    cold_index: List[Tuple[set, str]] = []  # empty = cold
    cold_final = score_final(cold_index, test)
    cold_path = score_pathways(cold_index, test)

    taught_final = score_final(index, test)
    taught_path = score_pathways(index, test)
    # also score train self (sanity)
    train_self = score_final(index, train[: min(80, len(train))])

    # lift
    lift = {
        "final_acc_delta": round(taught_final["accuracy"] - cold_final["accuracy"], 4),
        "hop_acc_delta": round(taught_path["hop_accuracy"] - cold_path["hop_accuracy"], 4),
        "pathway_acc_delta": round(
            taught_path["full_pathway_accuracy"] - cold_path["full_pathway_accuracy"], 4
        ),
    }

    man = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": "GSM8K",
        "why_first": (
            "Flagship LLM multi-hop math reasoning; grade-school domain; "
            "worst open-answer baseline; pathways in <<expr=val>> solutions"
        ),
        "source": str(gsm8k_root),
        "n_train_problems": len(train),
        "n_test_problems": len(test),
        "n_bank_rows": len([r for r in bank_rows if r and not r.startswith("#")]),
        "n_unique_calc_atoms": len(calc_seen),
        "n_exam_rows": len([r for r in exam_rows if r and not r.startswith("#")]),
        "written_dirs": written,
        "cold": {"final": cold_final, "pathways": cold_path},
        "after_teach": {"final": taught_final, "pathways": taught_path, "train_self": train_self},
        "lift": lift,
        "pass_hints": {
            "final_target": 0.20,
            "hop_target": 0.50,
            "note": "Climb toward LLM-reported GSM8K ranges gradually; hop mastery first",
        },
        "next_benchmarks_after_gsm8k": [
            "bbh (hard multi-hop reasoning)",
            "arc_challenge (science reasoning)",
            "hellaswag (commonsense)",
            "mmlu (broad knowledge — later)",
        ],
    }

    for d in dirs:
        try:
            if d.is_dir():
                (d / "MANIFEST.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
                (d / "REPORT.md").write_text(render_report(man), encoding="utf-8")
        except OSError:
            pass

    # monorepo results mirror
    res = DATA / "results"
    if res.is_dir():
        (res / "GSM8K_TEACH.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
        (res / "GSM8K_TEACH.md").write_text(render_report(man), encoding="utf-8")

    # emergent observe-only
    try:
        from .game_drive_bench import log_emergent

        events = []
        if lift["final_acc_delta"] > 0.05:
            events.append(
                {
                    "type": "gsm8k_teach_lift",
                    "final_delta": lift["final_acc_delta"],
                    "after_acc": taught_final["accuracy"],
                }
            )
        if taught_path["hop_accuracy"] >= 0.5:
            events.append(
                {
                    "type": "gsm8k_pathway_hop_mastery_signal",
                    "hop_accuracy": taught_path["hop_accuracy"],
                }
            )
        if taught_final["accuracy"] >= 0.15:
            events.append(
                {
                    "type": "gsm8k_emerging_final_solve",
                    "accuracy": taught_final["accuracy"],
                    "note": "still early; watch climb",
                }
            )
        log_emergent(
            source="curriculum_gsm8k",
            signals={
                "events": events,
                "after_teach": man["after_teach"],
                "lift": lift,
                "n_train": len(train),
                "n_test": len(test),
            },
            note="GSM8K teach pack; observe only — do not curb",
        )
    except Exception as e:
        man["emergent_log_error"] = str(e)

    return man


def render_report(man: Dict[str, Any]) -> str:
    cold_f = man["cold"]["final"]
    aft_f = man["after_teach"]["final"]
    cold_p = man["cold"]["pathways"]
    aft_p = man["after_teach"]["pathways"]
    lift = man["lift"]
    lines = [
        "# GSM8K teach pack — first external reasoning benchmark",
        "",
        f"Generated: `{man.get('generated_at')}`",
        "",
        f"**Why first:** {man.get('why_first')}",
        "",
        f"Train problems: **{man.get('n_train_problems')}** · Test: **{man.get('n_test_problems')}**  ",
        f"Bank rows: **{man.get('n_bank_rows')}** · Unique calc atoms: **{man.get('n_unique_calc_atoms')}**",
        "",
        "## Scores (bank retrieval + pathways)",
        "",
        "| Phase | Final acc | Hop acc | Full pathway acc |",
        "|-------|----------:|--------:|-----------------:|",
        f"| Cold (no teach) | {cold_f['accuracy']:.3f} | {cold_p['hop_accuracy']:.3f} | {cold_p['full_pathway_accuracy']:.3f} |",
        f"| After teach | **{aft_f['accuracy']:.3f}** | **{aft_p['hop_accuracy']:.3f}** | **{aft_p['full_pathway_accuracy']:.3f}** |",
        f"| Δ lift | {lift['final_acc_delta']:+.3f} | {lift['hop_acc_delta']:+.3f} | {lift['pathway_acc_delta']:+.3f} |",
        "",
        f"Train self-check final: `{man['after_teach']['train_self']}`",
        "",
        "## What was taught",
        "",
        "1. **Calc atoms** — each `<<expr=value>>` hop as math fact (pathway)",
        "2. **Word problems** — full question → final numeric answer",
        "3. **Bridges** — last step → final (composition)",
        "",
        "## Next benchmarks (after GSM8K climbs)",
        "",
    ]
    for x in man.get("next_benchmarks_after_gsm8k") or []:
        lines.append(f"- {x}")
    lines += [
        "",
        "## Files",
        "",
        "```",
        "data/curriculum/gsm8k/bank.tsv",
        "data/curriculum/gsm8k/exam.tsv",
        "data/curriculum/gsm8k/pathways.jsonl",
        "D:/fsot_training/curriculum/gsm8k/  (mirror)",
        "```",
        "",
    ]
    return "\n".join(lines)
