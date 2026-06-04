from unittest.mock import MagicMock, patch

from app.analyzer import analyze_log
from app.cache import cache_key
from app.models import AnalysisResult


def test_cache_key_stable_for_same_log():
    log = "Error: connection refused\n  at redis:6379"
    a = cache_key(log, "kubernetes")
    b = cache_key(log, "kubernetes")
    c = cache_key(log + "  \n", "kubernetes")
    assert a == b == c


def test_cache_key_differs_for_different_logs():
    assert cache_key("error a", None) != cache_key("error b", None)


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
    first = analyze_log(log, "kubernetes")
    second = analyze_log(log, "kubernetes")

    assert first.symptom == "Redis down"
    assert second.symptom == "Redis down"
    mock_claude.assert_called_once()


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
        result = analyze_log("some log without redis cache", None)
        assert isinstance(result, AnalysisResult)
        mock_claude.assert_called_once()
