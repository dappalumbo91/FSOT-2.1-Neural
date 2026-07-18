# Long-context / capacity suite

Generated: `2026-07-18T20:36:17.307713+00:00`

| Dataset | Test | Bal | Long | Feats | Chunks | Steps/chunk |
|---------|------|-----|------|-------|--------|-------------|
| imdb_50k/IMDB Dataset.csv | **0.556** | 0.556 | True | 160 | 6 | 560 |
| sentiment_tiny/sentiment_analysis.csv | **0.565** | 0.565 | False | 64 | 1 | 400 |
| financial_sentiment/data.csv | **0.352** | 0.352 | False | 64 | 1 | 400 |
| sms_spam/spam.csv | **0.833** | 0.833 | False | 64 | 1 | 400 |
| twitter_entity_sentiment/twitter_training.csv | **0.239** | 0.239 | False | 64 | 1 | 400 |
| financial_news_sentiment/all-data.csv | **0.315** | 0.315 | False | 64 | 1 | 400 |
| sentiment_tiny/sentiment_analysis.csv [forced_long] | **0.488** | 0.489 | True | 160 | 6 | 560 |

Hierarchical path: document → overlapping chunks → per-chunk Morse/reservoir (head+tail sample if overlength) → mean/max/std/first/last pool → deeper FSOT-gated MLP.
