## Context

El feature `backend/features/payments/` existe como skeleton desde `database-schema-seed`: el modelo `Pago` está completo, el router tiene stubs y `service.py`/`repository.py` están vacíos. La integración con MercadoPago es cero. Los pedidos se crean en estado `PENDIENTE` y no tienen mecanismo de avance.

El SDK oficial `mercadopago` ya está en `requirements.txt`. La tabla `payments` ya existe en la BD (migration `20260428_0001`). El router está registrado en `main.py` bajo `/api/v1/pagos`.

## Goals / Non-Goals

**Goals:**
- Implementar `POST /api/v1/pagos` — crear preferencia en MP y registrar `Pago` con idempotency_key
- Implementar `POST /api/v1/pagos/webhook/mercadopago` — IPN handler idempotente con verificación real via API MP
- Implementar `GET /api/v1/pagos/pedido/{pedido_id}` — estado del último pago de un pedido propio
- Transición automática `PENDIENTE → CONFIRMADO` al recibir webhook con status `approved`
- Tests de integración para los 3 endpoints

**Non-Goals:**
- Tokenización de tarjeta (SDK JS de MercadoPago.js — es Fase B, frontend)
- FSM completa del pedido (#16 order-state-machine-fsm)
- Decremento de stock en confirmación (se hace en #16; en este change la transición de estado se registra pero el stock no cambia todavía — **ver D7**)
- Integración con notificaciones push al cliente

## Decisions

### D1 — SDK oficial vs HTTP directo

**Decisión**: usar `mercadopago` SDK Python en `PaymentService`.

**Alternativa**: `httpx` directo contra la REST API de MP.

**Rationale**: el SDK ya está instalado, maneja autenticación, reintentos y wrapping de errores. El cliente `mercadopago.SDK(access_token)` devuelve respuestas uniformes. No hay ventaja en HTTP directo para este scope.

---

### D2 — Idempotency key: quién lo genera, cuándo

**Decisión**: el backend genera el `idempotency_key` (UUID4) al momento de crear el registro `Pago`, antes de llamar a la API de MP. Se pasa como header `X-Idempotency-Key` a la Orders API de MP.

**Alternativa**: que el frontend lo genere y lo envíe en el body. Agrega complejidad al cliente y es una responsabilidad innecesaria.

**Rationale**: RN-PA02 solo requiere unicidad y que duplicados se ignoren — generar en backend garantiza eso sin coordinar con el cliente.

---

### D3 — external_reference: cómo vincular la notificación al pedido

**Decisión**: `external_reference = str(pedido_id)`. Se envía al crear la preferencia en MP y MP lo devuelve en el webhook.

**Rationale**: RN-PA09. El `pedido_id` es suficiente para lookupear el pedido en BD. Alternativa (mp_order_id como FK) requiere una segunda llamada a la API en el webhook solo para obtener el pedido_id.

---

### D4 — Procesamiento del webhook: síncrono vs tarea de background

**Decisión**: el webhook responde `HTTP 200` inmediatamente y luego procesa **sincrónicamente** dentro del mismo request (FastAPI await).

**Alternativa**: encolar en Celery/ARQ y procesar en background worker. Más robusto pero agrega infra.

**Rationale**: RN-PA03 requiere 200 inmediato; con `async def` en FastAPI el 200 se envía antes de que MP cierre la conexión. Para el MVP con carga baja, una query a la API de MP + 1-2 writes a BD es suficientemente rápido. Si hay timeout real, se puede agregar ARQ en deuda técnica.

**Trade-off aceptado**: si la llamada de verificación a la API de MP tarda >5s, MP puede reintentar y recibir el 200 igualmente (idempotencia resuelve los duplicados).

---

### D5 — Verificación del estado: siempre re-consultar a MP

**Decisión**: el webhook NUNCA confía en los datos del body del IPN. Siempre llama a `mp_sdk.payment().get(payment_id)` para obtener el estado real.

**Rationale**: RN-PA04. Los webhooks de MP pueden llegar con datos incompletos o ser falsificados. La fuente de verdad es la API de MP.

---

### D6 — Idempotencia del webhook: cómo detectar duplicados

**Decisión**: antes de procesar, verificar si ya existe un `Pago` con el mismo `mp_payment_id` en estado `approved`. Si existe, retornar 200 sin hacer nada.

**Alternativa**: tabla de webhook_events con hash del payload. Más robusto pero overkill.

**Rationale**: RN-PA02. `mp_payment_id` (ID del pago en MP) es el identificador único de un pago. Si llegó y ya fue procesado como `approved`, no hay que hacer nada.

---

### D7 — Transición PENDIENTE→CONFIRMADO: dónde vive la lógica

**Decisión**: `PaymentService.procesar_webhook()` llama a `OrderService.transicionar_estado(pedido_id, "PENDIENTE", "CONFIRMADO", actor_id=SYSTEM_USER_ID)`. La FSM vive en `OrderService`, no en `PaymentService`.

**Alternativa**: `PaymentService` hace el update de estado directo en BD. Viola separación de concerns.

**Rationale**: `OrderService` es dueño del estado del pedido. El decremento de stock se agregará en #16 cuando se implemente la FSM completa — por eso `transicionar_estado` en este change SOLO actualiza `orders.estado_codigo` y registra en `order_state_history`, sin tocar stock. El método ya existirá cuando #16 lo extienda.

**Decisión sobre SYSTEM_USER_ID**: usar `cambiado_por_id = None` (actor SISTEMA) en `order_state_history` — consistente con RN-FS09 que permite actor nulo para transiciones automáticas.

---

### D8 — Ownership validation para crear pago

**Decisión**: `POST /api/v1/pagos` requiere rol CLIENT y verifica que el `pedido_id` pertenezca al usuario autenticado. Si el pedido no existe o no es del usuario: `403 Forbidden`.

**Rationale**: un cliente no puede iniciar el pago de un pedido ajeno. Gestor/Admin no inician pagos — eso es responsabilidad del cliente.

---

### D9 — Consultar estado de pago: endpoint propio vs enriquecer GET /pedidos/{id}

**Decisión**: `GET /api/v1/pagos/pedido/{pedido_id}` en el router de pagos. Retorna el último `Pago` asociado al pedido.

**Alternativa**: enriquecer `GET /api/v1/pedidos/{id}` con campo `ultimo_pago`. Convierte el endpoint de pedidos en un agregado que mezcla concerns.

**Rationale**: separación de concerns. El frontend puede hacer dos calls cuando necesite ambos. `GET /pedidos/{id}` ya tiene su contrato definido en order-creation-backend.

---

### D10 — Esquema de re-intento

**Decisión**: el endpoint `POST /api/v1/pagos` acepta reintentos para pedidos PENDIENTE con pagos previos rechazados. Valida que no exista ya un `Pago` con `mp_status in ("approved", "pending", "in_process")` antes de crear uno nuevo.

**Rationale**: RN-PA08 (1:N Pedido→Pago). Si el pago anterior está `approved` o `pending`, no se debe crear otro. Si está `rejected` o `cancelled`, sí se puede reintentar.

## Risks / Trade-offs

- **MP Sandbox timeout en webhook**: el handler verifica la API de MP síncronamente; si la sandbox está lenta, el 200 puede tardar y MP reintentará. Mitigación: idempotencia en D6 garantiza que el reintento no duplica.
- **Firma del webhook no verificada**: MP recomienda verificar la firma HMAC del header `x-signature`. Queda como deuda técnica documentada — para el MVP del integrador, validar solo la existencia del pedido y verificar con la API es suficiente (RN-PA04 cubre el riesgo real de fraude).
- **SYSTEM_USER_ID = None**: si en el futuro la FK `cambiado_por_id` se vuelve NOT NULL, habrá que introducir un usuario "SISTEMA" en seed. Por ahora la columna es nullable.

## Migration Plan

No hay cambios de schema — la tabla `payments` ya existe desde `database-schema-seed`. No se necesita nueva migration de Alembic.

## Open Questions

- ¿El `access_token` de MercadoPago se configura via variable de entorno `MP_ACCESS_TOKEN`? **Asumido: sí**, debe existir en `.env` y en `backend/core/config.py`.
- ¿El endpoint de webhook necesita autenticación? **No** — MP no envía tokens de usuario; la autenticidad se verifica via re-consulta a la API (D5).
