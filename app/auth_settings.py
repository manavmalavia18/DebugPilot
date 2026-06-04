import os
import secrets

COOKIE_NAME = "debugpilot_session"


def auth_enabled() -> bool:
    if os.getenv("AUTH_DISABLED", "").lower() in ("1", "true", "yes"):
        return False
    return bool(os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET"))


def jwt_secret() -> str:
    value = os.getenv("JWT_SECRET", "").strip()
    if value:
        return value
    if auth_enabled():
        raise RuntimeError("JWT_SECRET is required when GitHub auth is enabled")
    return secrets.token_urlsafe(32)


def public_base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")


def cookie_secure() -> bool:
    return os.getenv("AUTH_COOKIE_SECURE", "").lower() in ("1", "true", "yes")
