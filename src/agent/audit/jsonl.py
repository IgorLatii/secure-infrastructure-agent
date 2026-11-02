import json
from dataclasses import asdict
from pathlib import Path

from .models import AuditEvent
from .sink import AuditSink


class JsonlAuditSink(AuditSink):
    def __init__(self, path: str | Path):
        self._path = Path(path)

    def write(self, event: AuditEvent) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self._path.open(
            "a",
            encoding="utf-8",
        ) as file:
            json.dump(
                asdict(event),
                file,
                ensure_ascii=False,
            )
            file.write("\n")