import redis
import json
import hashlib

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

def make_cache_key(prefix: str, **kwargs) -> str:
    raw = json.dumps(kwargs, sort_keys=True)
    hashed = hashlib.md5(raw.encode()).hexdigest()
    return f"{prefix}:{hashed}"

def get_cached(key: str):
    value = redis_client.get(key)
    if value:
        return json.loads(value)
    return None

def set_cached(key: str, value, ttl_seconds: int = 600):
    redis_client.setex(key, ttl_seconds, json.dumps(value))