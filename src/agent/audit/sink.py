from abc import ABC, abstractmethod

from .models import AuditEvent


class AuditSink(ABC):
    @abstractmethod
    def write(self, event: AuditEvent) -> None:
        """
        Persist a single audit event.
        """
        raise NotImplementedError