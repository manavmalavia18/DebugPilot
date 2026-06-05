import json
import os
from pathlib import Path

import pytest

from app.retrieval import find_relevant_playbooks

EVAL_PATH = Path(__file__).parent / "eval_logs.json"


def _load_eval_cases() -> list[dict]:
    return json.loads(EVAL_PATH.read_text())


@pytest.mark.parametrize("case", _load_eval_cases(), ids=lambda case: case["id"])
def test_eval_top_playbook_keyword_fallback(monkeypatch, case):
    """Fast regression: keyword path must rank the expected playbook first."""
    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "1")
    matches = find_relevant_playbooks(case["log"], limit=3)
    assert matches, f"No matches for {case['id']}"
    assert matches[0].name == case["expect_top"]


@pytest.mark.parametrize("case", _load_eval_cases(), ids=lambda case: case["id"])
@pytest.mark.skipif(
    os.getenv("EVAL_INTEGRATION") != "1",
    reason="Set EVAL_INTEGRATION=1 to run semantic embedding eval (downloads model).",
)
def test_eval_top_playbook_semantic(case):
    """Full RAG eval with fastembed — run locally before changing playbooks or embeddings."""
    matches = find_relevant_playbooks(case["log"], limit=3)
    assert matches, f"No matches for {case['id']}"
    assert matches[0].name == case["expect_top"]
    min_score = case.get("min_score")
    if min_score is not None:
        assert matches[0].score >= min_score
