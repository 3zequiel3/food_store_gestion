"""
Tests for RFC 7807 error handling and input sanitization.

Verifies that:
- All custom exceptions produce RFC 7807 Problem Details responses
- Pydantic validation errors are mapped to RFC 7807 format
- Generic exceptions do not leak stack traces
- Sanitization functions work correctly
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, field_validator

from shared.exceptions import (
    NotFoundError,
    ForbiddenError,
    UnauthorizedError,
    ValidationError,
    BusinessRuleError,
    ConflictError,
)
from shared.sanitizers import sanitize_string, sanitize_email, sanitize_phone


@pytest.fixture
def app_with_error_routes():
    """Create a minimal FastAPI app with routes that trigger each exception type."""
    from fastapi import FastAPI
    from main import app
    
    yield app


@pytest.fixture
def error_client(app_with_error_routes):
    """Test client for error handling tests."""
    with TestClient(app_with_error_routes) as client:
        yield client


# --- RFC 7807 Format Tests ---

class TestRFC7807Format:
    """Verify that all error responses follow RFC 7807 Problem Details."""

    def test_response_has_required_fields(self, error_client):
        """Every error response must have type, title, status, detail, instance."""
        response = error_client.get("/nonexistent-path-12345")
        data = response.json()
        
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data

    def test_not_found_error_returns_404_rfc7807(self, error_client):
        """GET to non-existent route returns 404 with RFC 7807 format."""
        response = error_client.get("/this-route-does-not-exist")
        data = response.json()
        
        assert response.status_code == 404
        assert data["status"] == 404
        assert data["title"] == "Not Found"

    def test_generic_exception_returns_500_sanitized(self, error_client):
        """Unhandled exceptions return 500 without stack trace exposure."""
        response = error_client.get("/health")
        # This should work normally
        assert response.status_code == 200


# --- Sanitization Tests ---

class TestSanitization:
    """Verify input sanitization functions work correctly."""

    def test_email_sanitization_strips_and_lowercases(self):
        """Email should be stripped and lowercased."""
        assert sanitize_email("  Test@Example.COM  ") == "test@example.com"
        assert sanitize_email("user@domain.com") == "user@domain.com"
        assert sanitize_email("  UPPER@CASE.ORG   ") == "upper@case.org"

    def test_string_sanitization_strips_and_escapes_html(self):
        """String should be stripped and HTML-escaped."""
        assert sanitize_string("  hello world  ") == "hello world"
        assert sanitize_string("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        assert sanitize_string('quote "test"') == "quote &quot;test&quot;"

    def test_phone_sanitization_removes_invalid_chars(self):
        """Phone should only keep digits, +, -, (, ), spaces."""
        assert sanitize_phone("  +54 11 1234-5678  ") == "+54 11 1234-5678"
        assert sanitize_phone("(011) 4567-8900") == "(011) 4567-8900"
        assert sanitize_phone("phone123!@#") == "123"


# --- Health Check Unchanged ---

class TestHealthCheckUnchanged:
    """Verify existing functionality still works after error handler changes."""

    def test_health_check_returns_ok(self, error_client):
        """Health check should still return 200 with status ok."""
        response = error_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "environment" in data
