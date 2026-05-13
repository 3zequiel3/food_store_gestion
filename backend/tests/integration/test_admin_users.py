"""
Integration tests for admin user management endpoints.

Covers:
  GET  /api/v1/admin/usuarios                   — paginated listing
  PUT  /api/v1/admin/usuarios/{id}              — edit personal data
  PATCH /api/v1/admin/usuarios/{id}/rol         — role replacement
  PATCH /api/v1/admin/usuarios/{id}/estado      — activate/deactivate

Business rules verified:
  - Only ADMIN role can access any endpoint (403 otherwise)
  - Pagination structure (items, total, page, page_size)
  - Search filter (nombre/email, case-insensitive ILIKE)
  - Role filter
  - PUT rejects extra fields (email, password_hash) → 422
  - PATCH /rol rejects invalid role codes → 422
  - PATCH /rol rejects degrading last ADMIN → 409
  - PATCH /rol and PATCH /estado revoke refresh tokens atomically
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.shared.security import hash_password, hash_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_refresh_tokens(session: Session, user_id: int, count: int = 2) -> list:
    """Insert N active refresh tokens for a user directly in the DB."""
    from backend.features.auth.models import RefreshToken

    tokens = []
    for i in range(count):
        rt = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(f"admin-test-token-{user_id}-{i}"),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            revoked_at=None,
        )
        session.add(rt)
        tokens.append(rt)
    session.commit()
    return tokens


def _make_user(session: Session, email: str, nombre: str, apellido: str, role_ids: list[int], is_active: bool = True):
    """Factory: create a Usuario with given roles and commit."""
    from backend.features.users.models import Usuario, UsuarioRol

    user = Usuario(
        email=email,
        password_hash=hash_password("test_pass_123"),
        nombre=nombre,
        apellido=apellido,
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    for role_id in role_ids:
        session.add(UsuarioRol(user_id=user.id, role_id=role_id))
    session.commit()
    session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(test_db_session: Session, sample_roles):
    """A single ADMIN user."""
    return _make_user(
        test_db_session,
        email="admin@test.com",
        nombre="Admin",
        apellido="Boss",
        role_ids=[1],  # ADMIN
    )


@pytest.fixture
def admin_headers(client: TestClient, admin_user):
    """Auth headers for admin_user."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "test_pass_123"},
    )
    assert resp.status_code == 200
    return {}


@pytest.fixture
def client_user(test_db_session: Session, sample_roles):
    """A CLIENT user (cannot access admin endpoints)."""
    return _make_user(
        test_db_session,
        email="client@test.com",
        nombre="Cliente",
        apellido="Normal",
        role_ids=[4],  # CLIENT
    )


@pytest.fixture
def client_headers(client: TestClient, client_user):
    """Auth headers for client_user."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "client@test.com", "password": "test_pass_123"},
    )
    assert resp.status_code == 200
    return {}


@pytest.fixture
def stock_user(test_db_session: Session, sample_roles):
    """A STOCK user for role filter tests."""
    return _make_user(
        test_db_session,
        email="stock@test.com",
        nombre="Stock",
        apellido="Manager",
        role_ids=[2],  # STOCK
    )


# ---------------------------------------------------------------------------
# 6.2 GET /admin/usuarios — sin filtros
# ---------------------------------------------------------------------------


def test_list_usuarios_sin_filtros_returns_200_with_pagination(
    client: TestClient,
    admin_user,
    admin_headers,
):
    """GET /admin/usuarios returns 200 with correct pagination structure."""
    resp = client.get("/api/v1/admin/usuarios", headers=admin_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "page_size" in body
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert isinstance(body["items"], list)
    assert body["total"] >= 1  # at least admin_user


def test_list_usuarios_response_item_has_expected_fields(
    client: TestClient,
    admin_user,
    admin_headers,
):
    """Each item in GET /admin/usuarios has all required fields."""
    resp = client.get("/api/v1/admin/usuarios", headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1

    item = items[0]
    for field in ("id", "email", "nombre", "apellido", "is_active", "roles"):
        assert field in item, f"Missing field: {field}"
    assert isinstance(item["roles"], list)
    # password_hash must NOT be exposed
    assert "password_hash" not in item
    assert "eliminado_en" not in item


# ---------------------------------------------------------------------------
# 6.3 GET /admin/usuarios?search=<term>
# ---------------------------------------------------------------------------


def test_list_usuarios_search_filtra_por_nombre(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """GET /admin/usuarios?search=juan returns only matching users."""
    # Create a user named "Juan" to match (nombre contains "juan")
    _make_user(test_db_session, "matchinguser@test.com", "Juan", "Perez", [4])
    # Create a user that should NOT match (neither nombre nor email contains "juan")
    _make_user(test_db_session, "pedro@test.com", "Pedro", "Garcia", [4])

    resp = client.get("/api/v1/admin/usuarios?search=juan", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    emails = [item["email"] for item in body["items"]]
    assert "matchinguser@test.com" in emails
    assert "pedro@test.com" not in emails


def test_list_usuarios_search_es_case_insensitive(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """search=JUAN should match 'juan' (case-insensitive ILIKE)."""
    _make_user(test_db_session, "juanmix@test.com", "juan", "Lopez", [4])

    resp = client.get("/api/v1/admin/usuarios?search=JUAN", headers=admin_headers)
    assert resp.status_code == 200
    emails = [item["email"] for item in resp.json()["items"]]
    assert "juanmix@test.com" in emails


def test_list_usuarios_search_por_email(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """search filters on email too."""
    _make_user(test_db_session, "findme@example.org", "NoMatch", "Nope", [4])

    resp = client.get("/api/v1/admin/usuarios?search=findme", headers=admin_headers)
    assert resp.status_code == 200
    emails = [item["email"] for item in resp.json()["items"]]
    assert "findme@example.org" in emails


# ---------------------------------------------------------------------------
# 6.4 GET /admin/usuarios?rol=STOCK
# ---------------------------------------------------------------------------


def test_list_usuarios_filtro_por_rol(
    client: TestClient,
    admin_user,
    stock_user,
    admin_headers,
):
    """GET /admin/usuarios?rol=STOCK returns only STOCK-role users."""
    resp = client.get("/api/v1/admin/usuarios?rol=STOCK", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    emails = [item["email"] for item in body["items"]]
    assert "stock@test.com" in emails
    assert "admin@test.com" not in emails


# ---------------------------------------------------------------------------
# 6.5 GET /admin/usuarios con rol CLIENT — espera 403
# ---------------------------------------------------------------------------


def test_list_usuarios_con_rol_client_retorna_403(
    client: TestClient,
    client_user,
    client_headers,
):
    """GET /admin/usuarios with CLIENT role returns 403."""
    resp = client.get("/api/v1/admin/usuarios", headers=client_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 6.6 PUT /admin/usuarios/{id} exitoso
# ---------------------------------------------------------------------------


def test_put_usuario_actualiza_datos_personales(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PUT /admin/usuarios/{id} updates nombre and apellido, returns 200."""
    target = _make_user(test_db_session, "target@test.com", "OldName", "OldApellido", [4])

    resp = client.put(
        f"/api/v1/admin/usuarios/{target.id}",
        json={"nombre": "NuevoNombre", "apellido": "NuevoApellido"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nombre"] == "NuevoNombre"
    assert body["apellido"] == "NuevoApellido"
    assert body["email"] == "target@test.com"  # email unchanged


def test_put_usuario_actualiza_solo_telefono(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PUT /admin/usuarios/{id} with only telefono returns 200 with updated telefono."""
    target = _make_user(test_db_session, "tel@test.com", "Carlos", "Lopez", [4])

    resp = client.put(
        f"/api/v1/admin/usuarios/{target.id}",
        json={"telefono": "+54 11 9999-0000"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["telefono"] == "+54 11 9999-0000"


# ---------------------------------------------------------------------------
# 6.7 PUT /admin/usuarios/{id} con id inexistente — espera 404
# ---------------------------------------------------------------------------


def test_put_usuario_id_inexistente_retorna_404(
    client: TestClient,
    admin_user,
    admin_headers,
):
    """PUT /admin/usuarios/99999 returns 404 when user does not exist."""
    resp = client.put(
        "/api/v1/admin/usuarios/99999",
        json={"nombre": "NombreValido"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6.8 PUT /admin/usuarios/{id} con campo `email` en body — espera 422
# ---------------------------------------------------------------------------


def test_put_usuario_con_email_en_body_retorna_422(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PUT /admin/usuarios/{id} with email in body returns 422 (extra='forbid')."""
    target = _make_user(test_db_session, "extrachk@test.com", "Foo", "Bar", [4])

    resp = client.put(
        f"/api/v1/admin/usuarios/{target.id}",
        json={"nombre": "X", "email": "hacker@evil.com"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_put_usuario_con_password_hash_en_body_retorna_422(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PUT /admin/usuarios/{id} with password_hash in body returns 422."""
    target = _make_user(test_db_session, "pwdhack@test.com", "Foo", "Bar", [4])

    resp = client.put(
        f"/api/v1/admin/usuarios/{target.id}",
        json={"password_hash": "leaked"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 6.9 PATCH /admin/usuarios/{id}/rol exitoso
# ---------------------------------------------------------------------------


def test_patch_rol_exitoso_cambia_roles_y_revoca_tokens(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PATCH /rol returns 200 with new roles, and refresh tokens are revoked."""
    from backend.features.auth.models import RefreshToken

    target = _make_user(test_db_session, "rolechange@test.com", "Role", "Change", [4])  # CLIENT
    _seed_refresh_tokens(test_db_session, target.id, count=2)

    resp = client.patch(
        f"/api/v1/admin/usuarios/{target.id}/rol",
        json={"roles": ["STOCK"]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["roles"] == ["STOCK"]

    # Verify tokens revoked
    test_db_session.expire_all()
    tokens = test_db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == target.id)
    ).scalars().all()
    assert len(tokens) == 2
    for t in tokens:
        assert t.revoked_at is not None, "SECURITY: refresh token not revoked after role change"


def test_patch_rol_puede_asignar_multiples_roles(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PATCH /rol with ["STOCK", "PEDIDOS"] assigns both roles."""
    target = _make_user(test_db_session, "multirole@test.com", "Multi", "Role", [4])

    resp = client.patch(
        f"/api/v1/admin/usuarios/{target.id}/rol",
        json={"roles": ["STOCK", "PEDIDOS"]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    roles = set(resp.json()["roles"])
    assert roles == {"STOCK", "PEDIDOS"}


# ---------------------------------------------------------------------------
# 6.10 PATCH /admin/usuarios/{id}/rol quitando último ADMIN — espera 409
# ---------------------------------------------------------------------------


def test_patch_rol_ultimo_admin_retorna_409(
    client: TestClient,
    admin_user,
    admin_headers,
):
    """PATCH /rol on the only ADMIN returns 409 (last admin guard)."""
    resp = client.patch(
        f"/api/v1/admin/usuarios/{admin_user.id}/rol",
        json={"roles": ["CLIENT"]},
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_patch_rol_segundo_admin_puede_degradar_primero(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """With two ADMINs, degrading one is allowed (last-admin guard does not block)."""
    # Create a second admin
    second_admin = _make_user(test_db_session, "admin2@test.com", "Admin2", "Two", [1])

    # Degrade the second admin to CLIENT — still 1 admin left
    resp = client.patch(
        f"/api/v1/admin/usuarios/{second_admin.id}/rol",
        json={"roles": ["CLIENT"]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["roles"] == ["CLIENT"]


# ---------------------------------------------------------------------------
# 6.11 PATCH /admin/usuarios/{id}/rol con código de rol inválido — espera 422
# ---------------------------------------------------------------------------


def test_patch_rol_codigo_invalido_retorna_422(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PATCH /rol with unknown role code returns 422."""
    target = _make_user(test_db_session, "badrole@test.com", "Bad", "Role", [4])

    resp = client.patch(
        f"/api/v1/admin/usuarios/{target.id}/rol",
        json={"roles": ["SUPERADMIN"]},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_patch_rol_lista_vacia_retorna_422(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PATCH /rol with empty roles list returns 422 (min_length=1 on the list)."""
    target = _make_user(test_db_session, "emptyrole@test.com", "Empty", "Role", [4])

    resp = client.patch(
        f"/api/v1/admin/usuarios/{target.id}/rol",
        json={"roles": []},
        headers=admin_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 6.12 PATCH /admin/usuarios/{id}/estado desactivar
# ---------------------------------------------------------------------------


def test_patch_estado_desactivar_retorna_200_y_revoca_tokens(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PATCH /estado with is_active=false deactivates user and revokes refresh tokens."""
    from backend.features.auth.models import RefreshToken

    target = _make_user(test_db_session, "deactivate@test.com", "De", "Activate", [4])
    _seed_refresh_tokens(test_db_session, target.id, count=3)

    resp = client.patch(
        f"/api/v1/admin/usuarios/{target.id}/estado",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_active"] is False

    # Verify tokens revoked
    test_db_session.expire_all()
    tokens = test_db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == target.id)
    ).scalars().all()
    assert len(tokens) == 3
    for t in tokens:
        assert t.revoked_at is not None, "SECURITY: token not revoked after deactivation"


# ---------------------------------------------------------------------------
# 6.13 PATCH /admin/usuarios/{id}/estado activar usuario desactivado
# ---------------------------------------------------------------------------


def test_patch_estado_activar_usuario_desactivado(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PATCH /estado with is_active=true reactivates a deactivated user."""
    target = _make_user(
        test_db_session,
        "reactivate@test.com",
        "Re",
        "Activate",
        [4],
        is_active=False,  # starts deactivated
    )

    resp = client.patch(
        f"/api/v1/admin/usuarios/{target.id}/estado",
        json={"is_active": True},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


def test_patch_estado_activar_no_revoca_tokens(
    client: TestClient,
    admin_user,
    test_db_session: Session,
    sample_roles,
    admin_headers,
):
    """PATCH /estado with is_active=true does NOT revoke existing tokens."""
    from backend.features.auth.models import RefreshToken

    target = _make_user(test_db_session, "reactivate2@test.com", "Re2", "Activate", [4], is_active=False)
    _seed_refresh_tokens(test_db_session, target.id, count=1)

    resp = client.patch(
        f"/api/v1/admin/usuarios/{target.id}/estado",
        json={"is_active": True},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    test_db_session.expire_all()
    tokens = test_db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == target.id)
    ).scalars().all()
    # Token should NOT have been revoked by activation
    assert all(t.revoked_at is None for t in tokens), (
        "Activation should not revoke existing tokens"
    )


def test_patch_estado_id_inexistente_retorna_404(
    client: TestClient,
    admin_user,
    admin_headers,
):
    """PATCH /estado on non-existent user returns 404."""
    resp = client.patch(
        "/api/v1/admin/usuarios/99999/estado",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_patch_rol_id_inexistente_retorna_404(
    client: TestClient,
    admin_user,
    admin_headers,
):
    """PATCH /rol on non-existent user returns 404."""
    resp = client.patch(
        "/api/v1/admin/usuarios/99999/rol",
        json={"roles": ["CLIENT"]},
        headers=admin_headers,
    )
    assert resp.status_code == 404
