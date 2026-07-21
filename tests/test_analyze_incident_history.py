from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import AnalysisResult, SavedIncident, User


@patch("app.main.analyze_log")
def test_analyze_returns_incident_history_matches(mock_analyze):
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

    with Session(engine) as session:
        user = User(github_id=0, username="dev")
        session.add(user)
        session.commit()
        session.refresh(user)
        session.add(
            SavedIncident(
                user_id=user.id,
                log_text=(
                    "CrashLoopBackOff redis connection refused localhost:6379 "
                    "cache pod api debugpilot"
                ),
                category="kubernetes",
                symptom="Redis unreachable",
                root_cause="localhost REDIS_URL",
                likely_fix="Use redis service DNS",
                confidence="high",
                response_json="{}",
            )
        )
        session.commit()

    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    try:
        with TestClient(app) as client:
            response = client.post(
                "/analyze",
                json={
                    "log_text": (
                        "CrashLoopBackOff connection refused localhost:6379 "
                        "redis cache unreachable pod api"
                    ),
                    "save": False,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["incident_history_matches"]
    match = body["incident_history_matches"][0]
    assert match["incident_id"] == 1
    assert match["symptom"] == "Redis unreachable"
    assert match["method"] == "keyword"
    assert match["score"] > 0

    # Claude path must receive non-empty history context when matches exist.
    kwargs = mock_analyze.call_args.kwargs
    assert kwargs["incident_history_context"]
    assert "Past incident #1" in kwargs["incident_history_context"]
    assert "Redis unreachable" in kwargs["incident_history_context"]
