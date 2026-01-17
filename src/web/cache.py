"""
Caching for Gmail Cleanup API

Simple in-memory cache with TTL for expensive operations.
Includes automatic cleanup of expired entries to prevent memory leaks.
"""

from functools import wraps
import time
import hashlib
import json
import atexit
from threading import Lock, Thread, Event

from flask import request


class SimpleCache:
    """Thread-safe in-memory cache with TTL and automatic cleanup."""

    def __init__(self, cleanup_interval: int = 60):
        """
        Initialize cache with automatic cleanup.

        Args:
            cleanup_interval: Seconds between cleanup runs (default: 60)
        """
        self.cache = {}
        self.lock = Lock()
        self._cleanup_interval = cleanup_interval
        self._stop_event = Event()
        self._cleanup_thread = None

    def start_cleanup_thread(self):
        """Start background cleanup thread."""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return  # Already running

        self._stop_event.clear()
        self._cleanup_thread = Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def stop_cleanup_thread(self):
        """Stop background cleanup thread."""
        self._stop_event.set()
        if self._cleanup_thread is not None:
            self._cleanup_thread.join(timeout=2)
            self._cleanup_thread = None

    def _cleanup_loop(self):
        """Background loop that periodically removes expired entries."""
        while not self._stop_event.is_set():
            self._cleanup_expired()
            self._stop_event.wait(self._cleanup_interval)

    def _cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        removed = 0
        now = time.time()
        with self.lock:
            expired_keys = [k for k, (_, exp) in self.cache.items() if exp <= now]
            for k in expired_keys:
                del self.cache[k]
                removed += 1
        return removed

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
                "expired_entries": len(self.cache) - valid_entries,
                "cleanup_running": self._cleanup_thread is not None and self._cleanup_thread.is_alive()
            }


# Global cache instance with cleanup
cache = SimpleCache(cleanup_interval=60)
cache.start_cleanup_thread()

# Clean up on exit
atexit.register(cache.stop_cleanup_thread)


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
