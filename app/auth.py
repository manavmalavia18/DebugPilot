import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException, Request, Response
from sqlmodel import Session, select

from app.auth_settings import COOKIE_NAME, cookie_secure, jwt_secret, public_base_url
from app.models import User

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7
OAUTH_STATE_COOKIE = "debugpilot_oauth_state"


def github_client_id() -> str:
    client_id = os.getenv("GITHUB_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    return client_id


def github_client_secret() -> str:
    secret = os.getenv("GITHUB_CLIENT_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    return secret


def build_github_login_redirect(response: Response) -> str:
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": github_client_id(),
        "redirect_uri": f"{public_base_url()}/auth/github/callback",
        "scope": "read:user",
        "state": state,
    }
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        max_age=600,
        samesite="lax",
        secure=cookie_secure(),
    )
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"


def verify_oauth_state(request: Request, state: str) -> None:
    expected = request.cookies.get(OAUTH_STATE_COOKIE)
    if not expected or not state or expected != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")


def exchange_github_code(code: str) -> dict[str, Any]:
    with httpx.Client(timeout=15.0) as client:
        token_res = client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": github_client_id(),
                "client_secret": github_client_secret(),
                "code": code,
                "redirect_uri": f"{public_base_url()}/auth/github/callback",
            },
        )
        token_res.raise_for_status()
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub did not return an access token")

        user_res = client.get(
            GITHUB_USER_URL,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
        )
        user_res.raise_for_status()
        return user_res.json()


def upsert_user_from_github(session: Session, profile: dict[str, Any]) -> User:
    github_id = int(profile["id"])
    row = session.exec(select(User).where(User.github_id == github_id)).first()
    if row:
        row.username = profile.get("login") or row.username
        row.display_name = profile.get("name") or row.display_name
        row.avatar_url = profile.get("avatar_url") or row.avatar_url
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    user = User(
        github_id=github_id,
        username=profile.get("login") or f"github-{github_id}",
        display_name=profile.get("name"),
        avatar_url=profile.get("avatar_url"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_session_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=JWT_EXPIRE_DAYS * 86400,
        samesite="lax",
        secure=cookie_secure(),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


def decode_session_token(token: str) -> int:
    try:
        payload = jwt.decode(token, jwt_secret(), algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc


def user_from_request(request: Request, session: Session) -> User | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    user_id = decode_session_token(token)
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
