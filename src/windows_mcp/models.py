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

@dataclass
class WindowsEvent:
    event_id: int
    provider_name: str
    level: str
    time_created: str
    record_id: int
    message: str
    message_truncated: bool


@dataclass
class WindowsEvents:
    target: str
    log_name: str
    lookback_minutes: int
    events: list[WindowsEvent]


@dataclass
class ScheduledTaskAction:
    execute: str
    arguments: str


@dataclass
class ScheduledTask:
    task_name: str
    task_path: str
    state: str
    enabled: bool
    actions: list[ScheduledTaskAction]


@dataclass
class ScheduledTasks:
    target: str
    tasks: list[ScheduledTask]


@dataclass
class StartupEntry:
    name: str
    command: str
    location: str
    scope: str
    user_sid: str | None


@dataclass
class StartupEntries:
    target: str
    entries: list[StartupEntry]


@dataclass
class NetworkConnection:
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int
    state: str
    pid: int
    process_name: str


@dataclass
class NetworkConnections:
    target: str
    connections: list[NetworkConnection]