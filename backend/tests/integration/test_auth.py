"""
Integration tests for auth endpoints.

Tests registration, login, token refresh, and logout flows.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def assert_auth_cookies(response):
    cookies = response.headers.get_list("set-cookie")
    joined = "; ".join(cookies).lower()
    assert "access_token=" in joined
    assert "refresh_token=" in joined
    assert "httponly" in joined
    assert "samesite=lax" in joined


def get_cookie(response, name: str) -> str:
    value = response.cookies.get(name)
    assert value
    return value


class TestRegistration:
    """Tests for POST /api/v1/auth/register endpoint."""

    def test_register_success(self, client: TestClient, test_db_session: Session, sample_roles):
        """Successful registration creates user with CLIENT role."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "secure_password_123",
                "nombre": "New",
                "apellido": "User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert data["token_type"] == "cookie"
        assert data["expires_in"] == 1800
        assert data["user"]["email"] == "newuser@example.com"
        assert_auth_cookies(response)

        # Verify user was created with CLIENT role
        from backend.features.users.models import Usuario
        user = test_db_session.query(Usuario).filter_by(email="newuser@example.com").first()
        assert user is not None
        assert user.nombre == "New"
        role_codes = [r.codigo for r in user.roles]
        assert "CLIENT" in role_codes

    def test_register_duplicate_email(self, client: TestClient, sample_user):
        """Registration with duplicate email returns 409 RFC 7807."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",  # Same as sample_user
                "password": "secure_password_123",
                "nombre": "Another",
                "apellido": "User",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert data["status"] == 409
        assert data["title"] == "Conflict"

    def test_register_weak_password(self, client: TestClient):
        """Registration with weak password returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "123",  # Too short
                "nombre": "Weak",
                "apellido": "Password",
            },
        )

        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        """Registration with invalid email returns 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "secure_password_123",
                "nombre": "Invalid",
                "apellido": "Email",
            },
        )

        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/v1/auth/login endpoint."""

    def test_login_success(self, client: TestClient, sample_user):
        """Successful login returns token pair."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "test_password_123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert data["token_type"] == "cookie"
        assert data["expires_in"] == 1800
        assert data["user"]["email"] == "test@example.com"
        assert_auth_cookies(response)

    def test_login_invalid_email(self, client: TestClient, sample_user):
        """Login with non-existent email returns 401 with generic message."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "test_password_123",
            },
        )

        assert response.status_code == 401
        data = response.json()
        # RN-AU08: Same message for both cases
        assert "inválidas" in data["detail"].lower() or "invalid" in data["detail"].lower()

    def test_login_invalid_password(self, client: TestClient, sample_user):
        """Login with wrong password returns 401 with generic message."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrong_password",
            },
        )

        assert response.status_code == 401
        data = response.json()
        # RN-AU08: Same message for both cases
        assert "inválidas" in data["detail"].lower() or "invalid" in data["detail"].lower()

    def test_login_invalid_email_same_message_as_wrong_password(self, client: TestClient, sample_user):
        """RN-AU08: Error messages should be identical for invalid email vs wrong password."""
        response_invalid_email = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "test_password_123",
            },
        )

        response_wrong_password = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "wrong_password",
            },
        )

        # Both should have the same error message
        assert response_invalid_email.json()["detail"] == response_wrong_password.json()["detail"]


class TestTokenRefresh:
    """Tests for POST /api/v1/auth/refresh endpoint."""

    def test_refresh_success(self, client: TestClient, sample_user):
        """Token refresh returns new token pair."""
        # First login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "test_password_123",
            },
        )
        refresh_token = get_cookie(login_response, "refresh_token")

        # Now refresh using cookie jar
        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 200
        data = response.json()
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert data["token_type"] == "cookie"
        assert get_cookie(response, "refresh_token") != refresh_token

    def test_refresh_expired_token(self, client: TestClient, test_db_session: Session, sample_user):
        """Refresh with expired token returns 401."""
        from datetime import datetime, timedelta, timezone
        from backend.features.auth.models import RefreshToken
        from backend.shared.security import create_refresh_token, hash_token

        # Create an expired token (no family_id — D1 removed that field)
        expired_token = create_refresh_token()
        refresh_db = RefreshToken(
            user_id=sample_user.id,
            token_hash=hash_token(expired_token),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
        )
        test_db_session.add(refresh_db)
        test_db_session.commit()

        client.cookies.set("refresh_token", expired_token, path="/api/v1/auth")
        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == 401

    def test_refresh_replay_attack(self, client: TestClient, sample_user):
        """RN-AU05: Reusing a refresh token revokes all tokens."""
        # First login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "test_password_123",
            },
        )
        refresh_token = get_cookie(login_response, "refresh_token")

        # Use the token once (refresh)
        response1 = client.post("/api/v1/auth/refresh")
        assert response1.status_code == 200

        # Try to use the same token again (replay attack)
        client.cookies.set("refresh_token", refresh_token, path="/api/v1/auth")
        response2 = client.post("/api/v1/auth/refresh")
        assert response2.status_code == 401
        assert "reutilizado" in response2.json()["detail"].lower() or "reuse" in response2.json()["detail"].lower()


class TestLogout:
    """Tests for POST /api/v1/auth/logout endpoint."""

    def test_logout_success(self, client: TestClient, sample_user):
        """Logout revokes refresh token."""
        # Login first
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "test_password_123",
            },
        )
        refresh_token = get_cookie(login_response, "refresh_token")

        # Logout
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 204

        # Try to refresh with revoked token
        client.cookies.set("refresh_token", refresh_token, path="/api/v1/auth")
        refresh_response = client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 401

    def test_logout_without_cookie_is_best_effort(self, client: TestClient):
        """Logout without refresh cookie is best-effort and clears cookies."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 204


class TestProtectedRoutes:
    """Tests for RBAC and protected routes."""

    def test_protected_route_no_token(self, client: TestClient):
        """Access without token returns 401."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_protected_route_with_cookie(self, client: TestClient, sample_user):
        """Access with valid access cookie returns user info."""
        client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "test_password_123"},
        )
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "CLIENT" in data["roles"]
