"""
Pydantic v2 schemas for the products domain.

Separation:
- ProductoCreate    — body for POST /productos
- ProductoUpdate    — body for PUT /productos/{id} (exclude_unset in service)
- ProductoRead      — flat response (list, create, update, patch)
- CategoriaRead     — nested DTO for product detail (local, no cross-import)
- IngredienteAsociadoRead — nested DTO built from tuple[Ingrediente, bool]
- ProductoDetail    — GET /{id} response (extends ProductoRead)
- PaginatedProductos — GET / response
- PatchDisponibilidad — PATCH /{id}/disponibilidad
- PatchStock          — PATCH /{id}/stock
- AsociarIngrediente  — POST /{id}/ingredientes
- SetCategorias       — PUT /{id}/categorias

Important: precio is typed as Decimal (not float) to preserve NUMERIC(10,2)
precision per RN-CA04. The ORM model has Mapped[float] (smell) but Pydantic
with from_attributes=True correctly casts it via Decimal.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class ProductoCreate(BaseModel):
    """Payload for creating a new product (POST /productos)."""

    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: str | None = None
    precio: Decimal = Field(..., gt=0)
    stock_cantidad: int = Field(0, ge=0)
    disponible: bool = True
    imagen_url: str | None = Field(None, max_length=500)
    # Optional: if provided, replaces the full category set on creation.
    # Pass [] to create with no categories; omit (None) to skip the M:N op.
    categoria_ids: list[int] | None = None


class ProductoUpdate(BaseModel):
    """Payload for partially updating a product (PUT /productos/{id}).

    All fields are optional. The service calls model_dump(exclude_unset=True)
    to distinguish "field not sent" from "field explicitly set to None".
    categoria_ids is intentionally absent — use PUT /{id}/categorias instead.
    """

    nombre: str | None = Field(None, min_length=1, max_length=255)
    descripcion: str | None = None
    precio: Decimal | None = Field(None, gt=0)
    stock_cantidad: int | None = Field(None, ge=0)
    disponible: bool | None = None
    imagen_url: str | None = Field(None, max_length=500)


class PatchDisponibilidad(BaseModel):
    """Payload for toggling product availability (PATCH /{id}/disponibilidad)."""

    disponible: bool


class PatchStock(BaseModel):
    """Payload for setting absolute stock (PATCH /{id}/stock)."""

    stock_cantidad: int = Field(..., ge=0)


class AsociarIngrediente(BaseModel):
    """Payload for associating an ingredient to a product."""

    ingrediente_id: int
    es_removible: bool = False


class SetCategorias(BaseModel):
    """Payload for replacing the full category set of a product."""

    categoria_ids: list[int]


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------


class ProductoRead(BaseModel):
    """Flat product representation — used in list and mutation responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    precio: Decimal
    stock_cantidad: int
    disponible: bool
    imagen_url: str | None
    creado_en: datetime
    actualizado_en: datetime


class CategoriaRead(BaseModel):
    """Nested DTO for category data inside ProductoDetail.

    Defined locally to avoid import coupling with categories.schemas.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    padre_id: int | None


class IngredienteAsociadoRead(BaseModel):
    """Nested DTO for ingredient + removable flag inside ProductoDetail.

    Built manually from tuple[Ingrediente, bool] — no from_attributes needed.
    """

    id: int
    nombre: str
    es_alergeno: bool
    es_removible: bool


class ProductoDetail(ProductoRead):
    """Full product representation with M:N associations — used in GET /{id}."""

    categorias: list[CategoriaRead]
    ingredientes: list[IngredienteAsociadoRead]


class PaginatedProductos(BaseModel):
    """Paginated response for GET /productos."""

    items: list[ProductoRead]
    total: int
    page: int
    limit: int
