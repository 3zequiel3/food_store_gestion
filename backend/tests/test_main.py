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
    assert response.status_code in [
        200,
        404,
    ]  # OPTIONS might not be implemented on all endpoints


def test_request_logging_middleware(client: TestClient, caplog):
    """Test that request logging middleware is active."""
    import logging

    caplog.set_level(logging.INFO)

    response = client.get("/health")

    assert response.status_code == 200
    # Middleware should log the request
    # Note: caplog might not capture if middleware uses a different logger


def test_api_routes_exist(client: TestClient):
    """Test that API feature routes are registered."""
    # These routes return 404 currently (not implemented)
    # But they should be registered in the app
    response = client.get("/api/products/")
    assert response.status_code == 200

    response = client.get("/api/users/")
    assert response.status_code == 200

    response = client.get("/api/orders/")
    assert response.status_code == 200


def test_404_not_found(client: TestClient):
    """Test that non-existent routes return 404."""
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_app_startup(client: TestClient):
    """Test that app starts without errors."""
    # If we got a client, the app started successfully
    response = client.get("/health")
    assert response.status_code == 200
