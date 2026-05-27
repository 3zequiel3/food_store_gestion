"""
Seed script: loads minimal canonical data idempotently.

Usage:
    cd /path/to/project   # project root (parent of backend/)
    export DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/foodstore_dev
    python -m  scripts.seed

What this script loads:
    - 5 roles          (IDs stable: 1=ADMIN, 2=STOCK, 3=PEDIDOS, 4=CLIENT, 5=COCINA)
    - 7 order states   (PENDIENTE..CANCELADO with ordering and terminal flag)
    - 3 payment methods (TARJETA, EFECTIVO, TRANSFERENCIA)
    - 5 root categories + 10 leaves (Pizzas→Clásicas/Especiales,
      Hamburguesas→Simples/Dobles, Empanadas→Al horno/Fritas,
      Bebidas→Gaseosas/Aguas, Postres→Helados/Tortas)
    - 12 ingredientes  (incluye flags es_alergeno / es_removible)
    - 6 productos      (con links a categorías e ingredientes)
    - 1 admin user     (admin@foodstore.com, password from ADMIN_PASSWORD env)
    - 1 cocina user    (cocina@foodstore.com, password from ADMIN_PASSWORD env)
    - 1 cliente user   (cliente@foodstore.com, password from CLIENT_PASSWORD or ADMIN_PASSWORD env)
    - 3 user_roles bindings (admin → ADMIN, cocina → COCINA, cliente → CLIENT)

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
    Ingrediente,
)
from features.products.models import (  # noqa: E402
    ProductoCategoria,
    ProductoIngrediente,
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
    """Insert the 5 canonical roles with stable IDs (idempotent)."""
    roles = [
        {"id": 1, "codigo": "ADMIN",    "descripcion": "Administrador del sistema"},
        {"id": 2, "codigo": "STOCK",    "descripcion": "Gestiona inventario"},
        {"id": 3, "codigo": "PEDIDOS",  "descripcion": "Gestiona pedidos y entregas"},
        {"id": 4, "codigo": "CLIENT",   "descripcion": "Cliente final"},
        {"id": 5, "codigo": "COCINA",   "descripcion": "Cocinero"},
    ]
    stmt = pg_insert(Rol).values(roles).on_conflict_do_nothing(index_elements=["id"])
    session.execute(stmt)
    logger.info("seed_roles: done")


def seed_estados_pedido(session) -> None:
    """
    Insert the canonical order states (idempotent).

    Includes the three terminal cancellation flavors used by the FSM:
      - CANCELADO         (generic / legacy)
      - CANCELADO_ADMIN   (admin-driven, motivo required)
      - CANCELADO_CLIENTE (client-driven, refund handled out-of-band)
    """
    estados = [
        {"codigo": "PENDIENTE",         "descripcion": "Pedido recibido, aguardando confirmación",       "orden": 1, "es_terminal": False},
        {"codigo": "CONFIRMADO",        "descripcion": "Pedido confirmado por el local",                 "orden": 2, "es_terminal": False},
        {"codigo": "EN_PREPARACION",    "descripcion": "Pedido en cocina",                               "orden": 3, "es_terminal": False},
        {"codigo": "TERMINADO",         "descripcion": "Pedido listo para ser retirado o entregado",     "orden": 4, "es_terminal": False},
        {"codigo": "EN_CAMINO",         "descripcion": "Pedido en camino al cliente",                    "orden": 5, "es_terminal": False},
        {"codigo": "ENTREGADO",         "descripcion": "Pedido entregado al cliente",                    "orden": 6, "es_terminal": True},
        {"codigo": "CANCELADO",         "descripcion": "Pedido cancelado",                               "orden": 7, "es_terminal": True},
        {"codigo": "CANCELADO_ADMIN",   "descripcion": "Pedido cancelado por el administrador",          "orden": 8, "es_terminal": True},
        {"codigo": "CANCELADO_CLIENTE", "descripcion": "Pedido cancelado por el cliente",                "orden": 9, "es_terminal": True},
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


def seed_cocina_user(session) -> None:
    """
    Insert the cocina test user and bind it to the COCINA role (idempotent).

    Password is read from ADMIN_PASSWORD env var (same as admin).
    If not set, defaults to 'admin1234' with a loud WARNING.
    """
    cocina_password = os.environ.get("ADMIN_PASSWORD")
    if not cocina_password:
        cocina_password = "admin1234"

    password_hash = _bcrypt_lib.hashpw(cocina_password.encode(), _bcrypt_lib.gensalt(rounds=12)).decode()

    # Insert user (conflict on email → skip)
    user_values = [
        {
            "email": "cocina@foodstore.com",
            "password_hash": password_hash,
            "nombre": "Cocina",
            "apellido": "Test",
            "is_active": True,
        }
    ]
    stmt = (
        pg_insert(Usuario)
        .values(user_values)
        .on_conflict_do_nothing(index_elements=["email"])
    )
    session.execute(stmt)

    # Retrieve the cocina user id
    cocina_user = session.execute(
        text("SELECT id FROM users WHERE email = 'cocina@foodstore.com'")
    ).fetchone()

    if cocina_user is None:
        raise RuntimeError("Cocina user not found after insert — this should never happen.")

    cocina_user_id = cocina_user[0]

    # Bind cocina user to COCINA role (role_id=5, conflict on composite PK → skip)
    ur_values = [{"user_id": cocina_user_id, "role_id": 5}]
    stmt = (
        pg_insert(UsuarioRol)
        .values(ur_values)
        .on_conflict_do_nothing(index_elements=["user_id", "role_id"])
    )
    session.execute(stmt)
    logger.info("seed_cocina_user: done (user_id=%s)", cocina_user_id)


# ---------------------------------------------------------------------------
# Catalog seeds — categorías, ingredientes, productos
# ---------------------------------------------------------------------------


def _upsert_categoria(session, nombre: str, padre_id: int | None) -> int:
    """
    Find a category by (nombre, padre_id) or insert it. Returns its id.

    Two categories with the same name under different parents are valid
    (e.g. "Clásicas" under "Pizzas" and "Clásicas" under "Empanadas"),
    so the uniqueness key is the (nombre, padre_id) pair.
    """
    if padre_id is None:
        existing_id = session.execute(
            text(
                "SELECT id FROM categories "
                "WHERE nombre = :n AND padre_id IS NULL AND eliminado_en IS NULL"
            ),
            {"n": nombre},
        ).scalar_one_or_none()
    else:
        existing_id = session.execute(
            text(
                "SELECT id FROM categories "
                "WHERE nombre = :n AND padre_id = :p AND eliminado_en IS NULL"
            ),
            {"n": nombre, "p": padre_id},
        ).scalar_one_or_none()

    if existing_id is not None:
        return existing_id

    return session.execute(
        text(
            "INSERT INTO categories (nombre, padre_id) "
            "VALUES (:n, :p) RETURNING id"
        ),
        {"n": nombre, "p": padre_id},
    ).scalar_one()


def seed_categorias(session) -> dict[str, int]:
    """
    Insert the category tree (idempotent).

    Structure (root → leaves):
        Pizzas       → Clásicas, Especiales
        Hamburguesas → Simples, Dobles
        Empanadas    → Al horno, Fritas
        Bebidas      → Gaseosas, Aguas
        Postres      → Helados, Tortas

    Returns a mapping LEAF_NAME → leaf_id for `seed_productos` to wire the
    M:N pivot. Products MUST be linked to leaf categories only — the
    products service enforces this with `_assert_categorias_are_leaf`.
    """
    tree: dict[str, list[str]] = {
        "Pizzas":       ["Clásicas", "Especiales"],
        "Hamburguesas": ["Simples", "Dobles"],
        "Empanadas":    ["Al horno", "Fritas"],
        "Bebidas":      ["Gaseosas", "Aguas"],
        "Postres":      ["Helados", "Tortas"],
    }

    leaves: dict[str, int] = {}
    for root_name, leaf_names in tree.items():
        root_id = _upsert_categoria(session, root_name, padre_id=None)
        for leaf_name in leaf_names:
            leaf_id = _upsert_categoria(session, leaf_name, padre_id=root_id)
            leaves[leaf_name] = leaf_id

    logger.info(
        "seed_categorias: %d roots, %d leaves ready",
        len(tree), len(leaves),
    )
    return leaves


def seed_ingredientes(session) -> dict[str, int]:
    """
    Insert canonical ingredients (idempotent via UNIQUE(nombre)).

    Returns a mapping name → id used by seed_productos to wire the M:N pivot.
    """
    ingredientes = [
        {"nombre": "Muzzarella",         "es_alergeno": True,  "es_removible": True},
        {"nombre": "Tomate",             "es_alergeno": False, "es_removible": True},
        {"nombre": "Cebolla",            "es_alergeno": False, "es_removible": True},
        {"nombre": "Lechuga",            "es_alergeno": False, "es_removible": True},
        {"nombre": "Jamón",              "es_alergeno": False, "es_removible": True},
        {"nombre": "Huevo",              "es_alergeno": True,  "es_removible": True},
        {"nombre": "Aceitunas",          "es_alergeno": False, "es_removible": True},
        {"nombre": "Pan de hamburguesa", "es_alergeno": True,  "es_removible": False},
        {"nombre": "Carne",              "es_alergeno": False, "es_removible": False},
        {"nombre": "Masa de empanada",   "es_alergeno": True,  "es_removible": False},
        {"nombre": "Harina",             "es_alergeno": True,  "es_removible": False},
        {"nombre": "Azúcar",             "es_alergeno": False, "es_removible": False},
    ]
    stmt = (
        pg_insert(Ingrediente)
        .values(ingredientes)
        .on_conflict_do_nothing(index_elements=["nombre"])
    )
    session.execute(stmt)

    rows = session.execute(
        text(
            "SELECT id, nombre FROM ingredients "
            "WHERE nombre = ANY(:names) AND eliminado_en IS NULL"
        ),
        {"names": [i["nombre"] for i in ingredientes]},
    ).all()
    result = {row[1]: row[0] for row in rows}
    logger.info("seed_ingredientes: %d ingredients ready", len(result))
    return result


def seed_productos(
    session,
    categorias: dict[str, int],
    ingredientes: dict[str, int],
) -> None:
    """
    Insert demo products with their category and ingredient links.

    Idempotent by `nombre` (no unique constraint → SELECT-then-INSERT).
    Pivots use ON CONFLICT DO NOTHING on their composite PKs.
    """
    # Each product links to a LEAF category (the root nodes have children and
    # are therefore not eligible — `_assert_categorias_are_leaf` would reject).
    productos = [
        {
            "nombre": "Pizza Muzzarella",
            "descripcion": "Pizza clásica con muzzarella, salsa de tomate y aceitunas.",
            "precio": "5500.00",
            "stock_cantidad": 20,
            "categorias": ["Clásicas"],
            "ingredientes": ["Muzzarella", "Tomate", "Aceitunas", "Harina"],
        },
        {
            "nombre": "Pizza Especial",
            "descripcion": "Pizza con muzzarella, jamón y huevo.",
            "precio": "6800.00",
            "stock_cantidad": 15,
            "categorias": ["Especiales"],
            "ingredientes": ["Muzzarella", "Tomate", "Jamón", "Huevo", "Harina"],
        },
        {
            "nombre": "Hamburguesa Clásica",
            "descripcion": "Hamburguesa con carne, queso, lechuga, tomate y cebolla.",
            "precio": "5200.00",
            "stock_cantidad": 25,
            "categorias": ["Simples"],
            "ingredientes": [
                "Carne", "Pan de hamburguesa", "Muzzarella",
                "Lechuga", "Tomate", "Cebolla",
            ],
        },
        {
            "nombre": "Empanada de Carne",
            "descripcion": "Empanada tradicional de carne cortada a cuchillo.",
            "precio": "900.00",
            "stock_cantidad": 60,
            "categorias": ["Al horno"],
            "ingredientes": ["Carne", "Cebolla", "Huevo", "Masa de empanada"],
        },
        {
            "nombre": "Coca-Cola 500ml",
            "descripcion": "Botella de Coca-Cola 500 ml.",
            "precio": "1500.00",
            "stock_cantidad": 80,
            "categorias": ["Gaseosas"],
            "ingredientes": [],
        },
        {
            "nombre": "Brownie con nueces",
            "descripcion": "Brownie casero de chocolate con nueces.",
            "precio": "2200.00",
            "stock_cantidad": 18,
            "categorias": ["Tortas"],
            "ingredientes": ["Harina", "Huevo", "Azúcar"],
        },
    ]

    for prod in productos:
        existing_id = session.execute(
            text(
                "SELECT id FROM products "
                "WHERE nombre = :n AND eliminado_en IS NULL"
            ),
            {"n": prod["nombre"]},
        ).scalar_one_or_none()

        if existing_id is not None:
            prod_id = existing_id
        else:
            prod_id = session.execute(
                text(
                    "INSERT INTO products "
                    "(nombre, descripcion, precio, stock_cantidad, disponible) "
                    "VALUES (:n, :d, :pr, :s, TRUE) RETURNING id"
                ),
                {
                    "n": prod["nombre"],
                    "d": prod["descripcion"],
                    "pr": prod["precio"],
                    "s": prod["stock_cantidad"],
                },
            ).scalar_one()

        # M:N pivot: producto ↔ categoría
        for cat_name in prod["categorias"]:
            cat_id = categorias.get(cat_name)
            if cat_id is None:
                logger.warning(
                    "seed_productos: missing category %r for %r — skipping link",
                    cat_name, prod["nombre"],
                )
                continue
            session.execute(
                pg_insert(ProductoCategoria)
                .values(product_id=prod_id, category_id=cat_id)
                .on_conflict_do_nothing(index_elements=["product_id", "category_id"])
            )

        # M:N pivot: producto ↔ ingrediente
        for ing_name in prod["ingredientes"]:
            ing_id = ingredientes.get(ing_name)
            if ing_id is None:
                logger.warning(
                    "seed_productos: missing ingredient %r for %r — skipping link",
                    ing_name, prod["nombre"],
                )
                continue
            session.execute(
                pg_insert(ProductoIngrediente)
                .values(product_id=prod_id, ingredient_id=ing_id)
                .on_conflict_do_nothing(index_elements=["product_id", "ingredient_id"])
            )

    logger.info("seed_productos: %d productos ready", len(productos))


def seed_client_user(session) -> None:
    """
    Insert a CLIENT test user and bind it to the CLIENT role (idempotent).

    Password resolves in this order:
        1. CLIENT_PASSWORD env var
        2. ADMIN_PASSWORD env var (so a single env can seed all test users)
        3. Insecure default 'cliente1234' with a loud WARNING
    """
    client_password = (
        os.environ.get("CLIENT_PASSWORD")
        or os.environ.get("ADMIN_PASSWORD")
    )
    if not client_password:
        client_password = "cliente1234"
        logger.warning(
            "Neither CLIENT_PASSWORD nor ADMIN_PASSWORD is set. "
            "Using insecure default 'cliente1234' for the test client user."
        )

    password_hash = _bcrypt_lib.hashpw(
        client_password.encode(), _bcrypt_lib.gensalt(rounds=12)
    ).decode()

    user_values = [
        {
            "email": "cliente@foodstore.com",
            "password_hash": password_hash,
            "nombre": "Cliente",
            "apellido": "Test",
            "is_active": True,
        }
    ]
    stmt = (
        pg_insert(Usuario)
        .values(user_values)
        .on_conflict_do_nothing(index_elements=["email"])
    )
    session.execute(stmt)

    client_user = session.execute(
        text("SELECT id FROM users WHERE email = 'cliente@foodstore.com'")
    ).fetchone()
    if client_user is None:
        raise RuntimeError("Client user not found after insert — this should never happen.")
    client_user_id = client_user[0]

    # Bind to CLIENT role (role_id=4)
    ur_values = [{"user_id": client_user_id, "role_id": 4}]
    stmt = (
        pg_insert(UsuarioRol)
        .values(ur_values)
        .on_conflict_do_nothing(index_elements=["user_id", "role_id"])
    )
    session.execute(stmt)
    logger.info("seed_client_user: done (user_id=%s)", client_user_id)


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
        seed_cocina_user(session)
        seed_client_user(session)
        cat_ids = seed_categorias(session)
        ing_ids = seed_ingredientes(session)
        seed_productos(session, cat_ids, ing_ids)
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
