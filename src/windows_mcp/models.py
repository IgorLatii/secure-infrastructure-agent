from dataclasses import dataclass


@dataclass
class MemoryInfo:
    total_gb: float
    used_gb: float
    used_percent: float


@dataclass
class DiskInfo:
    drive: str
    total_gb: float
    free_gb: float


@dataclass
class SystemHealth:
    target: str
    uptime_hours: float
    cpu_percent: float
    memory: MemoryInfo
    disks: list[DiskInfo]
    pending_reboot: bool