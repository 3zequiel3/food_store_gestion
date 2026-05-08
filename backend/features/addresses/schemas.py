"""
Pydantic v2 schemas for delivery addresses CRUD.
Three schemas: DireccionCreate, DireccionUpdate, DireccionRead.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DireccionCreate(BaseModel):
    """Create payload. `es_principal` and `usuario_id` are NEVER accepted (anti-smuggling, D3/D6)."""

    calle: str = Field(..., min_length=1, max_length=255)
    numero: str = Field(..., min_length=1, max_length=20)
    piso_depto: str | None = Field(None, max_length=50)
    ciudad: str = Field(..., min_length=1, max_length=100)
    codigo_postal: str = Field(..., min_length=1, max_length=20)
    referencia: str | None = Field(None, max_length=500)

    model_config = {"extra": "forbid"}


class DireccionUpdate(BaseModel):
    """All fields optional. The service uses `model_dump(exclude_unset=True)`.
    `es_principal` is NEVER accepted (use PATCH /predeterminada instead)."""

    calle: str | None = Field(None, min_length=1, max_length=255)
    numero: str | None = Field(None, min_length=1, max_length=20)
    piso_depto: str | None = Field(None, max_length=50)
    ciudad: str | None = Field(None, min_length=1, max_length=100)
    codigo_postal: str | None = Field(None, min_length=1, max_length=20)
    referencia: str | None = Field(None, max_length=500)

    model_config = {"extra": "forbid"}


class DireccionRead(BaseModel):
    """Public representation. `usuario_id` is aliased from `user_id` to match spec naming."""

    id: int
    usuario_id: int = Field(..., validation_alias="user_id")
    calle: str
    numero: str
    piso_depto: str | None
    ciudad: str
    codigo_postal: str
    referencia: str | None
    es_principal: bool
    creado_en: datetime
    actualizado_en: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
