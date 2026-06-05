import os

import pytest

# Set before test modules import app (conftest loads first).
os.environ["AUTH_DISABLED"] = "1"
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-ci")
os.environ["SEMANTIC_RAG_DISABLED"] = "1"


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    """Keep tests in local dev mode even when CI injects GitHub OAuth secrets."""
    monkeypatch.setenv("AUTH_DISABLED", "1")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-ci")
    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "1")
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)
    monkeypatch.setattr("app.retrieval.warmup_playbook_index", lambda: None)
