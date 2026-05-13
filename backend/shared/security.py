"""
Security utilities for authentication and authorization.

Provides password hashing (bcrypt), JWT token creation/validation,
and refresh token generation.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
from jose import JWTError, jwt

from config import settings


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(
    user_id: int,
    email: str,
    roles: List[str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: The user's ID
        email: The user's email
        roles: List of role codes (e.g., ['CLIENT', 'ADMIN'])
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "exp": expire,
        "type": "access",
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.

    Args:
        token: The JWT token string

    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def create_refresh_token() -> str:
    """
    Create a new opaque refresh token (UUID v4).

    Returns:
        Raw UUID string to return to client
    """
    return str(uuid.uuid4())


def hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for secure storage.

    Never store raw tokens in the database.

    Args:
        token: The raw token string

    Returns:
        SHA-256 hex digest
    """
    return hashlib.sha256(token.encode()).hexdigest()
