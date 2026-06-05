import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import AnalysisResult, SavedIncident, User


@pytest.fixture
def chat_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(github_id=0, username="dev")
        session.add(user)
        session.commit()
        session.refresh(user)
        result = AnalysisResult(
            category="kubernetes",
            symptom="Pod crash",
            what_failed="api",
            root_cause="Redis on localhost",
            confidence="high",
            debug_commands=["kubectl logs api"],
            likely_fix="Use redis://redis:6379/0",
            prevention=[],
            warnings=[],
        )
        incident = SavedIncident(
            user_id=user.id,
            log_text="Connection refused localhost:6379",
            category=result.category,
            symptom=result.symptom,
            root_cause=result.root_cause,
            likely_fix=result.likely_fix,
            confidence=result.confidence,
            response_json=json.dumps(result.model_dump()),
        )
        session.add(incident)
        session.commit()
        session.refresh(incident)
        yield session, incident.id


@pytest.fixture
def chat_client(chat_session):
    session, _incident_id = chat_session

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@patch("app.main.follow_up_with_claude")
def test_incident_chat_persists_messages(mock_follow_up, chat_client, chat_session):
    mock_follow_up.return_value = "Use the cluster DNS name redis:6379 instead of localhost."
    _session, incident_id = chat_session

    empty = chat_client.get(f"/incidents/{incident_id}/messages")
    assert empty.status_code == 200
    assert empty.json() == []

    response = chat_client.post(
        f"/incidents/{incident_id}/chat",
        json={"message": "Why is localhost wrong?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "redis:6379" in body["reply"]
    assert body["message"]["role"] == "assistant"

    listed = chat_client.get(f"/incidents/{incident_id}/messages")
    assert listed.status_code == 200
    messages = listed.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


@patch("app.main.analyze_log")
def test_analyze_returns_incident_id_when_saved(mock_analyze):
    mock_analyze.return_value = (
        AnalysisResult(
            category="kubernetes",
            symptom="Pod crash",
            what_failed="api",
            root_cause="OOM",
            confidence="high",
            debug_commands=["kubectl logs api"],
            likely_fix="Raise memory limit",
            prevention=[],
            warnings=[],
        ),
        False,
    )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    try:
        with TestClient(app) as client:
            response = client.post(
                "/analyze",
                json={"log_text": "OOMKilled", "save": True},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["incident_id"] is not None
        assert isinstance(body["incident_id"], int)
    finally:
        app.dependency_overrides.clear()
