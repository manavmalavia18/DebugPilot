import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


@pytest.fixture
def client():
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


def test_auth_config_disabled_by_default(client):
    response = client.get("/auth/config")
    assert response.status_code == 200
    assert response.json()["auth_enabled"] is False


def test_auth_me_dev_user_when_disabled(client):
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "dev"


@patch.dict(
    os.environ,
    {
        "AUTH_DISABLED": "",
        "GITHUB_CLIENT_ID": "test-id",
        "GITHUB_CLIENT_SECRET": "test-secret",
        "JWT_SECRET": "test-jwt-secret-key",
        "PUBLIC_BASE_URL": "http://testserver",
    },
    clear=False,
)
def test_analyze_requires_login_when_auth_enabled(client):
    response = client.post(
        "/analyze",
        json={"log_text": "error", "save": False},
    )
    assert response.status_code == 401
