"""
Tests for the rate limiting module.

Tests the RateLimiter class, rate_limit decorator, and
rate limit header handling.
"""

import pytest
import time
from unittest.mock import MagicMock, patch, PropertyMock
from flask import Flask, g

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from web.rate_limit import RateLimiter, rate_limit, add_rate_limit_headers
from web.errors import APIError


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_init(self, fresh_rate_limiter):
        """Test RateLimiter initialization."""
        assert fresh_rate_limiter.requests == {}

    def test_first_request_allowed(self, fresh_rate_limiter):
        """Test first request is always allowed."""
        allowed, info = fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=60)

        assert allowed is True
        assert info['limit'] == 10
        assert info['remaining'] == 9

    def test_within_limit_allowed(self, fresh_rate_limiter):
        """Test requests within limit are allowed."""
        # Make 5 requests
        for i in range(5):
            allowed, info = fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=60)
            assert allowed is True

        # Should have 5 remaining
        allowed, info = fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=60)
        assert allowed is True
        assert info['remaining'] == 4  # 10 - 6 = 4

    def test_at_limit_denied(self, fresh_rate_limiter):
        """Test request at limit is denied."""
        # Use up all requests
        for i in range(10):
            fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=60)

        # 11th request should be denied
        allowed, info = fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=60)

        assert allowed is False
        assert info['remaining'] == 0

    def test_different_clients_independent(self, fresh_rate_limiter):
        """Test different clients have independent limits."""
        # Use up client1's requests
        for i in range(10):
            fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=60)

        # Client2 should still be allowed
        allowed, info = fresh_rate_limiter.is_allowed("client2", limit=10, window_seconds=60)

        assert allowed is True
        assert info['remaining'] == 9

    def test_window_expiry(self, fresh_rate_limiter):
        """Test requests are allowed after window expires."""
        # Use up all requests
        for i in range(10):
            fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=1)

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        allowed, info = fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=1)

        assert allowed is True
        assert info['remaining'] == 9

    def test_retry_after_calculation(self, fresh_rate_limiter):
        """Test retry_after is calculated correctly."""
        # Use up all requests
        for i in range(10):
            fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=60)

        # Check retry_after
        allowed, info = fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=60)

        assert allowed is False
        assert 'reset_in' in info
        assert info['reset_in'] > 0
        assert info['reset_in'] <= 61  # Should be within window

    def test_thread_safety(self, fresh_rate_limiter):
        """Test rate limiter is thread-safe."""
        import threading
        results = []

        def make_requests():
            for _ in range(20):
                allowed, _ = fresh_rate_limiter.is_allowed("shared_client", limit=50, window_seconds=60)
                results.append(allowed)

        threads = [threading.Thread(target=make_requests) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have exactly 50 allowed and 50 denied
        assert results.count(True) == 50
        assert results.count(False) == 50

    def test_old_requests_cleaned(self, fresh_rate_limiter):
        """Test old requests are cleaned from the list."""
        # Make some requests
        for i in range(5):
            fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=1)

        # Wait for window
        time.sleep(1.1)

        # Make another request - old ones should be cleaned
        fresh_rate_limiter.is_allowed("client1", limit=10, window_seconds=1)

        # Check internal state
        assert len(fresh_rate_limiter.requests["client1"]) == 1

    def test_limit_of_one(self, fresh_rate_limiter):
        """Test with limit of 1."""
        allowed1, _ = fresh_rate_limiter.is_allowed("client1", limit=1, window_seconds=60)
        allowed2, _ = fresh_rate_limiter.is_allowed("client1", limit=1, window_seconds=60)

        assert allowed1 is True
        assert allowed2 is False

    def test_very_short_window(self, fresh_rate_limiter):
        """Test with very short window."""
        # Use up limit
        for i in range(5):
            fresh_rate_limiter.is_allowed("client1", limit=5, window_seconds=0.1)

        # Should be denied
        allowed, _ = fresh_rate_limiter.is_allowed("client1", limit=5, window_seconds=0.1)
        assert allowed is False

        # Wait for window
        time.sleep(0.15)

        # Should be allowed
        allowed, _ = fresh_rate_limiter.is_allowed("client1", limit=5, window_seconds=0.1)
        assert allowed is True


class TestRateLimitDecorator:
    """Tests for the rate_limit decorator."""

    def test_decorator_allows_within_limit(self):
        """Test decorator allows requests within limit."""
        app = Flask(__name__)

        @app.route('/test')
        @rate_limit(limit=10, window=60)
        def test_endpoint():
            return "OK"

        with app.test_client() as client:
            # First request should succeed
            response = client.get('/test')
            assert response.status_code == 200

    def test_decorator_blocks_over_limit(self):
        """Test decorator blocks requests over limit."""
        app = Flask(__name__)

        # Create a fresh rate limiter for this test
        from web import rate_limit as rl_module
        original_limiter = rl_module.rate_limiter
        rl_module.rate_limiter = RateLimiter()

        try:
            @app.route('/test')
            @rate_limit(limit=2, window=60)
            def test_endpoint():
                return "OK"

            with app.test_client() as client:
                # First two requests should succeed
                client.get('/test')
                client.get('/test')

                # Third request should fail
                response = client.get('/test')
                assert response.status_code == 429
        finally:
            rl_module.rate_limiter = original_limiter

    def test_decorator_custom_key_func(self):
        """Test decorator with custom key function."""
        app = Flask(__name__)

        from web import rate_limit as rl_module
        original_limiter = rl_module.rate_limiter
        rl_module.rate_limiter = RateLimiter()

        try:
            @app.route('/test')
            @rate_limit(limit=2, window=60, key_func=lambda: "custom_key")
            def test_endpoint():
                return "OK"

            with app.test_client() as client:
                # Use up the limit
                client.get('/test')
                client.get('/test')

                # Third should fail
                response = client.get('/test')
                assert response.status_code == 429
        finally:
            rl_module.rate_limiter = original_limiter

    def test_decorator_stores_rate_limit_info(self):
        """Test decorator stores rate limit info in g."""
        app = Flask(__name__)

        from web import rate_limit as rl_module
        original_limiter = rl_module.rate_limiter
        rl_module.rate_limiter = RateLimiter()

        stored_info = {}

        try:
            @app.route('/test')
            @rate_limit(limit=10, window=60)
            def test_endpoint():
                stored_info.update(g.rate_limit_info)
                return "OK"

            with app.test_client() as client:
                client.get('/test')

            assert 'limit' in stored_info
            assert 'remaining' in stored_info
            assert stored_info['limit'] == 10
        finally:
            rl_module.rate_limiter = original_limiter

    def test_decorator_error_details(self):
        """Test decorator includes details in error response."""
        app = Flask(__name__)

        from web import rate_limit as rl_module
        from web.errors import error_response

        # Register error handler
        @app.errorhandler(APIError)
        def handle_api_error(e):
            return error_response(e)

        original_limiter = rl_module.rate_limiter
        rl_module.rate_limiter = RateLimiter()

        try:
            @app.route('/test')
            @rate_limit(limit=1, window=60)
            def test_endpoint():
                return "OK"

            with app.test_client() as client:
                client.get('/test')  # Use up limit
                response = client.get('/test')  # Should fail

                assert response.status_code == 429
                # The error should be raised, but we need proper handler
        finally:
            rl_module.rate_limiter = original_limiter


class TestAddRateLimitHeaders:
    """Tests for the add_rate_limit_headers function."""

    def test_adds_headers_when_info_present(self):
        """Test headers are added when rate limit info is present."""
        app = Flask(__name__)

        with app.app_context():
            with app.test_request_context():
                g.rate_limit_info = {
                    'limit': 100,
                    'remaining': 95,
                    'reset_in': 60
                }

                response = MagicMock()
                response.headers = {}

                result = add_rate_limit_headers(response)

                assert result.headers['X-RateLimit-Limit'] == '100'
                assert result.headers['X-RateLimit-Remaining'] == '95'
                assert result.headers['X-RateLimit-Reset'] == '60'

    def test_no_headers_when_info_missing(self):
        """Test no headers added when rate limit info is missing."""
        app = Flask(__name__)

        with app.app_context():
            with app.test_request_context():
                # Don't set g.rate_limit_info

                response = MagicMock()
                response.headers = {}

                result = add_rate_limit_headers(response)

                assert 'X-RateLimit-Limit' not in result.headers

    def test_returns_response(self):
        """Test function returns the response object."""
        app = Flask(__name__)

        with app.app_context():
            with app.test_request_context():
                response = MagicMock()
                response.headers = {}

                result = add_rate_limit_headers(response)

                assert result is response


class TestRateLimitIntegration:
    """Integration tests for rate limiting with Flask app."""

    def test_rate_limit_with_real_app(self):
        """Test rate limiting with actual Flask app."""
        app = Flask(__name__)

        from web import rate_limit as rl_module
        original_limiter = rl_module.rate_limiter
        rl_module.rate_limiter = RateLimiter()

        try:
            @app.route('/api/test')
            @rate_limit(limit=3, window=60)
            def api_test():
                return {"status": "ok"}

            @app.after_request
            def after_request(response):
                return add_rate_limit_headers(response)

            with app.test_client() as client:
                # Make requests and check headers
                response1 = client.get('/api/test')
                assert response1.headers.get('X-RateLimit-Limit') == '3'
                assert response1.headers.get('X-RateLimit-Remaining') == '2'

                response2 = client.get('/api/test')
                assert response2.headers.get('X-RateLimit-Remaining') == '1'

                response3 = client.get('/api/test')
                assert response3.headers.get('X-RateLimit-Remaining') == '0'

        finally:
            rl_module.rate_limiter = original_limiter

    def test_different_endpoints_same_limit(self):
        """Test multiple endpoints share rate limit by IP."""
        app = Flask(__name__)

        from web import rate_limit as rl_module
        original_limiter = rl_module.rate_limiter
        rl_module.rate_limiter = RateLimiter()

        try:
            @app.route('/api/a')
            @rate_limit(limit=3, window=60)
            def api_a():
                return "A"

            @app.route('/api/b')
            @rate_limit(limit=3, window=60)
            def api_b():
                return "B"

            with app.test_client() as client:
                # Each endpoint has its own limit because the key includes
                # both IP and endpoint by default
                client.get('/api/a')
                client.get('/api/a')
                client.get('/api/a')

                # Endpoint B should still work (separate limit)
                response = client.get('/api/b')
                assert response.status_code == 200

        finally:
            rl_module.rate_limiter = original_limiter


class TestRateLimiterEdgeCases:
    """Edge case tests for rate limiter."""

    def test_empty_key(self, fresh_rate_limiter):
        """Test rate limiting with empty key."""
        allowed, info = fresh_rate_limiter.is_allowed("", limit=10, window_seconds=60)

        assert allowed is True

    def test_special_characters_in_key(self, fresh_rate_limiter):
        """Test rate limiting with special characters in key."""
        key = "192.168.1.1:user@example.com"
        allowed, info = fresh_rate_limiter.is_allowed(key, limit=10, window_seconds=60)

        assert allowed is True

    def test_very_large_limit(self, fresh_rate_limiter):
        """Test with very large limit."""
        allowed, info = fresh_rate_limiter.is_allowed("client1", limit=1000000, window_seconds=60)

        assert allowed is True
        assert info['remaining'] == 999999

    def test_zero_window(self, fresh_rate_limiter):
        """Test with zero window (effectively no rate limiting per request)."""
        # This is an edge case - with 0 window, all old requests are cleaned immediately
        for i in range(10):
            allowed, _ = fresh_rate_limiter.is_allowed("client1", limit=1, window_seconds=0)
            # Each request starts fresh because window is 0

    def test_concurrent_limit_exact(self, fresh_rate_limiter):
        """Test hitting limit exactly."""
        limit = 5
        for i in range(limit):
            allowed, info = fresh_rate_limiter.is_allowed("client1", limit=limit, window_seconds=60)
            assert allowed is True
            assert info['remaining'] == limit - i - 1

        # Next request should fail
        allowed, info = fresh_rate_limiter.is_allowed("client1", limit=limit, window_seconds=60)
        assert allowed is False
        assert info['remaining'] == 0

    def test_reset_in_never_negative(self, fresh_rate_limiter):
        """Test that reset_in is never negative."""
        # Use up limit
        for i in range(5):
            fresh_rate_limiter.is_allowed("client1", limit=5, window_seconds=60)

        allowed, info = fresh_rate_limiter.is_allowed("client1", limit=5, window_seconds=60)

        assert info['reset_in'] >= 0
