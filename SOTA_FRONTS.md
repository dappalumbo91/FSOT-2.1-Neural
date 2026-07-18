# SOTA fronts — data + refinement

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
| SMS spam | **~0.90–0.93** | 2 | Strong binary |
| Sentiment tiny | **~0.49–0.51** | 3 | Climbing (was 0.27 linear early) |
| Financial sentiment | **~0.36–0.43** | 3 | Open |
| Financial news | ~0.33–0.35 | 3 | Open |
| IMDB 50k sample | ~0.48–0.50 | 2 | Needs longer context / capacity |
| Twitter entity | ~0.27–0.40 | 4 | Open |
| Social media | ~0.23 | 19 | Hard multi-class |

Method: Morse → FluidReservoir → time-pool fingerprint → **FSOT-gated multi-layer probe**.

## EEG bands

- CSV band proxies from emotions / mental-state / external EEG feature tables
- EDF lightweight reader ready when `.edf` files appear on I:/D:
- Results: `data/results/eeg_bands_suite.json`

## Scale under learning

- Encode load ~4 docs/s at 8–64 units (CPU reservoir path)
- Probe train on CPU/CUDA measured in `data/results/scale_learning.json`
- Encode still dominates; next climb is GPU-side reservoir encode

## How to re-run

```powershell
cd "I:\fsot nuron"
$env:PYTHONPATH = "I:\fsot nuron"
python run_sota_fronts.py
```

## Next climb order

1. Sentiment / financial 3-class — richer Morse-time attention (learned pool) + more samples  
2. IMDB — longer sequences, hierarchical reservoir  
3. GPU encode path for scale-under-learning  
4. Full OpenNeuro EDF PD segments when available on external drive  
