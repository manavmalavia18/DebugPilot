import json
from datetime import datetime, timezone

from app.events.schema import IncidentEvent, build_github_external_id


def test_build_github_external_id():
    assert build_github_external_id("acme", "api", 12345) == "github:acme/api:12345:1"
    assert (
        build_github_external_id("acme", "api", 12345, run_attempt=2)
        == "github:acme/api:12345:2"
    )


def test_incident_event_roundtrip():
    event = IncidentEvent(
        source="github_actions",
        external_id="github:org/repo:99",
        log_text="##[error] test failed",
        source_hint="github_actions",
        metadata={"repo": "org/repo", "actor": "dev"},
        received_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    restored = IncidentEvent.from_json_bytes(event.to_json_bytes())
    assert restored.external_id == event.external_id
    assert restored.source == "github_actions"
    assert restored.metadata["actor"] == "dev"


def test_incident_event_kafka_key_is_external_id():
    event = IncidentEvent(
        source="manual",
        external_id="manual:abc",
        log_text="oops",
    )
    payload = json.loads(event.to_json_bytes())
    assert payload["external_id"] == "manual:abc"
