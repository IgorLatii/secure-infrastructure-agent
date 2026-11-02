from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    run_id: str
    step: int | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    event_id: str = field(
        default_factory=lambda: str(uuid4())
    )