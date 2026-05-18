"""
Tests for Alembic migration 20260518_0100_rename_en_camino_to_terminado.

Strategy: run the upgrade/downgrade SQL directly against a minimal SQLite
in-memory schema that mirrors the three affected tables (order_states, orders,
order_state_history).  We do NOT use the Alembic runner — the conftest suite
uses SQLite, and alembic env.py points to Postgres.  The migration itself
consists exclusively of UPDATE statements; testing them against an equivalent
schema gives full coverage of the business logic without requiring a live PG
connection.

Runner: cd backend && uv run pytest tests/unit/test_migration_rename_en_camino.py -xvs
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS order_states (
    codigo    TEXT PRIMARY KEY,
    descripcion TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    estado_codigo     TEXT NOT NULL REFERENCES order_states(codigo)
);

CREATE TABLE IF NOT EXISTS order_state_history (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    estado_anterior_codigo TEXT REFERENCES order_states(codigo),
    estado_nuevo_codigo    TEXT NOT NULL REFERENCES order_states(codigo)
);
"""

_SEED = """
INSERT OR IGNORE INTO order_states (codigo, descripcion) VALUES
    ('PENDIENTE',      'Esperando confirmación'),
    ('CONFIRMADO',     'Confirmado'),
    ('EN_PREPARACION', 'En preparación'),
    ('EN_CAMINO',      'Pedido en camino al cliente'),
    ('ENTREGADO',      'Pedido entregado'),
    ('CANCELADO',      'Cancelado');

-- An order sitting in EN_CAMINO (to be migrated)
INSERT INTO orders (estado_codigo) VALUES ('EN_CAMINO');
-- A normal order that must NOT be touched
INSERT INTO orders (estado_codigo) VALUES ('PENDIENTE');

-- History row with both from and to = EN_CAMINO
INSERT INTO order_state_history (estado_anterior_codigo, estado_nuevo_codigo)
    VALUES ('EN_CAMINO', 'EN_CAMINO');
-- History row: only the "to" column is EN_CAMINO
INSERT INTO order_state_history (estado_anterior_codigo, estado_nuevo_codigo)
    VALUES ('CONFIRMADO', 'EN_CAMINO');
-- History row: only the "from" column is EN_CAMINO
INSERT INTO order_state_history (estado_anterior_codigo, estado_nuevo_codigo)
    VALUES ('EN_CAMINO', 'ENTREGADO');
-- Row completely unrelated to EN_CAMINO — must be untouched
INSERT INTO order_state_history (estado_anterior_codigo, estado_nuevo_codigo)
    VALUES ('PENDIENTE', 'CONFIRMADO');
"""

# upgrade() SQL, inlined from the migration to keep tests self-contained.
_UPGRADE_SQLS = [
    """
    UPDATE order_states
    SET codigo = 'TERMINADO',
        descripcion = 'Pedido listo para ser retirado o entregado'
    WHERE codigo = 'EN_CAMINO'
    """,
    """
    UPDATE orders
    SET estado_codigo = 'TERMINADO'
    WHERE estado_codigo = 'EN_CAMINO'
    """,
    """
    UPDATE order_state_history
    SET estado_anterior_codigo = 'TERMINADO'
    WHERE estado_anterior_codigo = 'EN_CAMINO'
    """,
    """
    UPDATE order_state_history
    SET estado_nuevo_codigo = 'TERMINADO'
    WHERE estado_nuevo_codigo = 'EN_CAMINO'
    """,
]

# downgrade() SQL, inlined from the migration.
_DOWNGRADE_SQLS = [
    """
    UPDATE order_state_history
    SET estado_nuevo_codigo = 'EN_CAMINO'
    WHERE estado_nuevo_codigo = 'TERMINADO'
    """,
    """
    UPDATE order_state_history
    SET estado_anterior_codigo = 'EN_CAMINO'
    WHERE estado_anterior_codigo = 'TERMINADO'
    """,
    """
    UPDATE orders
    SET estado_codigo = 'EN_CAMINO'
    WHERE estado_codigo = 'TERMINADO'
    """,
    """
    UPDATE order_states
    SET codigo = 'EN_CAMINO',
        descripcion = 'Pedido en camino al cliente'
    WHERE codigo = 'TERMINADO'
    """,
]


@pytest.fixture()
def migration_engine():
    """Minimal SQLite in-memory engine with the three affected tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        for stmt in _CREATE_TABLES.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        for stmt in _SEED.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    return engine


def _run_sqls(engine, sqls: list[str]) -> None:
    with engine.begin() as conn:
        for sql in sqls:
            conn.execute(text(sql))


def _fetch_all(engine, query: str) -> list:
    with engine.connect() as conn:
        return conn.execute(text(query)).fetchall()


# ---------------------------------------------------------------------------
# upgrade() tests
# ---------------------------------------------------------------------------


class TestUpgrade:
    def test_order_states_catalog_renamed(self, migration_engine):
        """After upgrade, order_states must contain TERMINADO and no EN_CAMINO."""
        _run_sqls(migration_engine, _UPGRADE_SQLS)

        codes = [r[0] for r in _fetch_all(migration_engine, "SELECT codigo FROM order_states")]

        assert "EN_CAMINO" not in codes, "EN_CAMINO must be gone after upgrade"
        assert "TERMINADO" in codes, "TERMINADO must exist after upgrade"

    def test_orders_migrated_to_terminado(self, migration_engine):
        """All orders that were EN_CAMINO must become TERMINADO after upgrade."""
        _run_sqls(migration_engine, _UPGRADE_SQLS)

        rows = _fetch_all(
            migration_engine,
            "SELECT estado_codigo FROM orders WHERE estado_codigo = 'EN_CAMINO'",
        )
        assert len(rows) == 0, "No orders should remain in EN_CAMINO after upgrade"

        terminado_rows = _fetch_all(
            migration_engine,
            "SELECT estado_codigo FROM orders WHERE estado_codigo = 'TERMINADO'",
        )
        assert len(terminado_rows) == 1, "The previously-EN_CAMINO order must now be TERMINADO"

    def test_unrelated_orders_untouched(self, migration_engine):
        """Orders in other states must not be modified by the upgrade."""
        _run_sqls(migration_engine, _UPGRADE_SQLS)

        pendiente_rows = _fetch_all(
            migration_engine,
            "SELECT id FROM orders WHERE estado_codigo = 'PENDIENTE'",
        )
        assert len(pendiente_rows) == 1, "PENDIENTE order must survive the upgrade unchanged"

    def test_history_nuevo_codigo_migrated(self, migration_engine):
        """Rows with estado_nuevo_codigo = EN_CAMINO must become TERMINADO."""
        _run_sqls(migration_engine, _UPGRADE_SQLS)

        en_camino_nuevo = _fetch_all(
            migration_engine,
            "SELECT id FROM order_state_history WHERE estado_nuevo_codigo = 'EN_CAMINO'",
        )
        assert len(en_camino_nuevo) == 0

        terminado_nuevo = _fetch_all(
            migration_engine,
            "SELECT id FROM order_state_history WHERE estado_nuevo_codigo = 'TERMINADO'",
        )
        # Rows 1 (EN_CAMINO→EN_CAMINO) and 2 (CONFIRMADO→EN_CAMINO) should show TERMINADO
        assert len(terminado_nuevo) == 2

    def test_history_anterior_codigo_migrated(self, migration_engine):
        """Rows with estado_anterior_codigo = EN_CAMINO must become TERMINADO."""
        _run_sqls(migration_engine, _UPGRADE_SQLS)

        en_camino_anterior = _fetch_all(
            migration_engine,
            "SELECT id FROM order_state_history WHERE estado_anterior_codigo = 'EN_CAMINO'",
        )
        assert len(en_camino_anterior) == 0

        terminado_anterior = _fetch_all(
            migration_engine,
            "SELECT id FROM order_state_history WHERE estado_anterior_codigo = 'TERMINADO'",
        )
        # Rows 1 (EN_CAMINO→EN_CAMINO) and 3 (EN_CAMINO→ENTREGADO) should show TERMINADO
        assert len(terminado_anterior) == 2

    def test_unrelated_history_untouched(self, migration_engine):
        """Rows completely unrelated to EN_CAMINO must not be touched."""
        _run_sqls(migration_engine, _UPGRADE_SQLS)

        row = _fetch_all(
            migration_engine,
            """
            SELECT id FROM order_state_history
            WHERE estado_anterior_codigo = 'PENDIENTE'
              AND estado_nuevo_codigo = 'CONFIRMADO'
            """,
        )
        assert len(row) == 1, "PENDIENTE→CONFIRMADO history row must survive unchanged"

    def test_upgrade_is_idempotent(self, migration_engine):
        """Running upgrade twice must produce the same result as running it once."""
        _run_sqls(migration_engine, _UPGRADE_SQLS)
        _run_sqls(migration_engine, _UPGRADE_SQLS)  # second run

        codes = [r[0] for r in _fetch_all(migration_engine, "SELECT codigo FROM order_states")]
        assert "EN_CAMINO" not in codes
        assert "TERMINADO" in codes


# ---------------------------------------------------------------------------
# downgrade() tests
# ---------------------------------------------------------------------------


class TestDowngrade:
    def test_full_roundtrip(self, migration_engine):
        """upgrade() followed by downgrade() must restore the original catalog row."""
        _run_sqls(migration_engine, _UPGRADE_SQLS)
        _run_sqls(migration_engine, _DOWNGRADE_SQLS)

        codes = [r[0] for r in _fetch_all(migration_engine, "SELECT codigo FROM order_states")]
        assert "EN_CAMINO" in codes, "EN_CAMINO must be restored after downgrade"
        assert "TERMINADO" not in codes, "TERMINADO must be gone after downgrade"

    def test_orders_reverted_after_downgrade(self, migration_engine):
        """After upgrade + downgrade, orders must be back to EN_CAMINO."""
        _run_sqls(migration_engine, _UPGRADE_SQLS)
        _run_sqls(migration_engine, _DOWNGRADE_SQLS)

        rows = _fetch_all(
            migration_engine,
            "SELECT estado_codigo FROM orders WHERE estado_codigo = 'EN_CAMINO'",
        )
        assert len(rows) == 1

    def test_history_reverted_after_downgrade(self, migration_engine):
        """After upgrade + downgrade, all TERMINADO references must become EN_CAMINO again."""
        _run_sqls(migration_engine, _UPGRADE_SQLS)
        _run_sqls(migration_engine, _DOWNGRADE_SQLS)

        terminado_nuevo = _fetch_all(
            migration_engine,
            "SELECT id FROM order_state_history WHERE estado_nuevo_codigo = 'TERMINADO'",
        )
        assert len(terminado_nuevo) == 0

        en_camino_nuevo = _fetch_all(
            migration_engine,
            "SELECT id FROM order_state_history WHERE estado_nuevo_codigo = 'EN_CAMINO'",
        )
        assert len(en_camino_nuevo) == 2
