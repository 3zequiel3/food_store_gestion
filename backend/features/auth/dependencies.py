"""
Auth dependencies for FastAPI.

Provides dependency functions for authentication and authorization:
- get_current_user: Extract and validate JWT from request
- require_role: Factory for role-based access control
"""

from typing import Optional

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.features.users.models import Usuario
from backend.shared.database import get_db
from backend.shared.exceptions import ForbiddenError, UnauthorizedError
from backend.shared.security import decode_access_token

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Extract and validate JWT token, return authenticated user.

    Args:
        token: JWT token from Authorization header
        db: Database session

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

    # Find user
    from sqlalchemy import select

    query = select(Usuario).where(
        Usuario.id == user_id,
        Usuario.eliminado_en.is_(None),
        Usuario.is_active.is_(True),
    )
    user = db.execute(query).scalar_one_or_none()

    if not user:
        raise UnauthorizedError("Usuario no encontrado o inactivo")

    return user


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

    async def role_checker(
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


async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[Usuario]:
    """
    Get current user if authenticated, None otherwise.

    Use this for endpoints that work both authenticated and anonymously.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        User if authenticated, None otherwise
    """
    # Extract token from header manually
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Remove "Bearer " prefix

    try:
        return await get_current_user(token, db)
    except UnauthorizedError:
        return None
