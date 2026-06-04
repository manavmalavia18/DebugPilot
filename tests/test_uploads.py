import io

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPLOADS_LOCAL_DIR", str(tmp_path / "uploads"))
    monkeypatch.delenv("UPLOADS_S3_BUCKET", raising=False)

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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_upload_log_file(client):
    payload = b"Error: connection refused to redis:6379\nPod CrashLoopBackOff"
    response = client.post(
        "/uploads",
        files={"file": ("pod.log", io.BytesIO(payload), "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "pod.log"
    assert body["storage_backend"] == "local"
    assert "redis" in body["log_text"]


def test_analyze_with_upload_id(client, monkeypatch):
    from app.models import AnalysisResult

    upload = client.post(
        "/uploads",
        files={"file": ("ci.log", io.BytesIO(b"GitHub Actions workflow failed"), "text/plain")},
    )
    upload_id = upload.json()["id"]

    def fake_analyze(log_text, source_hint=None):
        return (
            AnalysisResult(
                category="github_actions",
                symptom="Workflow failed",
                what_failed="CI",
                root_cause="test",
                confidence="high",
                debug_commands=["gh run list"],
                likely_fix="fix workflow",
                prevention=[],
                warnings=[],
            ),
            False,
        )

    monkeypatch.setattr("app.main.analyze_log", fake_analyze)

    response = client.post(
        "/analyze",
        json={"upload_id": upload_id, "save": False},
    )
    assert response.status_code == 200
    assert response.json()["symptom"] == "Workflow failed"
