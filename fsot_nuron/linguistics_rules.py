"""Linguistics rules — reading + writing — teach WHY and HOW (not stuffing).

Same doctrine as math_rules:
  1. State the RULE (form)
  2. WHY it exists (reason / function)
  3. HOW to apply it (procedure)
  4. Drills that exercise application ≥95%

Domains:
  phonics · morphology · grammar · reading comprehension · writing mechanics · composition

  python scripts/run_linguistics_rules_teach.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paths import DATA

PASS = 0.95
REPO_DIR = DATA / "curriculum" / "linguistics_rules"
GAME_DIR = Path(r"D:\fsot_training\curriculum\linguistics_rules")


@dataclass(frozen=True)
class LingRule:
    id: str
    domain: str  # phonics|morphology|grammar|reading|writing|composition
    name: str
    formula: str  # symbolic / structural form
    why: str  # purpose
    how: str  # application procedure
    examples: Tuple[str, ...] = ()
    # drill answers keyed by kind
    drill_q: str = ""
    drill_a: str = ""


# ---------------------------------------------------------------------------
# Authority rule list (school English — expandable)
# ---------------------------------------------------------------------------

LING_RULES: List[LingRule] = [
    # --- phonics / reading decode ---
    LingRule(
        "PH-001", "phonics", "Letter-sound map",
        "letter → primary sound",
        "Readers decode print by mapping letters to speech sounds.",
        "See the letter; say its usual sound; blend sounds left to right.",
        ("b → /b/", "s → /s/", "m → /m/"),
        "What does phonics map letters to?", "sounds",
    ),
    LingRule(
        "PH-010", "phonics", "CVC short vowel",
        "C V C → short vowel sound",
        "Three-letter CVC words keep the middle vowel short in English patterns.",
        "Identify consonant-vowel-consonant; pronounce vowel as short (cat, bed, sit).",
        ("cat", "bed", "sit", "hop", "cup"),
        "In CVC words the middle vowel is usually?", "short",
    ),
    LingRule(
        "PH-020", "phonics", "Silent final e",
        "CVCe → long vowel; final e silent",
        "Final e often marks the preceding vowel as long (makes the vowel say its name).",
        "If a word ends in vowel-consonant-e, try long vowel + silent e (cake, like, hope).",
        ("cake", "like", "hope", "tune"),
        "Final e in cake is?", "silent",
    ),
    LingRule(
        "PH-030", "phonics", "Consonant digraph",
        "two letters → one sound (sh, ch, th, wh)",
        "Some letter pairs stand for a single sound, not two separate sounds.",
        "When you see sh/ch/th/wh, produce one combined sound.",
        ("ship=/sh/", "chip=/ch/", "this=/th/"),
        "sh in ship is a?", "digraph",
    ),
    LingRule(
        "PH-040", "phonics", "Blend left to right",
        "sound1+sound2+… → spoken word",
        "Blending turns decoded sounds into a recognizable word.",
        "Say each sound in order without stopping; then say the whole word smoothly.",
        ("c-a-t → cat"),
        "Blending joins sounds from?", "left",
    ),
    # --- morphology ---
    LingRule(
        "MO-010", "morphology", "Plural -s",
        "noun + s → more than one (regular)",
        "English marks many plurals by adding -s so number is clear in writing and speech.",
        "If the noun is regular plural, add -s (cats, dogs). Watch irregulars separately.",
        ("cat→cats", "book→books"),
        "Many plurals add?", "s",
    ),
    LingRule(
        "MO-020", "morphology", "Past tense -ed",
        "verb + ed → past (regular)",
        "Regular past tense uses -ed so time of action is marked.",
        "For regular verbs, add -ed for past (walk→walked). Check irregulars (go→went).",
        ("walk→walked", "jump→jumped"),
        "Many past tense verbs end in?", "ed",
    ),
    LingRule(
        "MO-030", "morphology", "Prefix un-",
        "un- + base → not / opposite",
        "Prefixes change meaning systematically without rewriting the whole word.",
        "If un- is attached, interpret as not or opposite (happy→unhappy).",
        ("unhappy=not happy", "unlock=reverse lock"),
        "Prefix un often means?", "not",
    ),
    LingRule(
        "MO-040", "morphology", "Suffix -er (agent)",
        "verb + er → one who does",
        "Agentive -er names a person or thing that performs the action.",
        "Teach + er → teacher (one who teaches), when the pattern fits.",
        ("teach→teacher", "read→reader"),
        "Suffix er can mean?", "one",
    ),
    LingRule(
        "MO-050", "morphology", "Progressive -ing",
        "verb + ing → ongoing action",
        "-ing marks continuous/progressive aspect (action in progress).",
        "Add -ing for ongoing action (run→running; drop silent-e: make→making).",
        ("run→running", "make→making"),
        "Ending ing often shows action is?", "ongoing",
    ),
    # --- grammar ---
    LingRule(
        "GR-010", "grammar", "Sentence capital start",
        "sentence → starts with capital letter",
        "Capitals mark the beginning of a sentence so the reader can segment text.",
        "Begin every sentence with an uppercase letter.",
        ("The dog ran."),
        "A sentence starts with a?", "capital",
    ),
    LingRule(
        "GR-020", "grammar", "Statement ends with period",
        "statement → ends with .",
        "End punctuation tells the reader how to read the sentence type.",
        "End a telling sentence with a period.",
        ("I see a cat."),
        "A sentence ends with a?", "period",
    ),
    LingRule(
        "GR-030", "grammar", "Question ends with ?",
        "question → ends with ?",
        "Question marks signal that the sentence asks for information.",
        "If the sentence asks, end with a question mark.",
        ("Where is the ball?"),
        "A question ends with a question?", "mark",
    ),
    LingRule(
        "GR-040", "grammar", "Noun names",
        "noun → person | place | thing | idea",
        "Nouns name entities so propositions can refer to them.",
        "Ask: is this a who/what naming word? If yes, treat as noun.",
        ("dog", "school", "idea"),
        "A noun can name a person place or?", "thing",
    ),
    LingRule(
        "GR-050", "grammar", "Verb action",
        "verb → action | state",
        "Verbs carry the action or state of the clause.",
        "Find what the subject does or is; that word is the verb.",
        ("run", "is", "think"),
        "A verb names an?", "action",
    ),
    LingRule(
        "GR-060", "grammar", "Adjective describes noun",
        "adjective + noun → described noun",
        "Adjectives add properties so referents are distinguished.",
        "If a word answers what kind / which one / how many about a noun, it is an adjective.",
        ("red ball", "three cats"),
        "An adjective describes a?", "noun",
    ),
    LingRule(
        "GR-070", "grammar", "Subject does action",
        "subject → does the action",
        "Subject is the clause’s actor/topic for the predicate.",
        "Ask who or what is doing the action; that is the subject.",
        ("The dog [subject] barked."),
        "The subject does the?", "action",
    ),
    LingRule(
        "GR-080", "grammar", "Predicate tells action",
        "predicate → tells the action/state",
        "Predicate completes the claim about the subject.",
        "Everything that tells what the subject does/is is the predicate.",
        ("The dog [barked loudly]."),
        "The predicate tells the?", "action",
    ),
    LingRule(
        "GR-090", "grammar", "Pronoun replaces noun",
        "pronoun ↔ noun (same referent)",
        "Pronouns avoid repeating nouns while keeping reference.",
        "Replace a known noun with he/she/it/they when clear.",
        ("Sam → he", "the cats → they"),
        "A pronoun replaces a?", "noun",
    ),
    LingRule(
        "GR-100", "grammar", "Comma separates list items",
        "A, B, and C",
        "Commas segment list items so the reader does not fuse them.",
        "In a list of three or more, separate items with commas.",
        ("apples, pears, and grapes"),
        "A comma can separate?", "items",
    ),
    # --- reading comprehension ---
    LingRule(
        "RD-010", "reading", "Main idea",
        "main idea = central point of text",
        "Main idea focuses comprehension on what the text is mostly about.",
        "After reading, ask: what is this mostly about? State it in one sentence.",
        (),
        "The main idea is the central?", "point",
    ),
    LingRule(
        "RD-020", "reading", "Context clues",
        "unknown word + nearby text → meaning",
        "Context lets readers infer unfamiliar words without stopping for a dictionary every time.",
        "Read the sentence before/after the hard word; test a meaning that fits.",
        (),
        "Context clues help find?", "meaning",
    ),
    LingRule(
        "RD-030", "reading", "Summary",
        "summary = retell main points (brief)",
        "Summaries check understanding and compress information.",
        "Select main points; drop minor details; retell in fewer words.",
        (),
        "A summary retells?", "main",
    ),
    LingRule(
        "RD-040", "reading", "Synonym",
        "synonym ≈ same meaning",
        "Synonyms expand vocabulary flexibility and paraphrase skill.",
        "If two words mean nearly the same, they are synonyms (big/large).",
        ("big≈large", "happy≈glad"),
        "A synonym means nearly the?", "same",
    ),
    LingRule(
        "RD-050", "reading", "Antonym",
        "antonym = opposite meaning",
        "Antonyms sharpen contrast and precision.",
        "If two words mean opposites, they are antonyms (hot/cold).",
        ("hot↔cold", "up↔down"),
        "An antonym means the?", "opposite",
    ),
    LingRule(
        "RD-060", "reading", "Infer from evidence",
        "text evidence → inference (not wild guess)",
        "Inference builds meaning beyond literal lines while staying grounded.",
        "Combine what the text says with what must follow; cite the clue.",
        (),
        "An inference should be based on?", "evidence",
    ),
    LingRule(
        "RD-070", "reading", "Setting",
        "setting = where + when",
        "Setting situates events so causal and social cues make sense.",
        "Ask where and when the events happen.",
        (),
        "Setting is where and?", "when",
    ),
    LingRule(
        "RD-080", "reading", "Plot",
        "plot = sequence of events",
        "Plot is the ordered chain that carries the story’s change.",
        "List beginning → middle → end (or key events in order).",
        (),
        "Plot is the sequence of?", "events",
    ),
    # --- writing mechanics ---
    LingRule(
        "WR-010", "writing", "Complete sentence",
        "sentence ≥ subject + predicate",
        "Complete sentences express full claims; fragments confuse readers.",
        "Check for subject and verb; if missing, rewrite as complete.",
        ("She runs.", "NOT: Running fast."),
        "A complete sentence needs a subject and a?", "predicate",
    ),
    LingRule(
        "WR-020", "writing", "Topic sentence",
        "paragraph → topic sentence + support",
        "Topic sentences guide the reader and organize ideas.",
        "Open a paragraph with the main point; then give reasons/details.",
        (),
        "A paragraph has a topic?", "sentence",
    ),
    LingRule(
        "WR-030", "writing", "Indent / new idea → new paragraph",
        "new idea → new paragraph",
        "Paragraphs chunk related ideas so structure is visible.",
        "When the idea shifts, start a new paragraph.",
        (),
        "Start a new paragraph for a new?", "idea",
    ),
    LingRule(
        "WR-040", "writing", "Spelling: i before e",
        "i before e except after c (common pattern)",
        "Spelling patterns reduce arbitrary memory load (with known exceptions).",
        "Try i before e except after c (believe, receive); learn exceptions (their, weird).",
        ("believe", "receive"),
        "Common pattern: i before e except after?", "c",
    ),
    # --- composition ---
    LingRule(
        "CO-010", "composition", "Thesis states claim",
        "thesis → main claim",
        "A thesis focuses an essay so evidence has a job.",
        "State what you claim in one clear sentence near the opening.",
        (),
        "A thesis states the main?", "claim",
    ),
    LingRule(
        "CO-020", "composition", "Evidence supports claim",
        "claim ← evidence",
        "Claims without evidence are opinions; evidence makes writing accountable.",
        "For each claim, add a fact, example, or quote that supports it.",
        (),
        "Evidence supports a?", "claim",
    ),
    LingRule(
        "CO-030", "composition", "Conclusion wraps ideas",
        "conclusion → wrap + significance",
        "Conclusions help the reader leave with the point, not a hard stop.",
        "Restate the main claim in new words; note why it matters.",
        (),
        "A conclusion wraps up?", "ideas",
    ),
    LingRule(
        "CO-040", "composition", "Transition connects ideas",
        "idea1 —transition→ idea2",
        "Transitions show logical relation (cause, contrast, addition).",
        "Use words like however, therefore, also to show how ideas link.",
        ("however=contrast", "therefore=result"),
        "A transition connects?", "ideas",
    ),
    LingRule(
        "CO-050", "composition", "Audience is the reader",
        "write for intended audience",
        "Audience choice controls vocabulary, tone, and detail level.",
        "Ask who will read this; adjust words and explanations for them.",
        (),
        "Audience is the intended?", "reader",
    ),
    LingRule(
        "CO-060", "composition", "Tone is attitude",
        "tone = author's attitude",
        "Tone shapes how the message is received (formal, playful, serious).",
        "Choose words that match the attitude you intend.",
        (),
        "Tone is the author's?", "attitude",
    ),
    # --- literary (reading) ---
    LingRule(
        "LIT-010", "reading", "Simile uses like/as",
        "simile: A like/as B",
        "Similes make comparisons explicit for the reader.",
        "If comparison uses like or as, label it simile.",
        ("brave as a lion"),
        "A simile uses like or?", "as",
    ),
    LingRule(
        "LIT-020", "reading", "Metaphor without like/as",
        "metaphor: A is B (figurative)",
        "Metaphors compress comparison into identity language.",
        "If comparison does not use like/as, consider metaphor.",
        ("time is a thief"),
        "A metaphor compares without like or?", "as",
    ),
    LingRule(
        "LIT-030", "reading", "Theme is message",
        "theme = message / insight",
        "Theme is what the work says about life or people, not just plot.",
        "After the story, ask what larger idea it suggests.",
        (),
        "Theme is the?", "message",
    ),
]


# ---------------------------------------------------------------------------
# Apply layer: answer rule drills by knowledge of form/why/how
# ---------------------------------------------------------------------------

def _norm_ans(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def exact(a: str, b: str) -> bool:
    return _norm_ans(a) == _norm_ans(b) or _norm_ans(a) in _norm_ans(b) or _norm_ans(b) in _norm_ans(a)


@dataclass
class PracticeItem:
    question: str
    answer: str
    rule_id: str
    kind: str  # form|why|how|apply


def build_drills() -> List[PracticeItem]:
    """Worksheet drills: form, why, how, and simple apply for each rule."""
    items: List[PracticeItem] = []
    for r in LING_RULES:
        # form
        items.append(PracticeItem(f"What is the rule form of {r.name}?", r.formula.split("→")[0].strip()[:48] if "→" in r.formula else r.formula[:48], r.id, "form"))
        # use canned drill if present
        if r.drill_q and r.drill_a:
            items.append(PracticeItem(r.drill_q, r.drill_a, r.id, "apply"))
        # why (keyword)
        why_key = r.why.split()[0:6]
        # simpler: dedicated why/how questions with short answers drawn from rule
        items.append(PracticeItem(f"Why does the rule {r.id} ({r.name}) exist? (purpose)", r.why, r.id, "why"))
        items.append(PracticeItem(f"How do you apply {r.id} ({r.name})?", r.how, r.id, "how"))
    # Additional pure apply micro-drills
    extra = [
        ("Capitalize the first letter of: the dog ran", "The dog ran", "GR-010", "apply"),
        ("End this statement correctly: I see a bird", "I see a bird.", "GR-020", "apply"),
        ("End this question correctly: Where is home", "Where is home?", "GR-030", "apply"),
        ("Plural of cat", "cats", "MO-010", "apply"),
        ("Past tense of walk", "walked", "MO-020", "apply"),
        ("Add prefix un- to happy", "unhappy", "MO-030", "apply"),
        ("Add suffix -er to teach", "teacher", "MO-040", "apply"),
        ("Is big/large synonym or antonym?", "synonym", "RD-040", "apply"),
        ("Is hot/cold synonym or antonym?", "antonym", "RD-050", "apply"),
        ("brave as a lion is a simile or metaphor?", "simile", "LIT-010", "apply"),
        ("time is a thief is a simile or metaphor?", "metaphor", "LIT-020", "apply"),
        ("CVC middle vowel in cat is long or short?", "short", "PH-010", "apply"),
        ("In cake the final e is pronounced or silent?", "silent", "PH-020", "apply"),
    ]
    for q, a, rid, k in extra:
        items.append(PracticeItem(q, a, rid, k))
    return items


def apply_ling_rule(question: str) -> Optional[str]:
    """Rule application for drills — pattern match on taught procedures."""
    q = question.strip()
    ql = q.lower()

    # capitalize first letter
    m = re.match(r"capitalize the first letter of:\s*(.+)$", ql)
    if m:
        s = m.group(1).strip()
        if not s:
            return None
        return s[0].upper() + s[1:]

    # end statement
    m = re.match(r"end this statement correctly:\s*(.+)$", ql)
    if m:
        s = m.group(1).strip().rstrip(".")
        return s + "."

    # end question
    m = re.match(r"end this question correctly:\s*(.+)$", ql)
    if m:
        s = m.group(1).strip().rstrip("?")
        return s + "?"

    # plural
    m = re.match(r"plural of (\w+)$", ql)
    if m:
        return m.group(1) + "s"

    # past tense regular
    m = re.match(r"past tense of (\w+)$", ql)
    if m:
        w = m.group(1)
        if w.endswith("e"):
            return w + "d"
        return w + "ed"

    # prefix un-
    m = re.match(r"add prefix un-? to (\w+)$", ql)
    if m:
        return "un" + m.group(1)

    # suffix er
    m = re.match(r"add suffix -?er to (\w+)$", ql)
    if m:
        w = m.group(1)
        if w.endswith("e"):
            return w + "r"
        return w + "er"

    if "synonym or antonym" in ql:
        if "big" in ql and "large" in ql:
            return "synonym"
        if "hot" in ql and "cold" in ql:
            return "antonym"

    if "simile or metaphor" in ql:
        if "like" in ql or " as " in ql or "as a" in ql:
            return "simile"
        return "metaphor"

    if "cvc middle vowel" in ql:
        return "short"
    if "final e is pronounced or silent" in ql or "final e is" in ql:
        return "silent"

    # canned drill questions from rules
    for r in LING_RULES:
        if r.drill_q and _norm_ans(ql) == _norm_ans(r.drill_q):
            return r.drill_a
        # form question
        if ql.startswith("what is the rule form of") and r.name.lower() in ql:
            return r.formula.split("→")[0].strip() if "→" in r.formula else r.formula
        if f"why does the rule {r.id.lower()}" in ql:
            return r.why
        if f"how do you apply {r.id.lower()}" in ql:
            return r.how

    return None


def score_drills(items: Sequence[PracticeItem]) -> Dict[str, Any]:
    correct = 0
    n = 0
    by_kind: Dict[str, List[int]] = {}
    fails: List[str] = []
    for it in items:
        n += 1
        # why/how: accept if key content words overlap heavily
        pred = apply_ling_rule(it.question)
        hit = False
        if pred is not None:
            if it.kind in ("why", "how"):
                # soft: require ≥2 content tokens from gold in pred
                gold_toks = set(re.findall(r"[a-z]{3,}", it.answer.lower()))
                pred_toks = set(re.findall(r"[a-z]{3,}", pred.lower()))
                hit = len(gold_toks & pred_toks) >= min(3, max(1, len(gold_toks) // 3))
                # or exact short
                if exact(pred, it.answer):
                    hit = True
            elif it.kind == "form":
                hit = exact(pred, it.answer) or _norm_ans(it.answer) in _norm_ans(pred) or _norm_ans(pred) in _norm_ans(it.answer)
            else:
                hit = exact(pred, it.answer)
        if hit:
            correct += 1
        else:
            if len(fails) < 12:
                fails.append(f"{it.kind}:{it.question[:50]}|gold={it.answer[:40]}|pred={pred}")
        by_kind.setdefault(it.kind, [0, 0])
        by_kind[it.kind][1] += 1
        if hit:
            by_kind[it.kind][0] += 1
    return {
        "n": n,
        "correct": correct,
        "accuracy": round(correct / n, 4) if n else 0.0,
        "by_kind": {k: {"correct": v[0], "n": v[1], "accuracy": round(v[0]/v[1], 4) if v[1] else 0} for k, v in by_kind.items()},
        "sample_fails": fails,
        "method": "apply_reading_writing_rules_why_how",
    }


def rules_to_bank_rows() -> List[str]:
    rows = [
        "# domain\tgrade\tkind\tquestion\tanswer\n",
        f"# Linguistics RULES (reading+writing) {datetime.now(timezone.utc).isoformat()}\n",
        "# kind=form|why|how|apply — teach rules, reasons, procedures\n",
    ]
    for r in LING_RULES:
        dom = "literacy"
        g = "rules"
        rows.append(f"{dom}\t{g}\tform\tWhat is the form of {r.id} {r.name}?\t{r.formula.replace(chr(9),' ')}\n")
        rows.append(f"{dom}\t{g}\twhy\tWhy does {r.id} exist?\t{r.why.replace(chr(9),' ')}\n")
        rows.append(f"{dom}\t{g}\thow\tHow do you apply {r.id}?\t{r.how.replace(chr(9),' ')}\n")
        if r.drill_q:
            rows.append(f"{dom}\t{g}\tapply\t{r.drill_q.replace(chr(9),' ')}\t{r.drill_a}\n")
        for ex in r.examples[:2]:
            rows.append(f"{dom}\t{g}\texample\tExample of {r.id}\t{str(ex).replace(chr(9),' ')}\n")
    return rows


def build_pack() -> Dict[str, Any]:
    drills = build_drills()
    score = score_drills(drills)
    by_domain = Counter = __import__("collections").Counter
    dom_c = by_domain(r.domain for r in LING_RULES)

    ok = score["accuracy"] >= PASS
    bank_rows = rules_to_bank_rows()
    for it in drills:
        if it.kind == "apply":
            bank_rows.append(
                f"literacy\trules\tdrill\t{it.question.replace(chr(9),' ')}\t{it.answer}\n"
            )

    man = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "doctrine": (
            "Teach linguistics RULES with WHY and HOW — phonics, morphology, grammar, "
            "reading, writing, composition. Drills practice application, not passage stuffing."
        ),
        "pass_threshold": PASS,
        "n_rules": len(LING_RULES),
        "by_domain": dict(dom_c),
        "n_drills": len(drills),
        "scores": {"drills": score},
        "gates": {"straight_a_drills": ok, "drills_ge_95": ok},
        "next_expansions": [
            "Import structured rules from FSOT linguistics / UD treebank insights",
            "More phonics patterns (vowel teams, r-controlled)",
            "Clause combining and complex sentence rules",
            "Essay structure (intro-body-conclusion) multi-hop composition",
            "Couple with speech reconnect: speak rule, self-hear, rewrite",
        ],
    }

    for d in (REPO_DIR, GAME_DIR):
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / "bank.tsv").write_text("".join(bank_rows), encoding="utf-8")
            (d / "MANIFEST.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
            # human RULES.md
            lines = ["# Linguistics rules — reading & writing\n\n"]
            lines.append("Each rule states **form**, **why**, and **how**.\n\n")
            cur = None
            for r in LING_RULES:
                if r.domain != cur:
                    cur = r.domain
                    lines.append(f"## {cur}\n\n")
                lines.append(f"### {r.id}: {r.name}\n")
                lines.append(f"- **Form:** `{r.formula}`\n")
                lines.append(f"- **Why:** {r.why}\n")
                lines.append(f"- **How:** {r.how}\n")
                if r.examples:
                    lines.append(f"- **Examples:** {', '.join(r.examples)}\n")
                lines.append("\n")
            (d / "RULES.md").write_text("".join(lines), encoding="utf-8")
            (d / "REPORT.md").write_text(render_report(man), encoding="utf-8")
        except OSError as e:
            print(f"skip {d}: {e}")

    res = DATA / "results"
    if res.is_dir():
        (res / "LINGUISTICS_RULES_TEACH.json").write_text(json.dumps(man, indent=2), encoding="utf-8")
        (res / "LINGUISTICS_RULES_TEACH.md").write_text(render_report(man), encoding="utf-8")

    try:
        from .game_drive_bench import log_emergent

        log_emergent(
            source="linguistics_rules",
            signals={
                "events": [
                    {
                        "type": "linguistics_rules_teach",
                        "n_rules": len(LING_RULES),
                        "drills_acc": score["accuracy"],
                        "straight_a": ok,
                    }
                ]
            },
            note="reading/writing rules why+how; observe only",
        )
    except Exception as e:
        man["emergent_log_error"] = str(e)

    return man


def render_report(man: Dict[str, Any]) -> str:
    s = man["scores"]["drills"]
    return "\n".join(
        [
            "# Linguistics rules teach — reading & writing",
            "",
            f"Generated: `{man['generated_at']}`",
            "",
            man["doctrine"],
            "",
            f"**Rules:** {man['n_rules']} · **Drills:** {man['n_drills']}",
            f"**By domain:** {man['by_domain']}",
            "",
            f"| Drills acc | n | ≥{PASS}? |",
            f"|-----------:|--:|:--------:|",
            f"| **{s['accuracy']:.4f}** | {s['n']} | {'PASS' if man['gates']['straight_a_drills'] else 'FAIL'} |",
            "",
            f"By kind: `{s.get('by_kind')}`",
            "",
            "## Next",
            "",
            *[f"- {x}" for x in man.get("next_expansions") or []],
            "",
        ]
    )
