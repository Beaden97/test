"""
Rate Limiting for Gmail Cleanup API

Simple in-memory rate limiter to protect against abuse.
"""

from functools import wraps
from collections import defaultdict
import time
from threading import Lock

from flask import request, g
from .errors import APIError, ErrorCode


class RateLimiter:
    """Thread-safe in-memory rate limiter."""

    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - window_seconds

        with self.lock:
            # Clean old requests
            self.requests[key] = [
                ts for ts in self.requests[key]
                if ts > window_start
            ]

            current_count = len(self.requests[key])

            if current_count >= limit:
                retry_after = int(self.requests[key][0] - window_start) + 1
                return False, {
                    "limit": limit,
                    "remaining": 0,
                    "reset_in": retry_after
                }

            self.requests[key].append(now)
            return True, {
                "limit": limit,
                "remaining": limit - current_count - 1,
                "reset_in": window_seconds
            }


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(limit: int = 60, window: int = 60, key_func=None):
    """Rate limiting decorator.

    Args:
        limit: Max requests per window
        window: Window size in seconds
        key_func: Function to extract rate limit key (default: client IP)
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if key_func:
                key = key_func()
            else:
                key = request.remote_addr or "unknown"

            allowed, info = rate_limiter.is_allowed(key, limit, window)

            # Store rate limit info for headers
            g.rate_limit_info = info

            if not allowed:
                raise APIError(
                    message=f"Rate limit exceeded. Try again in {info['reset_in']} seconds",
                    code=ErrorCode.RATE_LIMITED,
                    status_code=429,
                    details=info
                )

            return f(*args, **kwargs)
        return decorated
    return decorator


def add_rate_limit_headers(response):
    """Add rate limit headers to response (call in after_request)."""
    if hasattr(g, 'rate_limit_info'):
        info = g.rate_limit_info
        response.headers['X-RateLimit-Limit'] = str(info['limit'])
        response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
        response.headers['X-RateLimit-Reset'] = str(info['reset_in'])
    return response
