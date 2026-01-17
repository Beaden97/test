"""
Caching for Gmail Cleanup API

Simple in-memory cache with TTL for expensive operations.
"""

from functools import wraps
import time
import hashlib
import json
from threading import Lock

from flask import request


class SimpleCache:
    """Thread-safe in-memory cache with TTL."""

    def __init__(self):
        self.cache = {}
        self.lock = Lock()

    def get(self, key: str):
        """Get value from cache if not expired."""
        with self.lock:
            if key in self.cache:
                value, expires_at = self.cache[key]
                if time.time() < expires_at:
                    return value, True  # (value, cache_hit)
                del self.cache[key]
        return None, False

    def set(self, key: str, value, ttl_seconds: int):
        """Set value with TTL."""
        with self.lock:
            self.cache[key] = (value, time.time() + ttl_seconds)

    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern."""
        with self.lock:
            if pattern is None:
                self.cache.clear()
            else:
                keys_to_delete = [k for k in self.cache if pattern in k]
                for k in keys_to_delete:
                    del self.cache[k]

    def stats(self) -> dict:
        """Get cache statistics."""
        with self.lock:
            now = time.time()
            valid_entries = sum(1 for _, (_, exp) in self.cache.items() if exp > now)
            return {
                "total_entries": len(self.cache),
                "valid_entries": valid_entries,
                "expired_entries": len(self.cache) - valid_entries
            }


# Global cache instance
cache = SimpleCache()


def cached(ttl_seconds: int = 300, key_prefix: str = None):
    """Caching decorator for functions.

    Args:
        ttl_seconds: Time to live in seconds
        key_prefix: Optional prefix for cache key
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Build cache key from function name and request params
            prefix = key_prefix or f.__name__
            params = dict(request.args) if request else {}
            params_str = json.dumps(params, sort_keys=True)
            cache_key = f"{prefix}:{hashlib.md5(params_str.encode()).hexdigest()}"

            # Check cache
            cached_value, hit = cache.get(cache_key)
            if hit:
                return cached_value

            # Execute function
            result = f(*args, **kwargs)

            # Cache the result
            cache.set(cache_key, result, ttl_seconds)

            return result
        return decorated
    return decorator


def invalidate_cache(pattern: str = None):
    """Invalidate cache entries."""
    cache.invalidate(pattern)
