# Short-horizon learning

Time: `2026-07-28T20:21:47.160811+00:00` → `2026-07-28T20:22:04.196284+00:00` (0.28 min)
OK: **True**

- docs=3 media=3 memories=7
- recall top1=**0.917** recall@3=**1.000**
- pixel_id top1=**0.667** synthetic=False
- caption↔pixel binds=**36** names=**4** pixel→name top1=**1.000**
- learning_probe top1=**0.900** margin=0.347
- SME θ/γ: True / True

## Notes

- pin=True mode=standalone
- media videos encoded: ['300.Rise.of.an.Empire.2014.1080p.BluRay.x264.YIFY.mp4', 'Aladdin.1992.720p.BRrip.x264.GAZ.YIFY.mp4', 'Alice.in.Wonderland.2010.1080p.BluRay.x264.YIFY.mp4']
- pixel_id top1=0.667 synthetic=False mode=retina_real_media_rf_cascade
- caption_bind binds=36 names=4 pixel→name top1=1.000 vote=1.000 purity=0.897 heldout=6
- learning_probe top1=0.900 margin=0.347 smeθ=True smeγ=True scalpel=True
