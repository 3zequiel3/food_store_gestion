"""
AdminUserService — business logic for admin user management.

Orchestrates AdminUserRepository and RefreshTokenRepository (for token revocation)
within a single UnitOfWork transaction.

Operations:
- list_usuarios: paginated list with optional search and role filter
- update_datos_personales: edit nombre/apellido/telefono
- change_rol: atomic role replacement with last-admin guard + token revocation (D4, D5)
- change_estado: activate/deactivate with token revocation on deactivation (D3)
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from backend.features.admin_users.repository import AdminUserRepository
from backend.features.admin_users.schemas import (
    AdminChangeEstadoRequest,
    AdminChangeRolRequest,
    AdminUpdateUserRequest,
    AdminUserResponse,
)
from backend.features.auth.repository import RefreshTokenRepository
from backend.features.users.models import Usuario
from backend.shared.exceptions import ConflictError, NotFoundError, ValidationError
from backend.shared.unit_of_work import UnitOfWork


class AdminUserService:
    """Service for admin user management operations.

    Each public method opens its own UnitOfWork context manager so that
    all repository operations (including token revocation) are atomic.
    """

    # ── List ─────────────────────────────────────────────────────────────────

    def list_usuarios(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        rol_codigo: Optional[str] = None,
    ) -> Tuple[List[AdminUserResponse], int]:
        """Return a paginated list of users with optional filters.

        Args:
            page: 1-indexed page number
            page_size: number of items per page
            search: case-insensitive partial match on nombre or email
            rol_codigo: filter to users with this role code

        Returns:
            (items as AdminUserResponse, total count before pagination)
        """
        with UnitOfWork() as uow:
            repo = AdminUserRepository(uow.session)
            items, total = repo.list_paginated(page, page_size, search, rol_codigo)
            responses = [AdminUserResponse.from_usuario(u) for u in items]

        return responses, total

    # ── Update personal data ──────────────────────────────────────────────────

    def update_datos_personales(
        self,
        user_id: int,
        payload: AdminUpdateUserRequest,
    ) -> AdminUserResponse:
        """Update nombre, apellido and/or telefono for any user.

        Args:
            user_id: target user ID
            payload: fields to update (all optional — only provided fields change)

        Returns:
            Updated user as AdminUserResponse

        Raises:
            NotFoundError: if user does not exist or is soft-deleted
        """
        update_data = payload.model_dump(exclude_none=True)

        with UnitOfWork() as uow:
            repo = AdminUserRepository(uow.session)

            user = repo.find_by_id_with_roles(user_id)
            if not user:
                raise NotFoundError(f"Usuario con id={user_id} no encontrado")

            if update_data:
                repo.update(user_id, **update_data)
                # Reload with roles eager-loaded after update
                user = repo.find_by_id_with_roles(user_id)

            response = AdminUserResponse.from_usuario(user)

        return response

    # ── Change roles ──────────────────────────────────────────────────────────

    def change_rol(
        self,
        user_id: int,
        payload: AdminChangeRolRequest,
    ) -> AdminUserResponse:
        """Replace the full set of roles for a user.

        Business rules enforced:
        - User must exist (404 if not found)
        - All role codes must be valid (422 if unknown code)
        - "Last ADMIN" invariant: if ADMIN is removed and no other active ADMIN
          would remain, raise ConflictError (409) — RN-RB04, D4

        After role update, all refresh tokens for the user are revoked so that
        the next login picks up the new roles (D5).

        Args:
            user_id: target user ID
            payload: new role codes (replaces existing set)

        Returns:
            Updated user as AdminUserResponse

        Raises:
            NotFoundError: if user does not exist or is soft-deleted
            ValidationError: if any role code is not in the system
            ConflictError: if operation would leave zero active ADMINs
        """
        role_codes = payload.roles

        with UnitOfWork() as uow:
            repo = AdminUserRepository(uow.session)

            # 1. Verify user exists
            user = repo.find_by_id_with_roles(user_id)
            if not user:
                raise NotFoundError(f"Usuario con id={user_id} no encontrado")

            # 2. Validate role codes
            found_roles = repo.get_roles_by_codes(role_codes)
            found_codes = {r.codigo for r in found_roles}
            missing = set(role_codes) - found_codes
            if missing:
                raise ValidationError(
                    f"Códigos de rol inválidos: {sorted(missing)}",
                    field="roles",
                )

            # 3. Last-ADMIN guard (D4)
            current_codes = {r.codigo for r in user.roles}
            removing_admin = "ADMIN" in current_codes and "ADMIN" not in set(role_codes)
            if removing_admin:
                remaining = repo.count_active_admins_excluding(user_id)
                if remaining == 0:
                    raise ConflictError(
                        "No se puede quitar el rol ADMIN: el sistema quedaría sin ningún administrador activo."
                    )

            # 4. Apply role replacement
            repo.set_roles(user_id, role_codes)

            # 5. Revoke refresh tokens (D5) — same UoW, same session
            token_repo = RefreshTokenRepository(uow.session)
            token_repo.revoke_all_user_tokens(user_id)

            # 6. Reload to return fresh data
            user = repo.find_by_id_with_roles(user_id)
            response = AdminUserResponse.from_usuario(user)

        return response

    # ── Change status ─────────────────────────────────────────────────────────

    def change_estado(
        self,
        user_id: int,
        payload: AdminChangeEstadoRequest,
    ) -> AdminUserResponse:
        """Activate or deactivate a user account.

        On deactivation (is_active=False): revokes all refresh tokens (D3).
        On activation (is_active=True): no token changes — user can log in again.

        Args:
            user_id: target user ID
            payload: new is_active value

        Returns:
            Updated user as AdminUserResponse

        Raises:
            NotFoundError: if user does not exist or is soft-deleted
        """
        with UnitOfWork() as uow:
            repo = AdminUserRepository(uow.session)

            user = repo.find_by_id_with_roles(user_id)
            if not user:
                raise NotFoundError(f"Usuario con id={user_id} no encontrado")

            repo.update(user_id, is_active=payload.is_active)

            if not payload.is_active:
                # Revoke all refresh tokens so the user can no longer refresh sessions
                token_repo = RefreshTokenRepository(uow.session)
                token_repo.revoke_all_user_tokens(user_id)

            user = repo.find_by_id_with_roles(user_id)
            response = AdminUserResponse.from_usuario(user)

        return response
