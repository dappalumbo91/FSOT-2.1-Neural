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
| Morse as the main “language” of the net | **Secondary demos only** (legacy Morse dumps removed); body I/O is **machine**; Shakespeare + NLP corpora kept for future language bridge — `docs/LANGUAGE_AND_NLP_BRIDGE.md` |
| Free-parameter transformer-style climbing | Forbidden on theory path |

Those demos may remain under `run_climb.py` / `run_sota_fronts.py` for exploration, but they are **not** the mission.

## Authority

| Layer | Source |
|-------|--------|
| Theory pin | **Standalone** `data/archive_snapshot/` → **D1D38A…** (no external drive required) |
| Codon map | `I:\64_codon_trinary_map.txt` ≡ archive ≡ `data/64_codon_trinary_map.txt` |
| Protein interaction form | Archive `04_Genetics-Longevity` fluid-to-solid / protein formulas |
| Bio targets | Allen Cell Types ephys (when CSV present) |
| Application recipe | pin → fold → bridge → couple — [`docs/FSOT_APPLICATION_NEURAL.md`](docs/FSOT_APPLICATION_NEURAL.md) |
| Usage doctrine | `I:\FSOT-Physical-Archive\FSOT_USAGE_DOCTRINE.md` |

**Do not stitch** encodings, neurons, and UI without the scalar. Every claim-sensitive path runs `run_archive_pin.py` / `run_fsot_bridge.py`.

## Primary commands

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_STANDALONE = "1"

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
| **Math solidified (archive → mind stack)** | [`docs/FSOT_MATH_SYSTEM_SOLIDIFIED.md`](docs/FSOT_MATH_SYSTEM_SOLIDIFIED.md) · pin D1D38A · 405-domain bridge |
| Formulas | [`docs/FORMULAS.md`](docs/FORMULAS.md) |
| Formal (Lean) | [`formal/`](formal/) · **`scientific_panel_ok`** · [`docs/FORMAL_VERIFICATION_CHOICE.md`](docs/FORMAL_VERIFICATION_CHOICE.md) · certificate `data/results/LEAN_WETLAB_CERTIFICATE.md` |
| Repo connectivity audit | [`docs/REPO_CONNECTIVITY_AUDIT.md`](docs/REPO_CONNECTIVITY_AUDIT.md) |
| **Forward intelligence (bio)** | [`docs/FORWARD_INTELLIGENCE_BIO.md`](docs/FORWARD_INTELLIGENCE_BIO.md) · `fsot_mind intel-bio` |
| **Game-drive capability** | [`docs/GAME_DRIVE_CAPABILITY.md`](docs/GAME_DRIVE_CAPABILITY.md) · `python scripts/run_game_drive_bench.py --bench` |
| **Benchmark teach ladder** | [`docs/BENCHMARK_TEACH_LADDER.md`](docs/BENCHMARK_TEACH_LADDER.md) · **rules first** · import Math generator · `python scripts/import_math_generator_rules.py` |
| **Math rulebook (imported)** | `data/math_rulebook/` · ~1520 atomic rules from Desktop Math generator |
| **Emergent monitor (observe only)** | `D:\fsot_training\logs\emergent_behavior.jsonl` · no curb |
| **Speech reconnect** | [`docs/SPEECH_RECONNECT.md`](docs/SPEECH_RECONNECT.md) |
| Embodiment | [`docs/EMBODIMENT_ROADMAP.md`](docs/EMBODIMENT_ROADMAP.md) — Python host → Zig/Rust/Ada body |
| Efficiency doctrine | [`docs/EFFICIENCY_DOCTRINE.md`](docs/EFFICIENCY_DOCTRINE.md) |
| Path / phases | [`BRAIN_PATH.md`](BRAIN_PATH.md) |
| Run ledger | `data/thesis_ledger/runs.jsonl` |

**Python is the lab, not the permanent body.** Destination is a **trinary bare-metal Zig** substrate. Sensory + system-metric loops inject as trit streams.

| Stage docs | |
|------------|--|
| **Current stage** | [`docs/STAGE_ZIG_NEURON_STEP.md`](docs/STAGE_ZIG_NEURON_STEP.md) |
| **Bio accuracy (wet-lab data)** | [`docs/BIO_ACCURACY.md`](docs/BIO_ACCURACY.md) |
| **Learning / study alignment** | [`docs/LEARNING_ALIGNMENT.md`](docs/LEARNING_ALIGNMENT.md) |
| **Scalpel rate lock** | [`docs/SCALPEL_RATE_SYSTEM.md`](docs/SCALPEL_RATE_SYSTEM.md) · `run_scalpel_rates.py` |
| **Accuracy standard** | [`docs/ACCURACY_STANDARD.md`](docs/ACCURACY_STANDARD.md) — AlphaFold-*class* rigor, not CASP competitor |
| **Intelligence probe** | [`docs/STAGE_INTELLIGENCE_PROBE.md`](docs/STAGE_INTELLIGENCE_PROBE.md) · `run_intelligence_probe.py --suite` |
| **Retention / consolidate** | [`docs/STAGE_RETENTION_CONSOLIDATION.md`](docs/STAGE_RETENTION_CONSOLIDATION.md) |
| **Checkpoint freeze** | [`CHECKPOINT_v0.5.md`](CHECKPOINT_v0.5.md) · tag `v0.5.0-bio-intel` |
| **Intel options (later)** | [`docs/INTELLIGENCE_ROADMAP_OPTIONS.md`](docs/INTELLIGENCE_ROADMAP_OPTIONS.md) |
| **Product UI / display** | [`docs/PRODUCT_UI_AND_DISPLAY.md`](docs/PRODUCT_UI_AND_DISPLAY.md) — Console v0.7 · [`docs/HARDWARE_BODY.md`](docs/HARDWARE_BODY.md) · [`docs/SELF_MODULATION_AND_SENSES.md`](docs/SELF_MODULATION_AND_SENSES.md) |
| **Reproducibility** | [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) — full clone-and-run package |
| **Autonomous multi-modal** | `python run_autonomous_learn.py` · document read + media + memory |
| **Knowledge / subtitles** | [`docs/KNOWLEDGE_CROSSFEED.md`](docs/KNOWLEDGE_CROSSFEED.md) · `run_episode_watch.py` |
| **Capability frontier (unclaimed)** | [`docs/CAPABILITY_FRONTIER.md`](docs/CAPABILITY_FRONTIER.md) · `python run_capability_frontier.py` |
| **Bio sensory system** | [`docs/BIO_SENSORY_SYSTEM.md`](docs/BIO_SENSORY_SYSTEM.md) · `python run_bio_sensory_check.py` |
| **Bio-equivalence distance** | [`docs/BIO_EQUIVALENCE_DISTANCE.md`](docs/BIO_EQUIVALENCE_DISTANCE.md) · `python run_bio_equivalence_scorecard.py` |
| **Multi-species / fly motifs** | [`docs/MULTI_SPECIES_COMPUTER_CENTRIC.md`](docs/MULTI_SPECIES_COMPUTER_CENTRIC.md) · FlyWire-class literature targets |
| **Stress / break map** | [`docs/STRESS_STAGE_REPORT.md`](docs/STRESS_STAGE_REPORT.md) · `python run_stress_suite.py` |
| **Study / learning EEG** | [`docs/LEARNING_EEG_STUDY.md`](docs/LEARNING_EEG_STUDY.md) · `python run_learning_eeg_study.py` |
| **Runtime inventory** | [`docs/RUNTIME_INVENTORY.md`](docs/RUNTIME_INVENTORY.md) · `python scripts/runtime_audit.py` |
| **GitHub hygiene** | [`docs/GITHUB_HYGIENE.md`](docs/GITHUB_HYGIENE.md) |
| **Wet-lab battery** | [`docs/WETLAB_ACCURACY_BATTERY.md`](docs/WETLAB_ACCURACY_BATTERY.md) · `python run_wetlab_accuracy_battery.py` |
| **Genome as code** | [`docs/GENOME_AS_CODE.md`](docs/GENOME_AS_CODE.md) · `python run_cellular_expand.py --check` |
| **Lean × wet-lab certificate** | [`docs/LEAN_WETLAB_CROSSREF.md`](docs/LEAN_WETLAB_CROSSREF.md) · `python scripts/export_lean_wetlab_certificate.py` |
| **Stage thesis (arXiv-style)** | [`docs/thesis/FSOT_NEURAL_STAGE_VERIFICATION.md`](docs/thesis/FSOT_NEURAL_STAGE_VERIFICATION.md) · `.tex` |
| **Precision climb (≤1% attempt)** | `python run_precision_climb.py` · `python scripts/audit_lean_nosorry.py` |
| **Full spine (consciousness / observer / yin–yang / POOF)** | [`docs/FSOT_FULL_SPINE_NEURAL.md`](docs/FSOT_FULL_SPINE_NEURAL.md) · `python run_full_spine_check.py` |
| **Formula completeness** | [`docs/FORMULA_COMPLETENESS.md`](docs/FORMULA_COMPLETENESS.md) · `python scripts/audit_formula_completeness.py` |
| **Timing resolution** | [`docs/TIMING_RESOLUTION.md`](docs/TIMING_RESOLUTION.md) · `python run_timing_resolution.py` |
| Trinary bare metal | [`docs/TRINARY_BARE_METAL.md`](docs/TRINARY_BARE_METAL.md) |
| Formulas | [`docs/FORMULAS.md`](docs/FORMULAS.md) |

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
