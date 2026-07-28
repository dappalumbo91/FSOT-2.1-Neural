# Hardware body — computer as organism substrate

The neural mind must **not** be permanently bound to one machine.  
On every boot the console **probes** what is available and maps it into interoceptive drives.

## Doctrine

| Principle | Implementation |
|-----------|----------------|
| Portable boot | `discover_hardware()` each launch |
| Graceful degrade | Missing sensors → 0 / omit |
| No free-fit health model | Equal-weight core channels in `MetricPacket.as_drive_scalar` |
| Body language | Machine encode (bytes→trits); Zig = silicon step |
| Autonomic plant | `SYS_METRIC` → thalamus (`metrics_to_thalamic_packet`) |

## Analogies (scientific routing)

| Human | Computer body |
|-------|----------------|
| Circulatory load | CPU util, GPU mem util |
| Energy / reserves | RAM util, disk free |
| Thermoregulation | temp sensors (when psutil exposes them) |
| Nervous I/O | Machine ABI frames, HID (later) |
| Embodied motor plant | Zig host / QEMU guest |

## API

```python
from fsot_nuron.hardware_body import (
    discover_hardware,
    sample_metrics,
    metrics_to_thalamic_packet,
    boot_body_report,
)

hw = discover_hardware()          # n_units / device / dt_ms recommendations
m = sample_metrics(hw)            # live plant sample
pkt = metrics_to_thalamic_packet(m)
report = boot_body_report()       # console Dashboard / Body tab block
```

## Console wiring (v0.6)

- **Dashboard boot:** archive pin + machine ABI + **hardware body report**
- **Body tab:** re-probe · sample interoception · Zig / QEMU
- **Visual tab:** live genetic graph size-capped from `recommended_n_units`; interoception modulates stim every ~2s while thinking

## What is *not* hard-coded

- Absolute core counts, GPU presence, RAM size  
- One specific hostname or drive letter for science paths (archive path is still env-configured)

The organism **adapts** to the body it wakes up in.

## Extended senses & self-modulation (v0.7+)

See [`docs/SELF_MODULATION_AND_SENSES.md`](SELF_MODULATION_AND_SENSES.md):

- Network I/O deltas, HID, log stream, optional audio  
- `self_modulation.modulate_from_metrics` — POOF dampen / SUCTION explore  
- Live Obsidian vault ticks under `artifacts/obsidian_vaults/FSOT_Neural_Live/`
