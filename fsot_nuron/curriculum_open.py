"""
Open PK→G8 curriculum packer — public knowledge through middle school.

Sources (no paywall textbooks required):
  - Arithmetic / mult / div / fractions / ratios / integers (public domain math)
  - Dolch + Fry-style sight words, grammar mechanics (public literacy practice)
  - STEM primer facts by grade band (OER spirit)
  - Digit vision labels 0–9

Outputs:
  data/curriculum/pk_to_g8/{facts,problems,bank,MANIFEST}
  also mirrored to D:/fsot_training/curriculum/pk_to_g8 when that drive exists

bank.tsv: domain \\t grade \\t kind \\t question \\t answer
"""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paths import DATA

# Primary in-repo (always)
CUR_DIR = DATA / "curriculum" / "pk_to_g8"
# Legacy alias still written for older ladder paths
LEGACY_DIR = DATA / "curriculum" / "pk_k_g1"
# Game drive mirror (user request: training data on game hard drive)
GAME_DIR = Path("D:/fsot_training/curriculum/pk_to_g8")

GRADES = [
    "preschool",
    "kindergarten",
    "grade1",
    "grade2",
    "grade3",
    "grade4",
    "grade5",
    "grade6",
    "grade7",
    "grade8",
]

NUM = {
    **{i: w for i, w in enumerate(
        "zero one two three four five six seven eight nine ten "
        "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
    )},
    **{i: f"{i}" for i in range(21, 101)},
}

DOLCH_PREPRIMER = (
    "a and away big blue can come down find for funny go help here i in is it jump "
    "little look make me my not one play red run said see the three to two up we where yellow you"
).split()
DOLCH_PRIMER = (
    "all am are at ate be black brown but came did do eat four get good have he into like "
    "must new no now on our out please pretty ran ride saw say she so soon that there they this "
    "too under want was well went what white who will with yes"
).split()
DOLCH_FIRST = (
    "after again an any as ask by could every fly from give giving had has her him his how just "
    "know let live may of old once open over put round some stop take thank them then think walk "
    "were when"
).split()
# Fry first 100 (public high-frequency words) for G2+ literacy
FRY_100 = (
    "the of and a to in is you that it he was for on are as with his they i at be this have from "
    "or one had by word but not what all were we when your can said there use an each which she do "
    "how their if will up other about out many then them these so some her would make like him into "
    "time has look two more write go see number no way could people my than first water been call who "
    "oil its now find long down day did get come made may part"
).split()

LETTER_STARTS = {
    "a": "apple", "b": "ball", "c": "cat", "d": "dog", "e": "egg", "f": "fish",
    "g": "goat", "h": "hat", "i": "igloo", "j": "jam", "k": "kite", "l": "leaf",
    "m": "moon", "n": "nest", "o": "octopus", "p": "pig", "q": "queen", "r": "rain",
    "s": "sun", "t": "tree", "u": "umbrella", "v": "van", "w": "water", "x": "xray",
    "y": "yarn", "z": "zoo",
}
LETTER_SOUND = {
    "a": "ah", "b": "buh", "c": "kuh", "d": "duh", "e": "eh", "f": "fuh",
    "g": "guh", "h": "huh", "i": "ih", "j": "juh", "k": "kuh", "l": "luh",
    "m": "muh", "n": "nuh", "o": "oh", "p": "puh", "q": "kwuh", "r": "ruh",
    "s": "sss", "t": "tuh", "u": "uh", "v": "vuh", "w": "wuh", "x": "ks",
    "y": "yuh", "z": "zzz",
}

# grade, id, fact, question, answer, alt
SCIENCE: List[Tuple[str, str, str, str, str, str]] = [
    ("preschool", "pk-sky", "The sky is blue on a sunny day.", "sky color", "blue", "color of sky"),
    ("preschool", "pk-grass", "Grass is green.", "grass color", "green", "color of grass"),
    ("preschool", "pk-sun", "The sun is out in the day.", "sun when", "day", "when is sun out"),
    ("preschool", "pk-moon", "The moon is out at night.", "moon when", "night", "when is moon out"),
    ("preschool", "pk-eyes", "We see with our eyes.", "see with", "eyes", "what sees"),
    ("preschool", "pk-ears", "We hear with our ears.", "hear with", "ears", "what hears"),
    ("preschool", "pk-dog", "A dog is an animal.", "dog is", "animal", "is dog animal"),
    ("preschool", "pk-water", "We drink water.", "we drink", "water", "what do we drink"),
    ("kindergarten", "k-plant-sun", "Plants need sun to grow.", "plants need", "sun", "what plants need"),
    ("kindergarten", "k-plant-water", "Plants need water to grow.", "plants drink", "water", "plants water"),
    ("kindergarten", "k-people-water", "People need water to live.", "people need", "water", "what people need"),
    ("kindergarten", "k-stop", "Stop at a red light.", "red light", "stop", "red light do"),
    ("kindergarten", "k-winter", "Winter is cold.", "winter is", "cold", "is winter cold"),
    ("kindergarten", "k-summer", "Summer is hot.", "summer is", "hot", "is summer hot"),
    ("grade1", "g1-earth", "Earth is a planet we live on.", "we live on", "earth", "home planet"),
    ("grade1", "g1-map", "A map shows where places are.", "shows places", "map", "find places tool"),
    ("grade1", "g1-living", "Living things need water.", "living need", "water", "living things need"),
    ("grade1", "g1-ice", "Ice is solid water.", "ice is", "solid", "ice form"),
    ("grade1", "g1-seed", "A seed can grow into a plant.", "seed grows", "plant", "seed becomes"),
    ("grade1", "g1-week", "A week has seven days.", "days in week", "seven", "how many days week"),
    # G2
    ("grade2", "g2-solid", "A solid keeps its shape.", "solid keeps", "shape", "solid property"),
    ("grade2", "g2-liquid", "A liquid takes the shape of its container.", "liquid takes", "shape", "liquid property"),
    ("grade2", "g2-habitat", "A habitat is where an animal lives.", "habitat is", "home", "what is habitat"),
    ("grade2", "g2-push", "A push can move an object.", "push can", "move", "what push does"),
    ("grade2", "g2-pull", "A pull can move an object.", "pull can", "move", "what pull does"),
    ("grade2", "g2-plant-parts", "Roots take in water for a plant.", "roots take", "water", "what roots do"),
    ("grade2", "g2-weather", "Weather is what the air is like outside.", "weather is", "air", "what is weather"),
    # G3
    ("grade3", "g3-force", "A force is a push or a pull.", "force is", "push", "what is force"),
    ("grade3", "g3-magnet", "Magnets attract iron.", "magnet attracts", "iron", "what magnets attract"),
    ("grade3", "g3-life-cycle", "Butterflies have a life cycle with stages.", "butterfly cycle", "stages", "butterfly life"),
    ("grade3", "g3-soil", "Plants grow in soil.", "plants grow in", "soil", "where plants grow"),
    ("grade3", "g3-energy-sun", "The sun is a source of energy.", "sun energy", "energy", "sun is source of"),
    ("grade3", "g3-water-cycle", "Rain is part of the water cycle.", "rain part of", "cycle", "rain belongs to"),
    # G4
    ("grade4", "g4-matter", "Matter is anything that has mass.", "matter has", "mass", "what matter has"),
    ("grade4", "g4-energy", "Energy makes things happen.", "energy makes", "happen", "what energy does"),
    ("grade4", "g4-ecosystem", "An ecosystem is living and nonliving things together.", "ecosystem has", "living", "ecosystem includes"),
    ("grade4", "g4-earthquake", "Earthquakes shake the ground.", "earthquake does", "shake", "what earthquake does"),
    ("grade4", "g4-fossil", "Fossils are remains of old living things.", "fossils are", "remains", "what fossils are"),
    ("grade4", "g4-circuit", "A closed circuit lets electricity flow.", "closed circuit lets", "flow", "circuit allows"),
    # G5
    ("grade5", "g5-gravity", "Gravity pulls objects toward Earth.", "gravity pulls", "earth", "gravity toward"),
    ("grade5", "g5-photosynthesis", "Plants make food using sunlight.", "plants make food with", "sunlight", "photosynthesis needs"),
    ("grade5", "g5-molecule", "Molecules are made of atoms.", "molecules made of", "atoms", "molecule parts"),
    ("grade5", "g5-solar", "Earth orbits the sun.", "earth orbits", "sun", "earth goes around"),
    ("grade5", "g5-food-chain", "A food chain shows who eats whom.", "food chain shows", "eats", "food chain is"),
    ("grade5", "g5-volume", "Volume measures how much space something takes.", "volume measures", "space", "what volume measures"),
    # G6 middle school
    ("grade6", "g6-cell", "The cell is the basic unit of life.", "basic unit of life", "cell", "life unit"),
    ("grade6", "g6-atom", "An atom is a basic unit of matter.", "basic unit of matter", "atom", "matter unit"),
    ("grade6", "g6-ratio", "A ratio compares two quantities.", "ratio compares", "quantities", "what ratio does"),
    ("grade6", "g6-variable", "A variable is a symbol for a number.", "variable is", "symbol", "what is variable"),
    ("grade6", "g6-plate", "Earth's crust is made of plates.", "crust made of", "plates", "earth crust"),
    ("grade6", "g6-kinetic", "Kinetic energy is energy of motion.", "kinetic energy is", "motion", "kinetic means"),
    # G7
    ("grade7", "g7-potential", "Potential energy is stored energy.", "potential energy is", "stored", "potential means"),
    ("grade7", "g7-element", "An element is a pure substance of one atom type.", "element is", "pure", "what is element"),
    ("grade7", "g7-gene", "Genes carry hereditary information.", "genes carry", "information", "what genes carry"),
    ("grade7", "g7-density", "Density is mass divided by volume.", "density is", "mass", "density formula start"),
    ("grade7", "g7-ecosystem-energy", "Energy flows through ecosystems.", "energy flows through", "ecosystems", "energy path"),
    ("grade7", "g7-newton", "A force can change an object's motion.", "force can change", "motion", "force effect"),
    # G8
    ("grade8", "g8-slope", "Slope measures steepness of a line.", "slope measures", "steepness", "what slope measures"),
    ("grade8", "g8-function", "A function maps each input to one output.", "function maps", "input", "function does"),
    ("grade8", "g8-pythagorean", "In a right triangle a squared plus b squared equals c squared.", "right triangle theorem", "pythagorean", "a2 plus b2"),
    ("grade8", "g8-scientific", "Scientific notation writes large numbers using powers of ten.", "scientific notation uses", "powers", "sci notation"),
    ("grade8", "g8-wave", "Waves transfer energy without transferring matter.", "waves transfer", "energy", "what waves transfer"),
    ("grade8", "g8-evolution", "Natural selection helps explain evolution.", "natural selection helps", "evolution", "selection explains"),
    # denser middle-school science
    ("grade5", "g5-mixture", "A mixture combines substances that keep their properties.", "mixture keeps", "properties", "mixture property"),
    ("grade5", "g5-solution", "A solution is a mixture that looks the same throughout.", "solution looks", "same", "solution is"),
    ("grade5", "g5-phase", "Water can change phase with heat.", "phase change needs", "heat", "phase needs"),
    ("grade6", "g6-mass", "Mass is the amount of matter in an object.", "mass is amount of", "matter", "what mass is"),
    ("grade6", "g6-volume", "Volume is the space an object occupies.", "volume is", "space", "what volume is"),
    ("grade6", "g6-hypothesis", "A hypothesis is a testable prediction.", "hypothesis is", "prediction", "what hypothesis is"),
    ("grade6", "g6-control", "A control is the standard for comparison in an experiment.", "control is", "standard", "experiment control"),
    ("grade7", "g7-compound", "A compound is two or more elements chemically combined.", "compound has", "elements", "compound is"),
    ("grade7", "g7-reaction", "A chemical reaction forms new substances.", "reaction forms", "substances", "reaction makes"),
    ("grade7", "g7-velocity", "Velocity is speed with direction.", "velocity includes", "direction", "velocity is"),
    ("grade7", "g7-acceleration", "Acceleration is change in velocity.", "acceleration is change in", "velocity", "what acceleration is"),
    ("grade8", "g8-isotope", "Isotopes are atoms of the same element with different neutrons.", "isotopes differ in", "neutrons", "isotope difference"),
    ("grade8", "g8-periodictable", "The periodic table organizes elements.", "periodic table organizes", "elements", "periodic table"),
    ("grade8", "g8-genetics", "DNA carries genetic instructions.", "dna carries", "instructions", "dna does"),
    ("grade8", "g8-climate", "Climate is long-term weather patterns.", "climate is", "long-term", "what climate is"),
]

RELS: List[Tuple[str, str, str, str, str]] = [
    ("preschool", "sun", "out_in", "day", "sun out_in"),
    ("preschool", "moon", "out_in", "night", "moon out_in"),
    ("preschool", "see", "uses", "eyes", "see uses"),
    ("preschool", "dog", "is_a", "animal", "dog is_a"),
    ("kindergarten", "plant", "needs", "sun", "plant needs"),
    ("kindergarten", "people", "needs", "water", "people needs"),
    ("kindergarten", "red_light", "means", "stop", "red_light means"),
    ("grade1", "earth", "is_a", "planet", "earth is_a"),
    ("grade1", "living", "needs", "water", "living needs"),
    ("grade1", "ice", "is", "solid", "ice is_rel"),
    ("grade2", "solid", "keeps", "shape", "solid keeps_rel"),
    ("grade2", "habitat", "is", "home", "habitat is_rel"),
    ("grade3", "force", "is", "push", "force is_rel"),
    ("grade3", "magnet", "attracts", "iron", "magnet attracts_rel"),
    ("grade4", "matter", "has", "mass", "matter has_rel"),
    ("grade4", "ecosystem", "has", "living", "ecosystem has_rel"),
    ("grade5", "gravity", "pulls", "earth", "gravity pulls_rel"),
    ("grade5", "earth", "orbits", "sun", "earth orbits_rel"),
    ("grade6", "cell", "is", "life", "cell is_rel"),
    ("grade6", "atom", "is", "matter", "atom is_rel"),
    ("grade7", "potential", "is", "stored", "potential is_rel"),
    ("grade7", "force", "changes", "motion", "force changes_rel"),
    ("grade8", "slope", "measures", "steepness", "slope measures_rel"),
    ("grade8", "waves", "transfer", "energy", "waves transfer_rel"),
]


def _kw(*parts: str) -> List[str]:
    out: List[str] = []
    for p in parts:
        for tok in re.findall(r"[A-Za-z0-9']+", p.lower()):
            if tok not in out and len(tok) > 0:
                out.append(tok)
    return out[:8]


def _fact(grade: str, domain: str, fid: str, fact: str, q: str, a: str, alt: str = "") -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "id": fid,
        "grade": grade,
        "domain": domain,
        "fact": fact,
        "question": q,
        "answer": str(a).lower() if str(a).isalpha() else str(a),
        "keywords": _kw(str(a), q, fact),
        "source": "open_curriculum_pk_g8",
    }
    if alt:
        row["alt_q"] = alt
    return row


def _prob(grade: str, domain: str, pid: str, prompt: str, answer: str, kind: str = "problem") -> Dict[str, Any]:
    return {
        "id": pid,
        "grade": grade,
        "domain": domain,
        "prompt": prompt,
        "answer": str(answer),
        "kind": kind,
        "keywords": _kw(str(answer), prompt),
        "source": "open_curriculum_pk_g8",
    }


BankRow = Tuple[str, str, str, str, str]  # domain, grade, kind, q, a


def _put(bank: List[BankRow], domain: str, grade: str, kind: str, q: str, a: str) -> None:
    bank.append((domain, grade, kind, q.strip(), str(a).strip()))


def build_math() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[BankRow]]:
    facts: List[Dict[str, Any]] = []
    problems: List[Dict[str, Any]] = []
    bank: List[BankRow] = []

    def teach(grade: str, q: str, a: Any, kind: str = "fact", fid: str = "") -> None:
        sa = str(a)
        _put(bank, "math", grade, kind, q, sa)
        if kind == "fact":
            facts.append(_fact(grade, "math", fid or f"m-{grade}-{len(facts)}", f"{q} = {sa}", q, sa))
        else:
            problems.append(_prob(grade, "math", fid or f"mp-{len(problems)}", q, sa, kind))

    # Count 0–100 names for small set + after/before
    for n in range(0, 21):
        g = "preschool" if n <= 5 else ("kindergarten" if n <= 10 else "grade1")
        w = NUM[n]
        teach(g, f"number {n}", w, "fact", f"count-{n}")
        teach(g, f"count word {w}", str(n), "fact", f"countw-{n}")
        if n < 20:
            teach(g, f"after {w}", NUM[n + 1], "fact", f"after-{n}")
        if n > 0:
            teach(g, f"before {w}", NUM[n - 1], "fact", f"before-{n}")

    # Add/sub 0–10 (PK–G1 core)
    for a in range(0, 11):
        for b in range(0, 11):
            s = a + b
            if s > 20:
                continue
            g = "preschool" if s <= 5 and max(a, b) <= 3 else ("kindergarten" if s <= 10 else "grade1")
            teach(g, f"{a} plus {b}", NUM.get(s, str(s)), "fact", f"add-{a}-{b}")
            teach(g, f"{a}+{b}", str(s), "problem", f"addp-{a}-{b}")
        for b in range(0, a + 1):
            d = a - b
            g = "preschool" if a <= 5 else ("kindergarten" if a <= 8 else "grade1")
            teach(g, f"{a} minus {b}", NUM.get(d, str(d)), "fact", f"sub-{a}-{b}")
            teach(g, f"{a}-{b}", str(d), "problem", f"subp-{a}-{b}")

    # Make ten
    for a in range(0, 11):
        teach("kindergarten" if a <= 5 else "grade1", f"make ten with {a}", NUM[10 - a], "fact", f"m10-{a}")

    # Place value G1–G2
    for tens in range(1, 10):
        teach("grade1", f"tens in {tens * 10}", str(tens), "fact", f"tens-{tens}")
        teach("grade2", f"{tens} tens equals", str(tens * 10), "fact", f"tenseq-{tens}")

    # Add/sub within 100 (selected systematic) G2
    for a in range(10, 100, 7):
        for b in (1, 5, 10, 12):
            if a + b <= 100:
                teach("grade2", f"{a} plus {b}", str(a + b), "fact", f"g2add-{a}-{b}")
                teach("grade2", f"{a}+{b}", str(a + b), "problem", f"g2addp-{a}-{b}")
            if a - b >= 0:
                teach("grade2", f"{a} minus {b}", str(a - b), "fact", f"g2sub-{a}-{b}")

    # Multiplication tables 0–12 (G3 core, intro G2 for 0–5)
    for a in range(0, 13):
        for b in range(0, 13):
            p = a * b
            if a <= 5 and b <= 5:
                g = "grade2"
            elif a <= 10 and b <= 10:
                g = "grade3"
            else:
                g = "grade4"
            teach(g, f"{a} times {b}", str(p), "fact", f"mul-{a}-{b}")
            teach(g, f"{a}x{b}", str(p), "problem", f"mulp-{a}-{b}")

    # Division facts (inverse of mult where b!=0) G3–G4
    for a in range(0, 11):
        for b in range(1, 11):
            p = a * b
            teach("grade3" if p <= 50 else "grade4", f"{p} divided by {b}", str(a), "fact", f"div-{p}-{b}")
            teach("grade3" if p <= 50 else "grade4", f"{p}/{b}", str(a), "problem", f"divp-{p}-{b}")

    # Fractions G3–G5
    for num, den, name in (
        (1, 2, "half"),
        (1, 3, "third"),
        (1, 4, "fourth"),
        (2, 4, "half"),
        (3, 4, "three-fourths"),
        (1, 5, "fifth"),
        (2, 5, "two-fifths"),
        (1, 10, "tenth"),
    ):
        g = "grade3" if den <= 4 else "grade4"
        teach(g, f"{num}/{den} is", name, "fact", f"frac-{num}-{den}")
        teach(g, f"fraction {num} over {den}", name, "problem", f"fracp-{num}-{den}")

    # Decimals G4–G5
    for d, w in (("0.5", "half"), ("0.25", "fourth"), ("0.1", "tenth"), ("1.5", "one-point-five"),
                 ("0.75", "three-fourths"), ("0.2", "fifth"), ("2.5", "two-point-five")):
        teach("grade4", f"decimal {d} is", w, "fact", f"dec-{d}")
    for a in (0.5, 1.0, 1.5, 2.0, 2.5, 3.25, 4.5, 5.75, 10.1, 12.25):
        for b in (0.25, 0.5, 1.0, 1.5, 2.25):
            s = round(a + b, 2)
            teach("grade5", f"{a} plus {b}", str(s), "fact", f"decadd-{a}-{b}")
            if a >= b:
                teach("grade5", f"{a} minus {b}", str(round(a - b, 2)), "fact", f"decsub-{a}-{b}")
    for a in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20):
        for b in (2, 3, 4, 5, 10):
            teach("grade5", f"{a} times {b} long", str(a * b), "fact", f"g5mul-{a}-{b}")
            if a % b == 0:
                teach("grade5", f"{a} divided by {b} long", str(a // b), "fact", f"g5div-{a}-{b}")

    # Area / perimeter concepts G3–G5
    for l, w in ((2, 3), (4, 5), (6, 7), (10, 10)):
        teach("grade3", f"area {l} by {w}", str(l * w), "fact", f"area-{l}-{w}")
        teach("grade3", f"perimeter {l} by {w}", str(2 * (l + w)), "fact", f"perim-{l}-{w}")

    # G6: ratios, percents, integers, order of ops
    for a, b in ((1, 2), (2, 3), (3, 4), (1, 4), (5, 10)):
        teach("grade6", f"ratio {a} to {b}", f"{a}:{b}", "fact", f"ratio-{a}-{b}")
        teach("grade6", f"{a} out of {b} as percent", str(int(100 * a / b)), "fact", f"pct-{a}-{b}")
    for a in range(-5, 6):
        for b in range(-5, 6):
            teach("grade6", f"integer {a} plus {b}", str(a + b), "fact", f"intadd-{a}-{b}")
            teach("grade6", f"integer {a} minus {b}", str(a - b), "fact", f"intsub-{a}-{b}")
    # simple order: 2+3*4 = 14
    for expr, val in (("2+3*4", 14), ("10-2*3", 4), ("(2+3)*4", 20), ("12/3+2", 6), ("5*2-4", 6)):
        teach("grade6", f"evaluate {expr}", str(val), "fact", f"oo-{expr}")
        teach("grade6", f"compute {expr}", str(val), "problem", f"oop-{expr}")

    # G7: proportions, simple linear, angles, percent applications
    for a in range(1, 9):
        for b in range(1, 9):
            for c in (2, 4, 6, 8, 10, 12):
                if a and (b * c) % a == 0:
                    x = (b * c) // a
                    if 0 < x < 100:
                        teach("grade7", f"proportion {a}/{b} = {c}/x x is", str(x), "fact", f"prop-{a}-{b}-{c}")
    for m in range(-4, 6):
        for x in range(0, 8):
            for b in range(-3, 4):
                teach("grade7", f"linear {m}*x+{b} at x={x}", str(m * x + b), "fact", f"lin-{m}-{x}-{b}")
    for deg, kind in ((90, "right"), (180, "straight"), (45, "acute"), (120, "obtuse"),
                      (30, "acute"), (60, "acute"), (150, "obtuse"), (0, "zero")):
        teach("grade7", f"angle {deg} is", kind, "fact", f"ang-{deg}")
    for p, whole in ((10, 50), (25, 80), (50, 40), (20, 100), (5, 200), (75, 40)):
        teach("grade7", f"{p} percent of {whole}", str(p * whole // 100), "fact", f"pctof-{p}-{whole}")

    # G8: slope, pythagorean triples, powers of 10, simple functions, scientific notation
    for x1 in range(0, 5):
        for y1 in range(0, 5):
            for dx, dy in ((1, 1), (2, 4), (3, 6), (4, 2), (5, 10), (2, 1)):
                x2, y2 = x1 + dx, y1 + dy
                if dx:
                    slope = dy / dx
                    s = str(int(slope)) if slope == int(slope) else str(slope)
                    teach("grade8", f"slope from ({x1},{y1}) to ({x2},{y2})", s, "fact", f"slope-{x1}-{y1}-{x2}-{y2}")
    for a, b, c in ((3, 4, 5), (5, 12, 13), (6, 8, 10), (9, 12, 15), (8, 15, 17), (7, 24, 25)):
        teach("grade8", f"pythagorean {a} {b} hyp", str(c), "fact", f"pyth-{a}-{b}")
        teach("grade8", f"{a}^2+{b}^2", str(a * a + b * b), "problem", f"pythp-{a}-{b}")
    for p in range(0, 9):
        teach("grade8", f"powers of ten {10 ** p}", str(p), "fact", f"pow10-{p}")
        teach("grade8", f"10^{p}", str(10 ** p), "problem", f"pow10p-{p}")
    for m in (1, 2, 3, 4, 5):
        for x in range(0, 10):
            # f(x)=mx+1
            teach("grade8", f"function {m}x+1 at {x}", str(m * x + 1), "fact", f"fn-{m}-{x}")
    for coeff, exp in ((3, 4), (2, 5), (7, 3), (1.5, 2), (4, 6), (9, 1)):
        teach("grade8", f"sci not {coeff} x 10^{exp}", str(coeff * (10 ** int(exp)) if exp == int(exp) else f"{coeff}e{exp}"),
              "fact", f"sci-{coeff}-{exp}")

    # concept labels
    for g, q, a in (
        ("grade1", "add means", "together"),
        ("grade1", "subtract means", "take"),
        ("grade3", "multiply means", "groups"),
        ("grade3", "divide means", "split"),
        ("grade6", "ratio compares", "quantities"),
        ("grade8", "slope measures", "steepness"),
    ):
        teach(g, q, a, "fact")

    return facts, problems, bank


def build_literacy() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[BankRow]]:
    facts: List[Dict[str, Any]] = []
    problems: List[Dict[str, Any]] = []
    bank: List[BankRow] = []

    for letter, word in LETTER_STARTS.items():
        g = "preschool" if letter <= "m" else "kindergarten"
        q = f"letter starts {word}"
        facts.append(_fact(g, "literacy", f"ls-{letter}", f"{letter.upper()} starts {word}.", q, letter, f"what starts {word}"))
        _put(bank, "literacy", g, "fact", q, letter)
        _put(bank, "literacy", g, "fact", f"what starts {word}", letter)
        sound = LETTER_SOUND[letter]
        qs = f"sound of {letter}"
        facts.append(_fact(g, "literacy", f"snd-{letter}", f"Letter {letter} sounds like {sound}.", qs, sound))
        _put(bank, "literacy", g, "fact", qs, sound)

    for g, words in (
        ("preschool", DOLCH_PREPRIMER),
        ("kindergarten", DOLCH_PRIMER),
        ("grade1", DOLCH_FIRST),
    ):
        for w in words:
            wl = w.lower()
            q = f"sight word {wl}"
            facts.append(_fact(g, "literacy", f"dolch-{g}-{wl}", f"{w} is a sight word.", q, wl))
            _put(bank, "literacy", g, "fact", q, wl)
            _put(bank, "literacy", g, "fact", f"read {wl}", wl)

    # Fry 100 split across G2–G4
    for i, w in enumerate(FRY_100):
        g = "grade2" if i < 40 else ("grade3" if i < 70 else "grade4")
        wl = w.lower()
        q = f"fry word {wl}"
        facts.append(_fact(g, "literacy", f"fry-{wl}", f"{w} is a high frequency word.", q, wl))
        _put(bank, "literacy", g, "fact", q, wl)

    grammar = [
        ("grade1", "sentence starts", "capital", "A sentence starts with a capital."),
        ("grade1", "sentence ends", "period", "A sentence ends with a period."),
        ("grade1", "question ends", "mark", "A question ends with a question mark."),
        ("grade2", "noun is", "person", "A noun can name a person place or thing."),
        ("grade2", "verb is", "action", "A verb names an action."),
        ("grade2", "adjective describes", "noun", "An adjective describes a noun."),
        ("grade2", "pronoun replaces", "noun", "A pronoun replaces a noun."),
        ("grade2", "comma can separate", "items", "A comma can separate items in a list."),
        ("grade3", "plural adds", "s", "Many plurals add s."),
        ("grade3", "past tense often ends", "ed", "Many past tense verbs end in ed."),
        ("grade3", "subject does the", "action", "The subject does the action."),
        ("grade3", "predicate tells", "action", "The predicate tells the action."),
        ("grade3", "synonym means", "same", "A synonym means nearly the same."),
        ("grade3", "antonym means", "opposite", "An antonym means the opposite."),
        ("grade4", "paragraph has", "topic", "A paragraph has a topic sentence."),
        ("grade4", "dictionary finds", "meaning", "A dictionary finds word meaning."),
        ("grade4", "prefix un means", "not", "The prefix un often means not."),
        ("grade4", "suffix er means", "one", "The suffix er can mean one who."),
        ("grade4", "main idea is", "point", "The main idea is the central point."),
        ("grade5", "metaphor compares without", "like", "A metaphor compares without like or as."),
        ("grade5", "simile uses", "like", "A simile uses like or as."),
        ("grade5", "idiom meaning is", "figurative", "An idiom has a figurative meaning."),
        ("grade5", "personification gives", "human", "Personification gives human traits."),
        ("grade5", "plot is the", "events", "Plot is the sequence of events."),
        ("grade5", "setting is", "where", "Setting is where and when."),
        ("grade5", "character is a", "person", "A character is a person in a story."),
        ("grade5", "summary retells", "main", "A summary retells main points."),
        ("grade6", "thesis states", "claim", "A thesis states the main claim."),
        ("grade6", "evidence supports", "claim", "Evidence supports a claim."),
        ("grade6", "conclusion wraps", "ideas", "A conclusion wraps up ideas."),
        ("grade6", "transition connects", "ideas", "A transition connects ideas."),
        ("grade6", "audience is the", "reader", "Audience is the intended reader."),
        ("grade6", "tone is the", "attitude", "Tone is the author's attitude."),
        ("grade6", "mood is the", "feeling", "Mood is the feeling for the reader."),
        ("grade6", "context clues help", "meaning", "Context clues help find meaning."),
        ("grade7", "citation gives", "source", "A citation gives the source."),
        ("grade7", "argument has", "claim", "An argument has a claim and reasons."),
        ("grade7", "counterargument opposes", "claim", "A counterargument opposes a claim."),
        ("grade7", "rhetoric aims to", "persuade", "Rhetoric aims to persuade."),
        ("grade7", "connotation is", "feeling", "Connotation is the feeling of a word."),
        ("grade7", "denotation is", "dictionary", "Denotation is dictionary meaning."),
        ("grade7", "allusion refers to", "known", "Allusion refers to something known."),
        ("grade7", "irony contrasts", "expectation", "Irony contrasts expectation and reality."),
        ("grade8", "theme is", "message", "Theme is the message of a text."),
        ("grade8", "bias favors", "side", "Bias favors one side."),
        ("grade8", "rhetoric ethos is", "credibility", "Ethos is credibility appeal."),
        ("grade8", "rhetoric pathos is", "emotion", "Pathos is emotion appeal."),
        ("grade8", "rhetoric logos is", "logic", "Logos is logic appeal."),
        ("grade8", "structure is how", "organized", "Structure is how a text is organized."),
        ("grade8", "syntax is", "sentence", "Syntax is sentence structure."),
        ("grade8", "parallelism repeats", "structure", "Parallelism repeats structure."),
        ("grade8", "fallacy is a", "error", "A fallacy is a reasoning error."),
    ]
    # academic vocabulary G5–G8
    for g, words in (
        ("grade5", "analyze compare contrast describe explain summarize infer predict".split()),
        ("grade6", "evaluate justify interpret synthesize classify hypothesize cite paraphrase".split()),
        ("grade7", "critique refute corroborate delineate elaborate imply convey articulate".split()),
        ("grade8", "nuance paradox ambiguity rhetoric rhetoric style diction syntax cohesion".split()),
    ):
        for w in words:
            q = f"academic word {w}"
            facts.append(_fact(g, "literacy", f"acad-{g}-{w}", f"{w} is an academic word.", q, w))
            _put(bank, "literacy", g, "fact", q, w)
            _put(bank, "literacy", g, "fact", f"define skill {w}", w)
    for g, q, a, fact in grammar:
        facts.append(_fact(g, "literacy", f"gr-{g}-{q[:12]}", fact, q, a))
        _put(bank, "literacy", g, "fact", q, a)
        problems.append(_prob(g, "literacy", f"grp-{len(problems)}", q, a))
        _put(bank, "literacy", g, "problem", q, a)

    return facts, problems, bank


def build_science() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[BankRow]]:
    facts: List[Dict[str, Any]] = []
    problems: List[Dict[str, Any]] = []
    bank: List[BankRow] = []

    for g, fid, fact, q, a, alt in SCIENCE:
        facts.append(_fact(g, "science", fid, fact, q, a, alt))
        _put(bank, "science", g, "fact", q, a)
        if alt:
            _put(bank, "science", g, "fact", alt, a)
        problems.append(_prob(g, "science", f"p-{fid}", alt or q, a))
        _put(bank, "science", g, "problem", alt or q, a)

    for g, src, rel, dst, cue in RELS:
        _put(bank, "science", g, "rel", cue, dst)
        _put(bank, "science", g, "rel", f"{src} {rel}", dst)

    paths = [
        ("preschool", "sun when", "day"),
        ("preschool", "see with", "eyes"),
        ("kindergarten", "plants need", "sun"),
        ("kindergarten", "red light", "stop"),
        ("grade1", "we live on", "earth"),
        ("grade1", "living need", "water"),
        ("grade2", "solid keeps", "shape"),
        ("grade3", "force is", "push"),
        ("grade4", "matter has", "mass"),
        ("grade5", "earth orbits", "sun"),
        ("grade6", "basic unit of life", "cell"),
        ("grade7", "force can change", "motion"),
        ("grade8", "slope measures", "steepness"),
        ("grade8", "waves transfer", "energy"),
    ]
    for g, cue, ans in paths:
        _put(bank, "science", g, "path", cue, ans)

    return facts, problems, bank


def build_vision() -> Tuple[List[Dict[str, Any]], List[BankRow]]:
    facts: List[Dict[str, Any]] = []
    bank: List[BankRow] = []
    for d in range(10):
        g = "kindergarten" if d <= 5 else "grade1"
        name = NUM[d]
        facts.append(_fact(g, "vision", f"digit-{d}", f"Digit {d} is called {name}.", f"digit {d} name", name, f"name of digit {d}"))
        _put(bank, "vision", g, "fact", f"digit {d} name", name)
        _put(bank, "vision", g, "fact", f"name of digit {d}", name)
        # carry digit ID readiness through middle school as review
        for gg in ("grade2", "grade3", "grade4", "grade5", "grade6", "grade7", "grade8"):
            _put(bank, "vision", gg, "fact", f"digit {d} name", name)
    return facts, bank


def _dedupe(bank: List[BankRow]) -> List[BankRow]:
    """Collapse same (domain,grade,q). Prefer fact/rel/problem over path (path is transfer-only)."""
    rank = {"fact": 3, "rel": 2, "problem": 2, "path": 0}
    by_q: Dict[Tuple[str, str, str], BankRow] = {}
    order: List[Tuple[str, str, str]] = []
    for domain, grade, kind, q, a in bank:
        key = (domain, grade, q.lower().strip())
        row = (domain, grade, kind, q.strip(), str(a).strip())
        if key not in by_q:
            order.append(key)
            by_q[key] = row
            continue
        old = by_q[key]
        if rank.get(kind, 1) >= rank.get(old[2], 1):
            # keep higher-rank kind; if tie, prefer matching answer of fact-like
            by_q[key] = row
    return [by_q[k] for k in order]


def _write_outputs(
    facts: List[Dict[str, Any]],
    problems: List[Dict[str, Any]],
    bank: List[BankRow],
    dest: Path,
) -> Dict[str, Any]:
    dest.mkdir(parents=True, exist_ok=True)
    facts_p = dest / "facts.jsonl"
    probs_p = dest / "problems.jsonl"
    bank_p = dest / "bank.tsv"
    man_p = dest / "MANIFEST.json"

    with facts_p.open("w", encoding="utf-8") as f:
        for row in facts:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
    with probs_p.open("w", encoding="utf-8") as f:
        for row in problems:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
    with bank_p.open("w", encoding="utf-8") as f:
        f.write("# domain\tgrade\tkind\tquestion\tanswer\n")
        f.write("# Open PK→G8 curriculum — curriculum_open.py\n")
        for domain, grade, kind, q, a in bank:
            f.write(f"{domain}\t{grade}\t{kind}\t{q.replace(chr(9), ' ')}\t{str(a).replace(chr(9), ' ')}\n")

    by_domain = Counter(d for d, _, _, _, _ in bank)
    by_grade = Counter(g for _, g, _, _, _ in bank)
    by_kind = Counter(k for _, _, k, _, _ in bank)
    manifest = {
        "n_facts_jsonl": len(facts),
        "n_problems_jsonl": len(problems),
        "n_bank_rows": len(bank),
        "by_domain": dict(by_domain),
        "by_grade": dict(by_grade),
        "by_kind": dict(by_kind),
        "grades": GRADES,
        "paths": {"facts": str(facts_p), "problems": str(probs_p), "bank": str(bank_p)},
        "doctrine": "open PK→G8; Zig domain ≥95% gates; middle school target",
    }
    man_p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def build_all(merge_existing: bool = False) -> Dict[str, Any]:
    facts: List[Dict[str, Any]] = []
    problems: List[Dict[str, Any]] = []
    bank: List[BankRow] = []

    for builder in (build_math, build_literacy, build_science):
        f, p, b = builder()
        facts.extend(f)
        problems.extend(p)
        bank.extend(b)
    vf, vb = build_vision()
    facts.extend(vf)
    bank.extend(vb)

    bank = _dedupe(bank)
    man = _write_outputs(facts, problems, bank, CUR_DIR)

    # legacy path for older ladder candidates
    LEGACY_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("facts.jsonl", "problems.jsonl", "bank.tsv", "MANIFEST.json"):
        src = CUR_DIR / name
        if src.is_file():
            shutil.copy2(src, LEGACY_DIR / name)

    # game drive mirror
    try:
        if Path("D:/").exists():
            man_game = _write_outputs(facts, problems, bank, GAME_DIR)
            man["game_mirror"] = man_game["paths"]
    except OSError as e:
        man["game_mirror_error"] = str(e)

    return man


def report() -> Dict[str, Any]:
    p = CUR_DIR / "MANIFEST.json"
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return build_all()
