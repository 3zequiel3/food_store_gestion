"""
User profile schemas (Pydantic v2).

Defines request/response models for the self-service profile endpoints:
- ProfileResponse  — GET /me, PATCH /me response (whitelist: NEVER password_hash)
- UpdateProfileRequest — PATCH /me body (all fields optional, extra=forbid)
- ChangePasswordRequest — POST /me/password body (extra=forbid)
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ProfileResponse(BaseModel):
    """Full user profile response.

    Whitelist of safe fields — password_hash, is_active, and eliminado_en
    are deliberately excluded (not opt-out, they simply aren't declared).
    """

    id: int
    email: EmailStr
    nombre: str
    apellido: str
    telefono: str | None
    roles: list[str]          # códigos: ["CLIENT"], ["CLIENT", "ADMIN"], etc.
    creado_en: datetime
    actualizado_en: datetime

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    """Body for PATCH /me.

    All fields optional — the service uses model_dump(exclude_unset=True) to
    distinguish 'not sent' from 'explicit null'.  email/password/roles are
    never accepted here (extra='forbid' returns 422 for unknown fields).
    """

    nombre: str | None = Field(None, min_length=2, max_length=80)
    apellido: str | None = Field(None, min_length=2, max_length=80)
    telefono: str | None = Field(
        None,
        pattern=r"^\+?[\d\s\-\(\)]{6,30}$",
        description=(
            "Formato libre internacional. "
            "Permite +, dígitos, espacios, guiones y paréntesis."
        ),
    )

    model_config = {"extra": "forbid"}


class ChangePasswordRequest(BaseModel):
    """Body for POST /me/password.

    password_actual: any non-empty string (verify_password does the real check).
    password_nuevo: min 8, max 128 chars (bcrypt truncates at 72 bytes anyway;
    max=128 prevents payload-abuse).
    """

    password_actual: str = Field(..., min_length=1)
    password_nuevo: str = Field(..., min_length=8, max_length=128)

    model_config = {"extra": "forbid"}
