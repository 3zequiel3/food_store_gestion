"""
Admin user management router.

All endpoints require ADMIN role.
Prefix (registered in main.py): /api/v1/admin/usuarios

Routes:
  GET    /                  — paginated listing with optional search and role filter
  POST   /                  — create a new user with email, password, and roles
  PUT    /{id}              — update personal data (nombre, apellido, telefono)
  PATCH  /{id}/rol          — replace roles (atomic, revokes refresh tokens)
  PATCH  /{id}/estado       — activate/deactivate account (revokes tokens on deactivation)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from features.admin_users.schemas import (
    AdminChangeEstadoRequest,
    AdminChangeRolRequest,
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    AdminUserListResponse,
    AdminUserResponse,
)
from features.admin_users.service import AdminUserService
from features.auth.dependencies import require_role

router = APIRouter()

_service = AdminUserService()


@router.get(
    "",
    response_model=AdminUserListResponse,
    summary="Listar usuarios (Admin)",
    description=(
        "Retorna todos los usuarios (activos e inactivos, no soft-deleted) "
        "con paginación y filtros opcionales de búsqueda y rol. "
        "Requiere rol ADMIN."
    ),
)
def list_usuarios(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    rol: Optional[str] = None,
    _current_user=Depends(require_role("ADMIN")),
) -> AdminUserListResponse:
    """GET /admin/usuarios — paginated user list."""
    items, total = _service.list_usuarios(
        page=page,
        page_size=page_size,
        search=search,
        rol_codigo=rol,
    )
    return AdminUserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=AdminUserResponse,
    status_code=201,
    summary="Crear un nuevo usuario (Admin)",
    description=(
        "Crea un usuario con email, contraseña, nombre, apellido, teléfono opcional "
        "y una lista de roles (mínimo 1). "
        "Los roles válidos para este formulario son ADMIN, CLIENT y COCINA. "
        "HTTP 409 si el email ya existe. "
        "HTTP 422 si algún código de rol no existe o la lista está vacía. "
        "Requiere rol ADMIN."
    ),
)
def create_usuario(
    payload: AdminCreateUserRequest,
    _current_user=Depends(require_role("ADMIN")),
) -> AdminUserResponse:
    """POST /admin/usuarios — create a new user."""
    return _service.create_usuario(payload)


@router.put(
    "/{user_id}",
    response_model=AdminUserResponse,
    summary="Actualizar datos personales de un usuario (Admin)",
    description=(
        "Actualiza nombre, apellido y/o telefono de cualquier usuario. "
        "Email, contraseña y roles tienen endpoints dedicados. "
        "Requiere rol ADMIN."
    ),
)
def update_usuario(
    user_id: int,
    payload: AdminUpdateUserRequest,
    _current_user=Depends(require_role("ADMIN")),
) -> AdminUserResponse:
    """PUT /admin/usuarios/{id} — update personal data."""
    return _service.update_datos_personales(user_id, payload)


@router.patch(
    "/{user_id}/rol",
    response_model=AdminUserResponse,
    summary="Cambiar roles de un usuario (Admin)",
    description=(
        "Reemplaza el conjunto completo de roles del usuario. "
        "Invalida todos los refresh tokens del usuario modificado. "
        "HTTP 409 si la operación dejaría al sistema sin ningún ADMIN activo. "
        "HTTP 422 si algún código de rol no existe. "
        "Requiere rol ADMIN."
    ),
)
def change_rol(
    user_id: int,
    payload: AdminChangeRolRequest,
    _current_user=Depends(require_role("ADMIN")),
) -> AdminUserResponse:
    """PATCH /admin/usuarios/{id}/rol — replace roles."""
    return _service.change_rol(user_id, payload)


@router.patch(
    "/{user_id}/estado",
    response_model=AdminUserResponse,
    summary="Activar o desactivar una cuenta (Admin)",
    description=(
        "Cambia is_active del usuario. "
        "Al desactivar: revoca todos los refresh tokens del usuario. "
        "Al activar: el usuario puede volver a autenticarse. "
        "Requiere rol ADMIN."
    ),
)
def change_estado(
    user_id: int,
    payload: AdminChangeEstadoRequest,
    _current_user=Depends(require_role("ADMIN")),
) -> AdminUserResponse:
    """PATCH /admin/usuarios/{id}/estado — activate/deactivate."""
    return _service.change_estado(user_id, payload)
