"""
Orders feature router.

D9: Endpoint at /api/v1/pedidos (castellano, consistent with the project's
    domain language — see addresses, productos, categorias, ingredientes).

D12: Requires CLIENT role via Depends(require_role("CLIENT")).
     require_role is defined in backend/features/auth/dependencies.py with
     signature: def require_role(*required_roles: str) -> Callable.
     No new implementation needed.

D3: Service-driven UoW — the router does NOT open a UnitOfWork.
    OrderService.crear_pedido() owns the transaction boundary.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from features.auth.dependencies import get_current_user, require_role
from features.orders.schemas import (
    AvanzarEstadoRequest,
    CrearPedidoRequest,
    PaginatedPedidos,
    PedidoDetalle,
    PedidoListFilters,
    PedidoRead,
    TransicionarRequest,
    TransicionarResponse,
)
from features.orders.service import OrderService
from features.users.models import Usuario

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedPedidos,
    status_code=status.HTTP_200_OK,
    summary="Listar pedidos",
    description=(
        "Lista pedidos con filtros y paginación. "
        "CLIENT ve solo sus propios pedidos; PEDIDOS/ADMIN ven todos. "
        "STOCK recibe 403. Requiere autenticación por cookie."
    ),
)
async def listar_pedidos(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    filtros: Annotated[PedidoListFilters, Depends()],
) -> PaginatedPedidos:
    """
    GET /api/v1/pedidos — role-aware order list.

    Authentication: cookie-backed session required (401 if missing/invalid).
    Authorization: dynamic RBAC in OrderService.listar_pedidos().
    HTTP mapping (global exception handler):
      ForbiddenError → 403
    """
    service = OrderService()
    return service.listar_pedidos(current_user, filtros)


@router.get(
    "/{pedido_id}",
    response_model=PedidoDetalle,
    status_code=status.HTTP_200_OK,
    summary="Detalle de pedido",
    description=(
        "Retorna el detalle completo de un pedido (items, historial, pagos). "
        "CLIENT solo puede ver sus propios pedidos (anti-leak 404 si es ajeno). "
        "PEDIDOS/ADMIN ven cualquier pedido. STOCK recibe 403."
    ),
)
async def get_pedido_detalle(
    pedido_id: int,
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> PedidoDetalle:
    """
    GET /api/v1/pedidos/{pedido_id} — role-aware order detail.

    Authentication: cookie-backed session required (401 if missing/invalid).
    Authorization: dynamic RBAC in OrderService.get_pedido_detalle().
    HTTP mapping (global exception handler):
      NotFoundError → 404  (pedido inexistente O ajeno para CLIENT — anti-leak D2)
      ForbiddenError → 403
    """
    service = OrderService()
    return service.get_pedido_detalle(current_user, pedido_id)


@router.post(
    "/",
    response_model=PedidoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido",
    description=(
        "Crea un nuevo pedido atómico a partir del carrito del cliente. "
        "Valida stock (SELECT FOR UPDATE), forma de pago, ownership de dirección "
        "y calcula el total con Decimal precision. "
        "Requiere rol CLIENT."
    ),
)
async def crear_pedido(
    payload: CrearPedidoRequest,
    current_user: Usuario = Depends(require_role("CLIENT")),
) -> PedidoRead:
    """
    POST /api/v1/pedidos — create a new order (spec §7.1, 9-step UoW).

    Authentication: cookie-backed session required (401 if missing/invalid).
    Authorization: CLIENT role required (403 if user lacks CLIENT role).
    """
    service = OrderService()
    pedido = service.crear_pedido(current_user.id, payload)
    return PedidoRead.model_validate(pedido)


@router.patch(
    "/{pedido_id}/estado",
    response_model=PedidoRead,
    status_code=status.HTTP_200_OK,
    summary="Avanzar estado del pedido",
    description=(
        "Ejecuta una transición de estado manual sobre un pedido. "
        "Valida FSM, RBAC por transición y ownership (CLIENT solo sus propios pedidos). "
        "CONFIRMADO no es un valor aceptado — esa transición es exclusiva del webhook de pago. "
        "Requiere autenticación por cookie."
    ),
)
async def avanzar_estado(
    pedido_id: int,
    payload: AvanzarEstadoRequest,
    current_user: Usuario = Depends(get_current_user),
) -> PedidoRead:
    """
    PATCH /api/v1/pedidos/{pedido_id}/estado

    Authentication: cookie-backed session required (401 if missing/invalid).
    Authorization: RBAC dynamic — validated inside OrderService.avanzar_estado().

    HTTP mapping (global exception handler):
      NotFoundError → 404
      ForbiddenError → 403
      InvalidStateTransitionError → 409
      BusinessRuleError → 422
    """
    service = OrderService()
    pedido = service.avanzar_estado(
        user_id=current_user.id,
        pedido_id=pedido_id,
        nuevo_estado=payload.nuevo_estado,
        motivo=payload.motivo,
    )
    return PedidoRead.model_validate(pedido)


@router.post(
    "/{pedido_id}/transicionar",
    response_model=TransicionarResponse,
    status_code=status.HTTP_200_OK,
    summary="Transicionar estado del pedido",
    description=(
        "Ejecuta una transición de estado genérica sobre un pedido. "
        "Acepta cualquier estado destino válido según la FSM (incluye CANCELADO_ADMIN, CANCELADO_CLIENTE). "
        "Valida FSM, RBAC por transición y ownership (CLIENT solo sus propios pedidos). "
        "Requiere autenticación por cookie."
    ),
)
async def transicionar_estado(
    pedido_id: int,
    payload: TransicionarRequest,
    current_user: Usuario = Depends(get_current_user),
) -> TransicionarResponse:
    """
    POST /api/v1/pedidos/{pedido_id}/transicionar

    Authentication: cookie-backed session required (401 if missing/invalid).
    Authorization: RBAC dynamic — validated inside OrderService.transicionar_pedido().

    HTTP mapping (global exception handler):
      NotFoundError → 404
      ForbiddenError → 403
      InvalidStateTransitionError → 409
      BusinessRuleError → 422
    """
    service = OrderService()
    pedido, estado_anterior, nuevo_historial = service.transicionar_pedido(
        user_id=current_user.id,
        pedido_id=pedido_id,
        estado_codigo_destino=payload.estado_codigo_destino,
        motivo=payload.motivo,
    )

    return TransicionarResponse(
        pedido_id=pedido.id,
        estado_anterior=estado_anterior,
        estado_nuevo=pedido.estado_codigo,
        historial=[nuevo_historial],
    )
