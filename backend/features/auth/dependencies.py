"""
Auth dependencies for FastAPI.

Provides dependency functions for authentication and authorization:
- get_current_user: Extract and validate JWT from request
- require_role: Factory for role-based access control

Design note (D1): get_current_user and get_optional_user use a direct
SQLAlchemy session (via get_session_factory()()) rather than UnitOfWork.
These are read-only middleware dependencies (1 SELECT each), not business
operations. Using UnitOfWork would add unnecessary commit overhead for
a purely read path.
"""

from typing import Optional

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import backend.shared.unit_of_work as _uow_mod

from backend.features.users.models import Usuario
from backend.shared.exceptions import ForbiddenError, UnauthorizedError
from backend.shared.security import decode_access_token

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
) -> Usuario:
    """
    Extract and validate JWT token, return authenticated user.

    READ-ONLY: this dependency opens a session for a single SELECT.
    Do NOT perform writes — no commit is issued. (D1, R2)

    Opens a direct SQLAlchemy session via get_session_factory()() and closes it
    in a finally block. This is an HTTP middleware dependency, not a business
    operation — UnitOfWork would be overhead for a single read.

    Args:
        token: JWT token from Authorization header (via oauth2_scheme)

    Returns:
        Authenticated user entity

    Raises:
        UnauthorizedError: If token is missing, invalid, or expired
    """
    if not token:
        raise UnauthorizedError("Token de autenticación requerido")

    # Decode and validate token
    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedError("Token inválido o expirado")

    # Check token type
    if payload.get("type") != "access":
        raise UnauthorizedError("Tipo de token inválido")

    # Extract user ID
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Token malformado")

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise UnauthorizedError("Token malformado")

    # Open a direct session (D1 — read-only, no UnitOfWork needed).
    # Access get_session_factory via the module reference so that the test
    # monkeypatch (which patches _uow_mod.get_session_factory) is respected.
    session = _uow_mod.get_session_factory()()
    try:
        # selectinload eagerly loads `roles` so the relationship is accessible
        # after session.close() (avoids DetachedInstanceError on user.roles).
        query = select(Usuario).options(selectinload(Usuario.roles)).where(
            Usuario.id == user_id,
            Usuario.eliminado_en.is_(None),
            Usuario.is_active.is_(True),
        )
        user = session.execute(query).scalar_one_or_none()

        if not user:
            raise UnauthorizedError("Usuario no encontrado o inactivo")

        return user
    finally:
        session.close()


def require_role(*required_roles: str):
    """
    Factory for role-based access control dependency.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: Usuario = Depends(require_role("ADMIN")),
        ):
            ...

    Args:
        *required_roles: Role codes that are allowed (e.g., "ADMIN", "STOCK")

    Returns:
        Dependency function that validates user roles
    """

    def role_checker(
        user: Usuario = Depends(get_current_user),
    ) -> Usuario:
        # Get user's role codes
        user_roles = {rol.codigo for rol in user.roles}

        # Check if user has any of the required roles
        if not user_roles.intersection(set(required_roles)):
            raise ForbiddenError(
                f"Se requiere uno de los roles: {', '.join(required_roles)}"
            )

        return user

    return role_checker


def get_optional_user(
    request: Request,
) -> Optional[Usuario]:
    """
    Get current user if authenticated, None otherwise.

    Use this for endpoints that work both authenticated and anonymously.

    READ-ONLY: delegates to get_current_user which opens a direct session.
    No writes are issued. (D1)

    Args:
        request: FastAPI request object

    Returns:
        User if authenticated, None otherwise
    """
    # Extract token from header manually
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Remove "Bearer " prefix

    try:
        return get_current_user(token)
    except UnauthorizedError:
        return None
