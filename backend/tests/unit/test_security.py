"""
Unit tests for security utilities.

Tests password hashing, JWT encoding/decoding, and token generation.
"""

import time
from datetime import timedelta

import pytest
from jose import jwt

from backend.config import settings
from backend.shared.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)


class TestPasswordHashing:
    """Tests for bcrypt password hashing."""

    def test_hash_password_produces_different_hashes(self):
        """Same password should produce different hashes (salt)."""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert hash1.startswith("$2b$")  # bcrypt prefix
        assert hash2.startswith("$2b$")

    def test_verify_password_correct(self):
        """Verify should return True for correct password."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Verify should return False for incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_bcrypt_cost_factor(self):
        """Verify bcrypt uses cost factor 12."""
        password = "test"
        hashed = hash_password(password)

        # bcrypt format: $2b$12$... where 12 is the cost factor
        parts = hashed.split("$")
        cost_factor = int(parts[2])
        assert cost_factor == 12


class TestJWTToken:
    """Tests for JWT access token generation and validation."""

    def test_create_access_token_contains_claims(self):
        """Token should contain user claims."""
        token = create_access_token(
            user_id=123,
            email="test@example.com",
            roles=["CLIENT"],
        )

        # Decode without verification to check payload (jose API: get_unverified_claims)
        payload = jwt.get_unverified_claims(token)

        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
        assert payload["roles"] == ["CLIENT"]
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_access_token_with_custom_expiry(self):
        """Token can have custom expiration time."""
        token = create_access_token(
            user_id=123,
            email="test@example.com",
            roles=["CLIENT"],
            expires_delta=timedelta(minutes=5),
        )

        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "123"

    def test_decode_valid_token(self):
        """decode_access_token should return payload for valid token."""
        token = create_access_token(
            user_id=123,
            email="test@example.com",
            roles=["CLIENT"],
        )

        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"

    def test_decode_invalid_token_returns_none(self):
        """decode_access_token should return None for invalid token."""
        payload = decode_access_token("invalid.token.here")

        assert payload is None

    def test_decode_tampered_token_returns_none(self):
        """decode_access_token should return None for tampered token."""
        token = create_access_token(
            user_id=123,
            email="test@example.com",
            roles=["CLIENT"],
        )

        # Tamper with the token
        tampered = token[:-10] + "tampered!!"

        payload = decode_access_token(tampered)
        assert payload is None

    def test_decode_expired_token_returns_none(self):
        """decode_access_token should return None for expired token."""
        # Create token that expires immediately (jose uses seconds granularity; seconds=0 is NOT expired)
        token = create_access_token(
            user_id=123,
            email="test@example.com",
            roles=["CLIENT"],
            expires_delta=timedelta(seconds=-1),
        )

        # Wait a bit to ensure expiration
        time.sleep(0.1)

        payload = decode_access_token(token)
        assert payload is None


class TestRefreshToken:
    """Tests for refresh token generation and hashing."""

    def test_create_refresh_token_is_uuid_v4(self):
        """Refresh token should be a valid UUID v4."""
        token = create_refresh_token()

        # Should be a valid UUID string
        import uuid
        uuid_obj = uuid.UUID(token)
        assert uuid_obj.version == 4

    def test_create_refresh_token_unique(self):
        """Each refresh token should be unique."""
        tokens = [create_refresh_token() for _ in range(10)]

        assert len(set(tokens)) == 10  # All unique

    def test_hash_token_produces_sha256(self):
        """hash_token should produce SHA-256 hex digest."""
        token = "test_token"
        hashed = hash_token(token)

        assert len(hashed) == 64  # SHA-256 hex is 64 chars
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_token_deterministic(self):
        """Same token should produce same hash."""
        token = "test_token"
        hash1 = hash_token(token)
        hash2 = hash_token(token)

        assert hash1 == hash2

    def test_hash_token_different_inputs(self):
        """Different tokens should produce different hashes."""
        hash1 = hash_token("token1")
        hash2 = hash_token("token2")

        assert hash1 != hash2
