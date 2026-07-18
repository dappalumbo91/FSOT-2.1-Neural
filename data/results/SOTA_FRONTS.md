# SOTA fronts â€” data + refinement

## Data downloads (external **I:** drive only)

Root: `I:\fsot nuron\data\external`  
Manifest: `data/external/DOWNLOAD_MANIFEST.json`  
(Large CSVs are **not** git-tracked; only the manifest is.)

| Kaggle ref | Local path | Size |
|------------|------------|------|
| jp797498e/twitter-entity-sentiment-analysis | `data/external/nlp/twitter_entity_sentiment` | ~10 MB |
| sbhatti/financial-sentiment-analysis | `data/external/nlp/financial_sentiment` | ~0.7 MB |
| ankurzing/sentiment-analysis-for-financial-news | `data/external/nlp/financial_news_sentiment` | ~2.6 MB |
| lakshmi25npathi/imdb-dataset-of-50k-movie-reviews | `data/external/nlp/imdb_50k` | ~63 MB |
| kashishparmar02/social-media-sentiments-analysis-dataset | `data/external/nlp/social_media_sentiment` | ~0.2 MB |
| samnikolas/eeg-dataset | `data/external/eeg/eeg_samnikolas` | ~4.7 MB |
| birdy654/eeg-brainwave-dataset-feeling-emotions | `data/external/eeg/eeg_emotions_birdy` | ~49 MB |

## Deep FSOT readout (measured)

| Dataset | Test | Classes | Note |
|---------|------|---------|------|
| SMS spam | **~0.90â€“0.93** | 2 | Strong binary |
| Sentiment tiny | **~0.49â€“0.51** | 3 | Climbing (was 0.27 linear early) |
| Financial sentiment | **~0.36â€“0.43** | 3 | Open |
| Financial news | ~0.33â€“0.35 | 3 | Open |
| IMDB 50k sample | ~0.48â€“0.50 | 2 | Needs longer context / capacity |
| Twitter entity | ~0.27â€“0.40 | 4 | Open |
| Social media | ~0.23 | 19 | Hard multi-class |

Method: Morse â†’ FluidReservoir â†’ time-pool fingerprint â†’ **FSOT-gated multi-layer probe**.

## EEG bands

- CSV band proxies from emotions / mental-state / external EEG feature tables
- EDF lightweight reader ready when `.edf` files appear on I:/D:
- Results: `data/results/eeg_bands_suite.json`

## Scale under learning

- Encode load ~4 docs/s at 8â€“64 units (CPU reservoir path)
- Probe train on CPU/CUDA measured in `data/results/scale_learning.json`
- Encode still dominates; next climb is GPU-side reservoir encode

## How to re-run

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
python run_sota_fronts.py
```

## Next climb order

1. Sentiment / financial 3-class â€” richer Morse-time attention (learned pool) + more samples  
2. IMDB â€” longer sequences, hierarchical reservoir  
3. GPU encode path for scale-under-learning  
4. Full OpenNeuro EDF PD segments when available on external drive

## Long-context capacity (latest)

| Dataset | Test | Long | Notes |
|---------|------|------|-------|
| imdb_50k/IMDB Dataset.csv | **0.556** | True | chunks=6 steps/chunk=560 |
| sentiment_tiny/sentiment_analysis.csv | **0.565** | False | chunks=1 steps/chunk=400 |
| financial_sentiment/data.csv | **0.352** | False | chunks=1 steps/chunk=400 |
| sms_spam/spam.csv | **0.833** | False | chunks=1 steps/chunk=400 |
| twitter_entity_sentiment/twitter_training.csv | **0.239** | False | chunks=1 steps/chunk=400 |
| financial_news_sentiment/all-data.csv | **0.315** | False | chunks=1 steps/chunk=400 |
| sentiment_tiny/sentiment_analysis.csv [forced_long] | **0.488** | True | chunks=6 steps/chunk=560 |

IMDB hierarchical long-context: **0.556** (was ~0.48â€“0.50). Sentiment medium-capacity (400 steps, 64-D): **0.565** (best 3-class so far).

## Climb update (learned attention + multi-seed hierarchical)

| Track | Prior | Best now |
|-------|-------|----------|
| IMDB hierarchical | 0.556 | **0.607** (seed 99) |
| Sentiment 3-class deep | 0.565 | **0.581** (seed 42) |
| Financial 3-class deep | ~0.36–0.43 | **0.408** |
| Learned Morse attention | experimental | still weak on multi-class (0.33); hierarchical path leads |

Multi-seed IMDB: 0.560 / 0.583 / **0.607** — capacity is climbing, not noise-only.
See `CLIMB.md` and `data/results/climb_suite.json`.

