"""
Seed script: loads minimal canonical data idempotently.

Usage:
    cd /path/to/project   # project root (parent of backend/)
    export DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/foodstore_dev
    python -m  scripts.seed

What this script loads:
    - 4 roles         (IDs stable: 1=ADMIN, 2=STOCK, 3=PEDIDOS, 4=CLIENT)
    - 6 order states  (PENDIENTE..CANCELADO with ordering and terminal flag)
    - 3 payment methods (MERCADOPAGO, EFECTIVO, TRANSFERENCIA)
    - 1 admin user    (admin@foodstore.com, password from ADMIN_PASSWORD env)
    - 1 user_roles binding (admin → ADMIN role)

All inserts use ON CONFLICT DO NOTHING so re-running is safe and idempotent.

Exit codes:
    0 — success (all seeds applied or already present)
    1 — error (DB connection failure, unexpected exception)
"""

import logging
import os
import sys

import bcrypt as _bcrypt_lib
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Ensure the project root is on sys.path when running as a module
from shared.database import Base, get_engine, get_session_factory  # noqa: E402
from features.catalog.models import (  # noqa: E402
    Rol,
    EstadoPedido,
    FormaPago,
)
from features.users.models import Usuario, UsuarioRol  # noqa: E402

# ---------------------------------------------------------------------------
# Logging: WARNING level to stderr (as required by task 9.2)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s [%(name)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


def seed_roles(session) -> None:
    """Insert the 4 canonical roles with stable IDs (idempotent)."""
    roles = [
        {"id": 1, "codigo": "ADMIN",    "descripcion": "Administrador del sistema"},
        {"id": 2, "codigo": "STOCK",    "descripcion": "Gestiona inventario"},
        {"id": 3, "codigo": "PEDIDOS",  "descripcion": "Gestiona pedidos y entregas"},
        {"id": 4, "codigo": "CLIENT",   "descripcion": "Cliente final"},
    ]
    stmt = pg_insert(Rol).values(roles).on_conflict_do_nothing(index_elements=["id"])
    session.execute(stmt)
    logger.info("seed_roles: done")


def seed_estados_pedido(session) -> None:
    """Insert the 6 canonical order states (idempotent)."""
    estados = [
        {"codigo": "PENDIENTE",       "descripcion": "Pedido recibido, aguardando confirmación", "orden": 1, "es_terminal": False},
        {"codigo": "CONFIRMADO",      "descripcion": "Pedido confirmado por el local",           "orden": 2, "es_terminal": False},
        {"codigo": "EN_PREPARACION",  "descripcion": "Pedido en cocina",                        "orden": 3, "es_terminal": False},
        {"codigo": "TERMINADO",       "descripcion": "Pedido listo para ser retirado o entregado",   "orden": 4, "es_terminal": False},
        {"codigo": "ENTREGADO",       "descripcion": "Pedido entregado al cliente",              "orden": 5, "es_terminal": True},
        {"codigo": "CANCELADO",       "descripcion": "Pedido cancelado",                        "orden": 6, "es_terminal": True},
    ]
    stmt = (
        pg_insert(EstadoPedido)
        .values(estados)
        .on_conflict_do_nothing(index_elements=["codigo"])
    )
    session.execute(stmt)
    logger.info("seed_estados_pedido: done")


def seed_formas_pago(session) -> None:
    """Insert the 3 canonical payment methods (idempotent).

    TARJETA replaces the legacy MERCADOPAGO code (renamed in migration
    20260514_1200_payment_order_state_refactor). Seeding MERCADOPAGO again
    each boot is what produced the duplicate row visible in the checkout UI.
    """
    formas = [
        {"codigo": "TARJETA",       "descripcion": "Pago online vía MercadoPago",    "habilitada": True},
        {"codigo": "EFECTIVO",      "descripcion": "Pago en efectivo al repartidor", "habilitada": True},
        {"codigo": "TRANSFERENCIA", "descripcion": "Transferencia bancaria",         "habilitada": True},
    ]
    stmt = (
        pg_insert(FormaPago)
        .values(formas)
        .on_conflict_do_nothing(index_elements=["codigo"])
    )
    session.execute(stmt)
    logger.info("seed_formas_pago: done")


def seed_admin(session) -> None:
    """
    Insert the admin user and bind it to the ADMIN role (idempotent).

    Password is read from ADMIN_PASSWORD env var.
    If not set, defaults to 'admin1234' with a loud WARNING.
    """
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_password:
        admin_password = "admin1234"
        logger.warning(
            "ADMIN_PASSWORD environment variable is not set. "
            "Using insecure default 'admin1234' — CHANGE IMMEDIATELY in production."
        )

    password_hash = _bcrypt_lib.hashpw(admin_password.encode(), _bcrypt_lib.gensalt(rounds=12)).decode()

    # Insert user (conflict on email → skip)
    user_values = [
        {
            "email": "admin@foodstore.com",
            "password_hash": password_hash,
            "nombre": "Admin",
            "apellido": "Sistema",
            "is_active": True,
        }
    ]
    stmt = (
        pg_insert(Usuario)
        .values(user_values)
        .on_conflict_do_nothing(index_elements=["email"])
    )
    session.execute(stmt)

    # Retrieve the admin user id (may have been inserted just now or previously)
    admin_user = session.execute(
        text("SELECT id FROM users WHERE email = 'admin@foodstore.com'")
    ).fetchone()

    if admin_user is None:
        raise RuntimeError("Admin user not found after insert — this should never happen.")

    admin_user_id = admin_user[0]

    # Bind admin user to ADMIN role (role_id=1, conflict on composite PK → skip)
    ur_values = [{"user_id": admin_user_id, "role_id": 1}]
    stmt = (
        pg_insert(UsuarioRol)
        .values(ur_values)
        .on_conflict_do_nothing(index_elements=["user_id", "role_id"])
    )
    session.execute(stmt)
    logger.info("seed_admin: done (user_id=%s)", admin_user_id)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_seed() -> None:
    """Run all seed functions in order and commit."""
    engine = get_engine()
    SessionFactory = get_session_factory()
    session = SessionFactory()

    try:
        seed_roles(session)
        seed_estados_pedido(session)
        seed_formas_pago(session)
        seed_admin(session)
        session.commit()
        logger.warning("Seed completed successfully.")
    except Exception as exc:
        session.rollback()
        logger.error("Seed failed: %s", exc, exc_info=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    try:
        run_seed()
        sys.exit(0)
    except Exception:
        sys.exit(1)
