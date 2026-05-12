## ADDED Requirements

### Requirement: Transición automática PENDIENTE → CONFIRMADO por pago aprobado

El sistema SHALL transicionar el estado de un pedido de `PENDIENTE` a `CONFIRMADO` exclusivamente cuando `PaymentService` procesa un webhook de MercadoPago con `status = "approved"` (RN-FS02). La transición SHALL registrarse en `order_state_history` con `cambiado_por_id = NULL` (actor SISTEMA). La transición SHALL ocurrir dentro de la misma transacción que actualiza `Pago.mp_status` (atomicidad).

#### Scenario: Pago aprobado dispara confirmación del pedido

- **WHEN** `PaymentService.procesar_webhook()` verifica que el pago tiene `status = "approved"` en la API de MercadoPago
- **THEN** `OrderService.transicionar_estado(pedido_id, "PENDIENTE", "CONFIRMADO", actor_id=None)` se invoca exitosamente
- **AND** `orders.estado_codigo` vale `"CONFIRMADO"` en BD
- **AND** existe exactamente una fila nueva en `order_state_history` con `estado_anterior_codigo = "PENDIENTE"`, `estado_nuevo_codigo = "CONFIRMADO"`, `cambiado_por_id = NULL`

#### Scenario: Transición rechazada si el pedido no está en PENDIENTE

- **WHEN** `PaymentService` intenta transicionar a `CONFIRMADO` un pedido que ya está en `CONFIRMADO` u otro estado distinto de `PENDIENTE`
- **THEN** `OrderService.transicionar_estado()` lanza `InvalidStateTransitionError`
- **AND** no se agrega ninguna fila en `order_state_history`
- **AND** el estado del pedido en BD no cambia
