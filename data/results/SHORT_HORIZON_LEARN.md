# Short-horizon learning

Time: `2026-07-28T20:13:43.897143+00:00` → `2026-07-28T20:14:01.725675+00:00` (0.30 min)
OK: **True**

- docs=3 media=3 memories=7
- recall top1=**0.917** recall@3=**1.000**
- pixel_id top1=**0.583** synthetic=False
- caption↔pixel binds=**32** names=**63** pixel→name top1=**0.000**
- learning_probe top1=**0.700** margin=0.263
- SME θ/γ: True / True

## Notes

- pin=True mode=standalone
- media videos encoded: ['300.Rise.of.an.Empire.2014.1080p.BluRay.x264.YIFY.mp4', 'Aladdin.1992.720p.BRrip.x264.GAZ.YIFY.mp4', 'Alice.in.Wonderland.2010.1080p.BluRay.x264.YIFY.mp4']
- pixel_id top1=0.583 synthetic=False mode=retina_real_media_rf_cascade
- caption_bind binds=32 names=63 pixel→name top1=0.000 heldout=0
- learning_probe top1=0.700 margin=0.263 smeθ=True smeγ=True scalpel=True
