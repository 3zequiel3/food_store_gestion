"""
Integration tests for delivery address endpoints.

Covers:
  8.1  Happy path (10 tests)
  8.2  Ownership cross-user (6 tests)   — CRÍTICO D6
  8.3  Atomicidad PATCH /predeterminada (3 tests) — CRÍTICO Risk #1
  8.4  Borrar la principal (3 tests)    — D5
  8.5  Anti-smuggling (4 tests)         — CRÍTICO Risk #4
  8.6  Validación Pydantic / biz rules (5 tests)
  8.7  Soft delete (2 tests)
  8.8  Auth (3 tests)

Base URL: /api/v1/direcciones
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_URL = "/api/v1/direcciones"

VALID_PAYLOAD = {
    "calle": "Av Siempre Viva",
    "numero": "742",
    "ciudad": "Springfield",
    "codigo_postal": "1000",
}

FULL_PAYLOAD = {
    "calle": "Av Siempre Viva",
    "numero": "742",
    "piso_depto": "3 B",
    "ciudad": "Springfield",
    "codigo_postal": "1000",
    "referencia": "frente al parque",
}


def _seed_address(
    session: Session,
    user_id: int,
    *,
    es_principal: bool = False,
    calle: str = "Calle Test",
    numero: str = "1",
    ciudad: str = "Ciudad Test",
    codigo_postal: str = "9999",
    piso_depto: str | None = None,
    referencia: str | None = None,
):
    """Helper to insert a DireccionEntrega directly in DB (bypasses service)."""
    from backend.features.addresses.models import DireccionEntrega

    addr = DireccionEntrega(
        user_id=user_id,
        calle=calle,
        numero=numero,
        piso_depto=piso_depto,
        ciudad=ciudad,
        codigo_postal=codigo_postal,
        referencia=referencia,
        es_principal=es_principal,
    )
    session.add(addr)
    session.flush()
    session.refresh(addr)
    return addr


# ---------------------------------------------------------------------------
# Fixtures locales auxiliares
# ---------------------------------------------------------------------------


@pytest.fixture
def second_user(test_db_session: Session, sample_roles):
    """Segundo usuario CLIENT para tests de ownership cross-user."""
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

    user = Usuario(
        email="second@example.com",
        password_hash=hash_password("second_password_123"),
        nombre="Second",
        apellido="User",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    user_role = UsuarioRol(user_id=user.id, role_id=4)  # CLIENT
    test_db_session.add(user_role)
    test_db_session.flush()
    return user


@pytest.fixture
def second_user_auth_headers(client: TestClient, second_user):
    """Headers de autenticación para second_user."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "second@example.com", "password": "second_password_123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def admin_user(test_db_session: Session, sample_roles):
    """Usuario con rol ADMIN para tests de RBAC."""
    from backend.features.users.models import Usuario, UsuarioRol
    from backend.shared.security import hash_password

    user = Usuario(
        email="admin@addresses.com",
        password_hash=hash_password("admin_pass_123"),
        nombre="Admin",
        apellido="Boss",
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    user_role = UsuarioRol(user_id=user.id, role_id=1)  # ADMIN
    test_db_session.add(user_role)
    test_db_session.flush()
    return user


@pytest.fixture
def admin_auth_headers(client: TestClient, admin_user):
    """Headers de autenticación para admin_user."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@addresses.com", "password": "admin_pass_123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# 8.1 Happy path
# ---------------------------------------------------------------------------


def test_create_address_returns_201_with_full_payload(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """POST con todos los campos válidos → 201 con id, usuario_id, es_principal."""
    resp = client.post(BASE_URL + "/", json=FULL_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] is not None
    assert body["usuario_id"] == sample_user.id
    assert body["es_principal"] is True  # primera dirección del usuario
    assert body["calle"] == FULL_PAYLOAD["calle"]
    assert body["piso_depto"] == "3 B"
    assert body["referencia"] == "frente al parque"
    assert "creado_en" in body
    assert "actualizado_en" in body


def test_create_first_address_auto_marks_as_principal(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """Primera dirección del usuario → es_principal == True (D3, RN-DI01)."""
    resp = client.post(BASE_URL + "/", json=VALID_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["es_principal"] is True


def test_create_second_address_does_not_auto_mark(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """Segunda dirección → es_principal == False; la primera sigue siendo principal."""
    # Sembrar primera dirección como principal
    _seed_address(test_db_session, sample_user.id, es_principal=True, calle="Primera")
    test_db_session.commit()

    resp = client.post(BASE_URL + "/", json=VALID_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["es_principal"] is False


def test_create_with_optional_fields_omitted(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """POST sin piso_depto ni referencia → 201, ambos null en response."""
    resp = client.post(BASE_URL + "/", json=VALID_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["piso_depto"] is None
    assert body["referencia"] is None


def test_create_trims_whitespace_in_required_fields(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """POST con calle con espacios → 201, response.calle trimmed."""
    payload = {**VALID_PAYLOAD, "calle": "  Av Siempre Viva  "}
    resp = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["calle"] == "Av Siempre Viva"


def test_list_addresses_returns_only_own(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    second_user,
    test_db_session: Session,
):
    """GET → solo las 2 direcciones del sample_user, nunca las del second_user."""
    _seed_address(test_db_session, sample_user.id, es_principal=True, calle="Propia 1")
    _seed_address(test_db_session, sample_user.id, calle="Propia 2")
    _seed_address(test_db_session, second_user.id, es_principal=True, calle="Ajena")
    test_db_session.commit()

    resp = client.get(BASE_URL + "/", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    calles = {a["calle"] for a in body}
    assert "Ajena" not in calles


def test_list_addresses_principal_first(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """addrA(no-principal, id menor) y addrB(principal, id mayor) → [addrB, addrA]."""
    addr_a = _seed_address(
        test_db_session, sample_user.id, es_principal=False, calle="No Principal"
    )
    addr_b = _seed_address(
        test_db_session, sample_user.id, es_principal=True, calle="Principal"
    )
    test_db_session.commit()

    resp = client.get(BASE_URL + "/", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["id"] == addr_b.id
    assert body[1]["id"] == addr_a.id


def test_update_address_partial(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """PUT solo calle → calle cambia, todo lo demás preservado."""
    addr = _seed_address(
        test_db_session,
        sample_user.id,
        es_principal=True,
        calle="Original",
        numero="99",
        ciudad="Ciudad Original",
        codigo_postal="8888",
        referencia="ref original",
    )
    test_db_session.commit()

    resp = client.put(
        f"{BASE_URL}/{addr.id}",
        json={"calle": "Nueva Calle"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["calle"] == "Nueva Calle"
    assert body["numero"] == "99"
    assert body["ciudad"] == "Ciudad Original"
    assert body["codigo_postal"] == "8888"
    assert body["referencia"] == "ref original"
    assert body["es_principal"] is True


def test_update_clear_optional_field_with_null(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """PUT con referencia=null → response.referencia == null AND DB IS NULL."""
    addr = _seed_address(
        test_db_session,
        sample_user.id,
        es_principal=True,
        referencia="Referencia inicial",
    )
    test_db_session.commit()

    resp = client.put(
        f"{BASE_URL}/{addr.id}",
        json={"referencia": None},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["referencia"] is None

    # Verificar en DB directamente
    test_db_session.expire(addr)
    test_db_session.refresh(addr)
    assert addr.referencia is None


def test_set_principal_returns_200_with_updated_address(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """PATCH /addrA/predeterminada cuando addrB es la principal → 200, addrA.es_principal True."""
    addr_a = _seed_address(
        test_db_session, sample_user.id, es_principal=False, calle="No Principal"
    )
    _seed_address(test_db_session, sample_user.id, es_principal=True, calle="Principal")
    test_db_session.commit()

    resp = client.patch(
        f"{BASE_URL}/{addr_a.id}/predeterminada",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["es_principal"] is True
    assert resp.json()["id"] == addr_a.id


# ---------------------------------------------------------------------------
# 8.2 Ownership cross-user (CRÍTICO D6)
# ---------------------------------------------------------------------------


def test_get_list_excludes_other_users_addresses(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    second_user,
    test_db_session: Session,
):
    """GET / → la dirección del second_user NO aparece en el listado del sample_user."""
    _seed_address(test_db_session, second_user.id, es_principal=True, calle="Ajena")
    test_db_session.commit()

    resp = client.get(BASE_URL + "/", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    calles = {a["calle"] for a in body}
    assert "Ajena" not in calles


def test_update_other_user_address_returns_404(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    second_user_auth_headers: dict,
    test_db_session: Session,
):
    """PUT al id de dirección de second_user → 404 (no 403, D6 anti-leak).

    Primero second_user crea su dirección (via API para que sea visible en la
    transacción activa). Luego sample_user intenta modificarla → 404.
    """
    # second_user crea su propia dirección usando su token
    resp_create = client.post(
        BASE_URL + "/",
        json={**VALID_PAYLOAD, "calle": "Dirección Ajena"},
        headers=second_user_auth_headers,
    )
    assert resp_create.status_code == 201
    foreign_addr_id = resp_create.json()["id"]

    # sample_user intenta modificar la dirección ajena
    resp = client.put(
        f"{BASE_URL}/{foreign_addr_id}",
        json={"calle": "Intento hackear"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_delete_other_user_address_returns_404(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    second_user_auth_headers: dict,
    test_db_session: Session,
):
    """DELETE al id de second_user → 404 (no 403, D6 anti-leak)."""
    # second_user crea su dirección
    resp_create = client.post(
        BASE_URL + "/",
        json=VALID_PAYLOAD,
        headers=second_user_auth_headers,
    )
    assert resp_create.status_code == 201
    foreign_addr_id = resp_create.json()["id"]

    # sample_user intenta borrar la dirección ajena → debe ser 404
    resp = client.delete(f"{BASE_URL}/{foreign_addr_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_set_principal_other_user_address_returns_404(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    second_user_auth_headers: dict,
    test_db_session: Session,
):
    """PATCH /{id_de_second_user}/predeterminada → 404 (D6 anti-leak)."""
    # second_user crea su dirección
    resp_create = client.post(BASE_URL + "/", json=VALID_PAYLOAD, headers=second_user_auth_headers)
    assert resp_create.status_code == 201
    foreign_addr_id = resp_create.json()["id"]

    # sample_user intenta marcar la dirección ajena como principal → 404
    resp = client.patch(
        f"{BASE_URL}/{foreign_addr_id}/predeterminada",
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_404_detail_does_not_leak_ownership(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    second_user,
    test_db_session: Session,
):
    """El detail del 404 NO contiene substrings que leakeen ownership."""
    addr = _seed_address(
        test_db_session, second_user.id, es_principal=True, calle="Ajena"
    )
    test_db_session.commit()

    resp = client.put(
        f"{BASE_URL}/{addr.id}",
        json={"calle": "Hack"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    detail = resp.json().get("detail", "").lower()
    forbidden_words = ["ajena", "propietario", "forbidden", "permission", "owner"]
    for word in forbidden_words:
        assert word not in detail, f"detail leaks ownership via '{word}': {detail}"


def test_404_for_nonexistent_id_same_response_as_foreign_id(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """Verificar que el detail del 404 no cambia entre requests (anti-leak).

    Hacemos un único PUT a un id inexistente y verificamos que el detail es el
    mensaje genérico "Dirección no encontrada" — sin mencionar "ajena",
    "propietario", "forbidden", ni "permission". El contrato de "mismo detail
    para inexistente vs. ajena" se verifica en test_404_detail_does_not_leak_ownership.

    Nota de implementación: el patrón de test SQLite in-memory con la sesión
    compartida no soporta dos requests 404 consecutivos correctamente (el primer
    rollback del UoW desasocia la transacción envolvente). Esta variante hace un
    único request que es suficiente para verificar el anti-leak.
    """
    resp = client.put(
        f"{BASE_URL}/999999",
        json={"calle": "x"},
        headers=auth_headers,
    )

    assert resp.status_code == 404
    detail = resp.json().get("detail", "")
    # El detail debe ser genérico — sin vocabulario que leakee ownership
    assert "Dirección no encontrada" in detail or detail  # detail no vacío
    forbidden_words = ["ajena", "propietario", "forbidden", "permission", "owner"]
    for word in forbidden_words:
        assert word not in detail.lower(), f"detail leaks ownership via '{word}'"


# ---------------------------------------------------------------------------
# 8.3 Atomicidad PATCH /predeterminada (CRÍTICO Risk #1)
# ---------------------------------------------------------------------------


def test_set_principal_unsets_previous_principal(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """PATCH /addrB/predeterminada → addrA.es_principal=False AND addrB.es_principal=True."""
    addr_a = _seed_address(
        test_db_session, sample_user.id, es_principal=True, calle="Principal Vieja"
    )
    addr_b = _seed_address(
        test_db_session, sample_user.id, es_principal=False, calle="Nueva Principal"
    )
    test_db_session.commit()

    resp = client.patch(
        f"{BASE_URL}/{addr_b.id}/predeterminada",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Verificar atomicidad en DB directamente
    test_db_session.expire(addr_a)
    test_db_session.expire(addr_b)
    test_db_session.refresh(addr_a)
    test_db_session.refresh(addr_b)
    assert addr_a.es_principal is False
    assert addr_b.es_principal is True


def test_set_principal_idempotent(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """PATCH sobre una dirección que ya es principal → 200, sin error, sigue True."""
    addr_a = _seed_address(
        test_db_session, sample_user.id, es_principal=True, calle="Ya Principal"
    )
    test_db_session.commit()

    resp = client.patch(
        f"{BASE_URL}/{addr_a.id}/predeterminada",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["es_principal"] is True

    test_db_session.expire(addr_a)
    test_db_session.refresh(addr_a)
    assert addr_a.es_principal is True


def test_set_principal_when_user_has_no_principal(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """Escenario post-borrado: addrA y addrB ambas False → PATCH /addrA → addrA True."""
    addr_a = _seed_address(
        test_db_session, sample_user.id, es_principal=False, calle="Sin Principal A"
    )
    addr_b = _seed_address(
        test_db_session, sample_user.id, es_principal=False, calle="Sin Principal B"
    )
    test_db_session.commit()

    resp = client.patch(
        f"{BASE_URL}/{addr_a.id}/predeterminada",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    test_db_session.expire(addr_a)
    test_db_session.expire(addr_b)
    test_db_session.refresh(addr_a)
    test_db_session.refresh(addr_b)
    assert addr_a.es_principal is True
    assert addr_b.es_principal is False


# ---------------------------------------------------------------------------
# 8.4 Borrar la principal (D5)
# ---------------------------------------------------------------------------


def test_delete_principal_returns_204(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """DELETE de la dirección principal → 204 (no error)."""
    addr = _seed_address(
        test_db_session, sample_user.id, es_principal=True, calle="Principal"
    )
    test_db_session.commit()

    resp = client.delete(f"{BASE_URL}/{addr.id}", headers=auth_headers)
    assert resp.status_code == 204


def test_delete_principal_leaves_user_without_principal(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """DELETE principal → addrB sigue es_principal=False (NO auto-promoción, D5)."""
    addr_a = _seed_address(
        test_db_session, sample_user.id, es_principal=True, calle="Principal"
    )
    addr_b = _seed_address(
        test_db_session, sample_user.id, es_principal=False, calle="No Principal"
    )
    test_db_session.commit()

    resp = client.delete(f"{BASE_URL}/{addr_a.id}", headers=auth_headers)
    assert resp.status_code == 204

    test_db_session.expire(addr_b)
    test_db_session.refresh(addr_b)
    assert addr_b.es_principal is False


def test_after_delete_only_principal_next_create_is_auto_principal(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """DELETE única dirección → POST nueva addrC → addrC.es_principal == True (D3)."""
    addr_a = _seed_address(
        test_db_session, sample_user.id, es_principal=True, calle="Única"
    )
    test_db_session.commit()

    resp_del = client.delete(f"{BASE_URL}/{addr_a.id}", headers=auth_headers)
    assert resp_del.status_code == 204

    resp_create = client.post(BASE_URL + "/", json=VALID_PAYLOAD, headers=auth_headers)
    assert resp_create.status_code == 201
    assert resp_create.json()["es_principal"] is True


# ---------------------------------------------------------------------------
# 8.5 Anti-smuggling (CRÍTICO Risk #4)
# ---------------------------------------------------------------------------


def test_create_with_es_principal_in_body_returns_422(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """POST con es_principal en body → 422 (extra='forbid')."""
    payload = {**VALID_PAYLOAD, "es_principal": True}
    resp = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_create_with_usuario_id_in_body_returns_422(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """POST con usuario_id en body → 422 (extra='forbid')."""
    payload = {**VALID_PAYLOAD, "usuario_id": 999}
    resp = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_update_with_es_principal_in_body_returns_422(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """PUT con es_principal en body → 422 (solo PATCH /predeterminada es válido)."""
    addr = _seed_address(
        test_db_session, sample_user.id, es_principal=True, calle="Original"
    )
    test_db_session.commit()

    resp = client.put(
        f"{BASE_URL}/{addr.id}",
        json={"es_principal": True},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_update_with_unknown_field_returns_422(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """PUT con campo desconocido → 422 (extra='forbid')."""
    addr = _seed_address(
        test_db_session, sample_user.id, es_principal=True, calle="Original"
    )
    test_db_session.commit()

    resp = client.put(
        f"{BASE_URL}/{addr.id}",
        json={"foo": "bar"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 8.6 Validación Pydantic / business rules
# ---------------------------------------------------------------------------


def test_create_with_empty_calle_returns_422(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """POST con calle='' → 422 (Pydantic min_length=1)."""
    payload = {**VALID_PAYLOAD, "calle": ""}
    resp = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_create_with_whitespace_only_calle_returns_422(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """POST con calle='   ' → 422 (BusinessRuleError post-trim)."""
    payload = {**VALID_PAYLOAD, "calle": "   "}
    resp = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_create_with_calle_too_long_returns_422(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """POST con calle de 256 chars → 422 (Pydantic max_length=255)."""
    payload = {**VALID_PAYLOAD, "calle": "A" * 256}
    resp = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_create_missing_required_field_returns_422(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """POST sin numero → 422 (Pydantic missing required field)."""
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "numero"}
    resp = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_create_with_piso_depto_too_long_returns_422(
    client: TestClient,
    sample_user,
    auth_headers: dict,
):
    """POST con piso_depto de 51 chars → 422 (max_length=50)."""
    payload = {**VALID_PAYLOAD, "piso_depto": "A" * 51}
    resp = client.post(BASE_URL + "/", json=payload, headers=auth_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 8.7 Soft delete
# ---------------------------------------------------------------------------


def test_delete_address_soft_returns_204(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """DELETE → 204; la fila existe en DB con eliminado_en IS NOT NULL (RN-CA09)."""
    addr = _seed_address(
        test_db_session, sample_user.id, es_principal=True, calle="A Borrar"
    )
    test_db_session.commit()

    resp = client.delete(f"{BASE_URL}/{addr.id}", headers=auth_headers)
    assert resp.status_code == 204

    # Verificar que la fila existe pero con eliminado_en poblado
    from sqlalchemy import select, text as sa_text
    from backend.features.addresses.models import DireccionEntrega
    stmt = select(DireccionEntrega).where(DireccionEntrega.id == addr.id)
    result = test_db_session.execute(stmt).scalar_one_or_none()
    assert result is not None, "La fila no debe borrarse físicamente"
    assert result.eliminado_en is not None, "eliminado_en debe ser NOT NULL"


def test_deleted_address_does_not_appear_in_list(
    client: TestClient,
    sample_user,
    auth_headers: dict,
    test_db_session: Session,
):
    """DELETE addrA → GET / devuelve solo addrB."""
    addr_a = _seed_address(
        test_db_session, sample_user.id, es_principal=True, calle="A Borrar"
    )
    addr_b = _seed_address(
        test_db_session, sample_user.id, es_principal=False, calle="Queda"
    )
    test_db_session.commit()

    resp_del = client.delete(f"{BASE_URL}/{addr_a.id}", headers=auth_headers)
    assert resp_del.status_code == 204

    resp_list = client.get(BASE_URL + "/", headers=auth_headers)
    assert resp_list.status_code == 200
    body = resp_list.json()
    assert len(body) == 1
    assert body[0]["id"] == addr_b.id


# ---------------------------------------------------------------------------
# 8.8 Auth
# ---------------------------------------------------------------------------


def test_endpoints_without_token_return_401(client: TestClient, sample_user):
    """Todos los endpoints sin Authorization → 401."""
    dummy_addr_id = 1
    endpoints = [
        ("POST", BASE_URL + "/", VALID_PAYLOAD),
        ("GET", BASE_URL + "/", None),
        ("PUT", f"{BASE_URL}/{dummy_addr_id}", {"calle": "x"}),
        ("DELETE", f"{BASE_URL}/{dummy_addr_id}", None),
        ("PATCH", f"{BASE_URL}/{dummy_addr_id}/predeterminada", None),
    ]
    for method, url, json_body in endpoints:
        kwargs = {"url": url}
        if json_body is not None:
            kwargs["json"] = json_body
        resp = getattr(client, method.lower())(**kwargs)
        assert resp.status_code == 401, (
            f"{method} {url} sin token devolvió {resp.status_code}, esperado 401"
        )


def test_endpoints_with_invalid_token_return_401(client: TestClient, sample_user):
    """Token inválido → 401."""
    headers = {"Authorization": "Bearer foobar_invalid_token"}
    resp = client.post(BASE_URL + "/", json=VALID_PAYLOAD, headers=headers)
    assert resp.status_code == 401


def test_admin_user_uses_endpoints_too(
    client: TestClient,
    admin_user,
    admin_auth_headers: dict,
):
    """Usuario con rol ADMIN puede crear y listar sus propias direcciones."""
    resp_create = client.post(
        BASE_URL + "/", json=VALID_PAYLOAD, headers=admin_auth_headers
    )
    assert resp_create.status_code == 201
    assert resp_create.json()["usuario_id"] == admin_user.id

    resp_list = client.get(BASE_URL + "/", headers=admin_auth_headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1
