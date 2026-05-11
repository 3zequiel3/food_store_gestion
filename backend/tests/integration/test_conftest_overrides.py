"""
Regression tests for conftest.py dependency overrides.

Verifies that ALL FastAPI dependency functions used by routers are properly
overridden in the test harness to use the in-memory SQLite session, NOT a
real Postgres connection.

This file is intentionally separate from domain-specific test files because
these tests are about the test infrastructure contract, not about any particular
feature's business logic.
"""

import pytest
import backend.shared.unit_of_work as _uow_mod


def test_get_uow_uses_test_db_session_not_real_postgres(client, test_db_session):
    """Regression: get_uow MUST be overridden so requests use the SQLite
    test session, not a real Postgres connection.

    Before fix: OperationalError is raised with "connection refused" /
    "localhost:5432" / "psycopg2" in the exception message, because get_uow
    bypasses dependency_overrides[get_db] and calls get_session_factory()()
    which tries to connect to a real Postgres instance.

    After fix: If an exception is raised, it must be a SQLite-local error
    (e.g. "no such function: literal" from sqlite3), NOT a Postgres connection
    error. This confirms that the override is active and the request reached the
    service layer via the in-memory SQLite session.

    NOTE: The categories repository uses func.literal() which is
    PostgreSQL-specific and unsupported by SQLite. That is a residual bug in
    the categories repository (separate concern). What matters here is that any
    failure comes from SQLite, not from a Postgres connection attempt.

    TODO: remove after Step 3 (legacy get_uow override will be deleted)
    """
    try:
        response = client.get("/api/v1/categorias/")
        # If we reach here, the request completed (possibly with 200 or error status).
        # Verify the response body does NOT contain Postgres connection details.
        response_body = response.text
        assert "connection refused" not in response_body.lower(), (
            f"Got 'connection refused' in response — get_uow override is missing. "
            f"Body: {response_body[:500]}"
        )
        assert "localhost:5432" not in response_body, (
            f"Response mentions localhost:5432 — hitting real Postgres. "
            f"Body: {response_body[:500]}"
        )
        assert "psycopg2" not in response_body.lower(), (
            f"Response contains psycopg2 — using Postgres session, not SQLite. "
            f"Body: {response_body[:500]}"
        )
    except Exception as exc:
        # An exception can bubble from TestClient if the server middleware
        # re-raises (raise_server_exceptions=True by default).
        # Verify the exception is NOT a Postgres connection error.
        exc_str = str(exc).lower()
        assert "connection refused" not in exc_str, (
            f"Got Postgres 'connection refused' — get_uow override is MISSING. "
            f"Exception: {exc}"
        )
        assert "localhost:5432" not in str(exc), (
            f"Exception mentions localhost:5432 — get_uow override is MISSING. "
            f"Exception: {exc}"
        )
        assert "psycopg2" not in exc_str, (
            f"Exception is a psycopg2 error — get_uow override is MISSING. "
            f"Exception: {exc}"
        )
        # Exception came from SQLite (or some other local error) — override is working.
        # This is expected while the categories repository uses PG-specific SQL.


def test_uow_session_factory_monkeypatched_to_test_db(test_db_session):
    """Verify that the _patch_uow_session_factory autouse fixture has patched
    get_session_factory in the unit_of_work module so that UnitOfWork()
    (no args) receives a session bound to the test SQLite connection, NOT a
    real Postgres factory.

    The factory creates a NEW session (not the same instance as test_db_session)
    but bound to the same SQLite connection, so it participates in the same
    transaction and shares visibility of all pending changes.

    This is the new mechanism that services use after refactor-uow-to-context-manager.
    """
    factory = _uow_mod.get_session_factory()
    uow_session = factory()

    # The UoW session must NOT be the same instance as test_db_session
    # (they have separate identity maps) but must be on the same connection.
    test_conn = test_db_session.get_bind()
    uow_conn = uow_session.get_bind()
    assert uow_conn is test_conn, (
        "get_session_factory() in unit_of_work module must return a factory that "
        "creates sessions bound to the test SQLite connection. Got a different "
        "connection — _patch_uow_session_factory autouse fixture is NOT active."
    )

    # Verify it is NOT a real Postgres connection
    bind_str = str(uow_conn)
    assert "postgres" not in bind_str.lower() and "psycopg2" not in bind_str.lower(), (
        f"UoW session is bound to Postgres, not SQLite: {bind_str}"
    )

    uow_session.close()
