import os

from sqlmodel import Session, select

from app.models import User

_SYSTEM_GITHUB_ID = os.getenv("DEBUGPILOT_SYSTEM_GITHUB_ID", "").strip()


def resolve_incident_user_id(
    session: Session,
    *,
    actor: str | None = None,
    actor_github_id: int | None = None,
) -> int:
    """Map automated incidents to a user row (GitHub id / username match or system user)."""
    if actor_github_id:
        row = session.exec(select(User).where(User.github_id == actor_github_id)).first()
        if row and row.id is not None:
            return row.id

    if actor:
        row = session.exec(select(User).where(User.username == actor)).first()
        if row and row.id is not None:
            return row.id

    if _SYSTEM_GITHUB_ID:
        try:
            github_id = int(_SYSTEM_GITHUB_ID)
        except ValueError:
            github_id = 0
        if github_id:
            row = session.exec(select(User).where(User.github_id == github_id)).first()
            if row and row.id is not None:
                return row.id

    raise RuntimeError(
        "No user available for automated incident ingestion. "
        "Log into DebugPilot with the GitHub account that triggered the workflow, "
        "or set DEBUGPILOT_SYSTEM_GITHUB_ID to that account's numeric GitHub id."
    )
