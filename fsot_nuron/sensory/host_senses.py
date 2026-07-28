"""
Extended host senses — computer body afferents beyond basic CPU/mem.

All sensors are **optional** and degrade gracefully. Same mind, different bodies.
Packet targets (scientific routing):
  SYS_METRIC / NETWORK → thal (interoception / autonomic)
  HID / AUDIO          → sens (exteroception)
  LOG                  → assoc (structured language stream)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from .packets import MetricPacket, SensoryModality, SensoryPacket
from ..seeds import SEEDS

# ---------------------------------------------------------------------------
# Module state (portable — no hard-coded machine identity)
# ---------------------------------------------------------------------------

_prev_net: Optional[Tuple[float, float, float]] = None  # bytes_sent, bytes_recv, t
_hid_clicks: float = 0.0
_hid_keys: float = 0.0
_hid_last_t: float = 0.0
_log_ring: List[str] = []
_LOG_CAP = 64


def reset_sense_state() -> None:
    global _prev_net, _hid_clicks, _hid_keys, _hid_last_t, _log_ring
    _prev_net = None
    _hid_clicks = 0.0
    _hid_keys = 0.0
    _hid_last_t = time.time()
    _log_ring = []


# ---------------------------------------------------------------------------
# HID (keyboard / mouse) — event-fed from host UI
# ---------------------------------------------------------------------------

def note_hid_key(n: int = 1) -> None:
    global _hid_keys
    _hid_keys += float(n)


def note_hid_click(n: int = 1) -> None:
    global _hid_clicks
    _hid_clicks += float(n)


def sample_hid(window_s: float = 2.0) -> Dict[str, float]:
    """
    Rate of recent HID events, decayed so idle → 0.
    Returns keys_rate, click_rate, activity in [0,1].
    """
    global _hid_keys, _hid_clicks, _hid_last_t
    now = time.time()
    dt = max(1e-3, now - _hid_last_t)
    # exponential decay of counters toward 0
    decay = math.exp(-dt / max(0.2, window_s))
    _hid_keys *= decay
    _hid_clicks *= decay
    _hid_last_t = now
    # normalize: ~10 keys/s or 5 clicks/s ≈ 1.0
    key_r = min(1.0, _hid_keys / (10.0 * window_s))
    clk_r = min(1.0, _hid_clicks / (5.0 * window_s))
    activity = min(1.0, 0.6 * key_r + 0.4 * clk_r)
    return {"keys_rate": key_r, "click_rate": clk_r, "activity": activity}


def hid_to_packet(hid: Optional[Dict[str, float]] = None, strength: float = 0.4) -> SensoryPacket:
    h = hid or sample_hid()
    return SensoryPacket(
        modality=SensoryModality.HID,
        target_region="sens",
        features=[h["activity"], h["keys_rate"], h["click_rate"]],
        strength=float(strength) * (SEEDS.phi / (1.0 + SEEDS.phi)),
        timestamp_ms=time.time() * 1000.0,
        meta={"kind": "hid", "channels": h},
    )


# ---------------------------------------------------------------------------
# Network I/O deltas
# ---------------------------------------------------------------------------

def sample_net_util() -> Tuple[float, Dict[str, float]]:
    """
    Bytes/s normalized to [0,1] (~10 MB/s = 1.0). Returns (util, detail).
    """
    global _prev_net
    detail: Dict[str, float] = {"bytes_sent_s": 0.0, "bytes_recv_s": 0.0}
    try:
        import psutil  # type: ignore

        io = psutil.net_io_counters()
        if io is None:
            return 0.0, detail
        now = time.time()
        sent, recv = float(io.bytes_sent), float(io.bytes_recv)
        if _prev_net is None:
            _prev_net = (sent, recv, now)
            return 0.0, detail
        ps, pr, pt = _prev_net
        dt = max(1e-3, now - pt)
        bs = max(0.0, (sent - ps) / dt)
        br = max(0.0, (recv - pr) / dt)
        _prev_net = (sent, recv, now)
        detail = {"bytes_sent_s": bs, "bytes_recv_s": br}
        # 10 MB/s ceiling
        util = min(1.0, (bs + br) / (10.0 * 1024 * 1024))
        return util, detail
    except Exception:
        return 0.0, detail


def network_to_packet(net_util: float, detail: Optional[Dict[str, float]] = None,
                      strength: float = 0.3) -> SensoryPacket:
    d = detail or {}
    return SensoryPacket(
        modality=SensoryModality.NETWORK,
        target_region="thal",
        features=[
            float(net_util),
            min(1.0, d.get("bytes_recv_s", 0.0) / (10.0 * 1024 * 1024)),
            min(1.0, d.get("bytes_sent_s", 0.0) / (10.0 * 1024 * 1024)),
        ],
        strength=float(strength) * (SEEDS.phi / (1.0 + SEEDS.phi)),
        timestamp_ms=time.time() * 1000.0,
        meta={"kind": "network", "detail": d},
    )


# ---------------------------------------------------------------------------
# Audio peak (optional — graceful if no mic / no backend)
# ---------------------------------------------------------------------------

def sample_audio_peak(duration_s: float = 0.05) -> Tuple[float, str]:
    """
    Peak amplitude [0,1] if a capture backend exists; else (0, reason).
    """
    # sounddevice
    try:
        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore

        rec = sd.rec(int(duration_s * 16000), samplerate=16000, channels=1, dtype="float32")
        sd.wait()
        peak = float(np.max(np.abs(rec))) if rec is not None else 0.0
        return min(1.0, peak * 4.0), "sounddevice"
    except Exception:
        pass
    # pyaudio fallback — skip long open; just report unavailable
    try:
        import pyaudio  # type: ignore  # noqa: F401

        return 0.0, "pyaudio_present_no_capture"
    except Exception:
        return 0.0, "no_audio_backend"


def audio_to_packet(peak: float, backend: str = "", strength: float = 0.35) -> SensoryPacket:
    return SensoryPacket(
        modality=SensoryModality.AUDIO,
        target_region="sens",
        features=[float(peak), float(peak) ** 2],
        strength=float(strength) * (SEEDS.phi / (1.0 + SEEDS.phi)) if peak > 0.01 else 0.0,
        timestamp_ms=time.time() * 1000.0,
        meta={"kind": "audio", "backend": backend},
    )


# ---------------------------------------------------------------------------
# Log stream → association cortex
# ---------------------------------------------------------------------------

def note_log_line(line: str) -> None:
    global _log_ring
    s = (line or "").strip()
    if not s:
        return
    _log_ring.append(s[:240])
    if len(_log_ring) > _LOG_CAP:
        _log_ring = _log_ring[-_LOG_CAP:]


def sample_log_features() -> Dict[str, float]:
    """
    Lightweight structured features from recent log lines (no NLP free-fit).
    Uses length / digit / fail keyword density as machine-readable stats.
    """
    if not _log_ring:
        return {"activity": 0.0, "error_density": 0.0, "digit_density": 0.0, "mean_len": 0.0}
    n = len(_log_ring)
    err = 0
    digits = 0
    chars = 0
    for line in _log_ring:
        low = line.lower()
        if any(k in low for k in ("error", "fail", "fault", "critical", "exception")):
            err += 1
        digits += sum(c.isdigit() for c in line)
        chars += len(line)
    return {
        "activity": min(1.0, n / float(_LOG_CAP)),
        "error_density": err / max(1, n),
        "digit_density": min(1.0, digits / max(1, chars)),
        "mean_len": min(1.0, (chars / max(1, n)) / 120.0),
    }


def log_to_packet(feats: Optional[Dict[str, float]] = None, strength: float = 0.3) -> SensoryPacket:
    f = feats or sample_log_features()
    return SensoryPacket(
        modality=SensoryModality.LOG,
        target_region="assoc",
        features=[f["activity"], f["error_density"], f["digit_density"], f["mean_len"]],
        strength=float(strength) * (SEEDS.phi / (1.0 + SEEDS.phi)) if f["activity"] > 0 else 0.0,
        timestamp_ms=time.time() * 1000.0,
        meta={"kind": "log", "channels": f, "n_lines": len(_log_ring)},
    )


# ---------------------------------------------------------------------------
# Combined host sample (all channels that exist)
# ---------------------------------------------------------------------------

@dataclass
class HostSenseSnapshot:
    """One multi-modal host sample for bus inject + UI."""

    metric: Optional[MetricPacket] = None
    net_util: float = 0.0
    net_detail: Dict[str, float] = field(default_factory=dict)
    hid: Dict[str, float] = field(default_factory=dict)
    audio_peak: float = 0.0
    audio_backend: str = ""
    log: Dict[str, float] = field(default_factory=dict)
    packets: List[SensoryPacket] = field(default_factory=list)
    sensors_live: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "net_util": self.net_util,
            "net_detail": self.net_detail,
            "hid": self.hid,
            "audio_peak": self.audio_peak,
            "audio_backend": self.audio_backend,
            "log": self.log,
            "sensors_live": self.sensors_live,
            "n_packets": len(self.packets),
            "packet_modalities": [p.modality.value for p in self.packets],
        }


def sample_host_senses(
    *,
    include_audio: bool = False,
    include_hid: bool = True,
    include_log: bool = True,
    include_net: bool = True,
    metric: Optional[MetricPacket] = None,
) -> HostSenseSnapshot:
    """
    Probe available host senses. Audio off by default (mic may not exist / may hang).
    """
    snap = HostSenseSnapshot(metric=metric)
    packets: List[SensoryPacket] = []

    if include_net:
        util, detail = sample_net_util()
        snap.net_util = util
        snap.net_detail = detail
        if util > 0 or detail:
            snap.sensors_live.append("network")
            packets.append(network_to_packet(util, detail))

    if include_hid:
        h = sample_hid()
        snap.hid = h
        snap.sensors_live.append("hid")
        # Always enqueue (strength scales with activity inside packet strength path)
        packets.append(hid_to_packet(h, strength=0.15 + 0.55 * float(h.get("activity", 0.0))))

    if include_audio:
        peak, backend = sample_audio_peak()
        snap.audio_peak = peak
        snap.audio_backend = backend
        snap.sensors_live.append(f"audio:{backend}")
        if peak > 0.01:
            packets.append(audio_to_packet(peak, backend))

    if include_log:
        lf = sample_log_features()
        snap.log = lf
        snap.sensors_live.append("log")
        if lf.get("activity", 0) > 0:
            packets.append(log_to_packet(lf))

    if metric is not None:
        from ..hardware_body import metrics_to_thalamic_packet

        packets.append(metrics_to_thalamic_packet(metric))
        snap.sensors_live.append("sys_metric")

    snap.packets = packets
    return snap
