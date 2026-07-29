# Zig mind stress + wet-lab parity
Generated: `2026-07-29T13:16:55.235441+00:00`  
Duration: 6.98s  

## Critical gates

| Gate | OK |
|------|----|
| neuron_scalar | True |
| neuron_trace | True |
| zig_codon_genetic | True |
| zig_bio_pass | True |
| zig_stress | True |
| zig_learn | True |
| wetlab_rate_band | True |

## Soft / scientific agreement

| Gate | OK |
|------|----|
| fi_rate_parity | True |
| fi_isi_parity | True |
| fi_adapt_parity | True |
| wetlab_isi | True |
| wetlab_adapt | True |

## Metrics

```json
{
  "max_abs_dS": 1.4955135163585709e-06,
  "spike_mismatch": 0,
  "scalar_py": 0.43231972120140144,
  "scalar_zig": 0.43231972120140144,
  "zig_bio": {
    "BIO_FI_n_units": 32.0,
    "BIO_FI_mean_rate_Hz": 17.916666666666668,
    "BIO_FI_mean_isi_ms": 70.43858871872852,
    "BIO_FI_mean_adapt": 0.08171378586781533,
    "BIO_FI_mean_isi_cv": 0.07965832116594439,
    "BIO_FI_mean_S": 0.3041942214888066,
    "BIO_FI_mean_Vm_mV": -82.46446228089546,
    "BIO_FI_total_spikes": 688.0,
    "BIO_FI_n_with_isi": 32.0
  },
  "python_bio": {
    "mean_rate_Hz": 17.916666666666668,
    "mean_isi_ms": 70.29625290632248,
    "mean_adapt": 0.07873139827279374,
    "mean_isi_cv": 0.07597405345442514,
    "mean_S": 0.0,
    "mean_Vm_mV": -82.22042957436113
  },
  "fi_rate_rel_err": 0.0,
  "fi_isi_rel_err": 0.002024799424170216,
  "fi_adapt_abs_err": 0.0029823875950215906,
  "wetlab": {
    "isi_rel_err_vs_allen": 0.0879650217194252,
    "isi_gate": true,
    "adapt_abs_err_vs_allen": 0.025408632978829587,
    "adapt_gate": true,
    "rate_band": true
  },
  "allen_target_isi": 77.23233252689907,
  "allen_target_adapt": 0.05630515288898574,
  "genetic": {
    "scn_expr": 1.432850377557623,
    "pyr_spin": 0.1044915460095421,
    "pv_ref": 7.345395478406609
  },
  "stress": {
    "STRESS_UNIT_rate_Hz": 14.0,
    "STRESS_UNIT_isi_ms": 71.84615384615384,
    "STRESS_UNIT_adapt": 0.00348432053321031,
    "STRESS_UNIT_spikes": 14.0,
    "STRESS_FI_n_units": 32.0,
    "STRESS_FI_mean_rate_Hz": 13.0,
    "STRESS_FI_mean_isi_ms": 76.75,
    "STRESS_FI_mean_adapt": 0.0048939640789953396,
    "STRESS_FI_mean_isi_cv": 0.007753993950643696,
    "STRESS_FI_mean_S": -0.34992523128665304,
    "STRESS_FI_mean_Vm_mV": -134.79401850293226,
    "STRESS_FI_total_spikes": 416.0,
    "STRESS_FI_n_with_isi": 32.0,
    "STRESS_PERIODIC_n_units": 16.0,
    "STRESS_PERIODIC_mean_rate_Hz": 23.4375,
    "STRESS_PERIODIC_mean_isi_ms": 42.022338321293425,
    "STRESS_PERIODIC_mean_adapt": 0.035521750648515635,
    "STRESS_PERIODIC_mean_isi_cv": 0.0,
    "STRESS_PERIODIC_mean_S": 0.3240812937051543,
    "STRESS_PERIODIC_mean_Vm_mV": 0.0,
    "STRESS_PERIODIC_total_spikes": 300.0,
    "STRESS_PERIODIC_n_with_isi": 16.0,
    "STRESS_NET_spikes": 208.0,
    "STRESS_NET_mean_S": -0.14840340817915237,
    "STRESS_NET_rate_Hz": 16.25,
    "STRESS_BRAIN_spikes": 95.0,
    "STRESS_BRAIN_mean_S": -0.22714819598579428,
    "STRESS_LEARN_top1": 1.0,
    "STRESS_LEARN_correct": 6.0,
    "STRESS_ORG_ticks": 60.0,
    "STRESS_ORG_episodes": 3.0,
    "STRESS_ORG_curiosity": 2.0
  },
  "learn_top1": 1.0
}
```

**critical_ok**=True **soft_ok**=True

Doctrine: neural authority is Zig; Python used here only for Allen map + parity lab.
