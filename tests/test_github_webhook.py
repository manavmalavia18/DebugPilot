import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _sign(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.fixture
def client():
    return TestClient(app)


def test_github_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("GITHUB_WEBHOOK_TOKEN", "token")
    payload = json.dumps({"action": "completed"}).encode()
    response = client.post(
        "/webhooks/github",
        content=payload,
        headers={
            "X-GitHub-Event": "workflow_run",
            "X-Hub-Signature-256": "sha256=bad",
        },
    )
    assert response.status_code == 401


def test_github_webhook_ignores_non_failure(client, monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("GITHUB_WEBHOOK_TOKEN", "token")
    body = {
        "action": "completed",
        "workflow_run": {"conclusion": "success", "id": 1},
        "repository": {"name": "repo", "owner": {"login": "org"}},
    }
    payload = json.dumps(body).encode()
    response = client.post(
        "/webhooks/github",
        content=payload,
        headers={
            "X-GitHub-Event": "workflow_run",
            "X-Hub-Signature-256": _sign(payload, "test-secret"),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
