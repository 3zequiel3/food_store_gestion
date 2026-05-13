"""
Integration tests for GET /api/v1/formas-pago endpoint.

Covers:
  - Authenticated user gets enabled payment methods
  - Disabled methods are excluded
  - Unauthenticated request returns 401

Base URL: /api/v1/formas-pago
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


BASE_URL = "/api/v1/formas-pago"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def sample_formas_pago_mixed(test_db_session: Session):
    """
    Seed payment methods with mixed habilitada status.
    
    - MERCADOPAGO: habilitada=True
    - EFECTIVO: habilitada=False
    - TRANSFERENCIA: habilitada=True
    """
    from features.catalog.models import FormaPago

    formas = [
        FormaPago(codigo="MERCADOPAGO", descripcion="MercadoPago", habilitada=True),
        FormaPago(codigo="EFECTIVO", descripcion="Efectivo", habilitada=False),
        FormaPago(codigo="TRANSFERENCIA", descripcion="Transferencia bancaria", habilitada=True),
    ]
    for forma in formas:
        test_db_session.add(forma)
    test_db_session.commit()
    return formas


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_formas_pago_returns_enabled_methods(
    client: TestClient,
    auth_headers: dict,
    sample_formas_pago_mixed,
):
    """GET /formas-pago returns only habilitada=True methods, ordered by id."""
    resp = client.get(BASE_URL, headers=auth_headers)
    assert resp.status_code == 200
    
    body = resp.json()
    assert len(body) == 2  # Only MERCADOPAGO and TRANSFERENCIA
    
    # Verify ordering by id (ascending)
    codigos = [f["codigo"] for f in body]
    assert codigos == ["MERCADOPAGO", "TRANSFERENCIA"]
    
    # Verify response structure
    for forma in body:
        assert "codigo" in forma
        assert "descripcion" in forma
        assert "habilitada" in forma
        assert forma["habilitada"] is True


def test_get_formas_pago_excludes_disabled(
    client: TestClient,
    auth_headers: dict,
    sample_formas_pago_mixed,
):
    """GET /formas-pago excludes methods with habilitada=False."""
    resp = client.get(BASE_URL, headers=auth_headers)
    assert resp.status_code == 200
    
    body = resp.json()
    codigos = {f["codigo"] for f in body}
    
    assert "MERCADOPAGO" in codigos
    assert "TRANSFERENCIA" in codigos
    assert "EFECTIVO" not in codigos  # Disabled, should not appear


def test_get_formas_pago_returns_401_unauthenticated(
    client: TestClient,
    sample_formas_pago_mixed,
):
    """GET /formas-pago without token returns 401."""
    resp = client.get(BASE_URL)
    assert resp.status_code == 401


def test_get_formas_pago_returns_401_invalid_token(
    client: TestClient,
    sample_formas_pago_mixed,
):
    """GET /formas-pago with invalid token returns 401."""
    headers = {"Authorization": "Bearer invalid_token"}
    resp = client.get(BASE_URL, headers=headers)
    assert resp.status_code == 401


def test_get_formas_pago_empty_when_all_disabled(
    client: TestClient,
    auth_headers: dict,
    test_db_session: Session,
):
    """GET /formas-pago returns empty list when all methods are disabled."""
    from features.catalog.models import FormaPago

    # Add only disabled payment methods
    formas = [
        FormaPago(codigo="DISABLED1", descripcion="Disabled 1", habilitada=False),
        FormaPago(codigo="DISABLED2", descripcion="Disabled 2", habilitada=False),
    ]
    for forma in formas:
        test_db_session.add(forma)
    test_db_session.commit()

    resp = client.get(BASE_URL, headers=auth_headers)
    assert resp.status_code == 200
    
    body = resp.json()
    assert len(body) == 0
    assert body == []
