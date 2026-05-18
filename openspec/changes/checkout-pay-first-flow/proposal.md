## Why

Hoy el pedido se crea en `POST /api/v1/pedidos/` **antes** de pagar. Si el cliente cierra el navegador en medio del checkout, queda un pedido huérfano en `PENDIENTE` sin Pago, visible en "Mis pedidos" y contando en métricas. Además, `PENDIENTE` significa hoy "esperando pago" — semántica confusa cuando el modelo real es "el local todavía no aceptó el pedido". Y arriba de todo, las opciones de pago se duplican en la UI por un bug visual del flow actual.

La causa raíz es que la creación de pedido y el cobro son dos endpoints separados (`POST /pedidos/` + `POST /pagos/`), sin transacción que los una. Este change invierte el flow: **el pedido no existe en la DB hasta que el checkout completa**. Online → cobramos primero, si MP aprueba creamos pedido + pago en una UoW atómica. Pickup+efectivo → creamos pedido sin pago (el cobro vive en mostrador). Cualquier otro camino aborta sin tocar la DB. Modelo simple, sin huérfanos, sin pedidos colgados esperando webhook (RN-PE01..RN-PE08, US-PE-*).

## What Changes

- **BREAKING**: nuevos endpoints `POST /api/v1/checkout/online` y `POST /api/v1/checkout/pickup-efectivo`. Reemplazan al par actual `POST /pedidos/` + `POST /pagos/`.
- **BREAKING**: `POST /api/v1/pedidos/` se elimina (no quedan clientes; el front es el único consumidor y migra a checkout).
- **BREAKING**: `POST /api/v1/pagos/` se elimina. El cobro deja de ser un endpoint independiente — vive dentro de `/checkout/online`. La spec viva `payments-checkout-api` (recién archivada el 2026-05-17) se modifica sustancialmente para reflejarlo. Es la evolución natural del contrato.
- **BREAKING — semántica**: `PENDIENTE` pasa a significar "pedido recién creado, esperando que el local acepte". Antes significaba "esperando pago". El estado terminal previo de error de cobro deja de existir como concepto porque sin pago aprobado no hay pedido.
- **D3 modo estricto MP**: solo `mp_status == "approved"` crea pedido. Cualquier otro status (`pending`, `in_process`, `rejected`, `cancelled`, etc.) NO crea pedido — devuelve `402 Payment Required` con `mp_status` y `status_detail`. Sin webhook reconciliando creaciones diferidas. Esta decisión revierte el contrato "200 OK con cualquier status" que estableció `payments-checkout-api`. Se aceptan los costos (perder ventas "en revisión") a cambio de operativa simple y sin estados intermedios.
- **D6 `external_reference` cambia** de `str(pedido_id)` a `idempotency_key` (UUID4 generado por el front). El pedido no existe cuando se llama a MP, así que no hay ID que usar. El webhook reconcilia por `idempotency_key`.
- **Carrito en Zustand `persist`**: ya existe — verificar y reforzar tests. El carrito vive en el front durante el armado y se vacía después del checkout exitoso.
- **Fix UI** del bug visual de opciones de pago duplicadas.
- **Webhook MP**: se mantiene `POST /api/v1/pagos/webhook/mercadopago` y `GET /api/v1/pagos/pedido/{id}`. El webhook ahora tiene menos casos porque ya no entran pagos `pending`/`in_process` al sistema desde el endpoint principal.
- **GET, PATCH, listados de pedidos**: sin cambios. Solo se elimina el endpoint de **creación**.
- **FSM**: la matriz de transiciones (`ALLOWED_TRANSITIONS`) mantiene su estructura. Cambios: (a) se redefine la semántica de `PENDIENTE` (de "esperando pago" a "esperando local"), (b) **se renombra el código `EN_CAMINO` a `TERMINADO`** para unificar el vocabulario entre retiro y envío. `TERMINADO` significa "pedido listo para ser retirado o entregado" — sirve tanto para pickup como delivery. Esto requiere migración Alembic (UPDATE en `payment_methods` no, en `estados_pedido`/`orders`/`order_state_history`), actualización de `state_machine.py` (`ALLOWED_TRANSITIONS`, `TRANSITION_ROLES`), seed, schemas, tests, y frontend (labels, types, badges, charts).

## Capabilities

### New Capabilities

- `checkout`: nueva capability que agrupa los dos endpoints de checkout (`POST /checkout/online` y `POST /checkout/pickup-efectivo`), su validación de carrito server-side, el cálculo atómico de totales y la persistencia transaccional Pedido+Pago.

### Modified Capabilities

- `order-creation`: el endpoint `POST /api/v1/pedidos/` se REMOVES. La creación de pedidos pasa al capability `checkout`. Esta spec queda con un único requirement: "creación deprecated", apuntando a `checkout`.
- `order-creation-frontend`: `useCreateOrder` se reemplaza por `useCheckoutOnline` y `useCheckoutPickupEfectivo`. La página de confirmación post-creación se mantiene; cambia el origen de los datos.
- `order-state-machine`: redefinición semántica de `PENDIENTE` (de "esperando pago" a "esperando local"). La matriz de transiciones (`ALLOWED_TRANSITIONS`, `TRANSITION_ROLES`) no cambia. Se elimina la transición automática "PENDIENTE → CONFIRMADO desde webhook MP" como camino normal de creación (el pedido nace ya pagado en el flow online); el webhook sigue existiendo para reconciliar casos excepcionales (transición fallida post-cobro, manual fallback).
- `payment-mercadopago-frontend`: `PaymentForm` ya no se monta como pantalla separada en `/cliente/pedidos/:id/pago`. Se integra dentro de `CheckoutPage` como un step del flow. Las categorías `onPending`/`onError` se simplifican: el modo estricto del backend elimina el caso `onPending` (no llega al front porque el backend ya respondió 402).
- `payments-checkout-api`: el endpoint `POST /api/v1/pagos/` se REMOVES. Las respuestas "200 OK con cualquier mp_status" dejan de existir. La nueva regla es "el cobro vive en `POST /checkout/online`". `GET /pagos/pedido/{id}` y `POST /pagos/webhook/mercadopago` se mantienen.
- `checkout-validation`: la navegación post-validación pasa a `/cliente/checkout` que ahora arma payload de checkout (no de creación de pedido). El requirement de navegación se ajusta levemente.

## Impact

- **Backend**:
  - Nuevo módulo `backend/features/checkout/` con `router.py`, `service.py`, `schemas.py`.
  - `backend/features/payments/router.py`: se elimina `POST /` (deprecación dura). Se mantienen `GET /pedido/{id}` y `POST /webhook/mercadopago`.
  - `backend/features/payments/service.py`: la creación de Pago migra al `CheckoutService` (que la reutiliza internamente); el método público `crear_pago_con_mp` se hace privado/se elimina.
  - `backend/features/orders/router.py`: se elimina `POST /`.
  - `backend/features/orders/service.py`: el método `crear_pedido` se elimina o se hace privado (`_crear_pedido_atomico`) y es llamado solo desde `CheckoutService`.
  - `backend/features/payments/service.py::procesar_webhook`: el `lookup` por `external_reference` cambia — ahora es el `idempotency_key`. Se agrega columna o reutiliza `external_reference` como string para guardar el UUID.
  - **No hay migración Alembic de schema nueva** — los modelos `Pedido`/`Pago` no cambian. Sí hay seeds y un script SQL idempotente para limpiar pedidos huérfanos en dev/testing.
- **Frontend**:
  - Nuevo módulo `frontend/src/features/checkout/services/checkout.service.ts`.
  - Hooks nuevos `useCheckoutOnline`, `useCheckoutPickupEfectivo`. Eliminan `useCreateOrder` y `useInitPayment` separado.
  - `CheckoutPage.tsx`: refactor mayor — pasa de "armar pedido y mandar" a "armar carrito + decidir ruta + cobrar (si online) + confirmar".
  - `PaymentPage.tsx` independiente se ELIMINA (el flow es ahora una sola pantalla).
  - `PaymentForm.tsx`: se integra dentro del checkout. Sigue existiendo como componente reutilizable pero pierde las rutas asociadas.
  - Bug de opciones de pago duplicadas: fix puntual en `PaymentMethodSelector` o en `CheckoutPage` (identificar en la fase de auditoría).
- **APIs (cliente externo si alguna vez existiera)**: BREAKING — `POST /pedidos/` y `POST /pagos/` ya no existen. Hoy nadie externo los usa.
- **Tests**: gran refactor — los tests de `POST /pedidos/` y `POST /pagos/` se reemplazan por tests de `POST /checkout/*`. Los tests existentes del FSM, listado de pedidos, webhook, GET por id siguen vigentes sin cambios.
- **Docs vivas**: `openspec/specs/{order-creation,order-creation-frontend,order-state-machine,payment-mercadopago-frontend,payments-checkout-api,checkout-validation}/spec.md` reciben deltas.
- **Datos**: pedidos huérfanos en `PENDIENTE` sin Pago en dev/testing se eliminan con script idempotente. En producción no hay migración automática (D7 — decisión del usuario manual).
- **Riesgo**: cualquier transición fallida post-cobro (MP aprueba, persistencia falla) queda como incidente operativo manual. Documentado, asumido. El webhook puede actuar como red de seguridad si llega antes del response al front.
