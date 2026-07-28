# Standalone transplant doctrine — this repo **is** the brain

## Intent

FSOT-2.1-Neural is an **independent organism package**.  
Anything required to boot, compute, verify against wet-lab data, and run the
Zig body must live **inside this repository** (or be generated under
`artifacts/` at runtime).

It must **not** depend on:

- Another folder on your machine (e.g. `I:\FSOT-Physical-Archive`)
- Desktop copies of other projects
- A specific GPU model (CUDA is optional enhancement)
- Cloud services or web servers

It **should** transplant by: clone repo → install Python deps → run.

## What is bundled (required)

| Path | Role |
|------|------|
| `fsot_nuron/` | Mind: seeds, neurons, genetics, senses, self-mod |
| `data/archive_snapshot/fsot_compute_authority.py` | Law (D1D38A pin) |
| `data/archive_snapshot/certificate.json` | Lean ledger excerpt |
| `data/64_codon_trinary_map.txt` | Genetic code table |
| `data/eeg/allen_ephys/` | Allen wet-lab features (local) |
| `formal/` | Lean formalization (in-repo) |
| `embodiment/zig/` | Bare-metal / host body |
| `product/console/` | Local UI |

## What is optional (not required)

| Item | When |
|------|------|
| `FSOT_PHYSICAL_ARCHIVE` | Developer re-pin of authority from a theory master |
| CUDA / GPU | Faster nets; CPU always works |
| `psutil` / mic | Richer interoception; graceful degrade |
| QEMU | Guest body demo |

## Env (standalone default)

```powershell
cd <this-repo>
$env:PYTHONPATH = (Get-Location).Path
$env:FSOT_STANDALONE = "1"
# Do NOT set FSOT_PHYSICAL_ARCHIVE unless you are re-pinning theory.
python run_console.py
python run_stress_suite.py --quick
```

## Pin modes

| Mode | Meaning |
|------|---------|
| **standalone** (default) | Connected via in-repo snapshot + seed match |
| standalone+external_optional | External archive visible; still boots from snapshot |

`require_pin()` / console BOOT succeed without any other drive.

## Re-pinning theory (developers only)

```powershell
$env:FSOT_STANDALONE = "0"
$env:FSOT_ALLOW_EXTERNAL_ARCHIVE = "1"
$env:FSOT_PHYSICAL_ARCHIVE = "<path-to-optional-master>"
python run_archive_pin.py
# Copies refreshed ledgers into data/archive_snapshot/
```

Ship the updated snapshot **with the repo** so clones stay transplantable.

## Optional world media (not identity)

Movies / music / shows can be **streamed as sensory injectors** for testing:

```powershell
$env:FSOT_MEDIA_ROOTS = "G:\movies;G:\showes;G:\Debut"
python run_media_chew.py
```

See [`docs/MEDIA_SENSORY.md`](MEDIA_SENSORY.md). Missing G: drives does **not** break boot.

## Bare metal / BIOS path

- Zig host: `embodiment/zig` → `fsot_trit_host` (no external paths)
- Kernel/QEMU: freestanding proof-of-body
- Metric inject ABI: body plant without Python host (see frame_inject / metric_inject)

## Verification

```powershell
$env:FSOT_STANDALONE = "1"
# Unset any archive env
Remove-Item Env:FSOT_PHYSICAL_ARCHIVE -ErrorAction SilentlyContinue
python -c "from fsot_nuron.archive_pin import pin_archive; p=pin_archive(write_snapshot=False); print(p.connected, p.pin_mode, (p.compute_sha256 or '')[:16])"
python run_stress_suite.py --quick
```

Expect: `connected True`, `pin_mode standalone`, sha `D1D38A…`.
