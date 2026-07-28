import hashlib
import json
from cachetools import TTLCache
from app.config import get_settings

settings = get_settings()

_cache: TTLCache = TTLCache(
    maxsize=settings.cache_max_size,
    ttl=settings.cache_ttl_seconds,
)


def make_key(endpoint: str, params: dict) -> str:
    """Create a stable cache key from endpoint name + params dict."""
    raw = json.dumps({"endpoint": endpoint, **params}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached(key: str):
    return _cache.get(key)


def set_cached(key: str, value) -> None:
    _cache[key] = value


def cache_size() -> int:
    return len(_cache)
