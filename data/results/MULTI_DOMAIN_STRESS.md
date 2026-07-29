# Multi-domain stress scoreboard

Time: `2026-07-29T11:11:47.859889+00:00`
OK: **True**  pass **6/6**  mean_score=**95.0**

| Domain | OK | Score | Key metrics |
|--------|:--:|------:|-------------|
| `authority_allen` | Y | 98.1 | pin=True, seed_ok=True, mean_rel_err=0.0018622511265274414 |
| `learning_sme` | Y | 90.9 | top1=0.9, margin=0.27880460317233796, gates=7/7, sme_theta=True |
| `documents_science` | Y | 100.0 | hit_rate=1.0, n=16 |
| `narrative_text` | Y | 85.8 | hit_rate=1.0, groundedness=0.7169959346906222 |
| `media_av` | Y | 98.2 | pixel_id_top1=0.75, caption_vote_top1=1.0, purity=0.91122852904456, n_names=7 |
| `short_horizon_5w1h` | Y | 97.0 | recall_top1=0.9130434782608695, recall_at_k=1.0, pixel_id=1.0, caption=1.0 |

## Notes

- 5W1H teaching structure used for docs/narrative/short-horizon.
- Not human-level comprehension — multi-domain organism stress.
- phi-gate=0.6180
- [learning_sme] scalpel_ok=True meta={'profile': 'ai_efficient', 'scalpel_ok': True, 'tol': 0.02, 'class_rel_err': {'Pyr': 0.019292187062748573, 'PV': 0.00020478653748109567, 'SST': 0.006930677405623652}, 'class_measured_Hz': {'Pyr': 16.66666603088379, 'PV': 83.33333587646484, 'SST': 29.33333396911621}, 'labels_count': {'PV': 4, 'SST': 2, 'Pyr': 26}}
- [learning_sme] Learning-layer gate pass 7/7 (SME direction + retrieval; not film comprehension).
- [documents_science] docs=4 probes=16 hit=16
- [narrative_text] 5w1h_hits=5/5 monologue_g=0.717
- [media_av] pixel_top1=0.750 cap_vote=1.000 purity=0.911 synthetic=False
- [short_horizon_5w1h] pin=True mode=standalone
- [short_horizon_5w1h] media videos encoded: ['300.Rise.of.an.Empire.2014.1080p.BluRay.x264.YIFY.mp4', 'Aladdin.1992.720p.BRrip.x264.GAZ.YIFY.mp4']
- [short_horizon_5w1h] pixel_id top1=1.000 synthetic=False mode=retina_real_media_rf_cascade
