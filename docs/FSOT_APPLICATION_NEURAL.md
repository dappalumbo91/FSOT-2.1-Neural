# FSOT application recipe — Neural body

**Authority:** `I:\FSOT-Physical-Archive`  
**Compute pin:** `D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70`  
**Formula:** \(S = K(T_1 + T_2 + T_3)\) — **zero free parameters**  
**Codon map:** `I:\64_codon_trinary_map.txt` ≡ archive Genetics ≡ project `data/64_codon_trinary_map.txt`  
**Doctrine:** `I:\FSOT-Physical-Archive\FSOT_USAGE_DOCTRINE.md`  
**Methodology:** `I:\FSOT_REPRODUCIBLE_METHODOLOGY.md` / archive copy  

---

## 0. What “using FSOT” means here

Not stitching encodings to dynamics. The fat-burn / Monte Carlo recipe:

```text
1. PIN     → vendor/fsot_compute.py + seed match
2. MATCH   → local SEEDS vs archive closed forms (≤1e-12 class)
3. FOLD    → preregistered (D_eff, hits, δψ, observed)
4. BRIDGE  → domain drivers → ScalarInput (seed-folded φ,e,π,γ only)
5. ENGINE  → keep neuron batch / genetic W / sensory bus
6. COUPLE  → S / trinary / poof modulate strength & features
7. MEASURE → Allen / scalpel / intelligence probe
8. FAIL CLOSED if pin or seeds break
```

---

## 1. Domain folds used by this project

| Fold key | D_eff | hits | δψ | observed | Role |
|----------|------:|-----:|---:|:--------:|------|
| Biology | 12 | 0 | 0.08 | no | Chemical/DNA genetics spine |
| Biochemistry | 13 | 1 | 0.35 | yes | Codon→AA process layer |
| Neural_Substrate | 13 | 0 | 0.1 | yes | Neuron batch defaults (N=4, P=3) |
| Neuroscience | 14 | 1 | 0.7 | yes | Atlas neuro S ≈ 0.514 |
| Computer_Body | 11 | 0 | 0.5 | no | Machine/OS I/O (not Morse) |

Canonical atlas checks (N=P=1): Biology S ≈ **0.445**, Neuroscience S ≈ **0.514**.

---

## 2. Machine path vs Morse (body language)

| Path | FSOT role |
|------|-----------|
| **Machine** ★ | OS bytes → lossless bit→trit **transport**; **bridge** payload stats → Computer_Body fold → S modulates sensory |
| **Chemical** | Codon map (A,G=+1; C,T=−1) → Biology fold → S modulates genetic inject |
| **Morse** | Secondary human telegraphy only — **not** a fold of the body |

Transport packing (T1 / `MachineFrame`) is the ABI carrier — same idea as Zig `TritWord`.  
**Meaning and drive** come from \(S\), not from packing alone.

---

## 3. Code entrypoints

```powershell
$env:FSOT_PHYSICAL_ARCHIVE = "I:\FSOT-Physical-Archive"
$env:PYTHONPATH = "I:\fsot nuron"

python run_archive_pin.py          # fail-closed pin
python run_fsot_bridge.py          # folds + machine/chem bridges + inject
python run_machine_encode.py --verify --inject-demo
```

| Module | Role |
|--------|------|
| `fsot_nuron/fsot_bridge.py` | Pin, folds, bridges, couple |
| `fsot_nuron/scalar.py` | Local float twin \(S=K(T1+T2+T3)\) |
| `fsot_nuron/seeds.py` | Seed constants (must match archive) |
| `fsot_nuron/machine_encode.py` | ABI + `encode_to_sensory_packet(use_fsot_bridge=True)` |
| `fsot_nuron/genetic_network.py` | Domain engine: W from seeds + codon spins |

---

## 4. Docs reviewed this session (relevance)

| Doc | Relevant to Neural? |
|-----|---------------------|
| `I:\FSOT-Physical-Archive` + methodology | **Yes — master math** |
| `I:\64_codon_trinary_map.txt` | **Yes — genetic authority** |
| `FSOT_USAGE_DOCTRINE.md` | **Yes — pin/bridge recipe** |
| `AGENTS_BIOHUB.md` / `KAGGLE_*` / `PIXEL_FIRST` / `WIN_PATH_0985` | **Biohub Kaggle only** — same *recipe*, different *domain engine* (U-Net not neurons). Do not import thr/NMS hacks into Neural. |

---

## 5. Forbidden (from doctrine + Biohub lessons)

- Invent free parameters / per-unit LSQ on \(S\)  
- Treat Morse as primary body language  
- “FSOT” graph surgery without pin → fold → bridge  
- Claim science when `seed_match_ok` is false  

---

*Marry systems through the scalar. Keep the domain engine real.*
