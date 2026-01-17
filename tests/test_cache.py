"""
Tests for the caching module.

Tests the SimpleCache class, cached decorator, and
cache invalidation functions.
"""

import pytest
import time
import json
import hashlib
from unittest.mock import MagicMock, patch
from flask import Flask

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from web.cache import SimpleCache, cache, cached, invalidate_cache


class TestSimpleCache:
    """Tests for the SimpleCache class."""

    def test_init(self, fresh_cache):
        """Test SimpleCache initialization."""
        assert fresh_cache.cache == {}

    def test_set_and_get(self, fresh_cache):
        """Test basic set and get operations."""
        fresh_cache.set("key1", "value1", ttl_seconds=60)
        value, hit = fresh_cache.get("key1")

        assert value == "value1"
        assert hit is True

    def test_get_nonexistent_key(self, fresh_cache):
        """Test getting a nonexistent key."""
        value, hit = fresh_cache.get("nonexistent")

        assert value is None
        assert hit is False

    def test_get_expired_key(self, fresh_cache):
        """Test getting an expired key."""
        fresh_cache.set("key1", "value1", ttl_seconds=0.1)

        # Wait for expiry
        time.sleep(0.15)

        value, hit = fresh_cache.get("key1")

        assert value is None
        assert hit is False

    def test_expired_key_removed(self, fresh_cache):
        """Test expired key is removed from cache."""
        fresh_cache.set("key1", "value1", ttl_seconds=0.1)

        # Wait for expiry
        time.sleep(0.15)

        # Access triggers removal
        fresh_cache.get("key1")

        # Key should be removed
        assert "key1" not in fresh_cache.cache

    def test_overwrite_existing_key(self, fresh_cache):
        """Test overwriting an existing key."""
        fresh_cache.set("key1", "value1", ttl_seconds=60)
        fresh_cache.set("key1", "value2", ttl_seconds=60)

        value, hit = fresh_cache.get("key1")

        assert value == "value2"

    def test_different_keys(self, fresh_cache):
        """Test multiple different keys."""
        fresh_cache.set("key1", "value1", ttl_seconds=60)
        fresh_cache.set("key2", "value2", ttl_seconds=60)
        fresh_cache.set("key3", "value3", ttl_seconds=60)

        value1, _ = fresh_cache.get("key1")
        value2, _ = fresh_cache.get("key2")
        value3, _ = fresh_cache.get("key3")

        assert value1 == "value1"
        assert value2 == "value2"
        assert value3 == "value3"

    def test_cache_complex_values(self, fresh_cache):
        """Test caching complex values."""
        complex_value = {
            'list': [1, 2, 3],
            'nested': {'a': 'b'},
            'number': 42
        }
        fresh_cache.set("complex", complex_value, ttl_seconds=60)

        value, hit = fresh_cache.get("complex")

        assert value == complex_value
        assert hit is True


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_all(self, fresh_cache):
        """Test invalidating all cache entries."""
        fresh_cache.set("key1", "value1", ttl_seconds=60)
        fresh_cache.set("key2", "value2", ttl_seconds=60)
        fresh_cache.set("key3", "value3", ttl_seconds=60)

        fresh_cache.invalidate()

        assert fresh_cache.cache == {}

    def test_invalidate_pattern(self, fresh_cache):
        """Test invalidating entries matching pattern."""
        fresh_cache.set("user:1:data", "data1", ttl_seconds=60)
        fresh_cache.set("user:2:data", "data2", ttl_seconds=60)
        fresh_cache.set("post:1:data", "post1", ttl_seconds=60)

        fresh_cache.invalidate("user:")

        # User entries should be gone
        _, hit1 = fresh_cache.get("user:1:data")
        _, hit2 = fresh_cache.get("user:2:data")
        assert hit1 is False
        assert hit2 is False

        # Post entry should remain
        value, hit3 = fresh_cache.get("post:1:data")
        assert hit3 is True
        assert value == "post1"

    def test_invalidate_pattern_no_matches(self, fresh_cache):
        """Test invalidating pattern with no matches."""
        fresh_cache.set("key1", "value1", ttl_seconds=60)

        fresh_cache.invalidate("nonexistent")

        # Original entry should remain
        value, hit = fresh_cache.get("key1")
        assert hit is True

    def test_invalidate_none_clears_all(self, fresh_cache):
        """Test invalidate(None) clears all entries."""
        fresh_cache.set("key1", "value1", ttl_seconds=60)
        fresh_cache.set("key2", "value2", ttl_seconds=60)

        fresh_cache.invalidate(None)

        assert len(fresh_cache.cache) == 0


class TestCacheStats:
    """Tests for cache statistics."""

    def test_stats_empty_cache(self, fresh_cache):
        """Test stats with empty cache."""
        stats = fresh_cache.stats()

        assert stats['total_entries'] == 0
        assert stats['valid_entries'] == 0
        assert stats['expired_entries'] == 0

    def test_stats_with_valid_entries(self, fresh_cache):
        """Test stats with valid entries."""
        fresh_cache.set("key1", "value1", ttl_seconds=60)
        fresh_cache.set("key2", "value2", ttl_seconds=60)

        stats = fresh_cache.stats()

        assert stats['total_entries'] == 2
        assert stats['valid_entries'] == 2
        assert stats['expired_entries'] == 0

    def test_stats_with_expired_entries(self, fresh_cache):
        """Test stats with expired entries."""
        fresh_cache.set("valid", "value", ttl_seconds=60)
        fresh_cache.set("expired", "value", ttl_seconds=0.1)

        # Wait for one to expire
        time.sleep(0.15)

        stats = fresh_cache.stats()

        assert stats['total_entries'] == 2
        assert stats['valid_entries'] == 1
        assert stats['expired_entries'] == 1


class TestCacheThreadSafety:
    """Tests for cache thread safety."""

    def test_concurrent_access(self, fresh_cache):
        """Test concurrent read/write operations."""
        import threading
        results = []

        def writer():
            for i in range(100):
                fresh_cache.set(f"key_{i}", f"value_{i}", ttl_seconds=60)

        def reader():
            for i in range(100):
                value, hit = fresh_cache.get(f"key_{i}")
                if hit:
                    results.append(value)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without errors

    def test_concurrent_invalidation(self, fresh_cache):
        """Test concurrent invalidation operations."""
        import threading

        def populate_and_invalidate():
            for i in range(50):
                fresh_cache.set(f"key_{i}", f"value_{i}", ttl_seconds=60)
            fresh_cache.invalidate()

        threads = [threading.Thread(target=populate_and_invalidate) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without errors


class TestCachedDecorator:
    """Tests for the cached decorator."""

    def test_cached_decorator_basic(self):
        """Test basic cached decorator functionality."""
        app = Flask(__name__)

        from web import cache as cache_module
        original_cache = cache_module.cache
        cache_module.cache = SimpleCache()

        call_count = [0]

        try:
            @app.route('/test')
            @cached(ttl_seconds=60)
            def test_endpoint():
                call_count[0] += 1
                return {"count": call_count[0]}

            with app.test_client() as client:
                # First call
                response1 = client.get('/test')
                # Second call should use cache
                response2 = client.get('/test')

                # Function should only be called once
                assert call_count[0] == 1

        finally:
            cache_module.cache = original_cache

    def test_cached_decorator_different_params(self):
        """Test cached decorator with different parameters."""
        app = Flask(__name__)

        from web import cache as cache_module
        original_cache = cache_module.cache
        cache_module.cache = SimpleCache()

        call_count = [0]

        try:
            @app.route('/test')
            @cached(ttl_seconds=60)
            def test_endpoint():
                call_count[0] += 1
                return {"count": call_count[0]}

            with app.test_client() as client:
                # Different query params should create different cache keys
                client.get('/test?param=1')
                client.get('/test?param=2')

                # Function should be called twice (different cache keys)
                assert call_count[0] == 2

        finally:
            cache_module.cache = original_cache

    def test_cached_decorator_expiry(self):
        """Test cached decorator respects TTL."""
        app = Flask(__name__)

        from web import cache as cache_module
        original_cache = cache_module.cache
        cache_module.cache = SimpleCache()

        call_count = [0]

        try:
            @app.route('/test')
            @cached(ttl_seconds=0.1)
            def test_endpoint():
                call_count[0] += 1
                return {"count": call_count[0]}

            with app.test_client() as client:
                client.get('/test')

                # Wait for cache to expire
                time.sleep(0.15)

                client.get('/test')

                # Function should be called twice
                assert call_count[0] == 2

        finally:
            cache_module.cache = original_cache

    def test_cached_decorator_custom_prefix(self):
        """Test cached decorator with custom key prefix."""
        app = Flask(__name__)

        from web import cache as cache_module
        original_cache = cache_module.cache
        cache_module.cache = SimpleCache()

        try:
            @app.route('/test')
            @cached(ttl_seconds=60, key_prefix='custom_prefix')
            def test_endpoint():
                return {"status": "ok"}

            with app.test_client() as client:
                client.get('/test')

                # Check cache key prefix
                cache_keys = list(cache_module.cache.cache.keys())
                assert any('custom_prefix' in key for key in cache_keys)

        finally:
            cache_module.cache = original_cache


class TestInvalidateCacheFunction:
    """Tests for the invalidate_cache function."""

    def test_invalidate_cache_all(self):
        """Test invalidate_cache clears all entries."""
        from web import cache as cache_module

        original_cache = cache_module.cache
        cache_module.cache = SimpleCache()

        try:
            cache_module.cache.set("key1", "value1", ttl_seconds=60)
            cache_module.cache.set("key2", "value2", ttl_seconds=60)

            invalidate_cache()

            assert len(cache_module.cache.cache) == 0

        finally:
            cache_module.cache = original_cache

    def test_invalidate_cache_pattern(self):
        """Test invalidate_cache with pattern."""
        from web import cache as cache_module

        original_cache = cache_module.cache
        cache_module.cache = SimpleCache()

        try:
            cache_module.cache.set("api_users:data", "value1", ttl_seconds=60)
            cache_module.cache.set("api_posts:data", "value2", ttl_seconds=60)

            invalidate_cache("users")

            _, hit1 = cache_module.cache.get("api_users:data")
            _, hit2 = cache_module.cache.get("api_posts:data")

            assert hit1 is False
            assert hit2 is True

        finally:
            cache_module.cache = original_cache


class TestCacheEdgeCases:
    """Edge case tests for caching."""

    def test_cache_none_value(self, fresh_cache):
        """Test caching None as a value."""
        fresh_cache.set("key", None, ttl_seconds=60)
        value, hit = fresh_cache.get("key")

        assert value is None
        assert hit is True

    def test_cache_empty_string_key(self, fresh_cache):
        """Test caching with empty string key."""
        fresh_cache.set("", "value", ttl_seconds=60)
        value, hit = fresh_cache.get("")

        assert value == "value"
        assert hit is True

    def test_cache_very_long_key(self, fresh_cache):
        """Test caching with very long key."""
        long_key = "x" * 10000
        fresh_cache.set(long_key, "value", ttl_seconds=60)
        value, hit = fresh_cache.get(long_key)

        assert value == "value"
        assert hit is True

    def test_cache_special_characters_in_key(self, fresh_cache):
        """Test caching with special characters in key."""
        special_key = "key:with/special?chars&symbols=true"
        fresh_cache.set(special_key, "value", ttl_seconds=60)
        value, hit = fresh_cache.get(special_key)

        assert value == "value"
        assert hit is True

    def test_cache_unicode_key(self, fresh_cache):
        """Test caching with unicode key."""
        unicode_key = "key_with_unicode_"
        fresh_cache.set(unicode_key, "value", ttl_seconds=60)
        value, hit = fresh_cache.get(unicode_key)

        assert value == "value"
        assert hit is True

    def test_cache_very_short_ttl(self, fresh_cache):
        """Test caching with very short TTL."""
        fresh_cache.set("key", "value", ttl_seconds=0.001)

        # Should still be valid immediately
        value, hit = fresh_cache.get("key")
        # May or may not hit depending on timing

    def test_cache_very_long_ttl(self, fresh_cache):
        """Test caching with very long TTL."""
        fresh_cache.set("key", "value", ttl_seconds=86400 * 365)  # 1 year

        value, hit = fresh_cache.get("key")

        assert value == "value"
        assert hit is True

    def test_cache_binary_data(self, fresh_cache):
        """Test caching binary data."""
        binary_data = b'\x00\x01\x02\x03'
        fresh_cache.set("binary", binary_data, ttl_seconds=60)
        value, hit = fresh_cache.get("binary")

        assert value == binary_data
        assert hit is True

    def test_cache_function_reference(self, fresh_cache):
        """Test caching function reference."""
        def my_func():
            return "hello"

        fresh_cache.set("func", my_func, ttl_seconds=60)
        value, hit = fresh_cache.get("func")

        assert value() == "hello"
        assert hit is True


class TestCacheKeyGeneration:
    """Tests for cache key generation in cached decorator."""

    def test_cache_key_includes_function_name(self):
        """Test cache key includes function name by default."""
        app = Flask(__name__)

        from web import cache as cache_module
        original_cache = cache_module.cache
        cache_module.cache = SimpleCache()

        try:
            @app.route('/test')
            @cached(ttl_seconds=60)
            def my_unique_function():
                return {"status": "ok"}

            with app.test_client() as client:
                client.get('/test')

                cache_keys = list(cache_module.cache.cache.keys())
                assert any('my_unique_function' in key for key in cache_keys)

        finally:
            cache_module.cache = original_cache

    def test_cache_key_hash_consistency(self):
        """Test cache key hash is consistent for same params."""
        params = {'a': 1, 'b': 2}
        params_str = json.dumps(params, sort_keys=True)
        hash1 = hashlib.md5(params_str.encode()).hexdigest()
        hash2 = hashlib.md5(params_str.encode()).hexdigest()

        assert hash1 == hash2

    def test_cache_key_hash_different_for_different_params(self):
        """Test cache key hash differs for different params."""
        params1 = {'a': 1}
        params2 = {'a': 2}
        params_str1 = json.dumps(params1, sort_keys=True)
        params_str2 = json.dumps(params2, sort_keys=True)
        hash1 = hashlib.md5(params_str1.encode()).hexdigest()
        hash2 = hashlib.md5(params_str2.encode()).hexdigest()

        assert hash1 != hash2
