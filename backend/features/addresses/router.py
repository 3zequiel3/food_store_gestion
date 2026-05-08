"""
Delivery addresses API router — 5 endpoints for self-service address management.

All endpoints require authentication via Depends(get_current_user). Ownership
is enforced inside the service via find_by_id_and_user — a non-existent or
foreign address yields 404 (NOT 403) to prevent information leak (D6, RN-DI03).

Endpoints:
  POST   /                          — create address (auto-marks principal if first)
  GET    /                          — list own active addresses (principal first)
  PUT    /{address_id}              — partial update (PATCH semantics, ownership enforced)
  DELETE /{address_id}              — soft delete (ownership enforced)
  PATCH  /{address_id}/predeterminada — atomic swap to set as default (RN-DI02)

Mounted at /api/v1/direcciones by backend/main.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from backend.dependencies import get_uow
from backend.features.addresses.schemas import (
    DireccionCreate,
    DireccionRead,
    DireccionUpdate,
)
from backend.features.addresses.service import AddressService
from backend.features.auth.dependencies import get_current_user
from backend.features.users.models import Usuario
from backend.shared.unit_of_work import UnitOfWork

router = APIRouter()


@router.post("/", response_model=DireccionRead, status_code=status.HTTP_201_CREATED)
async def crear_direccion(
    payload: DireccionCreate,
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> DireccionRead:
    """Create a new delivery address (auto-marks principal if first)."""
    service = AddressService(uow)
    address = service.create(current_user.id, payload)
    uow.commit()
    return DireccionRead.model_validate(address)


@router.get("/", response_model=list[DireccionRead])
async def listar_direcciones(
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> list[DireccionRead]:
    """List the authenticated user's active addresses (principal first)."""
    service = AddressService(uow)
    addresses = service.list_for_user(current_user.id)
    return [DireccionRead.model_validate(a) for a in addresses]


@router.put("/{address_id}", response_model=DireccionRead)
async def actualizar_direccion(
    address_id: int,
    payload: DireccionUpdate,
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> DireccionRead:
    """Partially update an address (PATCH semantics despite verb).

    Ownership: 404 if address doesn't exist OR belongs to another user (D6).
    """
    service = AddressService(uow)
    address = service.update(current_user.id, address_id, payload)
    uow.commit()
    return DireccionRead.model_validate(address)


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_direccion(
    address_id: int,
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> Response:
    """Soft-delete an address.

    Allowed even if it's the principal — per D5, the user is left with no
    principal. Returns 204 on success, 404 if not found or not owned.
    """
    service = AddressService(uow)
    service.delete(current_user.id, address_id)
    uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{address_id}/predeterminada", response_model=DireccionRead)
async def marcar_predeterminada(
    address_id: int,
    current_user: Usuario = Depends(get_current_user),
    uow: UnitOfWork = Depends(get_uow),
) -> DireccionRead:
    """Mark an address as the user's default (atomic swap).

    Unsets es_principal on whatever was principal previously and sets it on
    this one. Both updates committed in the same transaction (RN-DI02).
    """
    service = AddressService(uow)
    address = service.set_principal(current_user.id, address_id)
    uow.commit()
    return DireccionRead.model_validate(address)
