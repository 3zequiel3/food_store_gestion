"""
Rate limiting configuration using slowapi.

Provides Limiter instance for protecting endpoints against abuse.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter instance using IP address as key
limiter = Limiter(key_func=get_remote_address)

# Rate limit strings for common use cases
RATE_LIMITS = {
    "login": "5/15minute",  # 5 attempts per 15 minutes per IP
    "register": "3/hour",  # 3 registrations per hour per IP
    "refresh": "10/minute",  # 10 refresh requests per minute per IP
    "password_reset": "3/hour",  # 3 password reset attempts per hour
    "api_general": "100/minute",  # General API rate limit
}


def get_rate_limit_string(limit_type: str) -> str:
    """Get rate limit string by type."""
    return RATE_LIMITS.get(limit_type, RATE_LIMITS["api_general"])
