import os

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session

from app.auth import user_from_request
from app.auth_settings import auth_enabled
from app.database import get_session
from app.models import User


def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:
    if not auth_enabled():
        return _dev_user(session)

    user = user_from_request(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user


def _dev_user(session: Session) -> User:
    """Stable local user when auth is disabled (tests / local dev without OAuth)."""
    from sqlmodel import select

    row = session.exec(select(User).where(User.github_id == 0)).first()
    if row:
        return row
    user = User(
        github_id=0,
        username=os.getenv("AUTH_DEV_USERNAME", "dev"),
        display_name="Local Developer",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
