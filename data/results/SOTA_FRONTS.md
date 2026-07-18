# SOTA fronts run

Generated: `2026-07-18T18:59:05.764863+00:00`

## Data (external I: drive)

Downloads under `I:/fsot nuron/data/external/` — see `DOWNLOAD_MANIFEST.json`.

## Deep FSOT readout (multi-domain NLP)

- **financial_news_sentiment/all-data.csv**: test=0.333 bal=0.333 classes=3
- **financial_sentiment/data.csv**: test=0.357 bal=0.357 classes=3
- **social_media_sentiment/sentimentdataset.csv**: test=0.230 bal=0.215 classes=19
- **twitter_entity_sentiment/twitter_training.csv**: test=0.398 bal=0.398 classes=4
- **twitter_entity_sentiment/twitter_validation.csv**: test=0.274 bal=0.274 classes=4
- **imdb_50k/IMDB Dataset.csv**: test=0.500 bal=0.500 classes=2
- **sentiment_tiny/sentiment_analysis.csv**: test=0.512 bal=0.512 classes=3
- **sms_spam/spam.csv**: test=0.917 bal=0.917 classes=2

## Linear readout (baseline climb)

- sms_spam/spam.csv: test=0.944 seed_mean=0.907
- sentiment_tiny/sentiment_analysis.csv: test=0.444 seed_mean=0.426

## EEG bands: 5 reports, EDF found=0

## Scale-under-learning: cpu_rows=4 cuda=True
