"""
Regression tests for DetachedInstanceError against PostgreSQL (pg_only).

These three tests verify that ORM entities returned by services survive
the UoW commit + session close and can be serialized by Pydantic without
raising sqlalchemy.orm.exc.DetachedInstanceError.

WHY pg_only:
- The bug only manifests against a real Postgres engine because the test
  conftest monkeypatches get_session_factory() to use a SQLite session
  that ALREADY had expire_on_commit=False. Against Postgres (real
  DATABASE_URL), the production sessionmaker is used, which historically
  had the default expire_on_commit=True — the source of the bug.
- Without a live Postgres DATABASE_URL these tests are skipped gracefully.

EXPECTED STATES:
- BEFORE fix (expire_on_commit=True in database.py): all three return HTTP 500
  whose root cause is DetachedInstanceError (visible in server logs).
- AFTER fix (expire_on_commit=False in database.py): all three return 2xx with
  well-formed response bodies.

See: openspec/changes/fix-detached-instance-error-postgres/design.md — D1, D5, D6.

NOTE ON LOCAL EXECUTION:
The conftest pg_only skip logic checks for a postgres:// DATABASE_URL. In
SQLite-only CI or local dev without a Postgres container, these tests are
automatically SKIPPED. The skip is expected and acceptable — the real gate
is a manual TestSprite re-run with the backend running against Postgres.
See tasks.md Section 5 for the manual validation steps.
"""
from __future__ import annotations

import os

import pytest
import requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("TEST_API_BASE_URL", "http://localhost:8000")

_AUTH_EMAIL = "regresion_pg@example.com"
_AUTH_PASSWORD = "secure_regression_pass_123"


def _register_and_login() -> str:
    """Register a fresh user and return a Bearer token.

    Uses the real HTTP API (not the TestClient) because these tests require
    the backend to run against Postgres. Returns the access_token string.
    """
    # Register
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "email": _AUTH_EMAIL,
            "password": _AUTH_PASSWORD,
            "nombre": "Regresion",
            "apellido": "PG",
        },
        timeout=10,
    )
    # 201 on first run, 409 on reruns — both are fine, just need to login.
    assert resp.status_code in (201, 409), (
        f"Unexpected register status: {resp.status_code} — {resp.text}"
    )

    # Login
    login = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": _AUTH_EMAIL, "password": _AUTH_PASSWORD},
        timeout=10,
    )
    assert login.status_code == 200, (
        f"Login failed: {login.status_code} — {login.text}"
    )
    return login.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# pg_only regression tests
# ---------------------------------------------------------------------------


@pytest.mark.pg_only
def test_patch_users_me_returns_200_against_postgres():
    """PATCH /api/v1/usuarios/me returns 200 with a valid ProfileResponse.

    Regression for DetachedInstanceError on Usuario.roles (M2N relationship
    eager-loaded by selectinload in find_by_id_with_roles). With the default
    expire_on_commit=True, after UoW commit the Usuario instance is expired
    and session.close() detaches it — Pydantic's model_validate raises
    DetachedInstanceError producing HTTP 500.

    After fix (expire_on_commit=False): the ORM instance retains its attribute
    cache post-commit, Pydantic can read email, nombre, apellido, telefono and
    roles without hitting the closed session.
    """
    token = _register_and_login()
    headers = _auth_headers(token)

    response = requests.patch(
        f"{BASE_URL}/api/v1/usuarios/me",
        json={"telefono": "+54 11 1234-5678"},
        headers=headers,
        timeout=10,
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "email" in body, f"Missing 'email' in body: {body}"
    assert isinstance(body.get("roles"), list), f"'roles' must be a list: {body}"
    assert len(body["roles"]) > 0, f"'roles' must not be empty: {body}"
    assert body.get("telefono") == "+54 11 1234-5678", (
        f"Telefono not updated: {body}"
    )


@pytest.mark.pg_only
def test_post_direcciones_returns_201_against_postgres():
    """POST /api/v1/direcciones/ returns 201 with a valid DireccionRead.

    Regression for DetachedInstanceError on DireccionEntrega (scalar-only
    response schema). With the default expire_on_commit=True, the entity
    returned by crear_direccion() is expired post-commit and detached on
    session close — Pydantic cannot read calle, numero, ciudad, creado_en,
    etc., producing HTTP 500.

    After fix: all scalar attributes survive commit and serialize cleanly.
    """
    token = _register_and_login()
    headers = _auth_headers(token)

    response = requests.post(
        f"{BASE_URL}/api/v1/direcciones/",
        json={
            "calle": "Av Regresión PG",
            "numero": "500",
            "ciudad": "Buenos Aires",
            "codigo_postal": "1000",
        },
        headers=headers,
        timeout=10,
    )

    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("id") is not None, f"Missing 'id': {body}"
    assert body.get("calle") == "Av Regresión PG", f"calle mismatch: {body}"
    assert body.get("numero") == "500", f"numero mismatch: {body}"
    assert body.get("ciudad") == "Buenos Aires", f"ciudad mismatch: {body}"
    assert body.get("creado_en") is not None, f"creado_en is None: {body}"
    assert body.get("actualizado_en") is not None, f"actualizado_en is None: {body}"


@pytest.mark.pg_only
def test_post_pedidos_returns_201_against_postgres():
    """POST /api/v1/pedidos/ returns 201 with a valid PedidoRead.

    Regression for DetachedInstanceError on Pedido scalars (including
    creado_en server-default read via session.refresh(pedido, attribute_names=
    ["creado_en"]) pre-commit). With the default expire_on_commit=True, the
    refresh result is wiped by the subsequent commit expiry — the Pedido
    instance is then detached on session close.

    After fix (expire_on_commit=False): the pre-commit refresh populates
    creado_en in the ORM cache; commit does NOT expire it; Pydantic reads it
    cleanly. Note: session.refresh() calls in orders/service.py are preserved
    as explicit server-default reads (D3 — their role changes from
    anti-DetachedInstanceError defense to explicit server-default population).

    Pre-condition: backend must have at minimum one available product with
    stock > 0 and the catalog states seeded (PENDIENTE, MERCADOPAGO).
    If the backend is freshly seeded, this test passes. If the DB is empty,
    the endpoint will return 400/404, not 500.
    """
    token = _register_and_login()
    headers = _auth_headers(token)

    # Create a delivery address first (pre-condition for orders with direccion_id)
    addr_resp = requests.post(
        f"{BASE_URL}/api/v1/direcciones/",
        json={
            "calle": "Av Pedido Regresión",
            "numero": "1",
            "ciudad": "Rosario",
            "codigo_postal": "2000",
        },
        headers=headers,
        timeout=10,
    )
    assert addr_resp.status_code == 201, (
        f"Pre-condition failed (address creation): {addr_resp.status_code} — {addr_resp.text}"
    )
    direccion_id = addr_resp.json()["id"]

    # Get first available product
    products_resp = requests.get(
        f"{BASE_URL}/api/v1/productos/",
        timeout=10,
    )
    assert products_resp.status_code == 200, (
        f"Pre-condition failed (product list): {products_resp.status_code} — {products_resp.text}"
    )
    products = products_resp.json()
    available = [p for p in products if p.get("disponible") and p.get("stock_cantidad", 0) > 0]
    assert len(available) > 0, (
        "Pre-condition failed: no available product with stock > 0. "
        "Seed the DB before running pg_only tests."
    )
    producto_id = available[0]["id"]

    response = requests.post(
        f"{BASE_URL}/api/v1/pedidos/",
        json={
            "items": [{"producto_id": producto_id, "cantidad": 1}],
            "forma_pago_codigo": "MERCADOPAGO",
            "direccion_id": direccion_id,
        },
        headers=headers,
        timeout=10,
    )

    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert body.get("id") is not None, f"Missing 'id': {body}"
    assert body.get("estado_codigo") == "PENDIENTE", f"estado_codigo mismatch: {body}"
    assert body.get("total") is not None and float(body["total"]) > 0, (
        f"total must be > 0: {body}"
    )
    assert body.get("creado_en") is not None, f"creado_en is None: {body}"
