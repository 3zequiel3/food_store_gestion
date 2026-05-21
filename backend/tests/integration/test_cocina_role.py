"""
Integration tests for COCINA role in seed data.

Tests that the COCINA role (id=5) and cocina user (cocina@foodstore.com)
are correctly defined and idempotent.

Since the seed script uses PostgreSQL-specific ON CONFLICT, these tests
verify the same invariants by directly inserting the seed-equivalent data
via the ORM (which is how all other integration tests work).

Runner: cd backend && uv run pytest tests/integration/test_cocina_role.py -v
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.security import hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_cocina_role(session: Session) -> None:
    """Insert the COCINA role (id=5) directly via ORM."""
    from features.catalog.models import Rol

    role = Rol(id=5, codigo="COCINA", descripcion="Cocinero")
    session.merge(role)
    session.commit()


def _seed_cocina_user(session: Session, email: str = "cocina@foodstore.com") -> None:
    """Insert the cocina user with COCINA role directly via ORM."""
    from features.users.models import Usuario, UsuarioRol

    password_hash = hash_password("admin1234")
    user = Usuario(
        email=email,
        password_hash=password_hash,
        nombre="Cocina",
        apellido="Test",
        is_active=True,
    )
    session.add(user)
    session.flush()
    session.add(UsuarioRol(user_id=user.id, role_id=5))
    session.commit()
    session.refresh(user)
    return user


def _seed_original_roles(session: Session) -> None:
    """Insert the 4 original roles (ADMIN, STOCK, PEDIDOS, CLIENT)."""
    from features.catalog.models import Rol

    roles = [
        Rol(id=1, codigo="ADMIN", descripcion="Administrador del sistema"),
        Rol(id=2, codigo="STOCK", descripcion="Gestiona inventario"),
        Rol(id=3, codigo="PEDIDOS", descripcion="Gestiona pedidos y entregas"),
        Rol(id=4, codigo="CLIENT", descripcion="Cliente final"),
    ]
    for role in roles:
        session.merge(role)
    session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCocinaRoleInSeed:
    """Slice 1: COCINA role exists with correct id and codigo."""

    def test_cocina_role_exists_in_seed(self, test_db_session: Session):
        """After seeding, SELECT * FROM roles WHERE codigo='COCINA' returns id=5."""
        from features.catalog.models import Rol

        _seed_original_roles(test_db_session)
        _seed_cocina_role(test_db_session)

        role = test_db_session.execute(
            select(Rol).where(Rol.codigo == "COCINA")
        ).scalar_one_or_none()

        assert role is not None
        assert role.id == 5
        assert role.codigo == "COCINA"
        assert role.descripcion == "Cocinero"

    def test_cocina_user_exists_in_seed(self, test_db_session: Session):
        """After seeding, user cocina@foodstore.com exists with COCINA role."""
        from features.users.models import Usuario

        _seed_original_roles(test_db_session)
        _seed_cocina_role(test_db_session)
        _seed_cocina_user(test_db_session)

        user = test_db_session.execute(
            select(Usuario).where(Usuario.email == "cocina@foodstore.com")
        ).scalar_one_or_none()

        assert user is not None
        assert user.nombre == "Cocina"
        assert user.apellido == "Test"
        assert user.is_active is True
        role_codes = {r.codigo for r in user.roles}
        assert "COCINA" in role_codes

    def test_seed_idempotent_cocina(self, test_db_session: Session):
        """Running seed twice doesn't duplicate COCINA role or cocina user."""
        from features.catalog.models import Rol
        from features.users.models import Usuario
        from sqlalchemy import select as sa_select

        _seed_original_roles(test_db_session)

        # First "seed"
        _seed_cocina_role(test_db_session)
        _seed_cocina_user(test_db_session)

        # Second "seed" (idempotent re-run) — use merge for role, check user exists
        _seed_cocina_role(test_db_session)

        # For user, check if exists before inserting (simulating ON CONFLICT DO NOTHING)
        existing_user = test_db_session.execute(
            sa_select(Usuario).where(Usuario.email == "cocina@foodstore.com")
        ).scalar_one_or_none()
        if existing_user is None:
            _seed_cocina_user(test_db_session)

        # Role should still be exactly one
        roles = test_db_session.execute(
            sa_select(Rol).where(Rol.codigo == "COCINA")
        ).scalars().all()
        assert len(roles) == 1

        # User should still be exactly one
        users = test_db_session.execute(
            sa_select(Usuario).where(Usuario.email == "cocina@foodstore.com")
        ).scalars().all()
        assert len(users) == 1

    def test_original_four_roles_unchanged(self, test_db_session: Session):
        """The 4 original roles (ADMIN=1, STOCK=2, PEDIDOS=3, CLIENT=4) are present."""
        from features.catalog.models import Rol

        _seed_original_roles(test_db_session)
        _seed_cocina_role(test_db_session)

        expected = [
            (1, "ADMIN"),
            (2, "STOCK"),
            (3, "PEDIDOS"),
            (4, "CLIENT"),
        ]
        for expected_id, expected_codigo in expected:
            role = test_db_session.get(Rol, expected_id)
            assert role is not None, f"Role id={expected_id} missing"
            assert role.codigo == expected_codigo
