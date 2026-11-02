import json

from agent.audit.jsonl import JsonlAuditSink
from agent.audit.models import AuditEvent


def test_jsonl_audit_sink_writes_events(tmp_path):
    audit_file = tmp_path / "audit.jsonl"
    sink = JsonlAuditSink(audit_file)

    first_event = AuditEvent(
        event_type="run_started",
        run_id="run-123",
    )

    second_event = AuditEvent(
        event_type="tool_proposed",
        run_id="run-123",
        step=1,
        data={
            "tool_name": "get_process_details",
            "arguments": {
                "target": "LAB-PC",
                "pid": 4820,
            },
        },
    )

    sink.write(first_event)
    sink.write(second_event)

    lines = audit_file.read_text(
        encoding="utf-8",
    ).splitlines()

    assert len(lines) == 2

    first_record = json.loads(lines[0])
    second_record = json.loads(lines[1])

    assert first_record["event_type"] == "run_started"
    assert first_record["run_id"] == "run-123"
    assert first_record["step"] is None
    assert first_record["event_id"]
    assert first_record["timestamp"]

    assert second_record["event_type"] == "tool_proposed"
    assert second_record["run_id"] == "run-123"
    assert second_record["step"] == 1
    assert second_record["data"] == {
        "tool_name": "get_process_details",
        "arguments": {
            "target": "LAB-PC",
            "pid": 4820,
        },
    }