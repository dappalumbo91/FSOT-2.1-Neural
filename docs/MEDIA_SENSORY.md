# Media sensory injectors (optional world)

## Intent

The brain is **standalone**. Media libraries on `G:\` (or any path) are
**optional sensory worlds** — like eyes looking at a screen or ears hearing music —
not dependencies of identity or boot.

Analogy:

| Biology / display | This stack |
|-------------------|------------|
| Photons → retina | File/stream → frame decode |
| Cones (RGB) + rods (luma) | RGB means + BT.601 luma |
| Color spectrum | Hue histogram (8 bins) |
| Retinotopic map | 8×8 spatial grid |
| Motion / optic flow | Frame-to-frame |Δluma| |
| Contours | Spatial gradient energy |
| HDMI pixel pipe | Subsampled RGB frames over time |
| Cochlea bands | FFT log bands + RMS + centroid |

## Roots

Default test libraries (if present):

- `G:\movies`
- `G:\showes`
- `G:\Debut` (music)

Override:

```powershell
$env:FSOT_MEDIA_ROOTS = "G:\movies;G:\showes;G:\Debut"
python run_media_chew.py
```

Missing roots → report `ok=True` with zero packets (brain still fine).

## Run

```powershell
$env:FSOT_STANDALONE = "1"
$env:PYTHONPATH = (Get-Location).Path
python run_media_chew.py --videos 2 --frames 20 --audio 2
```

## API

```python
from fsot_nuron.sensory.media_stream import chew_media, MediaChewConfig

rep = chew_media(MediaChewConfig(roots=[r"G:\movies"], max_video_files=1))
```

Packets: `SensoryModality.VISION` / `AUDIO` → primarily **sens**; motion salience → **thal**.

## Console

Dashboard / Body: **Media chew** button runs the same pipeline (optional).
