# Runtime inventory — accurate FSOT-2.1-Neural system

Generated: `2026-07-28T15:56:08.804758+00:00`

This audit lists what the **mission-accurate** path actually imports and uses,
versus workspace bulk that is optional, demo, or local-only.

## Authority

| Layer | Path |
|-------|------|
| Physical archive | `I:\FSOT-Physical-Archive` |
| Compute pin | `vendor/fsot_compute.py` D1D38A… |
| Codon map | `data/64_codon_trinary_map.txt` ≡ `I:\64_codon_trinary_map.txt` |
| Snapshot | `data/archive_snapshot/` |

## Primary entrypoints (run these)

- `python run_archive_pin.py`
- `python run_fsot_bridge.py`
- `python run_stress_suite.py --quick`
- `python run_learning_eeg_study.py`
- `python run_console.py`
- `python scripts/runtime_audit.py`

## Package modules loaded by audit import graph

- `fsot_nuron`
- `fsot_nuron.allen_data`
- `fsot_nuron.archive_pin`
- `fsot_nuron.bio_metrics`
- `fsot_nuron.brain_architecture`
- `fsot_nuron.calibrate`
- `fsot_nuron.cell_types`
- `fsot_nuron.chemical_codon`
- `fsot_nuron.class_ephys`
- `fsot_nuron.fsot_bridge`
- `fsot_nuron.genetic_genotype`
- `fsot_nuron.genetic_network`
- `fsot_nuron.learning_bands`
- `fsot_nuron.learning_eeg_study`
- `fsot_nuron.learning_memory`
- `fsot_nuron.machine_encode`
- `fsot_nuron.modes`
- `fsot_nuron.neuron_batch`
- `fsot_nuron.obsidian_brain`
- `fsot_nuron.paths`
- `fsot_nuron.reservoir`
- `fsot_nuron.scalar`
- `fsot_nuron.scalpel_brain`
- `fsot_nuron.scalpel_rate`
- `fsot_nuron.seeds`
- `fsot_nuron.sensory`
- `fsot_nuron.sensory.bus`
- `fsot_nuron.sensory.packets`
- `fsot_nuron.thesis_ledger`
- `fsot_nuron.trinary_substrate`
- `product`
- `product.console`
- `product.console.app`

## Used files (30)

- `fsot_nuron/__init__.py`
- `fsot_nuron/allen_data.py`
- `fsot_nuron/archive_pin.py`
- `fsot_nuron/bio_metrics.py`
- `fsot_nuron/brain_architecture.py`
- `fsot_nuron/calibrate.py`
- `fsot_nuron/cell_types.py`
- `fsot_nuron/chemical_codon.py`
- `fsot_nuron/class_ephys.py`
- `fsot_nuron/fsot_bridge.py`
- `fsot_nuron/genetic_genotype.py`
- `fsot_nuron/genetic_network.py`
- `fsot_nuron/learning_bands.py`
- `fsot_nuron/learning_eeg_study.py`
- `fsot_nuron/learning_memory.py`
- `fsot_nuron/machine_encode.py`
- `fsot_nuron/modes.py`
- `fsot_nuron/neuron_batch.py`
- `fsot_nuron/obsidian_brain.py`
- `fsot_nuron/paths.py`
- `fsot_nuron/reservoir.py`
- `fsot_nuron/scalar.py`
- `fsot_nuron/scalpel_brain.py`
- `fsot_nuron/scalpel_rate.py`
- `fsot_nuron/seeds.py`
- `fsot_nuron/sensory/__init__.py`
- `fsot_nuron/sensory/bus.py`
- `fsot_nuron/sensory/packets.py`
- `fsot_nuron/thesis_ledger.py`
- `fsot_nuron/trinary_substrate.py`

## On disk but not imported by this audit (18)

These may still be used by secondary runners (Morse, NLP climb, EEG emotions demos).
Safe cleanup only after confirming no entrypoint you care about imports them.

- `fsot_nuron/bio_report_card.py`
- `fsot_nuron/deep_readout.py`
- `fsot_nuron/eeg_bands.py`
- `fsot_nuron/eeg_loader.py`
- `fsot_nuron/eeg_sources.py`
- `fsot_nuron/emotions_eeg.py`
- `fsot_nuron/failure_boundaries.py`
- `fsot_nuron/gpu_consensus.py`
- `fsot_nuron/language_loop.py`
- `fsot_nuron/literature_chew.py`
- `fsot_nuron/morse_itu.py`
- `fsot_nuron/multi_dataset.py`
- `fsot_nuron/pd_eeg_depth.py`
- `fsot_nuron/scale_learning.py`
- `fsot_nuron/scale_sweep.py`
- `fsot_nuron/train_readout.py`
- `fsot_nuron/validate.py`
- `fsot_nuron/wire_around_policy.py`

## Mission core (keep)

- fsot_nuron/ (genetic, scalpel, learning, machine_encode, fsot_bridge, sensory)
- product/console/
- embodiment/zig/src/ + build.zig + run_qemu.ps1
- formal/ (Lean panel)
- data/64_codon_trinary_map.txt
- data/archive_snapshot/
- data/neuro_failure_boundaries.json
- run_archive_pin.py
- run_fsot_bridge.py
- run_machine_encode.py
- run_scalpel_rates.py
- run_intelligence_probe.py
- run_learning_eeg_study.py
- run_stress_suite.py
- run_console.py
- run_genetic_bio.py
- run_brain_design.py
- scripts/parity_zig_neuron.py
- scripts/runtime_audit.py
- scripts/review_console_displays.py
- scripts/ci_smoke.py
- docs/ (thesis, bio, learning, stress, runtime inventory)
- MISSION.md
- CHECKPOINT_v0.5.md
- requirements.txt
- pyproject.toml

## Secondary / optional

- run_language_loop.py / morse_itu (secondary Morse)
- run_climb.py / multi_dataset NLP scoreboards
- data/itu_morse.json
- data/literature/*

## Local-only (must not confuse GitHub repro)

- data/external/** (NLP/IMDB downloads — gitignored)
- data/kaggle_datasets/**/*.csv (large — gitignored)
- data/eeg/allen_ephys/*.nwb (gitignored)
- artifacts/ (runtime — gitignored json)
- embodiment/zig/.zig-cache / zig-out (gitignored)
- files-3ccbc49e/ (legacy dump — should NOT be on GitHub)
- __pycache__/

## Cleanup candidates (workspace size)

- files-3ccbc49e/ — old morse/shakespeare experiments; not imported by mission
- data/external/nlp/* — IMDB/sentiment; mission says NLP secondary only
- data/results/* deep_nlp_*, multi_dataset_scoreboard, sota_fronts — demo scoreboards
- notebooks/ if empty or outdated
- dist/ build leftovers

## GitHub hygiene

- Tracked file count should stay small (~mission + docs + thin data).
- Large CSVs/NWB under `data/external` and kaggle paths are **gitignored**.
- `files-3ccbc49e/` must stay **untracked** (legacy).
- `artifacts/*.json` gitignored; keep `data/results/*.md` summaries if useful.

JSON: `artifacts/runtime_audit.json`
