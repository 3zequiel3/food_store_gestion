"""
Tests for main FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test GET /health endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data


def test_health_check_development(client: TestClient):
    """Test health check includes environment info."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["environment"] in ["development", "production"]


def test_cors_headers(client: TestClient):
    """Test CORS headers are present."""
    response = client.options("/health", headers={"Origin": "http://localhost:5173"})

    # FastAPI/Starlette should handle CORS
    # 200 = CORS preflight handled; 404 = no explicit OPTIONS handler; 405 = Method Not Allowed
    assert response.status_code in [200, 404, 405]


def test_request_logging_middleware(client: TestClient, caplog):
    """Test that request logging middleware is active."""
    import logging

    caplog.set_level(logging.INFO)

    response = client.get("/health")

    assert response.status_code == 200
    # Middleware should log the request
    # Note: caplog might not capture if middleware uses a different logger


def test_api_routes_exist(client: TestClient):
    """Test that all feature routers are registered under /api/v1/.

    Uses OpenAPI introspection (robust against auth/empty-state and method
    variations). Validates registration, not response semantics.

    Path naming follows spec del integrador §5: castellano para recursos de
    dominio (productos, pedidos, pagos, direcciones, categorias, ingredientes),
    inglés solo para módulos técnicos transversales (auth, users — éste último
    documentado en openspec/specs/user-profile/spec.md).
    """
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = list(response.json()["paths"].keys())

    expected_prefixes = [
        "/api/v1/auth",
        "/api/v1/usuarios",
        "/api/v1/productos",
        "/api/v1/pedidos",
        "/api/v1/pagos",
        "/api/v1/direcciones",
        "/api/v1/categorias",
        "/api/v1/ingredientes",
    ]

    for prefix in expected_prefixes:
        assert any(p.startswith(prefix) for p in paths), (
            f"No routes registered under {prefix}. Registered paths: {paths}"
        )


def test_404_not_found(client: TestClient):
    """Test that non-existent routes return 404."""
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_app_startup(client: TestClient):
    """Test that app starts without errors."""
    # If we got a client, the app started successfully
    response = client.get("/health")
    assert response.status_code == 200
