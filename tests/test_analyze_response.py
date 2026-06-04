from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


@patch("app.main.analyze_log")
def test_analyze_returns_cached_and_duration(mock_analyze):
    from app.models import AnalysisResult

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
        True,
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
                json={"log_text": "OOMKilled", "save": False},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["cached"] is True
    assert body["symptom"] == "Pod crash"
    assert "duration_ms" in body
    assert body["duration_ms"] >= 0
