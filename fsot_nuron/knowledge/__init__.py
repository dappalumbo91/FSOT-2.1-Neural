"""Knowledge cross-feed — text meaning bound into trinary/machine body language."""

from .lexicon import KnowledgeLexicon, KnowledgeEntry, load_lexicon
from .cross_feed import (
    cross_feed_episode,
    CrossFeedReport,
    knowledge_to_machine_packets,
    regurgitate_plain_english,
)
from .speech_text import transcribe_audio_file, STTResult
from .subtitles import load_subtitles, CaptionCue, find_sidecar_subtitles
from .dialogue_bind import process_episode_with_subtitles, DialogueBindReport
from .episode_memory import (
    save_episode,
    load_episode,
    list_episodes,
    retrieve_by_query,
    recall_plain_english,
    EpisodeMemory,
)
from .monologue import run_grounded_monologue, MonologueReport
from .vision_caption_bind import run_vision_caption_bind, VisionCaptionBindReport
from .teach_5w1h import build_5w1h, Teach5W1H

__all__ = [
    "KnowledgeLexicon",
    "KnowledgeEntry",
    "load_lexicon",
    "cross_feed_episode",
    "CrossFeedReport",
    "knowledge_to_machine_packets",
    "regurgitate_plain_english",
    "transcribe_audio_file",
    "STTResult",
    "load_subtitles",
    "CaptionCue",
    "find_sidecar_subtitles",
    "process_episode_with_subtitles",
    "DialogueBindReport",
    "save_episode",
    "load_episode",
    "list_episodes",
    "retrieve_by_query",
    "recall_plain_english",
    "EpisodeMemory",
    "run_grounded_monologue",
    "MonologueReport",
    "run_vision_caption_bind",
    "VisionCaptionBindReport",
    "build_5w1h",
    "Teach5W1H",
]
