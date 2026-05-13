"""
Rate limiting configuration using slowapi.

Provides Limiter instance for protecting endpoints against abuse.

Rate limits are environment-aware: tight in production to deter abuse, but
permissive in development/testing so end-to-end testing tools (TestSprite,
manual smoke tests, integration harnesses) can run many requests in a row
without tripping defensive throttling.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings

# Global limiter instance using IP address as key.
limiter = Limiter(key_func=get_remote_address)


def _build_rate_limits() -> dict[str, str]:
    """Return the rate-limit string table, adjusted for the current environment.

    In production (and any non-development environment) the values are the
    strict defaults intended to deter abuse. In development they are
    intentionally loose so an external test runner like TestSprite (which
    registers a fresh user per scenario) does not exhaust the per-IP window.
    """
    if settings.ENVIRONMENT == "development":
        return {
            "login": "1000/minute",
            "register": "1000/minute",
            "refresh": "1000/minute",
            "password_reset": "1000/minute",
            "api_general": "1000/minute",
        }
    return {
        "login": "5/15minute",  # 5 attempts per 15 minutes per IP
        "register": "3/hour",  # 3 registrations per hour per IP
        "refresh": "10/minute",  # 10 refresh requests per minute per IP
        "password_reset": "3/hour",  # 3 password reset attempts per hour
        "api_general": "100/minute",  # General API rate limit
    }


RATE_LIMITS = _build_rate_limits()


def get_rate_limit_string(limit_type: str) -> str:
    """Get rate limit string by type."""
    return RATE_LIMITS.get(limit_type, RATE_LIMITS["api_general"])
