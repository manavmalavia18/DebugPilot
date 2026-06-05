import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

DB_PATH = Path(os.getenv("DATABASE_PATH", Path(__file__).resolve().parent.parent / "debugpilot.db"))


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    return f"sqlite:///{DB_PATH}"


def _create_engine():
    url = _database_url()
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = _create_engine()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    _ensure_saved_incident_columns()


def _ensure_saved_incident_columns() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "savedincident" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("savedincident")}
    statements: list[str] = []
    if "resolution" not in columns:
        statements.append("ALTER TABLE savedincident ADD COLUMN resolution VARCHAR(2000)")
    if "feedback" not in columns:
        statements.append("ALTER TABLE savedincident ADD COLUMN feedback INTEGER")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def get_session():
    with Session(engine) as session:
        yield session
