# FSOT 2.1 verification linkage

This repository is the **neural substrate** application of FSOT 2.1.  
It does **not** re-derive the multi-domain formal verification already held in the Lean hub.

## Theory authority (required pin)

| Layer | Location |
|-------|----------|
| **Physical master** | `I:\FSOT-Physical-Archive` |
| **Canonical Lean hub** | `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full` |
| **Public theory** | [FSOT-2.1-Lean](https://github.com/dappalumbo91/FSOT-2.1-Lean) |
| **Compute authority** | `vendor/fsot_compute.py` (SHA256 pinned in certificate) |

### Connect this repo to the archive

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"
python run_archive_pin.py
python run_archive_pin.py --apply-env   # print FSOT_* env for this machine
```

What `run_archive_pin.py` does:

1. Resolves archive + Lean hub via `ARCHIVE_MANIFEST.json`  
2. Hashes `vendor/fsot_compute.py` and compares to certificate authority  
3. Reads `certificate.json` (lean_build_ok, sorry=0, 65 claims) and cross-proof report  
4. Checks local `fsot_nuron.seeds` against archive closed-form formulas  
5. Writes offline snapshots under `data/archive_snapshot/`  

After a successful pin you should see `connected: True` and `seed_match_ok: True`.  
If `compute_matches_cert: False`, the archive has **hash drift** (neural seeds still OK via formulas; re-pin theory hub before claim-sensitive theory publishes).

### Snapshot files (shipped when archive was present)

| File | Role |
|------|------|
| `data/archive_snapshot/pin.json` | Compact pin report |
| `data/archive_snapshot/certificate.json` | Full certificate copy (when available) |
| `data/archive_snapshot/cross_proof_verification_report.json` | Cross-proof ledger copy |
| `data/archive_snapshot/ARCHIVE_MANIFEST.json` | Archive policy copy |

## What is verified in the Lean hub

- Seed scalar spine \(S = K(T_1+T_2+T_3)\) with zero free parameters on the theory path  
- Multi-prover stack (Lean + Coq + Isabelle + F* + Rust + QEMU; ESP32 optional)  
- Extension domain panels and certificate claims  

## What this repo adds

| Layer | Role | Precision style |
|-------|------|-----------------|
| Batched micro-neuron | Apply scalar + timing to small nets | Allen pop-mean ISI/adapt lock |
| Failure boundaries | Known neurological break modes → lesions | Signature + wire-around |
| Morse (ITU) | Symbolic readout alphabet | Exact table round-trip |
| Chemical codon | Generative meaning (64-codon trinary) | 64/64 map invertibility; SMILES Lab bar |
| Consensus | No-softmax attention from FSOT-GPU | Owned operators |
| Multi-dataset scoreboard | EEG fit + text retrieval probes | Honest metric names |

## How to cite

1. **FSOT-2.1-Lean** commit / certificate `generated_at` as theory authority  
2. **This repo** commit for substrate implementation  
3. Local data roots (Allen ephys, OpenNeuro, Kaggle third-party CSVs as third-party)  
4. `data/archive_snapshot/pin.json` when offline

## Smoke checks (this repo)

```powershell
$env:PYTHONPATH = "."
python run_archive_pin.py
python run_language_loop.py --verify-only
python run_bio_validate.py --mode bio_match --primary-only
python run_failure_probe.py --mode all
python run_gpu_consensus.py --text "FSOT 2.1" --failure-mode PD_rate_irregularity
```

## Kaggle

Public notebook path already exercised (emotions + Morse chew). See `KAGGLE_RUNBOOK.md`.  
Do **not** re-upload third-party CSVs as your own dataset.
