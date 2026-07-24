# Mission — FSOT-2.1-Neural

## What this project is

A **biologically accurate neural network** whose structure comes from:

1. **64-codon trinary genetics** (DNA → primary trinary → amino acids)  
2. **Ion-channel gene programs** (SCN / KCN / CACNA / LEAK)  
3. **FSOT zero-free-parameter scalar** \(S = K(T_1+T_2+T_3)\) driving membrane-like dynamics  
4. **FSOT trinary synaptic weights** (protein-style interaction, no free-fit matrices)

```text
codon map (authority)
  → gene ORFs per unit
  → phenotype (threshold, refractory, AHP, d_eff, channels)
  → W_ij from trinary spins + charges + geometric φ·|i−j|^(−1/π)
  → FSOT neuron batch + recurrent genetic synapses
  → Allen ephys timing lock (bio_match)
  → hard bio metrics
```

## What this project is not (primary)

| Drift that happened | Status |
|---------------------|--------|
| IMDB / sentiment / SMS NLP scoreboard as the product | **Secondary demo only** |
| Morse as the main “language” of the net | Optional readout path |
| Free-parameter transformer-style climbing | Forbidden on theory path |

Those demos may remain under `run_climb.py` / `run_sota_fronts.py` for exploration, but they are **not** the mission.

## Authority

| Layer | Source |
|-------|--------|
| Theory pin | `I:\FSOT-Physical-Archive` → `vendor/fsot_compute.py` **D1D38A…** |
| Codon map | `data/64_codon_trinary_map.txt` (same as Genetics-Longevity / SR-ITE) |
| Protein interaction form | Archive `04_Genetics-Longevity` fluid-to-solid / protein formulas |
| Bio targets | Allen Cell Types ephys (when CSV present) |

## Primary commands

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"

python run_archive_pin.py
python run_genetic_bio.py --units 64 --steps 1200
python run_obsidian_brain.py   # local Markdown vault — no server/web
python scripts/ci_smoke.py
```

## Local second brain (Obsidian)

Connective patterns export as a **local-only** Markdown vault (wikilinks = synapses).

- **No web, no server, no cloud** — files under `artifacts/obsidian_vaults/`
- Open the folder in Obsidian desktop → Graph view (offline core plugin)
- Entry note: `00_Home.md`

## North star

**A multi-region, cell-typed, genetically structured FSOT brain for computer-native AI** — same neurological *mechanisms* as biology (genetics, E/I motifs, FSOT dynamics), **not** the same neuron count or vegetative load. Connective patterns visible (local Obsidian) and measurable against real data.

| Living science docs | |
|---------------------|--|
| Thesis | [`docs/THESIS.md`](docs/THESIS.md) |
| Formulas | [`docs/FORMULAS.md`](docs/FORMULAS.md) |
| Formal (Lean) | [`formal/`](formal/) · [`docs/FORMAL_VERIFICATION_CHOICE.md`](docs/FORMAL_VERIFICATION_CHOICE.md) |
| Embodiment | [`docs/EMBODIMENT_ROADMAP.md`](docs/EMBODIMENT_ROADMAP.md) — Python host → Zig/Rust/Ada body |
| Efficiency doctrine | [`docs/EFFICIENCY_DOCTRINE.md`](docs/EFFICIENCY_DOCTRINE.md) |
| Path / phases | [`BRAIN_PATH.md`](BRAIN_PATH.md) |
| Run ledger | `data/thesis_ledger/runs.jsonl` |

**Python is the lab, not the permanent body.** Destination is a **trinary bare-metal** substrate (Zig/Rust/Ada kernel) — not permanent binary ontology. Sensory + system-metric subconscious loops inject at the edge as trit streams. See `docs/TRINARY_BARE_METAL.md`.

## Success criteria

1. Codon map **64/64** round-trip  
2. Channel gene programs present and expressible  
3. Genetic \(W\) non-empty, seed-derived  
4. Population spikes under FI with genetic diversity  
5. Allen timing lock available in `bio_match` when ephys CSV is on disk  
6. Archive seed pin green  
7. Multi-region brain design with E/I cell types + projections (`run_brain_design.py`)  

## Honesty

Not a medical device. Computational brain *design* structured by genetics + FSOT, validated against population ephys statistics where data exists — not a clinical human brain replica.
