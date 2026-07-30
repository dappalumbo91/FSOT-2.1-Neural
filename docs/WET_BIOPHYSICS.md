# Wet biophysics + refined stochastic single-channel kinetics (Zig Fixed)

## Time base (no more vague “ms-class handwave”)

| Scale | Value |
|-------|--------|
| Network tick | **1 ms** |
| Channel Markov dt | **50 µs** |
| Channel steps / ms | **20** |
| Transition law | **P = 1 − exp(−k·dt)** (Fixed `exp`) |
| Competing exits | rate-weighted choice among transitions |

## Single-channel (not continuum P_open)

| Layer | Implementation |
|-------|----------------|
| Quantal release | **12 release sites**, binomial + **site refractory** |
| AMPA | **48** channels: **C0 → C1 → O**, **D** desens (multi-binding) |
| NMDA | **16** channels: **C0 → C1 → O ↔ B_Mg**, **D** |
| PRNG | Integer xorshift64* only |
| Ca²⁺ | Unitary current × **open NMDA count** |
| Downstream | CaMKII, PP1, AMPA traffic, late protein (Fixed ODEs) |
| Glia | EAAT scale on glu clearance |
| STDP | × spine eligibility (open counts + cascade) |

Still **not** all-atom MD. This is synapse-scale stochastic single-channel Markov at biophysically motivated rates.

## Files

- `channel_stoch_fixed.zig` — Markov channels + quantal release + RNG  
- `molecular_fixed.zig` — spine chemistry + channels  
- `glia_fixed.zig` — astro/micro/oligo  
- `stdp_fixed.zig` — timing plasticity  

## Run

```powershell
cd embodiment\zig
zig build -Doptimize=ReleaseFast
.\zig-out\bin\fsot_mind.exe glia
```

Expect:

```text
channel_stoch=true
ch_tx=… ampa_o=… nmda_o=… quanta=… silent0=…
FSOT_GLIA_MOLECULAR_OK
```

`silent0` = release attempts that failed all vesicles (true quantal failure).
