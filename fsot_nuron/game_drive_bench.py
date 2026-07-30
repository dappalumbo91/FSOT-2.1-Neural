"""Game-drive dataset catalog, convert-to-bank apparatus, capability scoreboard.

Training roots (game hard drive):
  D:\\fsot_training          — curriculum + MNIST packs (already wired)
  D:\\training data          — full benchmark / corpus holdings

Doctrine:
  • Convert public Q/A into mind bank.tsv rows (domain/grade/kind/q/a)
  • Score with bank retrieval + optional Zig depth-style overlap (host f64 lab)
  • Never claim LLM-level SOTA without the substrate path
  • Emergent monitor is observe-only (append JSONL; do not curb)

  python scripts/run_game_drive_bench.py --catalog
  python scripts/run_game_drive_bench.py --convert --bench
  python scripts/run_game_drive_bench.py --bench --limit 50
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Roots
# ---------------------------------------------------------------------------

DEFAULT_FSOT_TRAINING = Path(os.environ.get("FSOT_TRAINING_ROOT", r"D:\fsot_training"))
DEFAULT_GAME_DATA = Path(os.environ.get("FSOT_GAME_DATA", r"D:\training data"))
DEFAULT_OUT = DEFAULT_FSOT_TRAINING / "capability"
EMERGENT_LOG = DEFAULT_FSOT_TRAINING / "logs" / "emergent_behavior.jsonl"

# Mind bank schema: domain \t grade \t kind \t question \t answer
BANK_HEADER = "# domain\tgrade\tkind\tquestion\tanswer\n"


@dataclass
class DatasetHit:
    name: str
    path: str
    kind: str
    n_files: int = 0
    size_mb: float = 0.0
    sample_keys: List[str] = field(default_factory=list)
    convertible: bool = False
    notes: str = ""


@dataclass
class BenchItem:
    dataset: str
    question: str
    answer: str
    choices: Optional[List[str]] = None
    subject: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoreRow:
    dataset: str
    n: int
    correct: int
    accuracy: float
    chance: float
    above_chance: bool
    method: str
    notes: str = ""


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

KNOWN_BENCH = {
    "gsm8k": {"kind": "math_word", "convertible": True},
    "mmlu": {"kind": "mcq_multi_subject", "convertible": True},
    "hellaswag": {"kind": "commonsense_mcq", "convertible": True},
    "winogrande": {"kind": "coref_mcq", "convertible": True},
    "truthfulqa": {"kind": "truthful_qa", "convertible": True},
    "bbh": {"kind": "hard_reasoning", "convertible": True},
    "math": {"kind": "competition_math", "convertible": True},
    "humaneval": {"kind": "code", "convertible": False, "notes": "code gen — need code runtime"},
    "ifeval": {"kind": "instruction", "convertible": False, "notes": "instruction following"},
    "squad": {"kind": "extractive_qa", "convertible": True},
    "coqa": {"kind": "conversational_qa", "convertible": True},
    "arc": {"kind": "science_mcq", "convertible": True},
}


def _dir_size_mb(p: Path, cap_files: int = 5000) -> Tuple[int, float]:
    n = 0
    total = 0
    try:
        for f in p.rglob("*"):
            if f.is_file():
                n += 1
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
                if n >= cap_files:
                    break
    except OSError:
        pass
    return n, total / (1024 * 1024)


def _sample_jsonl_keys(path: Path) -> List[str]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            line = f.readline()
        if not line.strip():
            return []
        obj = json.loads(line)
        if isinstance(obj, dict):
            return list(obj.keys())[:12]
    except Exception:
        pass
    return []


def catalog(game_data: Path = DEFAULT_GAME_DATA, training: Path = DEFAULT_FSOT_TRAINING) -> Dict[str, Any]:
    hits: List[DatasetHit] = []

    # training pack
    if training.is_dir():
        n, mb = _dir_size_mb(training)
        hits.append(
            DatasetHit(
                name="fsot_training",
                path=str(training),
                kind="local_pack",
                n_files=n,
                size_mb=round(mb, 2),
                convertible=True,
                notes="curriculum pk_to_g8 + mnist packs",
            )
        )

    # game data root
    if game_data.is_dir():
        for child in sorted(game_data.iterdir(), key=lambda p: p.name.lower()):
            name = child.name
            key = name.lower().replace(" ", "_")
            meta = None
            for k, v in KNOWN_BENCH.items():
                if k in key or key in k:
                    meta = v
                    break
            if child.is_dir():
                n, mb = _dir_size_mb(child)
                sample = []
                for cand in child.rglob("*.jsonl"):
                    sample = _sample_jsonl_keys(cand)
                    break
                hits.append(
                    DatasetHit(
                        name=name,
                        path=str(child),
                        kind=(meta or {}).get("kind", "corpus"),
                        n_files=n,
                        size_mb=round(mb, 2),
                        sample_keys=sample,
                        convertible=bool((meta or {}).get("convertible", False)),
                        notes=(meta or {}).get("notes", ""),
                    )
                )
            elif child.suffix.lower() in {".csv", ".jsonl", ".json", ".tsv"}:
                mb = child.stat().st_size / (1024 * 1024)
                kind = "file"
                if "arc" in key:
                    kind = "science_mcq"
                hits.append(
                    DatasetHit(
                        name=name,
                        path=str(child),
                        kind=kind,
                        n_files=1,
                        size_mb=round(mb, 2),
                        convertible="arc" in key or child.suffix == ".jsonl",
                        notes="root-level file",
                    )
                )

    convertible = [h for h in hits if h.convertible]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fsot_training": str(training),
        "game_data": str(game_data),
        "n_hits": len(hits),
        "n_convertible": len(convertible),
        "hits": [asdict(h) for h in hits],
        "priority_bench": [
            "gsm8k",
            "ARC-Easy",
            "ARC-Challenge",
            "mmlu",
            "hellaswag",
            "winogrande",
            "truthfulqa",
            "bbh",
            "math",
            "fsot_training/curriculum",
        ],
    }


# ---------------------------------------------------------------------------
# Loaders → BenchItem
# ---------------------------------------------------------------------------

def _final_gsm8k_answer(ans: str) -> str:
    # GSM8K: #### 18
    m = re.search(r"####\s*(.+)\s*$", ans.strip())
    if m:
        return m.group(1).strip()
    # fallback last number
    nums = re.findall(r"-?\d+\.?\d*", ans.replace(",", ""))
    return nums[-1] if nums else ans.strip()[:48]


def load_gsm8k(path: Path, limit: int) -> List[BenchItem]:
    items: List[BenchItem] = []
    p = path / "test.jsonl"
    if not p.is_file():
        p = path / "train.jsonl"
    if not p.is_file():
        return items
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(items) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(o.get("question", "")).strip()
            a = _final_gsm8k_answer(str(o.get("answer", "")))
            if q and a:
                items.append(BenchItem("gsm8k", q, a, subject="math"))
    return items


def load_mmlu(path: Path, limit: int) -> List[BenchItem]:
    items: List[BenchItem] = []
    p = path / "test.jsonl"
    if not p.is_file():
        p = path / "validation.jsonl"
    if not p.is_file():
        return items
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(items) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(o.get("question", "")).strip()
            ch = o.get("choices") or []
            if not isinstance(ch, list) or not ch:
                continue
            idx = o.get("answer", 0)
            try:
                idx = int(idx)
            except (TypeError, ValueError):
                idx = 0
            if idx < 0 or idx >= len(ch):
                continue
            a = str(ch[idx]).strip()
            items.append(
                BenchItem(
                    "mmlu",
                    q,
                    a,
                    choices=[str(c) for c in ch],
                    subject=str(o.get("subject", "")),
                )
            )
    return items


def load_hellaswag(path: Path, limit: int) -> List[BenchItem]:
    items: List[BenchItem] = []
    p = path / "validation.jsonl"
    if not p.is_file():
        p = path / "test.jsonl"
    if not p.is_file():
        return items
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(items) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            ctx = str(o.get("context", "")).strip()
            ends = o.get("endings") or []
            lab = o.get("label", "0")
            try:
                li = int(lab)
            except (TypeError, ValueError):
                li = 0
            if not ctx or not ends or li >= len(ends):
                continue
            a = str(ends[li]).strip()
            items.append(
                BenchItem(
                    "hellaswag",
                    ctx,
                    a,
                    choices=[str(e) for e in ends],
                    subject=str(o.get("activity_label", "")),
                )
            )
    return items


def load_winogrande(path: Path, limit: int) -> List[BenchItem]:
    items: List[BenchItem] = []
    p = path / "validation.jsonl"
    if not p.is_file():
        return items
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(items) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            sent = str(o.get("sentence", "")).strip()
            o1, o2 = str(o.get("option1", "")), str(o.get("option2", ""))
            ans = str(o.get("answer", "1")).strip()
            a = o1 if ans == "1" else o2
            if sent and a:
                items.append(
                    BenchItem("winogrande", sent.replace("_", "___"), a, choices=[o1, o2])
                )
    return items


def load_truthfulqa(path: Path, limit: int) -> List[BenchItem]:
    items: List[BenchItem] = []
    p = path / "validation.jsonl"
    if not p.is_file():
        return items
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(items) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(o.get("question", "")).strip()
            a = str(o.get("best_answer", "")).strip()
            if q and a:
                items.append(BenchItem("truthfulqa", q, a, subject="truth"))
    return items


def load_bbh(path: Path, limit: int) -> List[BenchItem]:
    items: List[BenchItem] = []
    p = path / "bbh_mix.jsonl"
    if not p.is_file():
        # any jsonl
        js = list(path.glob("*.jsonl"))
        p = js[0] if js else path
    if not p.is_file():
        return items
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(items) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(o.get("input", o.get("question", ""))).strip()
            a = str(o.get("target", o.get("answer", ""))).strip()
            if q and a:
                items.append(BenchItem("bbh", q, a, subject=str(o.get("task", ""))))
    return items


def load_math(path: Path, limit: int) -> List[BenchItem]:
    items: List[BenchItem] = []
    p = path / "math.jsonl"
    if not p.is_file():
        return items
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(items) >= limit:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = str(o.get("problem", o.get("question", ""))).strip()
            sol = str(o.get("solution", o.get("answer", ""))).strip()
            # crude: last \boxed{...} or last line
            m = re.search(r"\\boxed\{([^}]+)\}", sol)
            a = m.group(1).strip() if m else sol.split("\n")[-1][:64]
            if q and a:
                items.append(BenchItem("math", q[:400], a, subject="competition_math"))
    return items


def load_arc_csv(path: Path, limit: int, name: str) -> List[BenchItem]:
    """ARC CSV: id,question,choices,answerKey — choices may be python-ish."""
    items: List[BenchItem] = []
    if not path.is_file():
        return items
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if len(items) >= limit:
                break
            q = (row.get("question") or "").strip()
            key = (row.get("answerKey") or "").strip()
            # choices column is messy; answerKey is A/B/C/D often
            ch_raw = row.get("choices") or ""
            choices: List[str] = []
            # try extract text': array([...]) style strings in quotes
            texts = re.findall(r"'([^']{2,120})'", ch_raw)
            if not texts:
                texts = re.findall(r'"([^"]{2,120})"', ch_raw)
            choices = texts[:4] if texts else []
            # map answer key
            a = key
            if choices and key in "ABCD" and len(key) == 1:
                idx = ord(key) - ord("A")
                if 0 <= idx < len(choices):
                    a = choices[idx]
            if q and a:
                items.append(BenchItem(name, q, a, choices=choices or None, subject="science"))
    return items


def load_curriculum_bank(path: Path, limit: int) -> List[BenchItem]:
    items: List[BenchItem] = []
    bank = path / "curriculum" / "pk_to_g8" / "bank.tsv"
    if not bank.is_file():
        bank = Path(r"I:\fsot nuron\data\curriculum\pk_to_g8\bank.tsv")
    if not bank.is_file():
        return items
    with bank.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            domain, grade, kind, q, a = parts[0], parts[1], parts[2], parts[3], parts[4]
            items.append(BenchItem("pk_to_g8", q, a, subject=f"{domain}/{grade}/{kind}"))
            if len(items) >= limit:
                break
    return items


def load_all_priority(game_data: Path, training: Path, limit: int) -> Dict[str, List[BenchItem]]:
    out: Dict[str, List[BenchItem]] = {}
    loaders = [
        ("gsm8k", lambda: load_gsm8k(game_data / "gsm8k", limit)),
        ("mmlu", lambda: load_mmlu(game_data / "mmlu", limit)),
        ("hellaswag", lambda: load_hellaswag(game_data / "hellaswag", limit)),
        ("winogrande", lambda: load_winogrande(game_data / "winogrande", limit)),
        ("truthfulqa", lambda: load_truthfulqa(game_data / "truthfulqa", limit)),
        ("bbh", lambda: load_bbh(game_data / "bbh", limit)),
        ("math", lambda: load_math(game_data / "math", limit)),
        ("arc_easy", lambda: load_arc_csv(game_data / "ARC-Easy_test.csv", limit, "arc_easy")),
        ("arc_challenge", lambda: load_arc_csv(game_data / "ARC-Challenge_test.csv", limit, "arc_challenge")),
        ("pk_to_g8", lambda: load_curriculum_bank(training, min(limit, 500))),
    ]
    for name, fn in loaders:
        try:
            items = fn()
            if items:
                out[name] = items
        except Exception as e:
            out[name] = []
            print(f"load fail {name}: {e}")
    return out


# ---------------------------------------------------------------------------
# Convert → bank.tsv
# ---------------------------------------------------------------------------

def items_to_bank_rows(items: Sequence[BenchItem], grade: str = "bench") -> List[str]:
    rows: List[str] = []
    for it in items:
        domain = "math" if it.dataset in ("gsm8k", "math", "bbh") else "science"
        if it.dataset in ("hellaswag", "winogrande", "truthfulqa"):
            domain = "literacy"
        if it.dataset == "mmlu":
            domain = "science"
        if it.dataset == "pk_to_g8":
            domain = (it.subject.split("/")[0] if it.subject else "literacy")
        q = it.question.replace("\t", " ").replace("\n", " ").strip()
        a = it.answer.replace("\t", " ").replace("\n", " ").strip()
        if len(q) > 240:
            q = q[:240]
        if len(a) > 96:
            a = a[:96]
        if not q or not a:
            continue
        # For MCQ, also store "q choice_text" hints
        rows.append(f"{domain}\t{grade}\tfact\t{q}\t{a}\n")
        if it.choices:
            for c in it.choices:
                c2 = c.replace("\t", " ").strip()[:96]
                if c2 and c2 != a:
                    # distractor not written as fact — only correct answer is bank truth
                    pass
    return rows


def write_converted_bank(
    by_ds: Dict[str, List[BenchItem]],
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    bank_path = out_dir / "bench_bank.tsv"
    exam_path = out_dir / "bench_exam.tsv"
    # hold out ~20% as exam by hashing
    bank_rows: List[str] = []
    exam_rows: List[str] = []
    for name, items in by_ds.items():
        for it in items:
            h = int(hashlib.md5(it.question.encode("utf-8", errors="replace")).hexdigest()[:8], 16)
            row_items = items_to_bank_rows([it], grade=f"bench_{name}")
            if not row_items:
                continue
            if h % 5 == 0:
                exam_rows.extend(row_items)
            else:
                bank_rows.extend(row_items)
    with bank_path.open("w", encoding="utf-8") as f:
        f.write(BANK_HEADER)
        f.write(f"# converted from game drive {datetime.now(timezone.utc).isoformat()}\n")
        f.writelines(bank_rows)
    with exam_path.open("w", encoding="utf-8") as f:
        f.write(BANK_HEADER)
        f.write("# held-out exam rows\n")
        f.writelines(exam_rows)
    return bank_path


# ---------------------------------------------------------------------------
# Scoring (host retrieval — mind-compatible, not LLM)
# ---------------------------------------------------------------------------

_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "in", "on", "for",
    "and", "or", "what", "which", "who", "how", "many", "do", "does", "did", "you",
    "we", "i", "it", "its", "this", "that", "with", "from", "as", "at", "by", "if",
}


def _tokens(s: str) -> List[str]:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s\.\-]", " ", s)
    return [t for t in s.split() if t and t not in _STOP and len(t) > 1]


def _norm_ans(s: str) -> str:
    s = s.lower().strip()
    s = s.replace(",", "")
    s = re.sub(r"\s+", " ", s)
    # strip trailing period
    if s.endswith("."):
        s = s[:-1]
    return s


def build_index(items: Sequence[BenchItem]) -> List[Tuple[set, str, BenchItem]]:
    idx = []
    for it in items:
        toks = set(_tokens(it.question))
        idx.append((toks, _norm_ans(it.answer), it))
    return idx


def retrieve_answer(q: str, index: List[Tuple[set, str, BenchItem]], choices: Optional[List[str]] = None) -> str:
    qt = set(_tokens(q))
    if not qt:
        return ""
    best_s = -1.0
    best_a = ""
    for toks, ans, it in index:
        if not toks:
            continue
        inter = len(qt & toks)
        if inter == 0:
            continue
        score = inter / (len(qt) ** 0.5 * len(toks) ** 0.5 + 1e-9)
        if score > best_s:
            best_s = score
            best_a = ans
    if choices:
        # if MCQ, pick choice closest to retrieved or to question tokens
        if best_a:
            for c in choices:
                if _norm_ans(c) == best_a or best_a in _norm_ans(c) or _norm_ans(c) in best_a:
                    return _norm_ans(c)
        # bag overlap with choices
        best_c = ""
        best_cs = -1.0
        for c in choices:
            ct = set(_tokens(c))
            inter = len(qt & ct)
            sc = inter / (len(ct) + 1)
            if sc > best_cs:
                best_cs = sc
                best_c = _norm_ans(c)
        if best_c and best_cs > 0:
            return best_c
    return best_a


def score_dataset(
    name: str,
    train_items: Sequence[BenchItem],
    test_items: Sequence[BenchItem],
) -> ScoreRow:
    index = build_index(train_items)
    correct = 0
    n = 0
    for it in test_items:
        n += 1
        pred = retrieve_answer(it.question, index, it.choices)
        gold = _norm_ans(it.answer)
        ok = False
        if pred and gold:
            if pred == gold or pred in gold or gold in pred:
                ok = True
            # numeric soft
            elif re.fullmatch(r"-?\d+\.?\d*", gold) and re.fullmatch(r"-?\d+\.?\d*", pred):
                try:
                    ok = abs(float(pred) - float(gold)) < 1e-6
                except ValueError:
                    ok = False
        if ok:
            correct += 1
    acc = correct / n if n else 0.0
    # chance estimate
    chance = 0.25
    if test_items and test_items[0].choices:
        chance = 1.0 / max(len(test_items[0].choices), 1)
    elif name == "gsm8k" or name == "math":
        chance = 0.0  # open numeric
    elif name == "pk_to_g8":
        chance = 0.05
    return ScoreRow(
        dataset=name,
        n=n,
        correct=correct,
        accuracy=round(acc, 4),
        chance=round(chance, 4),
        above_chance=acc > chance + 0.02 if chance > 0 else acc > 0.1,
        method="bank_token_overlap_retrieve",
        notes="host retrieval over converted bank; Fixed mind path uses same bank schema",
    )


def run_capability_board(
    game_data: Path = DEFAULT_GAME_DATA,
    training: Path = DEFAULT_FSOT_TRAINING,
    limit: int = 80,
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    out_dir = out_dir or (training / "capability")
    out_dir.mkdir(parents=True, exist_ok=True)

    by_ds = load_all_priority(game_data, training, limit=limit)
    bank_path = write_converted_bank(by_ds, out_dir)

    scores: List[ScoreRow] = []
    for name, items in by_ds.items():
        if len(items) < 4:
            continue
        # split 80/20 deterministically
        train, test = [], []
        for it in items:
            h = int(hashlib.md5(it.question.encode("utf-8", errors="replace")).hexdigest()[:8], 16)
            (test if h % 5 == 0 else train).append(it)
        if not test:
            test = items[: max(1, len(items) // 5)]
            train = items[len(test) :]
        if not train:
            train = items
        scores.append(score_dataset(name, train, test))

    # also score exam against bank if curriculum present
    pk = by_ds.get("pk_to_g8") or []
    if pk:
        # self-retrieval on curriculum is the "already claimed" baseline
        scores.append(score_dataset("pk_to_g8_self", pk, pk[: min(100, len(pk))]))

    board = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "game_data": str(game_data),
        "training": str(training),
        "limit_per_set": limit,
        "bank_path": str(bank_path),
        "n_datasets_loaded": len([k for k, v in by_ds.items() if v]),
        "loaded_counts": {k: len(v) for k, v in by_ds.items()},
        "scores": [asdict(s) for s in scores],
        "summary": {
            "mean_acc": round(sum(s.accuracy for s in scores) / len(scores), 4) if scores else 0,
            "n_above_chance": sum(1 for s in scores if s.above_chance),
            "n_scored": len(scores),
        },
        "doctrine": (
            "Scores are bank-retrieval / overlap capability of the FSOT mind stack "
            "after conversion — not LLM fine-tune SOTA. Curriculum pk_to_g8 is the "
            "straight-A path; external benches map progress toward broader claimability."
        ),
    }

    json_path = out_dir / "CAPABILITY_SCOREBOARD.json"
    md_path = out_dir / "CAPABILITY_SCOREBOARD.md"
    json_path.write_text(json.dumps(board, indent=2), encoding="utf-8")
    md_path.write_text(render_scoreboard_md(board), encoding="utf-8")

    # copy summary into monorepo data/results if present
    mono = Path(__file__).resolve().parents[1] / "data" / "results"
    if mono.is_dir():
        (mono / "GAME_DRIVE_CAPABILITY.json").write_text(json.dumps(board, indent=2), encoding="utf-8")
        (mono / "GAME_DRIVE_CAPABILITY.md").write_text(render_scoreboard_md(board), encoding="utf-8")

    return board


def render_scoreboard_md(board: Dict[str, Any]) -> str:
    lines = [
        "# Game-drive capability scoreboard",
        "",
        f"Generated: `{board.get('generated_at')}`",
        "",
        f"**Game data:** `{board.get('game_data')}`  ",
        f"**Training pack:** `{board.get('training')}`  ",
        f"**Bank:** `{board.get('bank_path')}`",
        "",
        board.get("doctrine", ""),
        "",
        "## Scores (bank retrieval)",
        "",
        "| Dataset | n | correct | acc | chance | above_chance |",
        "|---------|--:|--------:|----:|-------:|:------------:|",
    ]
    for s in board.get("scores") or []:
        lines.append(
            f"| {s['dataset']} | {s['n']} | {s['correct']} | {s['accuracy']:.3f} | "
            f"{s['chance']:.3f} | {'Y' if s['above_chance'] else 'N'} |"
        )
    sm = board.get("summary") or {}
    lines += [
        "",
        f"**Mean acc:** {sm.get('mean_acc')} · **Above chance:** {sm.get('n_above_chance')}/{sm.get('n_scored')}",
        "",
        "## Loaded counts",
        "",
        "```json",
        json.dumps(board.get("loaded_counts") or {}, indent=2),
        "```",
        "",
        "## Next",
        "",
        "- Ingest high-scoring convertible rows into open curriculum climb",
        "- Zig Fixed path: teach bank.tsv → depth/claim/frontier",
        "- Emergent monitor: `logs/emergent_behavior.jsonl` (observe only)",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Emergent behavior monitor (observe only — never curb)
# ---------------------------------------------------------------------------

def log_emergent(
    source: str,
    signals: Dict[str, Any],
    note: str = "",
    log_path: Path = EMERGENT_LOG,
) -> None:
    """Append an observation. Do not filter, dampen, or suppress behavior."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "signals": signals,
        "note": note,
        "policy": "observe_only_no_curb",
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def detect_emergent_from_board(board: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flag interesting capability shifts — not to suppress, only track."""
    events: List[Dict[str, Any]] = []
    for s in board.get("scores") or []:
        if s.get("above_chance") and s.get("accuracy", 0) >= 0.5:
            events.append(
                {
                    "type": "strong_transfer_candidate",
                    "dataset": s["dataset"],
                    "accuracy": s["accuracy"],
                }
            )
        if s.get("dataset") == "pk_to_g8" and s.get("accuracy", 0) >= 0.95:
            events.append({"type": "curriculum_mastery_signal", "accuracy": s["accuracy"]})
        # unexpected: open math any non-zero on pure retrieval
        if s.get("dataset") in ("gsm8k", "math") and s.get("accuracy", 0) > 0.05:
            events.append(
                {
                    "type": "open_math_nontrivial_retrieval",
                    "dataset": s["dataset"],
                    "accuracy": s["accuracy"],
                    "note": "not solving; partial lexical hit — watch if climbs",
                }
            )
    return events


def summarize_emergent(log_path: Path = EMERGENT_LOG, last_n: int = 50) -> Dict[str, Any]:
    if not log_path.is_file():
        return {"n": 0, "types": {}, "recent": []}
    rows = []
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    recent = rows[-last_n:]
    types: Counter = Counter()
    for r in recent:
        for sig in (r.get("signals") or {}).get("events") or []:
            if isinstance(sig, dict) and "type" in sig:
                types[sig["type"]] += 1
        # also top-level type
        if "type" in (r.get("signals") or {}):
            types[r["signals"]["type"]] += 1
    return {
        "n_total": len(rows),
        "n_recent": len(recent),
        "types": dict(types),
        "recent": recent[-10:],
        "policy": "observe_only_no_curb",
    }
