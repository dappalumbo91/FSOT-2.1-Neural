# STEM multimodal expansion (no history)

**Archive root:** `I:\FSOT-Physical-Archive` — FSOT theory + prior brain-state checkpoints.  
**Student mind:** Zig Fixed lattice + machine language ([fsot-neuron-zig](https://github.com/dappalumbo91/fsot-neuron-zig)).  
**Lab data:** monorepo + Kaggle CLI (authenticated).

## Doctrine

| Do | Don't |
|----|--------|
| Math, science, reading, writing | History / politics / culture-war corpora |
| Facts + problem-solving | LLM as the mind |
| Kaggle STEM images → vision features → tokens | Unfiltered web scrape as identity |
| Checkpoint organism state (save-game) | Lose learning between runs |

Multimodal = **same machine language**, extra modalities:

```text
Kaggle image/label
  → 8-D vision features + label text features
  → inject file (Zig already parses)
  → encode episode + lexicon digit words
  → quiz / reason / novel (later)
```

## Why Kaggle (not random web)

- Licensed datasets, reproducible `kaggle datasets download`
- You already have CLI credentials
- MNIST / science / literacy vision packs map cleanly to **digit / object / word** learning
- No need for DuckDuckGo for v1; optional later for open images with hard allowlists

## Commands

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"

python run_kaggle_multimodal.py --catalog
python run_kaggle_multimodal.py --mnist --limit 32

# Zig (Windows TEMP build)
$out = "$env:TEMP\fsot_mind_live.exe"
# ... build main_mind ...
& $out inject-file "I:\fsot nuron\data\multimodal\inject\mnist_digits_inject.txt"
```

## Curriculum ladder (toward HS graduate — stepwise)

| Band | Math | Science | Reading/Writing |
|------|------|---------|-----------------|
| PK–G1 | count, add | body, plants, sky | letters, simple words |
| G2–G5 | mult, fractions intro | matter, energy intro | sentences, paragraphs |
| G6–G8 | algebra prep, ratio | life/earth systems | evidence sentences |
| G9–G12 | algebra/geometry/stats | bio/chem/phys intro | essays on STEM only |

**No history track until STEM reasoning is solid.**

## Checkpoint (biological save-game)

See `src/checkpoint_fixed.zig` (organism episodes + tick + seed).  
Like LLM checkpoint / game save: resume connective learning without re-teaching from zero.

## Reproducibility

1. Commit inject samples + curriculum JSONL when gates pass.  
2. Push monorepo + **fsot-neuron-zig**.  
3. Teacher (Ollama) optional; student runs offline from artifacts.
