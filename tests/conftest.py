import pytest


@pytest.fixture(autouse=True)
def disable_auth_for_tests(monkeypatch):
    """Tests assume local dev mode unless a test explicitly enables OAuth."""
    monkeypatch.setenv("AUTH_DISABLED", "1")
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_SECRET", raising=False)
