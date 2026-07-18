# FSOT-2.1-Neural — Results

Generated: `2026-07-18T18:43:12.768004+00:00`  
Repo: https://github.com/dappalumbo91/FSOT-2.1-Neural  
Theory: https://github.com/dappalumbo91/FSOT-2.1-Lean (`D1D38A` authority)

## 1. Quality gates

- CI smoke: **PASS**
- Morse/codon verify: **see smoke**

## 2. Multi-dataset scoreboard (hard metrics)

- **eeg_mental_state/mental-state.csv** [tabular_signal] rank#1 fit=0.810
- **sms_spam/spam.csv** [text_classification] rank#2 hard_top1=0.800 bal=0.789 fit=0.800
- **kaggle_emotions/emotions.csv** [tabular_signal] rank#3 fit=0.648
- **sentiment_tiny/sentiment_analysis.csv** [text_classification] rank#4 hard_top1=0.475 bal=0.484 fit=0.475

_Full JSON: `data/results/multi_dataset_scoreboard.json`_

## 3. Bio report card (Allen-facing)

- Pass: **True**
- ISI rel error: **0.017594553080667527**
- Adapt rel error: **0.1969071974345275**
- Gaps: **5/6**

_Details: `data/results/bio_report_card.md`_

## 4. PD EEG depth

- Local EEG candidates: 40
- Signal files scored: 10
- Probe summary: `{"mode_id": "PD_rate_irregularity", "label": "Parkinson-like rate irregularity / sync pressure", "breached": true, "signature_hits": ["rate_drop"], "relative_flags": {"rate_drop": true, "rate_runaway": false, "isi_prolonged": false, "adaptation_runaway": false, "global_silence": false, "population_s`

## 5. Train/test readout (learned, not LOO retrieval)

- **sms_spam/spam.csv**: train=0.703 test=0.604 bal=0.604 (n_test=48)
- **sentiment_tiny/sentiment_analysis.csv**: train=0.360 test=0.271 bal=0.271 (n_test=48)

## 6. Scale + lesion consensus

- cpu n=64: 175342 unit-steps/s
- cpu n=256: 649063 unit-steps/s
- cpu n=1024: 2506689 unit-steps/s
- cuda n=64: 23084 unit-steps/s
- cuda n=256: 96601 unit-steps/s
- cuda n=1024: 379363 unit-steps/s
- cuda n=4096: 1486435 unit-steps/s

- Lesion consensus backend: `desktop_fsot_gpu`

## Honesty

- Retrieval ≠ diagnosis; train/test readout is a linear probe on FSOT fingerprints.
- Bio card is computational Allen match under tolerances.
- PD path uses local/OpenNeuro priors + optional lightweight signal stats.
