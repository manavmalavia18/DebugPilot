import pytest

from app.retrieval import (
    PlaybookMatch,
    _cosine_similarity,
    _keyword_matches,
    find_relevant_playbooks,
    playbooks_for_llm_context,
    semantic_rag_enabled,
)


def test_cosine_similarity_identical_vectors():
    vector = [1.0, 0.0, 0.0]
    assert _cosine_similarity(vector, vector) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_keyword_matches_redis_log():
    log = "CrashLoopBackOff connection refused localhost:6379 redis cache unreachable"
    matches = _keyword_matches(log, limit=3)
    assert matches
    assert matches[0].name == "redis-localhost-k8s"
    assert matches[0].method == "keyword"


def test_keyword_matches_misses_paraphrased_failure():
    log = "application cannot reach in-memory store inside the pod"
    matches = _keyword_matches(log, limit=3)
    assert not any(match.name == "redis-localhost-k8s" for match in matches)


def test_find_relevant_playbooks_semantic_mock(monkeypatch):
    def fake_vectors():
        return (
            ("redis-localhost-k8s", "redis playbook", (1.0, 0.0, 0.0)),
            ("ingress-503", "ingress playbook", (0.0, 1.0, 0.0)),
        )

    def fake_embed(text: str):
        if "cache" in text.lower() or "6379" in text:
            return [0.95, 0.05, 0.0]
        return [0.0, 1.0, 0.0]

    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "0")
    monkeypatch.setattr("app.retrieval._playbook_vectors", fake_vectors)
    monkeypatch.setattr("app.retrieval._embed_text", fake_embed)

    log = "cache service unreachable inside pod on port 6379"
    matches = find_relevant_playbooks(log, limit=2)

    assert matches
    assert matches[0].name == "redis-localhost-k8s"
    assert matches[0].method == "semantic"
    assert matches[0].score > 0.5


def test_playbooks_for_llm_context_drops_weak_semantic():
    matches = [
        PlaybookMatch(name="weak", content="x", score=0.69, method="semantic"),
        PlaybookMatch(name="strong", content="y", score=0.89, method="semantic"),
    ]
    context = playbooks_for_llm_context(matches)
    assert len(context) == 1
    assert context[0].name == "strong"


def test_playbooks_for_llm_context_keeps_keyword_matches():
    matches = [
        PlaybookMatch(name="redis-localhost-k8s", content="x", score=0.5, method="keyword"),
    ]
    assert playbooks_for_llm_context(matches) == matches


def test_find_relevant_playbooks_keyword_fallback(monkeypatch):
    monkeypatch.setenv("SEMANTIC_RAG_DISABLED", "1")
    assert semantic_rag_enabled() is False

    log = "CrashLoopBackOff redis localhost 6379"
    matches = find_relevant_playbooks(log, limit=2)

    assert matches
    assert matches[0].method == "keyword"
    assert isinstance(matches[0], PlaybookMatch)
