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

## Cross-modal co-stream (movies / shows)

Movies and shows carry **picture + soundtrack at the same time**. That is the
primary path to meaning — not filename metadata.

| Channel | Target | Role |
|---------|--------|------|
| Vision @ t | sens | Luma / color / motion / retinotopy |
| Audio @ t | sens | RMS / speech-band / spectrum |
| **Vision ⊗ Audio @ t** | **assoc** | Joint co-occurrence pattern |
| Speech-band + visual structure | hipp | Dialogue↔scene episodic tag |

Biological analog: infant word learning — hearing a word *while* seeing an object
binds them. Recurring joint patterns cluster into pre-symbolic “that again”
tokens; symbols (person, dialogue, action, …) attach by co-occurrence statistics.

**Metadata is optional tutor** (`use_metadata_tutor=True` by default).  
Cross-modal binding works with tutor off.

Full speech-to-text (Whisper etc.) can later replace speech-band priors with
real word tokens on the same joint path.

## Symbolic association stage

See also path tags in `media_meta.py` and anchors in `symbol_assoc.py`.  
We are **not** claiming Garfield-level open-world vision yet. We **are** building:

1. Sensory signatures (“how it looked / sounded”)  
2. Time-aligned A/V joints (“what co-occurred”)  
3. Prototype symbols + optional metadata tutors  
4. Retrieval / ranking for comparison across episodes  

## Console

Dashboard: **Media chew** button runs the same pipeline (optional).
