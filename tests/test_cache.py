from unittest.mock import MagicMock, patch

from app.analyzer import analyze_log
from app.cache import cache_key, history_fingerprint
from app.models import AnalysisResult


def test_cache_key_stable_for_same_log():
    log = "Error: connection refused\n  at redis:6379"
    a = cache_key(log, "kubernetes")
    b = cache_key(log, "kubernetes")
    c = cache_key(log + "  \n", "kubernetes")
    assert a == b == c


def test_cache_key_differs_for_different_logs():
    assert cache_key("error a", None) != cache_key("error b", None)


def test_cache_key_differs_when_history_context_changes():
    log = "CrashLoopBackOff redis connection refused"
    empty = cache_key(log, "kubernetes", history_fingerprint="")
    with_history = cache_key(
        log,
        "kubernetes",
        history_fingerprint=history_fingerprint("Past incident #1: use redis service DNS"),
    )
    assert empty != with_history
    assert history_fingerprint("") == ""
    assert history_fingerprint("Past incident #1") != history_fingerprint("Past incident #2")


@patch("app.analyzer.analyze_with_claude")
@patch("app.cache.get_redis")
def test_analyze_log_uses_redis_cache(mock_get_redis, mock_claude):
    stored = {}

    mock_client = MagicMock()

    def fake_get(key):
        return stored.get(key)

    def fake_setex(key, ttl, value):
        stored[key] = value

    mock_client.get.side_effect = fake_get
    mock_client.setex.side_effect = fake_setex
    mock_get_redis.return_value = mock_client

    payload = {
        "category": "kubernetes",
        "symptom": "Redis down",
        "what_failed": "pod",
        "root_cause": "wrong host",
        "confidence": "high",
        "debug_commands": ["kubectl get pods"],
        "likely_fix": "fix REDIS_HOST",
        "prevention": [],
        "warnings": [],
        "similar_incidents": [],
    }
    mock_claude.return_value = payload

    log = "redis connection refused localhost:6379 unique-test-12345"
    first, first_cached = analyze_log(log, "kubernetes")
    second, second_cached = analyze_log(log, "kubernetes")

    assert first.symptom == "Redis down"
    assert second.symptom == "Redis down"
    assert first_cached is False
    assert second_cached is True
    mock_claude.assert_called_once()


@patch("app.analyzer.analyze_with_claude")
@patch("app.cache.get_redis")
def test_analyze_log_cache_misses_when_history_context_added(mock_get_redis, mock_claude):
    """Same log with new past-incident context must not reuse the empty-history cache."""
    stored = {}
    mock_client = MagicMock()
    mock_client.get.side_effect = lambda key: stored.get(key)
    mock_client.setex.side_effect = lambda key, ttl, value: stored.__setitem__(key, value)
    mock_get_redis.return_value = mock_client

    mock_claude.side_effect = [
        {
            "category": "kubernetes",
            "symptom": "Redis down",
            "what_failed": "pod",
            "root_cause": "wrong host",
            "confidence": "high",
            "debug_commands": [],
            "likely_fix": "fix REDIS_HOST",
            "prevention": [],
            "warnings": [],
            "similar_incidents": [],
        },
        {
            "category": "kubernetes",
            "symptom": "Redis down (from history)",
            "what_failed": "pod",
            "root_cause": "localhost REDIS_URL",
            "confidence": "high",
            "debug_commands": [],
            "likely_fix": "Use redis service DNS",
            "prevention": [],
            "warnings": [],
            "similar_incidents": [],
        },
    ]

    log = "redis connection refused localhost:6379 history-cache-test"
    first, first_cached = analyze_log(log, "kubernetes", incident_history_context="")
    second, second_cached = analyze_log(
        log,
        "kubernetes",
        incident_history_context="Past incident #1:\nConfirmed resolution: use redis DNS",
    )

    assert first_cached is False
    assert second_cached is False
    assert second.symptom == "Redis down (from history)"
    assert mock_claude.call_count == 2
    assert "Past incident #1" in mock_claude.call_args_list[1].kwargs["incident_history_context"]


@patch("app.cache.get_redis", return_value=None)
def test_analyze_log_without_redis_still_works(mock_get_redis):
    with patch("app.analyzer.analyze_with_claude") as mock_claude:
        mock_claude.return_value = {
            "category": "app",
            "symptom": "x",
            "what_failed": "y",
            "root_cause": "z",
            "confidence": "low",
            "debug_commands": [],
            "likely_fix": "fix",
            "prevention": [],
            "warnings": [],
            "similar_incidents": [],
        }
        result, cached = analyze_log("some log without redis cache", None)
        assert isinstance(result, AnalysisResult)
        assert cached is False
        mock_claude.assert_called_once()
