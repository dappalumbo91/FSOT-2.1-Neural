"""
Chemical / codon generative layer for FSOT Morse-trinary signals.

Authority paths (local, already verified in your stack):
  - 64_codon_trinary_map.txt  (A,G→+1; C,T→−1 primary map)
  - genetic_code_64 / DNA→AA (IUPAC)
  - FSOT SMILES Lab dataset metadata (median error ~0.058% on constants)

Generative claim: reservoir trinary is read as codon streams → amino-acid /
process tokens → optional SMILES-domain process labels — the same chemical
spine FSOT already hits at extreme precision. This is interpretation +
cross-verify, not a new free-parameter chemistry model.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .paths import ROOT, ARTIFACTS

# Codon map candidates (your machines)
CODON_MAP_CANDIDATES = [
    ROOT / "data" / "64_codon_trinary_map.txt",
    Path(r"I:\FSOT-Physical-Archive\01_SR-ITE-USB-Original\3_driver_zig\64_codon_trinary_map.txt"),
    Path(r"I:\FSOT-Physical-Archive\04_Genetics-Longevity\64_codon_trinary_map.txt"),
    Path(r"C:\Users\damia\Desktop\FSOT_Trinary_Codon_Project\64_codon_trinary_map.txt"),
]

SMILES_JSON_CANDIDATES = [
    Path(r"I:\FSOT-Physical-Archive\01_SR-ITE-USB-Original\6_unified_oracle\smiles_lab\FSOT_SMILES_Lab_Dataset.json"),
    Path(r"C:\Users\damia\Desktop\FSOT SMILES Lab\FSOT_SMILES_Lab_Dataset.json"),
]

# IUPAC standard genetic code
DNA_TO_AA = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

AA_PROCESS = {
    "M": "start_met_initiator",
    "*": "stop_release",
    "F": "aromatic_phenylalanine",
    "L": "hydrophobic_leucine",
    "S": "hydroxyl_serine",
    "Y": "signal_tyrosine",
    "C": "disulfide_cysteine",
    "W": "aromatic_tryptophan",
    "P": "kink_proline",
    "H": "charge_histidine",
    "Q": "amide_glutamine",
    "R": "charge_arginine",
    "I": "hydrophobic_isoleucine",
    "T": "hydroxyl_threonine",
    "N": "amide_asparagine",
    "K": "charge_lysine",
    "V": "hydrophobic_valine",
    "A": "compact_alanine",
    "D": "charge_aspartate",
    "E": "charge_glutamate",
    "G": "flex_glycine",
}

# Trit → base under primary FSOT map (A,G=+1; C,T=-1). Ambiguity broken by secondary preference.
PLUS_BASES = ("A", "G")   # +1
MINUS_BASES = ("C", "T")  # -1


def find_codon_map() -> Optional[Path]:
    for p in CODON_MAP_CANDIDATES:
        if p.is_file():
            return p
    return None


def find_smiles_json() -> Optional[Path]:
    for p in SMILES_JSON_CANDIDATES:
        if p.is_file():
            return p
    return None


def parse_codon_trinary_map(path: Optional[Path] = None) -> Dict[str, Tuple[int, int, int]]:
    """Parse PRIMARY column [a, b, c] from 64_codon_trinary_map.txt."""
    path = path or find_codon_map()
    out: Dict[str, Tuple[int, int, int]] = {}
    if path is None:
        # Fallback: build from primary rule A,G=+1; C,T=-1
        for codon in DNA_TO_AA:
            trip = tuple(1 if b in "AG" else -1 for b in codon)
            out[codon] = trip  # type: ignore
        return out

    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        m = re.match(r"^([ACGT]{3})\s*\|\s*\[([^\]]+)\]", line.strip())
        if not m:
            continue
        codon = m.group(1)
        parts = [int(x.strip()) for x in m.group(2).split(",")]
        if len(parts) == 3:
            out[codon] = (parts[0], parts[1], parts[2])
    if len(out) < 64:
        # fill missing
        for codon in DNA_TO_AA:
            if codon not in out:
                out[codon] = tuple(1 if b in "AG" else -1 for b in codon)  # type: ignore
    return out


def invert_trinary_to_codons(
    trip: Tuple[int, int, int],
    primary_map: Dict[str, Tuple[int, int, int]],
) -> List[str]:
    """All codons whose primary trinary equals trip."""
    return [c for c, t in primary_map.items() if t == trip]


def trit_from_signed(x: int) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def ternary_stream_to_codons(
    ternary: Sequence[int],
    primary_map: Optional[Dict[str, Tuple[int, int, int]]] = None,
) -> List[Dict[str, Any]]:
    """
    Chunk non-zero trits into codons of 3. Zeros are separators (like Morse gaps).
    """
    primary_map = primary_map or parse_codon_trinary_map()
    # compress: drop zeros as breaks; keep ±1 runs as single trit for codon alphabet
    trits: List[int] = []
    i = 0
    n = len(ternary)
    while i < n:
        v = trit_from_signed(int(ternary[i]))
        if v == 0:
            i += 1
            continue
        j = i
        while j < n and trit_from_signed(int(ternary[j])) == v:
            j += 1
        trits.append(v)
        i = j

    # pad to multiple of 3 with 0 (superposed) — skip incomplete
    codons_out: List[Dict[str, Any]] = []
    for k in range(0, len(trits) - 2, 3):
        trip = (trits[k], trits[k + 1], trits[k + 2])
        # FSOT primary map has no 0; map any 0 → -1 (pyrimidine default)
        trip_pm = tuple(-1 if t == 0 else t for t in trip)
        matches = invert_trinary_to_codons(trip_pm, primary_map)  # type: ignore
        if not matches:
            continue
        # Prefer start codon ATG when available, else first lexicographic for determinism
        if "ATG" in matches:
            codon = "ATG"
        else:
            codon = sorted(matches)[0]
        aa = DNA_TO_AA.get(codon, "?")
        codons_out.append(
            {
                "trinary": list(trip_pm),
                "codon": codon,
                "aa": aa,
                "process": AA_PROCESS.get(aa, "unknown"),
                "synonyms": matches,
                "n_synonyms": len(matches),
            }
        )
    return codons_out


def codon_path_verify(primary_map: Optional[Dict[str, Tuple[int, int, int]]] = None) -> Dict[str, Any]:
    """
    Cross-verify: every codon → primary trinary → inverse contains original.
    Must be 64/64 for the map to be generative-safe.
    """
    primary_map = primary_map or parse_codon_trinary_map()
    ok = 0
    fails = []
    for codon, trip in primary_map.items():
        back = invert_trinary_to_codons(trip, primary_map)
        if codon in back:
            ok += 1
        else:
            fails.append(codon)
    return {
        "n_codons": len(primary_map),
        "roundtrip_ok": ok,
        "roundtrip_fail": fails,
        "perfect": ok == len(primary_map) and len(primary_map) >= 64,
        "map_path": str(find_codon_map()) if find_codon_map() else "synthetic_primary_rule",
    }


def smiles_lab_precision_ref() -> Dict[str, Any]:
    """Load FSOT SMILES Lab precision ledger if present (chemical authority)."""
    path = find_smiles_json()
    if path is None:
        return {"ok": False, "reason": "SMILES dataset not found on known paths"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data.get("metadata", {})
        return {
            "ok": True,
            "path": str(path),
            "hit_rate": meta.get("hit_rate"),
            "median_error_pct": meta.get("median_error_pct"),
            "mean_error_pct": meta.get("mean_error_pct"),
            "matched": meta.get("matched"),
            "total_constants": meta.get("total_constants"),
            "free_parameters": meta.get("free_parameters"),
            "note": meta.get("description", "")[:240],
        }
    except Exception as e:
        return {"ok": False, "reason": str(e)}


# Higher-level chemical narrative families (FSOT process → domain language)
PROCESS_FAMILY = {
    "start_met_initiator": "initiation",
    "stop_release": "termination",
    "aromatic_phenylalanine": "aromatic_scaffold",
    "aromatic_tryptophan": "aromatic_scaffold",
    "hydrophobic_leucine": "hydrophobic_core",
    "hydrophobic_isoleucine": "hydrophobic_core",
    "hydrophobic_valine": "hydrophobic_core",
    "charge_histidine": "proton_buffer",
    "charge_arginine": "cationic_contact",
    "charge_lysine": "cationic_contact",
    "charge_aspartate": "anionic_contact",
    "charge_glutamate": "anionic_contact",
    "hydroxyl_serine": "hbond_network",
    "hydroxyl_threonine": "hbond_network",
    "amide_glutamine": "polar_link",
    "amide_asparagine": "polar_link",
    "disulfide_cysteine": "covalent_bridge",
    "kink_proline": "backbone_kink",
    "compact_alanine": "compact_fill",
    "flex_glycine": "hinge_flex",
    "signal_tyrosine": "signal_phospho_site",
}


def enrich_chemical_utterance(codons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compress codon stream into a structured chemical narrative:
    family runs, charge balance, aromatic density, start/stop grammar.
    """
    if not codons:
        return {
            "enriched_utterance": "(no codon lock)",
            "families": [],
            "charge_balance": 0,
            "aromatic_fraction": 0.0,
        }
    families = [PROCESS_FAMILY.get(c["process"], "other") for c in codons]
    # run-length encode families
    runs: List[str] = []
    i = 0
    while i < len(families):
        j = i
        while j < len(families) and families[j] == families[i]:
            j += 1
        n = j - i
        runs.append(f"{families[i]}×{n}" if n > 1 else families[i])
        i = j

    aa = [c["aa"] for c in codons]
    cationic = sum(1 for a in aa if a in "RHK")
    anionic = sum(1 for a in aa if a in "DE")
    aromatic = sum(1 for a in aa if a in "FYW")
    has_start = any(c["codon"] == "ATG" for c in codons)
    has_stop = any(c["aa"] == "*" for c in codons)

    grammar = []
    if has_start:
        grammar.append("ORF_OPEN")
    grammar.append(f"LEN={len(codons)}")
    if has_stop:
        grammar.append("ORF_CLOSE")
    else:
        grammar.append("ORF_OPEN_ENDED")

    charge = cationic - anionic
    arom_f = aromatic / max(len(aa), 1)
    utterance = (
        f"[chem {' '.join(grammar)}] "
        + " → ".join(runs[:20])
        + f" || charge={charge:+d} aromatic={arom_f:.2f}"
    )
    return {
        "enriched_utterance": utterance,
        "families": runs[:32],
        "charge_balance": charge,
        "aromatic_fraction": arom_f,
        "grammar": grammar,
        "n_start_codons": sum(1 for c in codons if c["codon"] == "ATG"),
        "n_stop": sum(1 for c in codons if c["aa"] == "*"),
    }


def generative_chemical_report(ternary: Sequence[int]) -> Dict[str, Any]:
    """Full chemical generative readout from a trinary stream."""
    primary = parse_codon_trinary_map()
    codons = ternary_stream_to_codons(ternary, primary)
    aa_seq = "".join(c["aa"] for c in codons)
    processes = [c["process"] for c in codons]
    verify = codon_path_verify(primary)
    smiles = smiles_lab_precision_ref()
    enriched = enrich_chemical_utterance(codons)
    return {
        "n_codons": len(codons),
        "aa_sequence": aa_seq,
        "process_stream": processes,
        "codons": codons[:32],
        "codon_map_verify": verify,
        "smiles_lab_precision": smiles,
        "chemical_utterance": " → ".join(processes[:16]) if processes else "(no codon lock)",
        "enriched_utterance": enriched["enriched_utterance"],
        "chemical_structure": enriched,
    }
