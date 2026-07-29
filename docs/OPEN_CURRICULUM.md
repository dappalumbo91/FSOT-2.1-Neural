# Open curriculum (PK → K → G1)

## The point

People have taught children for millennia. **Public curriculum material exists.**  
We do **not** invent a toy 12-fact pack and call it grade 1.

## What we use (open / public)

| Source | Content |
|--------|---------|
| Arithmetic tables 0–10, count 0–20 | Public-domain math |
| Dolch sight words (pre-primer, primer, 1st) | Classic public literacy lists |
| Letter → sound / letter starts word | Standard early phonics practice |
| Primer science / body / safety facts | OER-style short facts |
| Digit names 0–9 + vision feature probe | Open digit learning (MNIST inject optional) |

**Not used (yet):** proprietary textbooks, paid curricula, history tracks.

## Build the bank

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
python run_curriculum_open.py
```

Writes:

- `data/curriculum/pk_k_g1/facts.jsonl`
- `data/curriculum/pk_k_g1/problems.jsonl`
- `data/curriculum/pk_k_g1/bank.tsv`  ← Zig loads this
- `data/curriculum/pk_k_g1/MANIFEST.json`

Typical size after generate: **~1500 bank rows**, **~900 facts**, heavy on **math**.

## Run the student ladder

```powershell
cd embodiment\zig
zig build
.\zig-out\bin\fsot_mind.exe ladder
```

Straight-A rule: **≥95% overall and ≥95% per domain** (math, science, literacy, vision) before advancing PK → K → G1.

## Optional: real MNIST pixels

```powershell
python run_kaggle_multimodal.py --mnist --limit 64
# then inject into mind (vision path)
```

Ladder vision domain currently uses **distinct 8-D digit prototypes** (MNIST-style projection stand-in) with held-out jitter. Full MNIST accuracy gating can be wired next on the same domain bar.

## Doctrine

1. Prefer open packs over LLM-invented fluff.  
2. Ollama teacher is optional expansion, not the curriculum.  
3. Ship `bank.tsv` on GitHub so anyone can clone and run offline.
