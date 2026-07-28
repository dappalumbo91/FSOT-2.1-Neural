"""
Sensory injectors for the FSOT brain (Python host scaffold).

Computer-native senses can exceed human modalities (GPU load, syscalls, etc.).
Implementation detail is temporary Python; the *packet shape* is the stable
contract for Zig/Rust/Ada embodiment later (see docs/EMBODIMENT_ROADMAP.md).

Encoding into the bus prefers **machine** words (UTF-8/T1 packs), not Morse.
See fsot_nuron.machine_encode and docs/MACHINE_ENCODING.md.
"""

from .packets import SensoryModality, SensoryPacket, MetricPacket
from .bus import SensoryBus
from .host_senses import (
    sample_host_senses,
    note_hid_key,
    note_hid_click,
    note_log_line,
    HostSenseSnapshot,
)
from .media_stream import (
    chew_media,
    MediaChewConfig,
    MediaChewReport,
    media_roots_from_env,
    discover_media_files,
)


def push_machine_text(
    bus: SensoryBus,
    text: str,
    *,
    target_region: str = "sens",
    strength: float = 0.55,
    path: str = "machine",
) -> SensoryPacket:
    """Encode text via machine (default) / chemical / morse and enqueue."""
    from fsot_nuron.machine_encode import EncodePath, encode_to_sensory_packet

    pkt = encode_to_sensory_packet(
        text,
        path=EncodePath(path),
        target_region=target_region,
        strength=strength,
    )
    bus.push(pkt)
    return pkt


def push_machine_frame_bytes(
    bus: SensoryBus,
    data: bytes,
    *,
    target_region: str = "sens",
    strength: float = 0.45,
) -> SensoryPacket:
    """Raw OS buffer → machine encode → sensory packet."""
    from fsot_nuron.machine_encode import EncodePath, encode_to_sensory_packet

    pkt = encode_to_sensory_packet(
        data,
        path=EncodePath.MACHINE,
        target_region=target_region,
        strength=strength,
    )
    bus.push(pkt)
    return pkt


__all__ = [
    "SensoryModality",
    "SensoryPacket",
    "MetricPacket",
    "SensoryBus",
    "push_machine_text",
    "push_machine_frame_bytes",
    "sample_host_senses",
    "note_hid_key",
    "note_hid_click",
    "note_log_line",
    "HostSenseSnapshot",
    "chew_media",
    "MediaChewConfig",
    "MediaChewReport",
    "media_roots_from_env",
    "discover_media_files",
]
