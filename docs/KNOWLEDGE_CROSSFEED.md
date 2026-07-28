# Knowledge cross-feed — patterns → text → trinary → words again

## Your insight (mapped)

| Human / you | FSOT Neural |
|-------------|-------------|
| Voice → text (how you talk to Grok) | Optional local STT (`faster-whisper`) |
| Words attached to what you see | Symbols + transcript co-bound with AV stream |
| Dictionary / world knowledge | Local `data/knowledge/lexicon.json` (+ optional online) |
| Brain does not “think English” | **Machine encode**: UTF-8 → **trits** (body language) |
| Later say it in your own words | `regurgitate_plain_english()` expands definitions + observations |

Audiovisual co-stream still works **without** STT or lexicon.  
Cross-feed is how associated patterns become **compact knowledge** and then **speakable**.

## Pipeline

```text
Show stream (pixels + soundtrack)
        │
        ├─► vision @ t, audio @ t, joint @ t   (cross_modal)
        │
        ├─► optional speech→text (STT)
        │
        ├─► symbols (action, dialogue, person, …)
        │         + title/transcript hits (Finn, Jake, …)
        │
        ▼
  Lexicon definitions (local; optional Wikipedia if FSOT_KNOWLEDGE_ONLINE=1)
        │
        ▼
  Teach text → machine path → trits → SensoryPackets (assoc + hipp)
        │
        ▼
  Plain English summary for the host (regurgitation)
```

## Run

```powershell
$env:FSOT_STANDALONE = "1"
$env:PYTHONPATH = (Get-Location).Path

# Symbols + lexicon + trinary (no STT)
python run_knowledge_demo.py

# With local speech→text (installs model weights on first run)
python run_knowledge_demo.py --stt

# Optional online definition expand
python run_knowledge_demo.py --online
```

Media chew with knowledge (default on):

```powershell
python run_media_chew.py --videos 1 --frames 12
# STT: set knowledge path via MediaChewConfig(speech_to_text=True) or extend CLI later
```

## Finn / Jake example

Local lexicon includes Adventure Time anchors:

- **Finn** → human boy protagonist  
- **Jake** → **dog** (shape-shifting), not human  

If the title/path or transcript mentions them, cross-feed attaches those definitions and encodes them as trits. More episodes tighten **co-occurrence** of their audiovisual patterns with those text bindings — that is training-by-experience, not a separate offline ImageNet stage.

## Dialogue as subtitles (lightweight)

Dialogue-heavy clusters are treated like **TV captions**, not a heavy continuous STT job:

1. Prefer sidecar **`.srt` / `.vtt`** next to the media file  
2. Else optional **STT → same cue shape** (`start` / `end` / `text`)  
3. **Sample AV moments at caption times** (dialogue-aligned, not only t=0)  
4. Bind caption line ↔ vision/audio at *t* → machine packets + knowledge  
5. **Save episode memory** → recall later in plain English  

```powershell
python run_episode_watch.py --path "G:\movies\Brave (2012) [1080p]\Brave....mp4"
python run_episode_watch.py --recall "Brave"
python run_episode_watch.py --list
# if no sidecar:  python run_episode_watch.py --path "...mp4" --stt
```

Modules: `subtitles.py`, `dialogue_bind.py`, `episode_memory.py`.

## Accuracy honesty

| Claim | Status |
|-------|--------|
| Patterns associate in real time without pre-training | Yes (AV joint + symbols) |
| Open-world “Garfield = cat” | Not yet — needs more episodes + stronger prototypes / STT |
| Text is body language via trinary | Yes (`text_to_utf8_trits` / machine packets) |
| Subtitle-style dialogue binding | Yes (sidecar SRT/VTT preferred; STT fallback) |
| Episodic recall in plain English | Yes (local `artifacts/episode_memory/`) |
| Full LLM inner monologue | No — compositional regurgitation from lexicon + stream stats |
