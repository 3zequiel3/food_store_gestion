## 1. Config — Agregar MP_ACCESS_TOKEN a Settings

- [x] 1.1 Agregar campo `MP_ACCESS_TOKEN: str` a `Settings` en `backend/config.py` con `Field(default="TEST-...", description="MercadoPago access token")`
- [x] 1.2 Agregar `MP_ACCESS_TOKEN=TEST-<tu-token>` al archivo `backend/.env` (o `.env.example` si existe)
- [x] 1.3 Verificar que `settings.MP_ACCESS_TOKEN` está disponible importando desde `backend.config`

## 2. Schemas — DTOs del feature payments

- [x] 2.1 Implementar `PagoCreate` en `backend/features/payments/schemas.py`: campos `pedido_id: int`
- [x] 2.2 Implementar `PagoRead` en `backend/features/payments/schemas.py`: campos `id`, `pedido_id`, `monto` (Decimal), `forma_pago_codigo`, `mp_payment_id` (opcional), `mp_status` (opcional), `idempotency_key`, `creado_en`, `actualizado_en`, más `init_point: Optional[str]` para la respuesta de creación
- [x] 2.3 Implementar `WebhookPayload` en `backend/features/payments/schemas.py`: campos `action: str`, `data: dict` con al menos `id: str` (ID del pago en MP)
- [x] 2.4 Agregar `model_config = ConfigDict(from_attributes=True)` a todos los schemas de lectura

## 3. Repository — PaymentRepository

- [x] 3.1 Crear clase `PaymentRepository` en `backend/features/payments/repository.py` que extienda `BaseRepository` (o el patrón existente) con sesión inyectada
- [x] 3.2 Implementar `create(pedido_id, monto, forma_pago_codigo, idempotency_key) -> Pago`: crea y hace flush del registro (NO commit — el service maneja UoW)
- [x] 3.3 Implementar `find_by_mp_payment_id(mp_payment_id: str) -> Optional[Pago]`
- [x] 3.4 Implementar `find_latest_by_pedido_id(pedido_id: int) -> Optional[Pago]`: retorna el pago más reciente (ORDER BY creado_en DESC LIMIT 1)
- [x] 3.5 Implementar `find_active_by_pedido_id(pedido_id: int) -> Optional[Pago]`: retorna pago con `mp_status IN ("approved", "pending", "in_process")` para validar reintentos
- [x] 3.6 Implementar `update_mp_fields(pago: Pago, mp_payment_id: str, mp_status: str)`: actualiza campos MP en el objeto (flush en UoW)

## 4. OrderService — Método transicionar_estado

- [x] 4.1 Agregar `InvalidStateTransitionError` a `backend/shared/exceptions.py` (HTTP 409 Conflict)
- [x] 4.2 Agregar método `transicionar_estado(pedido_id: int, estado_anterior: str, estado_nuevo: str, actor_id: Optional[int] = None) -> Pedido` a `OrderService` en `backend/features/orders/service.py`
- [x] 4.3 Dentro de `transicionar_estado`: abrir `UnitOfWork`, registrar `OrderRepository`, buscar pedido por `pedido_id` (NotFoundError si no existe)
- [x] 4.4 Validar que `pedido.estado_codigo == estado_anterior`; si no, lanzar `InvalidStateTransitionError` con mensaje claro
- [x] 4.5 Actualizar `pedido.estado_codigo = estado_nuevo` y hacer flush
- [x] 4.6 Insertar fila en `HistorialEstadoPedido` con `estado_anterior_codigo`, `estado_nuevo_codigo`, `cambiado_por_id=actor_id` (puede ser None = SISTEMA)
- [x] 4.7 Retornar el pedido actualizado (UoW commit en `__exit__`)

## 5. PaymentService — Lógica de negocio

- [x] 5.1 Crear clase `PaymentService` en `backend/features/payments/service.py` con `__init__(self) -> None`
- [x] 5.2 Implementar método `crear_preferencia(user_id: int, pedido_id: int) -> tuple[Pago, str]` que:
  - [x] 5.2a Abre UoW, registra `PaymentRepository` y `OrderRepository`
  - [x] 5.2b Busca el pedido; lanza `NotFoundError` si no existe o `ForbiddenError` si no pertenece al user
  - [x] 5.2c Valida que `pedido.estado_codigo == "PENDIENTE"`; lanza `BusinessRuleError` (409) si no
  - [x] 5.2d Llama a `uow.payments.find_active_by_pedido_id(pedido_id)`; lanza `BusinessRuleError` (409) si existe pago activo
  - [x] 5.2e Genera `idempotency_key = str(uuid.uuid4())`
  - [x] 5.2f Llama al SDK de MercadoPago: `sdk.preference().create({"items": [...], "external_reference": str(pedido_id), ...})` con el token de `settings.MP_ACCESS_TOKEN`
  - [x] 5.2g Crea el `Pago` vía `uow.payments.create(...)` con `mp_status="pending"` y guarda `mp_payment_id` de la respuesta si viene
  - [x] 5.2h Retorna `(pago, init_point)` donde `init_point` viene de `response["response"]["init_point"]`
- [x] 5.3 Implementar método `procesar_webhook(payload: WebhookPayload) -> None` que:
  - [x] 5.3a Extrae `mp_payment_id = payload.data.get("id")`; retorna silenciosamente si está vacío
  - [x] 5.3b Abre UoW, registra `PaymentRepository`
  - [x] 5.3c Busca `Pago` por `mp_payment_id`; si no existe, retorna silenciosamente (200)
  - [x] 5.3d Verifica idempotencia: si `pago.mp_status == "approved"`, retorna silenciosamente
  - [x] 5.3e Consulta la API real de MP: `sdk.payment().get(mp_payment_id)` para obtener el estado verificado
  - [x] 5.3f Actualiza `pago.mp_status` con el estado verificado vía `uow.payments.update_mp_fields(...)`
  - [x] 5.3g Si el estado verificado es `"approved"`: llama a `OrderService().transicionar_estado(pedido_id, "PENDIENTE", "CONFIRMADO", actor_id=None)` (fuera de la UoW de payments para evitar nested sessions)
  - [x] 5.3h UoW de payments hace commit (`__exit__`)
- [x] 5.4 Implementar método `obtener_pago_por_pedido(user_id: int, pedido_id: int) -> Pago` que:
  - [x] 5.4a Abre UoW, registra `PaymentRepository` y `OrderRepository`
  - [x] 5.4b Verifica ownership del pedido; lanza `ForbiddenError` si no pertenece al user
  - [x] 5.4c Llama a `uow.payments.find_latest_by_pedido_id(pedido_id)`; lanza `NotFoundError` si no hay pago

## 6. Router — Reemplazar stubs con endpoints reales

- [x] 6.1 Reemplazar `POST /` stub por `POST /api/v1/pagos` en `backend/features/payments/router.py`:
  - Parámetros: `body: PagoCreate`, `current_user = Depends(require_role("CLIENT"))`
  - Llama a `PaymentService().crear_preferencia(user_id, pedido_id)`
  - Retorna `201` con `PagoRead` (incluyendo `init_point`)
- [x] 6.2 Reemplazar `POST /webhook/mercadopago` stub por implementación real:
  - Sin autenticación de usuario (`router.post("/webhook/mercadopago")`)
  - Parámetros: `payload: WebhookPayload`
  - Llama a `PaymentService().procesar_webhook(payload)` en background (o síncrono)
  - Retorna `200 OK` inmediatamente (antes o durante el procesamiento)
- [x] 6.3 Agregar `GET /pedido/{pedido_id}` en `backend/features/payments/router.py`:
  - Parámetros: `pedido_id: int`, `current_user = Depends(require_role("CLIENT"))`
  - Llama a `PaymentService().obtener_pago_por_pedido(user_id, pedido_id)`
  - Retorna `200` con `PagoRead`
- [x] 6.4 Eliminar el stub `GET /{payment_id}` del router (no está en la spec)
- [x] 6.5 Verificar que el router sigue registrado en `main.py` bajo `/api/v1/pagos` y que el prefijo no genera conflictos de ruta con los nuevos endpoints

## 7. Tests de integración

- [x] 7.1 Crear archivo `backend/tests/features/test_payments.py` con fixtures de cliente autenticado y pedido PENDIENTE existente
- [x] 7.2 Test: `POST /api/v1/pagos` con pedido válido → 201 + `PagoRead` con `init_point` (mockear SDK de MP)
- [x] 7.3 Test: `POST /api/v1/pagos` con pedido de otro usuario → 403
- [x] 7.4 Test: `POST /api/v1/pagos` con pedido en estado CONFIRMADO → 409
- [x] 7.5 Test: `POST /api/v1/pagos` reintento con pago previo `approved` → 409
- [x] 7.6 Test: `POST /api/v1/pagos` reintento con pago previo `rejected` → 201 + nuevo `idempotency_key`
- [x] 7.7 Test: `POST /api/v1/pagos/webhook/mercadopago` con status `approved` → 200 + pedido pasa a CONFIRMADO + `order_state_history` tiene fila correcta
- [x] 7.8 Test: webhook `rejected` → 200 + pedido sigue PENDIENTE + `pago.mp_status = "rejected"`
- [x] 7.9 Test: webhook duplicado (mismo `mp_payment_id`, ya `approved`) → 200 + sin nueva fila en `order_state_history`
- [x] 7.10 Test: `GET /api/v1/pagos/pedido/{id}` con pago existente → 200 + `PagoRead`
- [x] 7.11 Test: `GET /api/v1/pagos/pedido/{id}` sin pagos → 404
- [x] 7.12 Test: `GET /api/v1/pagos/pedido/{id}` pedido ajeno → 403
- [x] 7.13 Ejecutar `pytest backend/tests/features/test_payments.py -v` y verificar que todos los tests pasan
- [x] 7.14 Ejecutar la suite completa `pytest backend/tests/ -v` y verificar que no hay regresiones
