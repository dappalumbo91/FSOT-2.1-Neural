# Wet biophysics + full stochastic single-channel kinetics (Zig Fixed)

## No continuous-P_open shortcut for receptors

Receptor current is **not** `g = P_open(glu,V)`.  
Each spine has **physical channels** with Markov states updated by Bernoulli trials.

## Per spine

| Layer | Implementation |
|-------|----------------|
| Quantal release | Binomial `N_VESICLES=8`, `p_release` → glu quanta (`channel_stoch_fixed`) |
| AMPA | **12** channels: C ↔ O → D → C |
| NMDA | **8** channels: C ↔ O ↔ B(Mg) / D |
| PRNG | Integer xorshift64* (no IEEE float) |
| Transition | `P = clamp(rate·dt, 0, 1)` then Bernoulli |
| Ca²⁺ | Unitary current × **open NMDA count** |
| Downstream | CaMKII, PP1, AMPA traffic, late protein (Fixed ODEs) |
| Glia | EAAT scale on glu clearance |
| STDP | × spine eligibility (includes open channel counts) |

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
