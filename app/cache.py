import hashlib
import json
import os
from typing import Any, Optional

import redis

TTL_SECONDS = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "604800"))
CACHE_VERSION = os.getenv("ANALYSIS_CACHE_VERSION", "1")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
KEY_PREFIX = "debugpilot:analysis"

_redis: Optional[redis.Redis] = None
_redis_checked = False


def get_redis() -> Optional[redis.Redis]:
    global _redis, _redis_checked
    if _redis_checked:
        return _redis
    _redis_checked = True

    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return None

    try:
        client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        _redis = client
    except redis.RedisError:
        _redis = None
    return _redis


def cache_key(log_text: str, source_hint: Optional[str], user_id: Optional[int] = None) -> str:
    normalized = " ".join(log_text.strip().split())
    hint = source_hint or ""
    user_part = str(user_id) if user_id is not None else ""
    payload = f"{CACHE_VERSION}\n{MODEL}\n{hint}\n{user_part}\n{normalized}"
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"{KEY_PREFIX}:{digest}"


def get_cached_analysis(key: str) -> Optional[dict[str, Any]]:
    client = get_redis()
    if not client:
        return None
    try:
        raw = client.get(key)
        if raw:
            return json.loads(raw)
    except (redis.RedisError, json.JSONDecodeError):
        return None
    return None


def set_cached_analysis(key: str, data: dict[str, Any]) -> None:
    client = get_redis()
    if not client:
        return
    try:
        client.setex(key, TTL_SECONDS, json.dumps(data))
    except redis.RedisError:
        pass
