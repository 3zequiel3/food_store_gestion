# Proposal: Pagos no aprobados como dato, no como excepción

## Why

Hoy `POST /api/v1/pagos/` modela como excepción HTTP 422 cualquier respuesta de MercadoPago que no sea `approved` (incluso `pending`, `in_process`, `rejected`, `cancelled`), mientras que el frontend espera recibir el `mp_status` como dato en un 200 OK. Resultado de la auditoría: (1) **contrato API roto** — el front siempre cae al `catch(err)` y muestra mensajes genéricos o "Estado inesperado" para casos que ni siquiera son error real (`pending` = revisión manual); (2) **phantom Pago** — cuando MP errorea sin status, el code igual commitea un `Pago` con `mp_status="pending"` (default del repo) que queda en `_ACTIVE_STATUSES` y bloquea para siempre los reintentos por `find_active_by_pedido_id`; (3) **código muerto frontend** — `initiatePayment`, `useInitPayment` y `interface PagoCreate` legacy del flow wallet, sin consumidores, mandando payloads incompletos al endpoint.

El módulo de pagos es el camino crítico de cualquier pedido. Mientras no se arregle, el cliente nunca ve un mensaje útil cuando MP rechaza la tarjeta y un pedido cuyo primer intento de pago falló por error de MP queda imposible de re-pagar sin tocar la base a mano.

## What Changes

### Backend

- **BREAKING (clientes externos del API, no aplica al front actual)**: `POST /api/v1/pagos/` deja de devolver `422` para los `mp_status` no aprobados. Pasa a devolver `200 OK` con `{mp_status, mp_id, status_detail, pago_id}` para cualquier status que MP haya respondido (`approved`, `pending`, `in_process`, `rejected`, `cancelled`, etc.). El front es el único cliente — no rompe nada en producción.
- Solo se lanza excepción cuando MP NO devuelve status (timeout, 5xx, token inválido). Se mapea a `502 mp_unreachable` (no a `422`) porque es falla de upstream, no de regla de negocio.
- **El `Pago` se crea solo si MP respondió con status**. Si MP errorea sin status, no se toca la DB. Elimina el phantom Pago que bloquea reintentos.
- El `Pago` se crea con el `mp_status` real devuelto por MP, no con el default `"pending"` del repo. Esto mantiene `_ACTIVE_STATUSES` coherente (un `rejected` NO bloquea reintentos, un `pending` SÍ — que es lo correcto).
- Nuevo schema `PagoCreateResponse` declarado como `response_model` en el router para que OpenAPI lo refleje.
- El `except Exception: pass` que silencia errores de transición `PENDIENTE→CONFIRMADO` se reemplaza por logging `ERROR` con `exc_info=True`. La transición sigue siendo best-effort (el webhook la repite), pero ahora queda traza en logs.

### Frontend

- `PaymentForm.tsx` clasifica los `mp_status` en cuatro categorías y expone un callback `onPending` separado de `onError`:
  - `approved` → `onSuccess`
  - `pending`, `in_process`, `authorized` → `onPending` (revisión manual, débito en proceso)
  - `rejected`, `cancelled` → `onError` con `status_detail` mapeado a mensaje user-friendly
  - Otros (`refunded`, `charged_back`, `in_mediation`, etc.) → `onError` genérico con `status_detail`
- Nuevo `statusDetailMessages.ts` con mapping `status_detail` MP → mensaje en castellano rioplatense. Cubre los detalles más comunes en Argentina (`cc_rejected_insufficient_amount`, `cc_rejected_bad_filled_security_code`, `cc_rejected_bad_filled_card_number`, `cc_rejected_other_reason`, `pending_review_manual`, etc.).
- `PaymentPage.tsx` maneja `onPending` mostrando un estado inline "Tu pago está en revisión. Te avisaremos cuando se confirme." con un botón "Ver estado del pedido" que lleva a `/cliente/pedidos/{id}/confirmacion`. El polling completo del estado queda como TODO para un change posterior (`payments-pending-polling`).
- **Limpieza de código muerto**:
  - Se borra `initiatePayment` de `payments.service.ts` (manda payload incompleto al endpoint Checkout API).
  - Se borra `useInitPayment.ts` completo (hook sin consumidores).
  - Se borra `interface PagoCreate { pedido_id: number }` de `payments.types.ts` (legacy del flow wallet).
- Se agrega `pago_id?: number` a `PaymentResponse` para futuros polling/lookups directos.

### Lo que NO entra (changes posteriores)

- Verificación HMAC del webhook (`payments-webhook-signature`).
- TOCTOU con `SELECT FOR UPDATE` en `find_active_by_pedido_id`.
- Alineación del contrato de `GET /pagos/pedido/{id}` con el nuevo response shape.
- Hardcode de `"TARJETA"` en `service.py:151` y guard de `forma_pago_codigo`.
- Seed desincronizado de `forma_pago` vs DB.
- PII leak en `console.log` del frontend.
- Polling completo de la pantalla de pending con backoff.

## Capabilities

### New Capabilities

- `payments-checkout-api`: contrato del endpoint `POST /api/v1/pagos/` (Checkout API inline). El change archivado `payment-checkout-api-implementation` introdujo la implementación pero no consolidó una capability viva específica para el endpoint — se crea acá porque el contrato cambia y necesita spec propia.

### Modified Capabilities

- `payment-mercadopago-frontend`: el `PaymentForm` / `PaymentPage` cambia su manejo del response — antes solo aprobaba o erraba; ahora distingue `approved` / `pending` / `rejected` / `other` y mapea `status_detail` a mensajes user-friendly. Además se eliminan archivos del legacy wallet flow declarados en la capability.

## Impact

| Área | Tipo | Descripción |
|------|------|-------------|
| `backend/features/payments/service.py` | Modified | Refactor de `crear_pago_api`: phases 3a/3b separadas, `Pago` se crea solo si hay status, `except Exception: pass` → logging |
| `backend/features/payments/schemas.py` | Modified | Nuevo `PagoCreateResponse` con `mp_status`, `mp_id`, `status_detail`, `pago_id` |
| `backend/features/payments/repository.py` | Modified | `create_pago` acepta `mp_status` opcional (en vez de default fijo `"pending"`) — los reintentos siguen funcionando porque `rejected` no está en `_ACTIVE_STATUSES` |
| `backend/features/payments/router.py` | Modified | `response_model=PagoCreateResponse` en el POST `/` |
| `backend/features/payments/tests/` | Modified | Tests nuevos: `pending`, `in_process`, `rejected`, `cancelled`, `mp_unreachable` (no crea Pago), `approved` (sigue creando + transiciona) |
| `shared/exceptions.py` | Modified (mínimo) | Verificar si `BusinessRuleError` con `code="mp_unreachable"` mapea a 502 o se necesita una nueva subclase / handler. Decisión final en `design.md` |
| `frontend/src/features/payments/components/PaymentForm.tsx` | Modified | Clasificación en 4 categorías + prop `onPending` |
| `frontend/src/features/payments/components/__tests__/PaymentForm.test.tsx` | Modified | Cobertura de los nuevos casos |
| `frontend/src/features/payments/lib/statusDetailMessages.ts` | New | Mapping `status_detail` → mensaje user-friendly |
| `frontend/src/features/payments/pages/PaymentPage.tsx` | Modified | Maneja `onPending` con vista inline + botón a confirmación |
| `frontend/src/features/payments/services/payments.service.ts` | Modified | Borra `initiatePayment` |
| `frontend/src/features/payments/hooks/useInitPayment.ts` | Removed | Hook completo (legacy wallet) |
| `frontend/src/features/payments/types/payments.types.ts` | Modified | Borra `interface PagoCreate` legacy, agrega `pago_id` a `PaymentResponse` |
| Roadmap (`docs/CHANGES.md`) | N/A | Change transversal de fix sobre módulo existente, no consume slot del roadmap. Anotar como hotfix post `payment-checkout-api-implementation` |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Algún cliente externo (móvil, integrador) consumía el 422 como señal de rechazo | Baja (no hay otros clientes hoy) | Documentar el cambio en `What Changes` como BREAKING para clientes externos |
| Cambio en `create_pago(mp_status=...)` rompe llamadas existentes del webhook | Baja | El webhook usa `update_mp_fields`, no `create_pago`. Se verifica en tests |
| `_ACTIVE_STATUSES` queda inconsistente con la nueva semántica | Baja | `_ACTIVE_STATUSES = ("approved", "pending", "in_process")` ya es correcto: `rejected` y `cancelled` NO bloquean reintentos. No se toca |
| El front muestra `onPending` pero no hace polling — UX pobre si el banco tarda mucho | Media | Mostrar mensaje explícito + botón a `/cliente/pedidos/{id}/confirmacion` donde puede refrescar. Polling completo queda en un change separado y trackeado |
| Tests existentes asumen 422 para no-approved | Alta | Tarea explícita en `tasks.md`: actualizar tests existentes antes de tocar el service |
