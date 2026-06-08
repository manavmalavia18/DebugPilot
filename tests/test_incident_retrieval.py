import pytest
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from app.incident_retrieval import (
    find_similar_saved_incidents,
    format_incident_history_context,
    incidents_for_llm_context,
    incidents_for_ui_display,
)
from app.models import SavedIncident, User


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(github_id=99, username="tester")
        session.add(user)
        session.commit()
        session.refresh(user)

        session.add(
            SavedIncident(
                user_id=user.id,
                log_text="CrashLoopBackOff redis connection refused localhost:6379 cache pod api",
                category="kubernetes",
                symptom="Redis unreachable",
                root_cause="App uses localhost instead of redis service",
                likely_fix="Set REDIS_URL to redis://redis:6379",
                confidence="high",
                response_json="{}",
            )
        )
        session.add(
            SavedIncident(
                user_id=user.id,
                log_text="terraform error acquiring state lock dynamodb",
                category="terraform",
                symptom="State lock",
                root_cause="Stale lock from CI",
                likely_fix="Run terraform force-unlock",
                confidence="medium",
                response_json="{}",
            )
        )
        session.commit()
        yield session, user.id


def test_find_similar_saved_incidents_keyword(session, monkeypatch):
    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "1")
    db, user_id = session
    log = "CrashLoopBackOff connection refused localhost:6379 redis cache unreachable"
    matches = find_similar_saved_incidents(db, user_id, log, limit=2)
    assert matches
    assert matches[0].incident_id == 1
    assert matches[0].method == "keyword"


def test_find_similar_saved_incidents_semantic_mock(session, monkeypatch):
    db, user_id = session

    def fake_embed(text: str):
        if "6379" in text or "redis" in text.lower():
            return [1.0, 0.0, 0.0]
        if "terraform" in text.lower() or "state lock" in text.lower():
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "0")
    monkeypatch.setattr("app.incident_retrieval._embed_text", fake_embed)

    matches = find_similar_saved_incidents(
        db,
        user_id,
        "pod cannot connect to cache on port 6379",
        limit=1,
    )
    assert matches
    assert matches[0].method == "semantic"
    assert "Redis unreachable" in matches[0].content


def test_incidents_for_llm_context_requires_strong_semantic_match():
    from app.incident_retrieval import IncidentHistoryMatch

    weak = incidents_for_llm_context(
        [
            IncidentHistoryMatch(
                incident_id=1,
                content="x",
                score=0.5,
                method="semantic",
                symptom="s",
            ),
        ]
    )
    assert weak == []


def test_find_similar_saved_incidents_weak_semantic_falls_back_to_keyword(session, monkeypatch):
    db, user_id = session

    def weak_embed(text: str):
        # Similar enough to rank but below RETRIEVAL_CONTEXT_MIN_SCORE (0.70).
        if "6379" in text or "redis" in text.lower():
            if "terraform" in text.lower() or "state lock" in text.lower():
                return [0.0, 0.0, 1.0]
            if "Symptom:" in text or "Root cause:" in text or "Fix:" in text:
                return [0.6, 0.0, 0.0]
            return [0.6, 0.8, 0.0]
        if "terraform" in text.lower() or "state lock" in text.lower():
            return [0.0, 0.0, 1.0]
        return [0.0, 0.0, 1.0]

    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "0")
    monkeypatch.setattr("app.incident_retrieval._embed_text", weak_embed)

    log = "CrashLoopBackOff connection refused localhost:6379 redis cache unreachable"
    matches = find_similar_saved_incidents(db, user_id, log, limit=2)
    assert matches
    assert matches[0].method == "keyword"
    assert matches[0].incident_id == 1


def test_keyword_match_uses_symptom_and_fix_fields(session, monkeypatch):
    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "1")
    db, user_id = session
    # Short log with few tokens — still matches via saved symptom/root_cause overlap.
    log = "redis connection refused localhost:6379"
    matches = find_similar_saved_incidents(db, user_id, log, limit=1)
    assert matches
    assert matches[0].incident_id == 1


def test_thumbs_down_incidents_excluded(session, monkeypatch):
    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "1")
    db, user_id = session
    row = db.exec(select(SavedIncident).where(SavedIncident.id == 1)).first()
    row.feedback = -1
    db.add(row)
    db.commit()

    log = "CrashLoopBackOff connection refused localhost:6379 redis cache unreachable"
    matches = find_similar_saved_incidents(db, user_id, log, limit=2)
    assert len(matches) == 0


def test_incidents_for_ui_display_falls_back_to_keyword():
    from app.incident_retrieval import IncidentHistoryMatch

    weak_semantic = [
        IncidentHistoryMatch(1, "a", 0.5, "semantic", "Redis crash"),
    ]
    assert incidents_for_llm_context(weak_semantic) == []

    keyword = [
        IncidentHistoryMatch(2, "b", 1.0, "keyword", "Redis crash"),
    ]
    display = incidents_for_ui_display(keyword)
    assert len(display) == 1
    assert display[0].incident_id == 2


def test_format_incident_history_context_includes_past_fix():
    from app.incident_retrieval import IncidentHistoryMatch

    text = format_incident_history_context(
        [
            IncidentHistoryMatch(
                incident_id=7,
                content="Root cause: bad host\nLikely fix: use service DNS",
                score=0.82,
                method="semantic",
                symptom="Redis unreachable",
            )
        ]
    )
    assert "Past incident #7" in text
    assert "use service DNS" in text
