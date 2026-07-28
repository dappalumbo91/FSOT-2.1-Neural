"""
Hardware-adaptive body discovery — computer as organism substrate.

The mind must not be hard-coded to one PC. On boot we *probe* what is available
and map it into interoceptive MetricPackets (autonomic / circulatory analog).

Doctrine:
  - No free-fit health model: equal-weight core channels when present
  - Missing sensors → strength 0 / omit (graceful degrade)
  - Optional psutil for richer metrics; stdlib fallback always works
"""

from __future__ import annotations

import os
import platform
import shutil
import time
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional

from .sensory.packets import MetricPacket, SensoryModality, SensoryPacket
from .seeds import SEEDS


@dataclass
class HardwareProfile:
    """What this host can provide — discovered at boot, not baked in."""

    hostname: str = ""
    system: str = ""  # Windows / Linux / Darwin
    machine: str = ""  # amd64 / arm64 / …
    processor: str = ""
    python: str = ""
    cpu_count_logical: int = 0
    cpu_count_physical: Optional[int] = None
    ram_total_gb: Optional[float] = None
    disk_total_gb: Optional[float] = None
    disk_free_gb: Optional[float] = None
    cuda_available: bool = False
    cuda_device_name: str = ""
    has_psutil: bool = False
    sensors_available: List[str] = field(default_factory=list)
    recommended_device: str = "cpu"
    recommended_n_units: int = 32
    recommended_dt_ms: float = 0.5
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _try_psutil():
    try:
        import psutil  # type: ignore

        return psutil
    except Exception:
        return None


def _ram_total_gb() -> Optional[float]:
    ps = _try_psutil()
    if ps is not None:
        return float(ps.virtual_memory().total) / (1024**3)
    # Windows
    if platform.system() == "Windows":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return float(stat.ullTotalPhys) / (1024**3)
        except Exception:
            return None
    # Linux
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = float(line.split()[1])
                    return kb / (1024**2)
    except Exception:
        return None
    return None


def _cuda_info() -> tuple[bool, str]:
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            return True, name
    except Exception:
        pass
    return False, ""


def discover_hardware() -> HardwareProfile:
    """Probe current machine — portable boot adaptation."""
    ps = _try_psutil()
    sensors: List[str] = ["cpu_count"]
    notes: List[str] = []

    cpu_log = os.cpu_count() or 1
    cpu_phys = None
    if ps is not None:
        try:
            cpu_phys = ps.cpu_count(logical=False)
        except Exception:
            pass
        sensors.append("cpu_util")
        sensors.append("mem_util")

    ram = _ram_total_gb()
    if ram is not None:
        sensors.append("ram_total")

    disk_total = disk_free = None
    try:
        usage = shutil.disk_usage(os.path.abspath(os.sep))
        disk_total = usage.total / (1024**3)
        disk_free = usage.free / (1024**3)
        sensors.append("disk")
    except Exception:
        notes.append("disk_usage unavailable")

    cuda, cuda_name = _cuda_info()
    if cuda:
        sensors.append("cuda")
        notes.append(f"CUDA: {cuda_name}")

    # Capability-based recommendations (seed-folded caps, not free fit)
    # More RAM/CPU → larger default net; never require one machine
    if ram is not None and ram >= 16 and cpu_log >= 8:
        n_units = 64
    elif ram is not None and ram >= 8:
        n_units = 48
    else:
        n_units = 32
    if cuda:
        n_units = min(128, n_units * 2)
        device = "cuda"
    else:
        device = "cpu"

    # Finer dt when CPU has headroom (φ-scaled preference)
    dt = 0.5 if cpu_log >= 4 else 1.0
    if cuda:
        dt = 0.25

    return HardwareProfile(
        hostname=platform.node(),
        system=platform.system(),
        machine=platform.machine(),
        processor=platform.processor() or platform.machine(),
        python=platform.python_version(),
        cpu_count_logical=cpu_log,
        cpu_count_physical=cpu_phys,
        ram_total_gb=ram,
        disk_total_gb=disk_total,
        disk_free_gb=disk_free,
        cuda_available=cuda,
        cuda_device_name=cuda_name,
        has_psutil=ps is not None,
        sensors_available=sensors,
        recommended_device=device,
        recommended_n_units=n_units,
        recommended_dt_ms=dt,
        notes=notes,
    )


def sample_metrics(profile: Optional[HardwareProfile] = None) -> MetricPacket:
    """
    One interoceptive sample of the computer body.
    Missing sensors stay 0 (graceful) — organism adapts.
    """
    ps = _try_psutil()
    cpu = mem = disk = net = temp = 0.0
    custom: Dict[str, float] = {}

    if ps is not None:
        try:
            cpu = float(ps.cpu_percent(interval=0.05)) / 100.0
        except Exception:
            cpu = 0.0
        try:
            mem = float(ps.virtual_memory().percent) / 100.0
        except Exception:
            mem = 0.0
        try:
            disk = float(ps.disk_usage(os.path.abspath(os.sep)).percent) / 100.0
        except Exception:
            disk = 0.0
        try:
            # net: normalize to 0..1 loosely via counters delta not available — use 0
            net = 0.0
        except Exception:
            pass
        try:
            if hasattr(ps, "sensors_temperatures"):
                temps = ps.sensors_temperatures() or {}
                vals = []
                for entries in temps.values():
                    for e in entries:
                        if getattr(e, "current", None) is not None:
                            vals.append(float(e.current))
                if vals:
                    # Normalize ~40–90 C → 0..1
                    t = sum(vals) / len(vals)
                    temp = max(0.0, min(1.0, (t - 40.0) / 50.0))
        except Exception:
            pass
    else:
        # stdlib: only static load proxies
        custom["cpu_count_norm"] = min(1.0, (os.cpu_count() or 1) / 16.0)

    if profile and profile.cuda_available:
        try:
            import torch

            if torch.cuda.is_available():
                # free/total memory as custom channel
                free, total = torch.cuda.mem_get_info(0)
                custom["gpu_mem_util"] = 1.0 - float(free) / max(1, float(total))
        except Exception:
            pass

    return MetricPacket(
        cpu_util=cpu,
        mem_util=mem,
        disk_util=disk,
        net_util=net,
        temp_norm=temp,
        custom=custom,
        timestamp_ms=time.time() * 1000.0,
    )


def metrics_to_thalamic_packet(metric: MetricPacket, strength: float = 0.35) -> SensoryPacket:
    """Autonomic plant → thalamus (same as SensoryBus.push_metric intent)."""
    return SensoryPacket(
        modality=SensoryModality.SYS_METRIC,
        target_region="thal",
        features=[metric.as_drive_scalar(), metric.cpu_util, metric.mem_util],
        strength=float(strength) * (SEEDS.phi / (1.0 + SEEDS.phi)),  # gate scale
        timestamp_ms=metric.timestamp_ms,
        meta={"kind": "interoception", "channels": metric.to_dict()},
    )


def boot_body_report() -> Dict[str, Any]:
    """Human-readable adaptive boot block for the console."""
    hw = discover_hardware()
    m = sample_metrics(hw)
    return {
        "hardware": hw.to_dict(),
        "sample_metric": m.to_dict(),
        "interoception_drive": m.as_drive_scalar(),
        "adaptation": {
            "device": hw.recommended_device,
            "n_units": hw.recommended_n_units,
            "dt_ms": hw.recommended_dt_ms,
            "note": "Not bound to one machine — re-probed every boot",
        },
    }
