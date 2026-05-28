"""
Auth dependencies for FastAPI.

Provides dependency functions for authentication and authorization:
- get_current_user: Extract and validate JWT from auth cookie
- require_role: Factory for role-based access control
"""




from typing import Optional

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import shared.unit_of_work as _uow_mod

from config import settings
from features.users.models import Usuario
from shared.exceptions import ForbiddenError, UnauthorizedError
from shared.security import decode_access_token


def _extract_access_token(request: Request) -> Optional[str]:
    """Read access token from HttpOnly cookie, with Bearer fallback for API tooling."""
    token = request.cookies.get(settings.AUTH_COOKIE_ACCESS_NAME)
    if token:
        return token

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def get_current_user(request: Request) -> Usuario:
    """
    Extract and validate JWT token from cookies, return authenticated user.

    READ-ONLY: opens a direct SQLAlchemy session for a single SELECT and closes
    it in a finally block. Do NOT perform writes — no commit is issued.
    """
    token = _extract_access_token(request)
    if not token:
        raise UnauthorizedError("Token de autenticación requerido")

    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedError("Token inválido o expirado")

    if payload.get("type") != "access":
        raise UnauthorizedError("Tipo de token inválido")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Token malformado")

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise UnauthorizedError("Token malformado")

    session = _uow_mod.get_session_factory()()
    try:
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
    """Factory for role-based access control dependency."""

    def role_checker(user: Usuario = get_current_user) -> Usuario:
        user_roles = {rol.codigo for rol in user.roles}
        if not user_roles.intersection(set(required_roles)):
            raise ForbiddenError(
                f"Se requiere uno de los roles: {', '.join(required_roles)}"
            )
        return user

    # FastAPI needs Depends declared at function definition time.
    from fastapi import Depends

    def dependency(user: Usuario = Depends(get_current_user)) -> Usuario:
        return role_checker(user)

    return dependency


def get_optional_user(request: Request) -> Optional[Usuario]:
    """Get current user if authenticated, None otherwise."""
    try:
        return get_current_user(request)
    except UnauthorizedError:
        return None
