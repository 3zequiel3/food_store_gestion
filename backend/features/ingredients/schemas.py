"""
Pydantic v2 schemas for Ingredient CRUD.

Four schemas cover the full API surface:
- IngredienteCreate: input for POST /
- IngredienteUpdate: input for PUT /{id}
- IngredienteRead: output for POST, PUT, and GET /{id}
- PaginatedIngredientes: output for GET / (paginated list wrapper)
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ── Request schemas ───────────────────────────────────────────────────────


class IngredienteCreate(BaseModel):
    """Payload for creating a new ingredient."""

    nombre: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["Tomate"],
    )
    es_alergeno: bool = Field(
        False,
        description="Whether this ingredient is an allergen.",
        examples=[False],
    )
    es_removible: bool = Field(
        False,
        description="Whether this ingredient is removable by the client when ordering.",
        examples=[False],
    )


class IngredienteUpdate(BaseModel):
    """Payload for partially updating an existing ingredient.

    All fields are optional. The service MUST use
    ``model_dump(exclude_unset=True)`` to distinguish "not sent" from
    "explicitly set" — this is CRITICAL for ``es_alergeno`` and
    ``es_removible``: if the client sends only ``{"nombre": "X"}``,
    neither boolean must be overwritten to its default ``None`` / ``False``.
    """

    nombre: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        examples=["Tomate Cherry"],
    )
    es_alergeno: bool | None = Field(
        None,
        description="Whether this ingredient is an allergen.",
        examples=[True],
    )
    es_removible: bool | None = Field(
        None,
        description="Whether this ingredient is removable by the client when ordering.",
        examples=[True],
    )


# ── Response schemas ──────────────────────────────────────────────────────


class IngredienteRead(BaseModel):
    """Public representation of a single ingredient."""

    id: int
    nombre: str
    es_alergeno: bool
    es_removible: bool
    creado_en: datetime
    actualizado_en: datetime

    model_config = {"from_attributes": True}


class PaginatedIngredientes(BaseModel):
    """Paginated list response for GET /api/v1/ingredientes.

    ``items`` contains the page of results; ``total`` is the count across
    all pages (after applying any active filters); ``page`` and ``limit``
    echo back the query params.
    """

    items: list[IngredienteRead]
    total: int
    page: int
    limit: int
