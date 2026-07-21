"""Eval suite for incident-history retrieval (Incident Intelligence)."""

import json
import os
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.incident_retrieval import (
    clear_incident_embed_cache,
    find_similar_saved_incidents,
    format_incident_history_context,
    incidents_for_llm_context,
)
from app.models import SavedIncident, User

EVAL_PATH = Path(__file__).parent / "eval_incident_history.json"


def _load_eval_cases() -> list[dict]:
    return json.loads(EVAL_PATH.read_text())


@pytest.fixture(autouse=True)
def _clear_embed_cache():
    clear_incident_embed_cache()
    yield
    clear_incident_embed_cache()


@pytest.fixture
def eval_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(github_id=42, username="eval")
        session.add(user)
        session.commit()
        session.refresh(user)

        session.add(
            SavedIncident(
                user_id=user.id,
                log_text=(
                    "CrashLoopBackOff redis connection refused localhost:6379 "
                    "cache pod api"
                ),
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
        session.add(
            SavedIncident(
                user_id=user.id,
                log_text=(
                    "CrashLoopBackOff redis connection refused localhost:6379 "
                    "cache pod api confirmed"
                ),
                category="kubernetes",
                symptom="Redis unreachable confirmed",
                root_cause="App uses localhost instead of redis service",
                likely_fix="Set REDIS_URL to redis://redis:6379",
                confidence="high",
                response_json="{}",
                resolution="Set REDIS_URL=redis://redis:6379/0 in the Deployment",
                feedback=1,
            )
        )
        session.commit()
        yield session, user.id


@pytest.mark.parametrize("case", _load_eval_cases(), ids=lambda case: case["id"])
def test_eval_incident_history_keyword(eval_session, monkeypatch, case):
    """Fast CI path: keyword retrieval ranks the expected past incident first."""
    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "1")
    db, user_id = eval_session

    matches = find_similar_saved_incidents(db, user_id, case["log"], limit=3)
    assert matches, f"No matches for {case['id']}"
    assert matches[0].symptom == case["expect_symptom"]
    assert matches[0].method == case["expect_method"]
    min_score = case.get("min_score")
    if min_score is not None:
        assert matches[0].score >= min_score

    context = format_incident_history_context(matches)
    assert context, f"Expected LLM context for {case['id']}"
    assert case["expect_symptom"] in context

    if case.get("prefer_resolved"):
        assert "Confirmed resolution" in matches[0].content


@pytest.mark.parametrize("case", _load_eval_cases(), ids=lambda case: case["id"])
@pytest.mark.skipif(
    os.getenv("EVAL_INTEGRATION") != "1",
    reason="Set EVAL_INTEGRATION=1 to run semantic embedding eval (downloads model).",
)
def test_eval_incident_history_semantic(eval_session, case):
    """Full semantic eval — run locally before changing embedding / boost logic."""
    db, user_id = eval_session
    matches = find_similar_saved_incidents(db, user_id, case["log"], limit=3)
    assert matches, f"No matches for {case['id']}"
    # Semantic may surface either redis incident; prefer_resolved must win.
    if case.get("prefer_resolved"):
        assert matches[0].symptom == case["expect_symptom"]
        assert "Confirmed resolution" in matches[0].content
    else:
        symptoms = {m.symptom for m in matches}
        assert case["expect_symptom"] in symptoms or any(
            case["expect_symptom"].split()[0] in s for s in symptoms
        )
    assert incidents_for_llm_context(matches) or matches[0].method == "keyword"
