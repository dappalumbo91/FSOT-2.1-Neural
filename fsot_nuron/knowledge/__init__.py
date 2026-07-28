"""Knowledge cross-feed — text meaning bound into trinary/machine body language."""

from .lexicon import KnowledgeLexicon, KnowledgeEntry, load_lexicon
from .cross_feed import (
    cross_feed_episode,
    CrossFeedReport,
    knowledge_to_machine_packets,
    regurgitate_plain_english,
)
from .speech_text import transcribe_audio_file, STTResult

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
]
