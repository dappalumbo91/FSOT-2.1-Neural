"""Import the full Math-generator rule corpus into FSOT-2.1-Neural.

Source (user Desktop — FSOT math generator):
  C:\\Users\\damia\\Desktop\\Math generator
  - RULE_DOCUMENT_REGISTRY.json
  - *_RULES.json (~1520 atomic rules across arithmetic…topology…engineering)

Doctrine:
  Teach RULES (input_form → output_form + operation), not Q/A stuffing.
  This module *pulls the authority rule book* you already built.

  python scripts/import_math_generator_rules.py
  python scripts/import_math_generator_rules.py --source "C:/Users/damia/Desktop/Math generator"
"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paths import DATA

DEFAULT_SOURCE = Path(
    os.environ.get("MATH_GENERATOR_ROOT", r"C:\Users\damia\Desktop\Math generator")
)
OUT_DIR = DATA / "math_rulebook"
GAME_OUT = Path(r"D:\fsot_training\math_rulebook")


def _safe_read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"skip {path.name}: {e}")
        return None


def load_registry(source: Path) -> List[Dict[str, Any]]:
    reg_path = source / "RULE_DOCUMENT_REGISTRY.json"
    if not reg_path.is_file():
        # fallback: all *_RULES.json
        return [
            {
                "document_id": p.stem.replace("_RULES", "").lower(),
                "file_name": p.name,
                "domain_family": p.stem.replace("_RULES", "").lower(),
            }
            for p in sorted(source.glob("*_RULES.json"))
        ]
    reg = _safe_read_json(reg_path) or {}
    docs = reg.get("documents") or []
    return list(docs)


def normalize_rule(raw: Dict[str, Any], document_id: str, domain_family: str, file_name: str) -> Dict[str, Any]:
    return {
        "id": str(raw.get("id", "")),
        "name": str(raw.get("name", "")),
        "category": str(raw.get("category", "")),
        "input_form": str(raw.get("input_form", "")),
        "output_form": str(raw.get("output_form", "")),
        "domains": list(raw.get("domains") or []),
        "preconditions": list(raw.get("preconditions") or []),
        "operation": str(raw.get("operation", "")),
        "properties": list(raw.get("properties") or []),
        "examples": list(raw.get("examples") or []),
        "counterexamples": list(raw.get("counterexamples") or []),
        "common_errors": list(raw.get("common_errors") or []),
        "document_id": document_id,
        "domain_family": domain_family,
        "source_file": file_name,
        "dependency_links": list(raw.get("dependency_links") or []),
    }


def import_all(source: Path = DEFAULT_SOURCE) -> Dict[str, Any]:
    if not source.is_dir():
        raise FileNotFoundError(f"Math generator not found: {source}")

    registry = load_registry(source)
    documents: List[Dict[str, Any]] = []
    all_rules: List[Dict[str, Any]] = []
    by_family: Counter = Counter()
    by_category: Counter = Counter()
    ids_seen: set = set()
    dup_ids: List[str] = []

    # Prefer registry order; also catch unregistered *_RULES.json
    seen_files: set = set()
    file_entries: List[Tuple[str, str, str]] = []  # file, doc_id, family
    for ent in registry:
        fn = ent.get("file_name") or ""
        if not fn:
            continue
        file_entries.append(
            (
                fn,
                str(ent.get("document_id") or Path(fn).stem),
                str(ent.get("domain_family") or ent.get("document_id") or "unknown"),
            )
        )
        seen_files.add(fn)

    for p in sorted(source.glob("*_RULES.json")):
        if p.name not in seen_files:
            file_entries.append(
                (p.name, p.stem.replace("_RULES", "").lower(), p.stem.replace("_RULES", "").lower())
            )

    for file_name, doc_id, family in file_entries:
        path = source / file_name
        if not path.is_file():
            # try Unified package copies
            alt = source / "Unified" / "ada_spark_formula_generator" / file_name
            path = alt if alt.is_file() else path
        if not path.is_file():
            print(f"missing {file_name}")
            continue
        payload = _safe_read_json(path)
        if not payload or "rules" not in payload:
            continue
        rules_raw = payload.get("rules") or []
        if not isinstance(rules_raw, list):
            continue
        doc_rules = []
        for raw in rules_raw:
            if not isinstance(raw, dict):
                continue
            nr = normalize_rule(raw, doc_id, family, file_name)
            rid = nr["id"]
            if rid in ids_seen:
                dup_ids.append(rid)
                # keep unique key
                nr["id"] = f"{doc_id}:{rid}"
            ids_seen.add(nr["id"])
            doc_rules.append(nr)
            all_rules.append(nr)
            by_family[family] += 1
            by_category[nr["category"] or "uncategorized"] += 1
        documents.append(
            {
                "document_id": doc_id,
                "file_name": file_name,
                "domain_family": family,
                "n_rules": len(doc_rules),
                "document_source": payload.get("document_source", ""),
                "domain_symbols": payload.get("domain_symbols") or {},
            }
        )

    # Optional: FSOT algorithmic law registry (separate schema — index only)
    law_path = source / "FSOT_ALGORITHMIC_LAW_REGISTRY.json"
    law_count = 0
    if law_path.is_file():
        law = _safe_read_json(law_path)
        if isinstance(law, dict):
            # count leaf-ish entries
            def count_laws(x: Any) -> int:
                if isinstance(x, list):
                    return sum(count_laws(i) for i in x)
                if isinstance(x, dict):
                    if "law_id" in x or "algorithmic_law" in x or (
                        "id" in x and ("formula" in x or "expression" in x)
                    ):
                        return 1
                    return sum(count_laws(v) for v in x.values())
                return 0

            law_count = count_laws(law)

    # Bank for mind teach: every rule as symbolic curriculum rows
    bank_rows: List[str] = [
        "# domain\tgrade\tkind\tquestion\tanswer\n",
        f"# Imported Math-generator rulebook {datetime.now(timezone.utc).isoformat()}\n",
        f"# source={source}\n",
        "# kind=rule_id|rule_name|rule_form|rule_op|rule_example\n",
    ]
    for r in all_rules:
        fam = re.sub(r"[^a-z0-9_]+", "_", r["domain_family"].lower())[:24]
        rid = r["id"]
        name = r["name"].replace("\t", " ")
        formula = f"{r['input_form']} → {r['output_form']}".replace("\t", " ")
        op = (r["operation"] or "")[:200].replace("\t", " ").replace("\n", " ")
        bank_rows.append(f"math\t{fam}\trule_id\tWhat rule is {rid}?\t{name}\n")
        bank_rows.append(f"math\t{fam}\trule_name\tState the form of {name}\t{formula}\n")
        bank_rows.append(f"math\t{fam}\trule_form\t{rid} input form\t{r['input_form']}\n")
        bank_rows.append(f"math\t{fam}\trule_form\t{rid} output form\t{r['output_form']}\n")
        if op:
            bank_rows.append(f"math\t{fam}\trule_op\tHow does {rid} operate?\t{op}\n")
        for ex in (r["examples"] or [])[:2]:
            exs = str(ex).replace("\t", " ").replace("\n", " ")[:160]
            if exs:
                bank_rows.append(f"math\t{fam}\trule_example\tExample for {rid}\t{exs}\n")

    master = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "n_documents": len(documents),
        "n_rules": len(all_rules),
        "n_duplicate_ids_renamed": len(dup_ids),
        "n_fsot_algorithmic_law_nodes_approx": law_count,
        "by_domain_family": dict(sorted(by_family.items(), key=lambda kv: -kv[1])),
        "by_category_top": dict(by_category.most_common(40)),
        "documents": documents,
        "doctrine": (
            "Authority mathematical rule book imported from Math generator. "
            "Teach rules (form + operation + examples). Apply by decomposition — not Q/A stuffing."
        ),
    }

    # Write outputs
    outs = [OUT_DIR, GAME_OUT]
    written = []
    for out in outs:
        try:
            out.mkdir(parents=True, exist_ok=True)
            (out / "MASTER_RULEBOOK.json").write_text(
                json.dumps({"meta": master, "rules": all_rules}, indent=2),
                encoding="utf-8",
            )
            # lighter index without full rule bodies for quick load
            index = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "category": r["category"],
                    "domain_family": r["domain_family"],
                    "input_form": r["input_form"],
                    "output_form": r["output_form"],
                }
                for r in all_rules
            ]
            (out / "RULE_INDEX.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
            (out / "MANIFEST.json").write_text(json.dumps(master, indent=2), encoding="utf-8")
            (out / "bank.tsv").write_text("".join(bank_rows), encoding="utf-8")
            # human summary
            lines = [
                "# Imported Math Generator Rule Book",
                "",
                f"Source: `{source}`",
                f"Generated: `{master['generated_at']}`",
                "",
                f"**Documents:** {master['n_documents']}  ",
                f"**Atomic rules:** **{master['n_rules']}**  ",
                f"**FSOT algorithmic law nodes (approx):** {law_count}",
                "",
                "## By domain family",
                "",
                "| Family | n |",
                "|--------|--:|",
            ]
            for fam, n in master["by_domain_family"].items():
                lines.append(f"| {fam} | {n} |")
            lines += [
                "",
                "## Files",
                "",
                "- `MASTER_RULEBOOK.json` — full normalized rules",
                "- `RULE_INDEX.json` — id/name/forms index",
                "- `bank.tsv` — mind teach rows (rule forms, not answer stuffing)",
                "",
                master["doctrine"],
                "",
            ]
            (out / "README.md").write_text("\n".join(lines), encoding="utf-8")
            # copy ARITHMETIC + ALGEBRA raw for apply layer
            for name in ("ARITHMETIC_RULES.json", "ALGEBRA_RULES.json", "GEOMETRY_RULES.json"):
                src = source / name
                if src.is_file():
                    shutil.copy2(src, out / name)
            written.append(str(out))
        except OSError as e:
            print(f"write fail {out}: {e}")

    # monorepo results snapshot
    res = DATA / "results"
    if res.is_dir():
        (res / "MATH_RULEBOOK_IMPORT.json").write_text(json.dumps(master, indent=2), encoding="utf-8")
        (res / "MATH_RULEBOOK_IMPORT.md").write_text(
            (OUT_DIR / "README.md").read_text(encoding="utf-8") if (OUT_DIR / "README.md").is_file() else json.dumps(master, indent=2),
            encoding="utf-8",
        )

    master["written"] = written
    master["n_bank_rows"] = len([r for r in bank_rows if not r.startswith("#")])
    return master


def load_master(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or (OUT_DIR / "MASTER_RULEBOOK.json")
    if not p.is_file():
        p = GAME_OUT / "MASTER_RULEBOOK.json"
    if not p.is_file():
        raise FileNotFoundError("Run import_math_generator_rules.py first")
    return json.loads(p.read_text(encoding="utf-8"))


def rules_for_family(family: str, master: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    m = master or load_master()
    fam = family.lower()
    return [r for r in m.get("rules") or [] if str(r.get("domain_family", "")).lower() == fam]


def arithmetic_rules(master: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    return rules_for_family("arithmetic", master)
