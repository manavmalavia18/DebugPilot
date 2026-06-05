import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.incident_retrieval import (
    _incident_content,
    dedupe_incident_history_matches,
    find_similar_saved_incidents,
)
from app.main import app
from app.models import AnalysisResult, SavedIncident, User


@pytest.fixture
def incident_session():
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
            symptom="Redis unreachable",
            what_failed="api",
            root_cause="localhost REDIS_URL",
            confidence="high",
            debug_commands=["kubectl get svc"],
            likely_fix="Use redis service DNS",
            prevention=[],
            warnings=[],
        )
        good = SavedIncident(
            user_id=user.id,
            log_text="CrashLoopBackOff redis connection refused localhost:6379 cache pod api",
            category=result.category,
            symptom=result.symptom,
            root_cause=result.root_cause,
            likely_fix=result.likely_fix,
            confidence=result.confidence,
            response_json=json.dumps(result.model_dump()),
            resolution="Set REDIS_URL=redis://redis:6379/0 in Helm",
        )
        bad = SavedIncident(
            user_id=user.id,
            log_text="CrashLoopBackOff redis connection refused localhost:6379 cache pod api duplicate",
            category="kubernetes",
            symptom="Redis unreachable",
            root_cause="wrong guess",
            likely_fix="bad fix",
            confidence="low",
            response_json="{}",
            feedback=-1,
        )
        session.add(good)
        session.add(bad)
        session.commit()
        session.refresh(good)
        session.refresh(bad)
        yield session, user.id, good.id


@pytest.fixture
def api_client(incident_session):
    session, _user_id, _good_id = incident_session

    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_patch_incident_feedback_and_resolution(api_client, incident_session):
    _session, _user_id, good_id = incident_session

    response = api_client.patch(
        f"/incidents/{good_id}",
        json={"feedback": "up", "resolution": "Updated REDIS_URL in values.yaml"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["feedback"] == "up"
    assert body["resolution"] == "Updated REDIS_URL in values.yaml"

    detail = api_client.get(f"/incidents/{good_id}")
    assert detail.status_code == 200
    assert detail.json()["incident_feedback"] == "up"
    assert detail.json()["incident_resolution"] == "Updated REDIS_URL in values.yaml"


def test_thumbs_down_incident_excluded_from_retrieval(incident_session, monkeypatch):
    session, user_id, _good_id = incident_session
    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "1")

    log = "CrashLoopBackOff connection refused localhost:6379 redis cache unreachable"
    matches = find_similar_saved_incidents(session, user_id, log, limit=3)
    assert len(matches) == 1
    assert matches[0].incident_id == 1


def test_incident_content_includes_resolution(incident_session):
    session, _user_id, good_id = incident_session
    row = session.get(SavedIncident, good_id)
    content = _incident_content(row)
    assert "Confirmed resolution:" in content
    assert "Helm" in content


def test_dedupe_incident_history_matches():
    from app.incident_retrieval import IncidentHistoryMatch

    matches = [
        IncidentHistoryMatch(1, "a", 0.94, "keyword", "Redis crash"),
        IncidentHistoryMatch(2, "b", 0.93, "keyword", "Redis crash"),
        IncidentHistoryMatch(3, "c", 0.80, "keyword", "Terraform lock"),
    ]
    deduped = dedupe_incident_history_matches(matches, limit=2)
    assert len(deduped) == 2
    assert deduped[0].incident_id == 1
    assert deduped[1].incident_id == 3


@patch("app.main.analyze_log")
def test_get_incident_returns_detail(_mock_analyze, api_client, incident_session):
    _session, _user_id, good_id = incident_session

    detail = api_client.get(f"/incidents/{good_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["incident_id"] == good_id
    assert body["symptom"] == "Redis unreachable"
    assert body["incident_resolution"] == "Set REDIS_URL=redis://redis:6379/0 in Helm"
