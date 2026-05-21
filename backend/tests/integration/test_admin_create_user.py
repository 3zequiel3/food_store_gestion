"""
Integration tests for Admin POST create user endpoint (Slice 4).

Tests POST /api/v1/admin/usuarios:
- ADMIN can create users with various roles (CLIENT, COCINA)
- Duplicate email returns 409
- Invalid/empty roles return 422
- Non-ADMIN roles get 403
- Password is stored hashed (not plaintext)

Runner: cd backend && uv run pytest tests/integration/test_admin_create_user.py -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.security import hash_password, verify_password

CREATE_USER_URL = "/api/v1/admin/usuarios"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_headers(client: TestClient, test_db_session: Session, sample_roles):
    """Auth headers for an ADMIN user."""
    from features.users.models import Usuario, UsuarioRol

    user = Usuario(
        email="admin_create@example.com",
        password_hash=hash_password("admin_pw_123"),
        nombre="Admin",
        apellido="Creator",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=1))  # ADMIN
    test_db_session.commit()

    client.post(
        "/api/v1/auth/login",
        json={"email": "admin_create@example.com", "password": "admin_pw_123"},
    )
    return {}


@pytest.fixture
def pedidos_headers(client: TestClient, test_db_session: Session, sample_roles):
    """Auth headers for a PEDIDOS user (should be forbidden)."""
    from features.users.models import Usuario, UsuarioRol

    user = Usuario(
        email="pedidos_create@example.com",
        password_hash=hash_password("pedidos_pw_123"),
        nombre="Pedidos",
        apellido="NoCreate",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    test_db_session.add(UsuarioRol(user_id=user.id, role_id=3))  # PEDIDOS
    test_db_session.commit()

    client.post(
        "/api/v1/auth/login",
        json={"email": "pedidos_create@example.com", "password": "pedidos_pw_123"},
    )
    return {}


@pytest.fixture
def client_headers_for_create(client: TestClient, sample_user):
    """Auth headers for a CLIENT user (should be forbidden)."""
    client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test_password_123"},
    )
    return {}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAdminCreateUser:
    """POST /api/v1/admin/usuarios — create user endpoint."""

    def test_admin_can_create_user_with_client_role(
        self, client: TestClient, admin_headers
    ):
        """ADMIN can create a user with CLIENT role, returns 201."""
        payload = {
            "email": "newclient@example.com",
            "password": "secure_password_123",
            "nombre": "New",
            "apellido": "Client",
            "roles": ["CLIENT"],
        }
        response = client.post(CREATE_USER_URL, json=payload, headers=admin_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newclient@example.com"
        assert data["nombre"] == "New"
        assert data["apellido"] == "Client"
        assert data["roles"] == ["CLIENT"]
        assert data["is_active"] is True
        # password_hash must NOT be in response
        assert "password_hash" not in data

    def test_admin_can_create_user_with_cocina_role(
        self, client: TestClient, admin_headers, test_db_session: Session
    ):
        """ADMIN can create a user with COCINA role, returns 201."""
        # Ensure COCINA role exists in the test DB
        from features.catalog.models import Rol
        from sqlalchemy import select as sa_select

        cocina_role = test_db_session.execute(
            sa_select(Rol).where(Rol.codigo == "COCINA")
        ).scalar_one_or_none()
        if not cocina_role:
            cocina_role = Rol(id=5, codigo="COCINA", descripcion="Cocinero")
            test_db_session.add(cocina_role)
            test_db_session.commit()

        payload = {
            "email": "newcocina@example.com",
            "password": "secure_password_123",
            "nombre": "New",
            "apellido": "Cocina",
            "roles": ["COCINA"],
        }
        response = client.post(CREATE_USER_URL, json=payload, headers=admin_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newcocina@example.com"
        assert data["roles"] == ["COCINA"]

    def test_create_user_duplicate_email_409(
        self, client: TestClient, admin_headers, test_db_session: Session
    ):
        """POST with existing email returns 409 Conflict."""
        from features.users.models import Usuario

        # Create a user first
        existing = Usuario(
            email="duplicate@example.com",
            password_hash=hash_password("existing_pw"),
            nombre="Existing",
            apellido="User",
            is_active=True,
        )
        test_db_session.add(existing)
        test_db_session.commit()

        # Try to create with same email
        payload = {
            "email": "duplicate@example.com",
            "password": "secure_password_123",
            "nombre": "Duplicate",
            "apellido": "Attempt",
            "roles": ["CLIENT"],
        }
        response = client.post(CREATE_USER_URL, json=payload, headers=admin_headers)

        assert response.status_code == 409

    def test_create_user_invalid_role_422(
        self, client: TestClient, admin_headers
    ):
        """POST with roles=['INVALID_ROLE'] returns 422."""
        payload = {
            "email": "invalidrole@example.com",
            "password": "secure_password_123",
            "nombre": "Invalid",
            "apellido": "Role",
            "roles": ["INVALID_ROLE"],
        }
        response = client.post(CREATE_USER_URL, json=payload, headers=admin_headers)

        assert response.status_code == 422

    def test_create_user_empty_roles_422(
        self, client: TestClient, admin_headers
    ):
        """POST with roles=[] returns 422."""
        payload = {
            "email": "emptyrole@example.com",
            "password": "secure_password_123",
            "nombre": "Empty",
            "apellido": "Role",
            "roles": [],
        }
        response = client.post(CREATE_USER_URL, json=payload, headers=admin_headers)

        assert response.status_code == 422

    def test_create_user_forbidden_for_non_admin(
        self, client: TestClient, pedidos_headers, client_headers_for_create
    ):
        """POST with PEDIDOS or CLIENT role returns 403."""
        payload = {
            "email": "forbidden@example.com",
            "password": "secure_password_123",
            "nombre": "Forbidden",
            "apellido": "User",
            "roles": ["CLIENT"],
        }

        # PEDIDOS should get 403
        response = client.post(CREATE_USER_URL, json=payload, headers=pedidos_headers)
        assert response.status_code == 403

        # CLIENT should get 403
        response = client.post(CREATE_USER_URL, json=payload, headers=client_headers_for_create)
        assert response.status_code == 403

    def test_create_user_password_hashed(
        self, client: TestClient, admin_headers, test_db_session: Session
    ):
        """Verify the stored password is hashed (not plaintext)."""
        from features.users.models import Usuario

        clear_password = "my_secret_password_123"
        payload = {
            "email": "hashcheck@example.com",
            "password": clear_password,
            "nombre": "Hash",
            "apellido": "Check",
            "roles": ["CLIENT"],
        }
        response = client.post(CREATE_USER_URL, json=payload, headers=admin_headers)
        assert response.status_code == 201

        # Fetch the user from DB and verify password is hashed
        user = test_db_session.execute(
            select(Usuario).where(Usuario.email == "hashcheck@example.com")
        ).scalar_one_or_none()
        assert user is not None

        # The stored password should NOT be the plaintext
        assert user.password_hash != clear_password

        # But it should verify correctly with bcrypt
        assert verify_password(clear_password, user.password_hash) is True
