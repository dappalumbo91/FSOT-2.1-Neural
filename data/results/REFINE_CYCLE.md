# Refine cycle

Threshold: **70.0%**  
Target: `open_world_pixel_id`  
Score: **69.33333333333333** → **69.33333333333333**

## Rule

Among layers **below** threshold, refine the **highest** score first.

## Notes

- scored 14 layers; threshold=70.0; domain=all
- TARGET (highest below threshold): open_world_pixel_id score=69.3 < 70.0
- applying fix: refine_pixel_id
- fix result: before=69.33333333333333 after=69.33333333333333 improved=True

## All layers (after)

- [ok] 96.3% `cell_class_rates`
- [ok] 99.4% `ei_microcircuit`
- [ok] 100.0% `thalamic_sensory_gate`
- [ok] 78.0% `retina_like_decode`
- [ok] 72.0% `cochlea_like_decode`
- [ok] 78.0% `fly_connectome_motifs`
- [ok] 85.0% `eeg_learning_bands`
- [ok] 72.0% `episodic_memory`
- [ok] 88.0% `information_accuracy`
- [ok] 74.0% `cross_modal_binding`
- [ok] 72.0% `language_dialogue`
- [below] 69.3% `open_world_pixel_id`
- [ok] 72.0% `self_curriculum`
- [ok] 72.0% `free_monologue`

JSON: `I:\fsot nuron\artifacts\refine_cycle_last.json`
