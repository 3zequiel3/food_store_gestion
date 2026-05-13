## Why

`order-creation-backend` permite crear pedidos, pero estos quedan en estado `PENDIENTE` indefinidamente: no existe mecanismo para iniciar ni confirmar un pago. Este change implementa la integración completa con MercadoPago (crear preferencia, procesar webhook IPN, consultar estado de pago), que es el único camino para que un pedido avance de `PENDIENTE` a `CONFIRMADO`.

## What Changes

- **Implementar `POST /api/v1/pagos`**: crea una preferencia/orden en MercadoPago para un pedido PENDIENTE del cliente autenticado, registra un `Pago` con `idempotency_key` UUID único, y retorna el `init_point` o los datos necesarios para el checkout.
- **Implementar `POST /api/v1/pagos/webhook/mercadopago`**: endpoint IPN que recibe notificaciones de MercadoPago, verifica el estado real consultando la API (RN-PA04), actualiza `Pago.mp_status`, y dispara la transición automática `PENDIENTE → CONFIRMADO` cuando el pago es `approved` (RN-PA05).
- **Implementar `GET /api/v1/pagos/pedido/{pedido_id}`**: retorna el estado del último pago asociado a un pedido propio (US-047).
- **Soporte de reintento (RN-PA08)**: `POST /api/v1/pagos` con pedido PENDIENTE y pago previo rechazado genera un nuevo `Pago` con nuevo `idempotency_key`, manteniendo el historial de intentos.
- **Completar `PaymentService` y `PaymentRepository`** (actualmente vacíos): lógica de integración con SDK de MercadoPago, validación de ownership, idempotencia y actualización de estado.
- **Rellenar `schemas.py`** del feature payments con los DTOs necesarios.
- El feature skeleton ya existe (`backend/features/payments/`): modelo `Pago` completo, router registrado en `main.py` bajo `/api/v1/pagos`. Este change lo completa, no lo crea.

## Capabilities

### New Capabilities
- `payments`: Integración con MercadoPago para el flujo de pago — crear preferencia, procesar webhook IPN con idempotencia, consultar estado por pedido y soportar reintentos.

### Modified Capabilities
- `order-creation`: Se agrega la relación `Pedido.pagos` (ya existe en el modelo pero la spec no la documenta); el transition `PENDIENTE → CONFIRMADO` ocurre desde este change (via webhook), lo que amplía el contrato del estado inicial.

## Impact

- `backend/features/payments/service.py` — implementación completa desde cero
- `backend/features/payments/repository.py` — implementación completa desde cero
- `backend/features/payments/schemas.py` — DTOs: `PagoCreate`, `PagoRead`, `WebhookPayload`
- `backend/features/payments/router.py` — reemplaza los stubs con endpoints reales
- `backend/features/orders/service.py` — se agrega método `confirmar_pedido(pedido_id)` para que el webhook lo invoque
- `backend/features/orders/router.py` — sin cambios de ruta; la transición la maneja PaymentService
- Dependencia externa: SDK `mercadopago` (ya en `requirements.txt`)
- Tests de integración: `backend/tests/features/test_payments.py`
