# Wet-lab accuracy battery

Generated: `2026-07-28T16:09:43.037486+00:00` · **34/36** pass · 13.6s

## Critical failures

_None — no skeptical gaps on critical wet-lab gates._

## Soft / stretch

- **T2/rate_Pyr_within_1pct** measured=`0.012070575883824328` expected=`|err| ≤ 1% (stretch)`
- **T2/rate_SST_within_1pct** measured=`0.010402939410548344` expected=`|err| ≤ 1% (stretch)`

## Full checklist

| Tier | Check | OK | Measured | Expected | Source |
|------|-------|:--:|----------|----------|--------|
| T0 | seeds_match_archive | Y | `7.172083472051352e-15` | <1e-12 class | I:\FSOT-Physical-Archive closed forms |
| T0 | archive_pin_D1D38A | Y | `D1D38A185487B452E470` | D1D38A… | vendor/fsot_compute.py |
| T0 | codon_map_64_roundtrip | Y | `64/64` | 64/64 | data/64_codon_trinary_map.txt (A,G=+1; C |
| T0 | atlas_S_Biology | Y | `0.4447250077038458` | ≈+0.445 | fsot_compute DomainConfig Biology D_eff= |
| T0 | atlas_S_Neuroscience | Y | `0.5143619629083619` | ≈+0.514 | fsot_compute Neuroscience D_eff=14 |
| T0 | fsot_bridge_zero_free | Y | `0` | 0 | S=K(T1+T2+T3) |
| T0 | machine_abi_roundtrip | Y | `{"utf8": true, "frame": true}` | lossless UTF-8 + frame | machine_encode (not Morse) |
| T0 | zig_host_body | Y | `True` | FSOT_TRIT PASS (+ FSOT_FRAME if rebuilt) | I:\fsot nuron\embodiment\zig\zig-out\bin |
| T1 | allen_target_Pyr | Y | `{"n": 723, "rate_Hz": 16.35121532610921}` | public Allen Cre means | Allen Cell Types Database (mouse, min_ce |
| T1 | allen_target_PV | Y | `{"n": 222, "rate_Hz": 83.3504049172855}` | public Allen Cre means | Allen Cell Types Database (mouse, min_ce |
| T1 | allen_target_SST | Y | `{"n": 155, "rate_Hz": 29.538052683455557` | public Allen Cre means | Allen Cell Types Database (mouse, min_ce |
| T1 | allen_target_VIP | Y | `{"n": 149, "rate_Hz": 34.81541758294487}` | public Allen Cre means | Allen Cell Types Database (mouse, min_ce |
| T1 | pv_faster_than_pyr | Y | `{"PV_Hz": 83.84615325927734, "Pyr_Hz": 1` | PV >> Pyr (cortical order) | Allen wet-lab order |
| T2 | rate_Pyr_within_2pct | Y | `{"target_Hz": 16.35121532610921, "measur` | |err| ≤ 2% | Allen Cre FI rate |
| T2 | rate_Pyr_within_1pct | N | `0.012070575883824328` | |err| ≤ 1% (stretch) | Allen Cre FI rate |
| T2 | rate_PV_within_2pct | Y | `{"target_Hz": 83.3504049172855, "measure` | |err| ≤ 2% | Allen Cre FI rate |
| T2 | rate_PV_within_1pct | Y | `0.005947761651353799` | |err| ≤ 1% (stretch) | Allen Cre FI rate |
| T2 | rate_SST_within_2pct | Y | `{"target_Hz": 29.538052683455557, "measu` | |err| ≤ 2% | Allen Cre FI rate |
| T2 | rate_SST_within_1pct | N | `0.010402939410548344` | |err| ≤ 1% (stretch) | Allen Cre FI rate |
| T2 | rate_VIP_within_2pct | Y | `{"target_Hz": 34.81541758294487, "measur` | |err| ≤ 2% | Allen Cre FI rate |
| T2 | rate_VIP_within_1pct | Y | `0.005745460888920435` | |err| ≤ 1% (stretch) | Allen Cre FI rate |
| T2 | scalpel_all_focus_2pct | Y | `True` | True | scalpel_calibrate tol=0.02 |
| T3 | mental_state_eeg_loaded | Y | `{"concentrating": 830, "neutral": 830, "` | concentrate/neutral/relaxed public EEG | I:\fsot nuron\data\kaggle_datasets\eeg_m |
| T3 | study_theta_elevated_vs_rest | Y | `1.573884113069094` | >1.0 (concentrate > relax energy proxy) | public mental-state EEG feature matrix |
| T3 | literature_sme_priors | Y | `["sederberg_2003_sme", "creery_2022_cons` | Sederberg SME + Creery consolidation | iEEG literature (coded priors) |
| T3 | sme_theta_encode_gt_rest | Y | `True` | True | Sederberg-style direction on spike-band  |
| T3 | sme_gamma_encode_gt_rest | Y | `True` | True | Sederberg-style direction on spike-band  |
| T3 | consolidate_top1_ge_half | Y | `0.625` | ≥0.5 | FSOT machine items + offline replay |
| T3 | consolidate_above_chance | Y | `0.625` | > 0.125 | 8-item chance floor |
| T4 | gene_ORF_SCN | Y | `{"n_codons": 6, "dna": "ATGAAATTTCGTTATT` | ≥4 codons DNA ORF | codon map + standard genetic code → phen |
| T4 | gene_ORF_KCN | Y | `{"n_codons": 6, "dna": "ATGCTGGTTTCATCTT` | ≥4 codons DNA ORF | codon map + standard genetic code → phen |
| T4 | gene_ORF_CACNA | Y | `{"n_codons": 6, "dna": "ATGGATGAGTGTTATT` | ≥4 codons DNA ORF | codon map + standard genetic code → phen |
| T4 | gene_ORF_LEAK | Y | `{"n_codons": 6, "dna": "ATGGGTGCAAGCTCTT` | ≥4 codons DNA ORF | codon map + standard genetic code → phen |
| T4 | genotype_diversity | Y | `5` | ≥2 unique composite spins | codon-derived spins |
| T4 | genetic_synapses_nonempty | Y | `128` | seed-folded W from trinary spins | trinary_pair_interaction + φ geometry |
| T4 | genetic_step_finite_S | Y | `0.28540849685668945` | finite S | FSOTNeuronBatch + genetic W |

Authority: Allen Cell Types · 64-codon map · archive D1D38A · study EEG · SME literature.
