"""
Pydantic v2 schemas for admin user management endpoints.

Request schemas:
- AdminUpdateUserRequest  — editar datos personales (nombre, apellido, telefono)
- AdminChangeRolRequest   — reemplazar conjunto de roles de un usuario
- AdminChangeEstadoRequest — activar/desactivar un usuario

Response schemas:
- AdminUserResponse       — datos completos de un usuario (incluyendo is_active y roles)
- AdminUserListResponse   — listado paginado de AdminUserResponse
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class AdminUserResponse(BaseModel):
    """Full public view of a user for admin operations.

    Includes is_active (intentionally — admins need to see account status).
    Excludes password_hash and eliminado_en.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre: str
    apellido: str
    telefono: Optional[str]
    is_active: bool
    roles: List[str]
    creado_en: Optional[datetime]
    actualizado_en: Optional[datetime]

    @classmethod
    def from_usuario(cls, usuario) -> "AdminUserResponse":
        """Build response from a Usuario ORM instance with eager-loaded roles."""
        return cls(
            id=usuario.id,
            email=usuario.email,
            nombre=usuario.nombre,
            apellido=usuario.apellido,
            telefono=usuario.telefono,
            is_active=usuario.is_active,
            roles=[rol.codigo for rol in usuario.roles],
            creado_en=usuario.creado_en,
            actualizado_en=usuario.actualizado_en,
        )


class AdminUserListResponse(BaseModel):
    """Paginated list of users for admin listing endpoint."""

    model_config = ConfigDict(from_attributes=True)

    items: List[AdminUserResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AdminUpdateUserRequest(BaseModel):
    """Update personal data of any user (admin operation).

    Only nombre, apellido, telefono are editable via this endpoint.
    Email, password, and roles have dedicated endpoints.
    extra='forbid' prevents email/password_hash smuggling.
    """

    model_config = ConfigDict(extra="forbid")

    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    apellido: Optional[str] = Field(None, min_length=2, max_length=100)
    telefono: Optional[str] = Field(None)


class AdminCreateUserRequest(BaseModel):
    """Create a new user from the admin panel.

    All fields required except telefono.
    roles must have at least one code; extra='forbid' prevents smuggling.
    Role codes are uppercase (ADMIN, CLIENT, COCINA) per RN-71.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=8)
    nombre: str = Field(..., min_length=2, max_length=80)
    apellido: str = Field(..., min_length=2, max_length=80)
    telefono: Optional[str] = None
    roles: List[str] = Field(..., min_length=1)


class AdminChangeRolRequest(BaseModel):
    """Replace the full set of roles for a user.

    roles: list of role codes (e.g. ["ADMIN", "STOCK"]).
    At least one role is required — users cannot have zero roles.
    """

    model_config = ConfigDict(extra="forbid")

    roles: List[str] = Field(..., min_length=1)


class AdminChangeEstadoRequest(BaseModel):
    """Activate or deactivate a user account."""

    model_config = ConfigDict(extra="forbid")

    is_active: bool
