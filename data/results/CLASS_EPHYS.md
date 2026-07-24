# Class ephys — Allen wet-lab → FSOT

Generated: `2026-07-24T18:04:22.226972+00:00`

## Wet-lab targets (mouse Cre lines)

- **PV** (n=222): ISI 20.3 ms, rate 83.4 Hz, adapt 0.009
- **Pyr** (n=723): ISI 83.5 ms, rate 16.4 Hz, adapt 0.062
- **SST** (n=155): ISI 64.0 ms, rate 29.5 Hz, adapt 0.094
- **VIP** (n=149): ISI 47.5 ms, rate 34.8 Hz, adapt 0.056

## Simulation (class-locked FI)

- **PV**: rate 29.2 Hz, ISI 31.8 ms
- **Pyr**: rate 10.8 Hz, ISI 90.3 ms
- **SST**: rate 12.5 Hz, ISI 76.0 ms
- **VIP**: rate 15.0 Hz, ISI 61.8 ms

## Gates

- `sim_pv_rate_gt_pyr`: **True**
- `sim_pv_isi_lt_pyr`: **True**
- `wet_lab_pv_faster_than_pyr`: **True**
- `has_pv_target`: **True**
- `has_pyr_target`: **True**

See `docs/BIO_ACCURACY.md` for how we use wet-lab data without owning a lab.
