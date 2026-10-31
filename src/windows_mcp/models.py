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


@dataclass
class ProcessInfo:
    name: str
    pid: int
    cpu_percent: float
    memory_mb: float


@dataclass
class TopProcesses:
    target: str
    top_by_cpu: list[ProcessInfo]
    top_by_memory: list[ProcessInfo]


@dataclass
class ServiceStatus:
    target: str
    service_name: str   # stable Windows service Name
    display_name: str   # localized; Unicode string
    status: str
    start_type: str