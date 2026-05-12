"""
AdminUserRepository — data access for admin user management.

Extends BaseRepository[Usuario] with:
- list_paginated: search + role filter + pagination (returns items + total)
- find_by_id_with_roles: eager-load roles for any user (including inactive)
- count_active_admins_excluding: validates the "last ADMIN" invariant (RN-RB04)
- set_roles: atomic role replacement within the caller's UoW session
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.features.catalog.models import Rol
from backend.features.users.models import Usuario, UsuarioRol
from backend.shared.repository import BaseRepository


class AdminUserRepository(BaseRepository[Usuario]):
    """Repository for admin user management operations.

    Inherits standard CRUD from BaseRepository[Usuario].
    All methods operate within the session provided by the caller's UoW.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session, Usuario)

    # ── Listing ──────────────────────────────────────────────────────────────

    def list_paginated(
        self,
        page: int,
        page_size: int,
        search: Optional[str] = None,
        rol_codigo: Optional[str] = None,
    ) -> Tuple[List[Usuario], int]:
        """Return a paginated list of users with optional filters.

        Filters applied:
        - eliminado_en IS NULL (soft-delete exclusion, via _get_base_query)
        - search: case-insensitive partial match on nombre OR email
        - rol_codigo: only users with the given role code

        Returns:
            (items, total) where total reflects the filtered count before pagination.
        """
        base = self._get_base_query().options(selectinload(Usuario.roles))

        if search:
            pattern = f"%{search}%"
            base = base.where(
                Usuario.nombre.ilike(pattern) | Usuario.email.ilike(pattern)
            )

        if rol_codigo:
            base = base.where(
                Usuario.id.in_(
                    select(UsuarioRol.user_id)
                    .join(Rol, Rol.id == UsuarioRol.role_id)
                    .where(Rol.codigo == rol_codigo)
                )
            )

        # Count before pagination
        count_query = select(func.count()).select_from(base.subquery())
        total: int = self.session.execute(count_query).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        items_query = base.offset(offset).limit(page_size)
        items: List[Usuario] = list(self.session.execute(items_query).scalars().all())

        return items, total

    # ── Single-user lookup ────────────────────────────────────────────────────

    def find_by_id_with_roles(self, user_id: int) -> Optional[Usuario]:
        """Find any non-soft-deleted user by ID with roles eager-loaded.

        Unlike UserProfileRepository.find_by_id_with_roles, this method
        does NOT filter by is_active — admins must be able to retrieve
        deactivated users for management purposes.

        Expires the cached identity-map entry first so that any in-session
        writes (e.g. set_roles flush) are visible in the reload.
        """
        # If the object is already in the session's identity map, expire it so
        # the following SELECT fetches fresh data from the DB (including updated
        # user_roles rows written by set_roles in the same session).
        from sqlalchemy import inspect as sa_inspect

        existing = self.session.get(Usuario, user_id)
        if existing is not None:
            self.session.expire(existing)

        query = (
            self._get_base_query()
            .where(Usuario.id == user_id)
            .options(selectinload(Usuario.roles))
        )
        return self.session.execute(query).scalar_one_or_none()

    # ── Last-admin guard ──────────────────────────────────────────────────────

    def count_active_admins_excluding(self, user_id: int) -> int:
        """Count active ADMIN users excluding the given user_id (D4).

        Used by the service to enforce the "at least one ADMIN" invariant
        before removing the ADMIN role from a user.

        Query:
            SELECT COUNT(users.id)
            FROM users
            JOIN user_roles ON user_roles.user_id = users.id
            JOIN roles ON roles.id = user_roles.role_id
            WHERE roles.codigo = 'ADMIN'
              AND users.is_active = TRUE
              AND users.eliminado_en IS NULL
              AND users.id != :user_id
        """
        query = (
            select(func.count(Usuario.id))
            .join(UsuarioRol, UsuarioRol.user_id == Usuario.id)
            .join(Rol, Rol.id == UsuarioRol.role_id)
            .where(
                Rol.codigo == "ADMIN",
                Usuario.is_active.is_(True),
                Usuario.eliminado_en.is_(None),
                Usuario.id != user_id,
            )
        )
        return self.session.execute(query).scalar() or 0

    # ── Role replacement ──────────────────────────────────────────────────────

    def set_roles(self, user_id: int, role_codes: List[str]) -> None:
        """Atomically replace all roles for a user (D6).

        Steps within the caller's session (same UoW):
        1. Delete all existing user_roles rows for user_id.
        2. Look up each role code → role_id.
        3. Insert the new UsuarioRol rows.

        Raises:
            ValueError: if any role code is not found in the roles table.
                        (Callers should validate via get_roles_by_codes first.)
        """
        # 1. Remove existing roles
        existing = self.session.execute(
            select(UsuarioRol).where(UsuarioRol.user_id == user_id)
        ).scalars().all()
        for ur in existing:
            self.session.delete(ur)
        self.session.flush()

        # 2. Resolve codes → IDs
        roles = self.session.execute(
            select(Rol).where(Rol.codigo.in_(role_codes))
        ).scalars().all()

        found_codes = {r.codigo for r in roles}
        missing = set(role_codes) - found_codes
        if missing:
            raise ValueError(f"Códigos de rol no válidos: {sorted(missing)}")

        # 3. Insert new rows
        for rol in roles:
            self.session.add(UsuarioRol(user_id=user_id, role_id=rol.id))
        self.session.flush()

    def get_roles_by_codes(self, role_codes: List[str]) -> List[Rol]:
        """Return Rol instances for the given codes.

        Used by the service to validate codes before calling set_roles.
        Returns an empty list entry for unknown codes (service checks completeness).
        """
        return list(
            self.session.execute(
                select(Rol).where(Rol.codigo.in_(role_codes))
            ).scalars().all()
        )
