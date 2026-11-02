from .models import AuditEvent
from .sink import AuditSink


class MemoryAuditSink(AuditSink):
    def __init__(self):
        self.events: list[AuditEvent] = []

    def write(self, event: AuditEvent) -> None:
        self.events.append(event)