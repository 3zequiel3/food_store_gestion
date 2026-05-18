## 1. Auditoría y limpieza inicial

- [ ] 1.1 Confirmar estado actual del FSM en `backend/features/orders/state_machine.py` y la matriz `ALLOWED_TRANSITIONS` vs lo documentado en la spec. Anotar discrepancias (e.g. uso de `CANCELADO_ADMIN`/`CANCELADO_CLIENTE` vs `CANCELADO` plano)
- [ ] 1.2 Grep exhaustivo de clientes de `POST /api/v1/pedidos/` y `POST /api/v1/pagos/` en `frontend/src` y en `backend/tests`. Documentar dónde aparecen y qué hace cada caller
- [ ] 1.3 Reproducir y localizar el bug visual de opciones de pago duplicadas. Confirmar archivo y línea exactos (hipótesis: `PaymentMethodSelector.tsx` con array duplicado en state, o doble montaje del componente en `CheckoutPage`)
- [ ] 1.4 Escribir script SQL idempotente `backend/scripts/cleanup_orphan_orders.sql` que elimine pedidos en `PENDIENTE` sin Pago asociado activo (`mp_status IN ('approved')`)
- [ ] 1.5 Ejecutar el script en dev local y validar que no rompe otros pedidos legítimos (los que ya están `CONFIRMADO`, `EN_PREPARACION`, etc., sobreviven)
- [ ] 1.6 Confirmar con el usuario: ¿se ejecuta cleanup en CI antes de cada suite o solo manual? Default: manual

## 2. Schemas backend (TDD)

- [ ] 2.1 Tests RED en `backend/features/checkout/tests/test_schemas.py`: `CheckoutItem` valida `producto_id >= 1`, `cantidad >= 1`, `personalizacion: list[int] | None` con elementos `>= 1`
- [ ] 2.2 Tests RED para `CheckoutOnlineRequest`: campos obligatorios, `tipo_entrega` en `{"DELIVERY", "PICKUP"}`, `direccion_id` nullable, `idempotency_key` debe ser UUID4 válido, `extra="forbid"` rechaza campos extra
- [ ] 2.3 Tests RED para `CheckoutPickupEfectivoRequest`: NO acepta `direccion_id`, NO acepta `card_token`, items + notas + extra forbid
- [ ] 2.4 Tests RED para `CheckoutOnlineResponse` y `CheckoutPickupEfectivoResponse`: estructura de campos
- [ ] 2.5 Tests RED para `CheckoutErrorResponse`: `code`, `detail`, `mp_status` opcional, `status_detail` opcional
- [ ] 2.6 Implementar los schemas en `backend/features/checkout/schemas.py`. Verificar tests GREEN

## 3. Service backend — CheckoutService (TDD)

- [ ] 3.1 Crear estructura del módulo `backend/features/checkout/{__init__.py,service.py,router.py,schemas.py,exceptions.py}`
- [ ] 3.2 Tests RED de `CheckoutService.crear_pedido_online`: happy path — MP approved → pedido + pago creados en UoW única
- [ ] 3.3 Tests RED: MP rejected → 0 inserts en `orders`, `order_items`, `order_state_history`, `pagos`. El service levanta `PaymentRejectedError` o similar
- [ ] 3.4 Tests RED: MP pending → 0 inserts, levanta `PaymentPendingNotAcceptedError` (modo estricto D3)
- [ ] 3.5 Tests RED: MP in_process → idem a pending
- [ ] 3.6 Tests RED: MP cancelled → 0 inserts, levanta `PaymentCancelledError`
- [ ] 3.7 Tests RED: MP devuelve status desconocido → 0 inserts, levanta `PaymentUnexpectedStatusError`
- [ ] 3.8 Tests RED: MP unreachable (sin status) → 0 inserts, levanta `UpstreamError("mp_unreachable")`
- [ ] 3.9 Tests RED: stock insuficiente PRE-MP → levanta `BusinessRuleError`, NO llama a MP
- [ ] 3.10 Tests RED: dirección de otro usuario → levanta `NotFoundError` (404, anti-leak)
- [ ] 3.11 Tests RED: producto inexistente / soft-deleted → `NotFoundError`
- [ ] 3.12 Tests RED: producto no disponible (`disponible=false`) → `BusinessRuleError`
- [ ] 3.13 Tests RED: idempotency_key ya usado (Pago existente con ese `external_reference`) → devuelve el resultado anterior sin re-cobrar
- [ ] 3.14 Tests RED: `total` se recalcula server-side (anti-smuggling) — incluso si el test envía un `total` inyectado, se ignora
- [ ] 3.15 Implementar `CheckoutService.crear_pedido_online`. Iterar hasta GREEN
- [ ] 3.16 Tests RED de `CheckoutService.crear_pedido_pickup_efectivo`: happy path — pedido creado, sin Pago, en `PENDIENTE`
- [ ] 3.17 Tests RED: rechazar si `direccion_id` se envía (debería filtrarse por Pydantic, pero defensa en service también)
- [ ] 3.18 Tests RED: stock insuficiente → rechazar, sin pedido
- [ ] 3.19 Tests RED: producto inexistente → 404
- [ ] 3.20 Implementar `CheckoutService.crear_pedido_pickup_efectivo`. Iterar hasta GREEN
- [ ] 3.21 Refactor: extraer `_validar_y_calcular_carrito` como método compartido entre ambos métodos públicos

## 4. Rename `EN_CAMINO` → `TERMINADO` (D13) — TDD + migración

Este grupo se puede ejecutar en paralelo a los Grupos 3, 5 y 6 (no comparten archivos críticos), pero DEBE completarse antes del Grupo 13 (validación cross-stack). Toca DB + backend + frontend + tests.

### 4.1 Migración Alembic

- [ ] 4.1.1 Crear nueva migración `backend/alembic/versions/<timestamp>_rename_en_camino_to_terminado.py` con `upgrade()` y `downgrade()`:
  - `upgrade()`: UPDATEs idempotentes en `estados_pedido`, `orders.estado_codigo`, `order_state_history.estado_anterior_codigo`, `order_state_history.estado_nuevo_codigo`
  - `downgrade()`: reverso simétrico
- [ ] 4.1.2 Tests de migración: aplicar en DB de prueba con filas `EN_CAMINO` existentes, verificar todas migraron. Hacer downgrade, verificar reversión correcta
- [ ] 4.1.3 Ejecutar la migración en dev local con `alembic upgrade head` y validar que `psql` ya no reporta filas con `codigo = 'EN_CAMINO'`

### 4.2 Backend código

- [ ] 4.2.1 Actualizar `backend/features/orders/state_machine.py`:
  - `ALLOWED_TRANSITIONS["EN_PREPARACION"]`: `{"EN_CAMINO", "CANCELADO_ADMIN"}` → `{"TERMINADO", "CANCELADO_ADMIN"}`
  - `ALLOWED_TRANSITIONS["EN_CAMINO"]` → `ALLOWED_TRANSITIONS["TERMINADO"]`
  - `TRANSITION_ROLES` actualizar las 2 claves que mencionan `EN_CAMINO`
- [ ] 4.2.2 Actualizar `backend/features/orders/schemas.py`:
  - `Literal["CANCELADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO"]` → `Literal["CANCELADO", "EN_PREPARACION", "TERMINADO", "ENTREGADO"]` (en `AvanzarEstadoRequest` y el tuple de estados válidos)
- [ ] 4.2.3 Actualizar `backend/scripts/seed.py` (línea ~75): el row de `estados_pedido` con codigo `"EN_CAMINO"` y descripción "Pedido en camino al cliente" → codigo `"TERMINADO"` con descripción "Pedido listo para ser retirado o entregado"
- [ ] 4.2.4 Actualizar `backend/README.md` línea 237 (enum del estado)

### 4.3 Backend tests

- [ ] 4.3.1 Actualizar `backend/tests/conftest.py` línea 262, 270 — fixture de estados
- [ ] 4.3.2 Actualizar `backend/tests/integration/test_state_machine.py` (líneas 32, 34, 43, 76, 80, 149) — comparaciones con literales
- [ ] 4.3.3 Actualizar `backend/tests/integration/test_schemas.py` línea 20 — set de estados válidos
- [ ] 4.3.4 Actualizar `backend/tests/integration/test_router_estado.py` línea 172
- [ ] 4.3.5 Actualizar `backend/tests/integration/test_order_service_fsm.py` (líneas 486, 491)
- [ ] 4.3.6 Actualizar `backend/tests/integration/test_e2e_estado.py` (líneas 111, 136, 137, 139, 141)
- [ ] 4.3.7 Actualizar `backend/tests/integration/test_fsm_checkout.py` línea 60 — descripción del FSM total
- [ ] 4.3.8 Tests nuevos que validan que la migración mantiene consistencia (no quedan FKs colgando) — opcional pero recomendado

### 4.4 Frontend código y tipos

- [ ] 4.4.1 Actualizar `frontend/src/features/orders/types/orders.types.ts` línea 5: tipo `EstadoCodigo` reemplaza `'EN_CAMINO'` por `'TERMINADO'`
- [ ] 4.4.2 Actualizar `frontend/src/features/orders/components/OrderFilters.tsx` línea 10: el option `value: 'EN_CAMINO'` → `'TERMINADO'`, label `'En camino'` → `'Listo para retirar/entregar'`
- [ ] 4.4.3 Actualizar `frontend/src/features/orders/components/OrderTimeline.tsx`:
  - Línea 4: `STATE_ORDER` reemplaza `'EN_CAMINO'` por `'TERMINADO'`
  - Línea 11: label `EN_CAMINO: 'En camino'` → `TERMINADO: 'Listo'`
- [ ] 4.4.4 Actualizar `frontend/src/features/orders/components/OrderStatusBadge.tsx` línea 8: la entrada de mapping
- [ ] 4.4.5 Actualizar `frontend/src/features/orders/components/OrderStateActions.tsx` (líneas 30, 33): el botón "Marcar en camino" → "Marcar listo", `estado_codigo_destino: 'EN_CAMINO'` → `'TERMINADO'`, case `'EN_CAMINO':` → `'TERMINADO':`
- [ ] 4.4.6 Actualizar `frontend/src/features/admin-metrics/components/PedidosPorEstadoChart.tsx` línea 13: la clave del color mapping

### 4.5 Frontend tests

- [ ] 4.5.1 Grep en `frontend/src/**/*.test.{ts,tsx}` por `'EN_CAMINO'` o `"EN_CAMINO"` y actualizar a `'TERMINADO'`
- [ ] 4.5.2 Si hay tests de snapshot que congelan el label "En camino", regenerarlos con `pnpm test --update-snapshots` (revisar diff antes de commitear)

### 4.6 Validación del rename

- [ ] 4.6.1 Backend: correr suite completa de orders + state_machine. Todos verdes (esperado: ~50+ tests)
- [ ] 4.6.2 Frontend: correr suite completa de orders. Todos verdes
- [ ] 4.6.3 Levantar back + front local, verificar que un pedido en estado `TERMINADO` se muestra con el nuevo label en filtros, timeline, badge y chart admin
- [ ] 4.6.4 Verificar `psql` que `SELECT codigo FROM estados_pedido` ya no contiene `EN_CAMINO`

## 5. Adaptación de PaymentService y OrderService

- [ ] 5.1 Migrar la lógica de "crear Pago con MP" del `PaymentService.crear_pago_con_mp` (público) a un método privado/interno o moverla al `CheckoutService`. El `PaymentService` mantiene `procesar_webhook` y queries (`find_by_pedido_id`)
- [ ] 5.2 Adaptar `PaymentRepository`: agregar `find_by_external_reference(external_reference: str)` para que el webhook lo use
- [ ] 5.3 Tests RED de `PaymentRepository.find_by_external_reference`: devuelve el Pago o None
- [ ] 5.4 Implementar el repo method. GREEN
- [ ] 5.5 Tests RED del webhook actualizado: usa `find_by_external_reference(idempotency_key)`, no `int(external_reference)`
- [ ] 5.6 Implementar el cambio en `procesar_webhook`. GREEN
- [ ] 5.7 Tests RED para el caso "incidente — webhook llega pero no hay Pago en DB": el handler responde 200 y emite log WARNING con `external_reference`
- [ ] 5.8 Implementar el branching. GREEN
- [ ] 5.9 Marcar `OrderService.crear_pedido` como método interno (o privado) — solo invocable desde `CheckoutService`. Eliminar del router

## 6. Router backend

- [ ] 6.1 Tests RED de integración para `POST /api/v1/checkout/online`: happy path approved con `httpx` AsyncClient + mocks de MP
- [ ] 6.2 Tests RED: rejected, pending, in_process, cancelled, refunded, unreachable — cada uno con su código HTTP esperado (402 o 422 según resolución) y body
- [ ] 6.3 Tests RED: validaciones del body (campos faltantes, tipos malos, `idempotency_key` inválido, `extra="forbid"`)
- [ ] 6.4 Tests RED: auth — 401 sin token, 403 sin rol CLIENT
- [ ] 6.5 Tests RED: idempotencia — mismo `idempotency_key` en dos requests devuelve el mismo resultado sin segundo cobro
- [ ] 6.6 Tests RED de integración para `POST /api/v1/checkout/pickup-efectivo`: happy path
- [ ] 6.7 Tests RED: validaciones, auth, stock
- [ ] 6.8 Crear `backend/features/checkout/router.py` con los dos endpoints, response_models, dependencias auth, mapping de excepciones a HTTP
- [ ] 6.9 Registrar el router en `backend/main.py` (o equivalente) bajo `/api/v1/checkout`
- [ ] 6.10 Iterar tests hasta GREEN
- [ ] 6.11 Eliminar `POST /` de `backend/features/orders/router.py` (mantener GET, PATCH, listados)
- [ ] 6.12 Eliminar `POST /` de `backend/features/payments/router.py` (mantener `GET /pedido/{id}` y `POST /webhook/mercadopago`)
- [ ] 6.13 Adaptar tests existentes que tocan los endpoints eliminados — borrar o reescribir contra los nuevos endpoints
- [ ] 6.14 Verificar OpenAPI en `/docs`: nuevos endpoints visibles, viejos ausentes, schemas correctos

## 7. Frontend — tipos y servicios

- [ ] 7.1 Crear `frontend/src/features/checkout/types/checkout.types.ts` con `CheckoutItem`, `CheckoutOnlineRequest`, `CheckoutOnlineResponse`, `CheckoutPickupEfectivoRequest`, `CheckoutPickupEfectivoResponse`, `CheckoutErrorResponse`
- [ ] 7.2 Tests RED en `frontend/src/features/checkout/services/__tests__/checkout.service.test.ts` para `createCheckoutOnline`: POST al endpoint correcto, body bien armado, response parseada
- [ ] 7.3 Tests RED para `createCheckoutPickupEfectivo`
- [ ] 7.4 Tests RED para mapping de errores (`402`, `422`, `502`)
- [ ] 7.5 Implementar `frontend/src/features/checkout/services/checkout.service.ts`. GREEN
- [ ] 7.6 Eliminar el archivo `frontend/src/features/checkout/services/orders.service.ts` (su única función `createOrder` para `POST /pedidos/` ya no existe)
- [ ] 7.7 Eliminar `frontend/src/features/payments/services/payments.service.ts` o vaciarlo (solo conservar lo que use `GET /pagos/pedido/:id` si aún se necesita)

## 8. Frontend — Zustand cart persist (verificación)

- [ ] 8.1 Tests RED de `cartStore` con `persist`: agregar item → simular reload → item presente
- [ ] 8.2 Tests RED: `clearCart()` limpia el `localStorage` (`cart-store` key)
- [ ] 8.3 Tests RED: el `persist` no incluye estado UI volátil (e.g. `isOpen`)
- [ ] 8.4 Si los tests fallan, ajustar config de `persist`. Si pasan, dejar tests como regresión

## 9. Frontend — hooks de checkout (TDD)

- [ ] 9.1 Tests RED para `useCheckoutOnline`: invoca `createCheckoutOnline` con el payload correcto desde `cartStore` + form data
- [ ] 9.2 Tests RED: genera `idempotency_key` (UUID4) al primer call y lo reutiliza en reintentos dentro de la misma sesión
- [ ] 9.3 Tests RED: navegación post-éxito a `/cliente/pedidos/:id/confirmacion` + `clearCart()`
- [ ] 9.4 Tests RED: manejo de errores 402/422/502 — toast apropiado, no clearCart, idempotency_key preservado
- [ ] 9.5 Implementar `useCheckoutOnline`. GREEN
- [ ] 9.6 Tests RED para `useCheckoutPickupEfectivo`: payload sin datos de pago, navegación post-éxito
- [ ] 9.7 Implementar `useCheckoutPickupEfectivo`. GREEN
- [ ] 9.8 Eliminar `useCreateOrder` y referencias

## 10. Frontend — CheckoutPage refactor

- [ ] 10.1 Tests RED de `CheckoutPage`: render con carrito + dirección + selector forma de pago + (PaymentForm condicional)
- [ ] 10.2 Tests RED: forma de pago `MERCADOPAGO` muestra `PaymentForm` inline; `EFECTIVO` lo oculta
- [ ] 10.3 Tests RED: botón "Confirmar y pagar" (online) deshabilitado hasta tener `card_token` válido del `PaymentForm`
- [ ] 10.4 Tests RED: botón "Confirmar pedido" (efectivo) habilitado con dirección/pickup + items
- [ ] 10.5 Tests RED: click confirma → invoca el hook correspondiente
- [ ] 10.6 Tests RED de regresión del bug — `screen.getAllByRole('radio', {name: /forma de pago/i})` devuelve exactamente N (no 2N) para N formas de pago habilitadas
- [ ] 10.7 Implementar refactor de `CheckoutPage`. GREEN
- [ ] 10.8 Fixear el bug de opciones duplicadas en `PaymentMethodSelector` (o en `CheckoutPage`). Verificar test 10.6 GREEN
- [ ] 10.9 Tests de regresión visual: snapshot de `CheckoutPage` con cada forma de pago seleccionada

## 11. Frontend — eliminar PaymentPage independiente

- [ ] 11.1 Eliminar `frontend/src/pages/client/PaymentPage.tsx` y sus tests
- [ ] 11.2 Eliminar `frontend/src/pages/client/PaymentResultPage.tsx` si solo era usado post-PaymentPage (confirmar con grep)
- [ ] 11.3 Eliminar la ruta `/cliente/pedidos/:id/pago` del router
- [ ] 11.4 Verificar que `PaymentForm` (`frontend/src/features/payments/components/PaymentForm.tsx`) sigue exportado y testeable como componente reutilizable. Si su contrato cambió (ya no llama a `POST /pagos/`), ajustar — ahora produce `card_token` que el parent consume
- [ ] 11.5 Tests de regresión de `PaymentForm` con el contrato nuevo (props `onTokenReady(token)` o similar)

## 12. Frontend — OrderConfirmationPage adaptación

- [ ] 12.1 Tests RED: la confirmación post-checkout online muestra estado `"PENDIENTE — Esperando que el local acepte tu pedido"` (semántica D4)
- [ ] 12.2 Tests RED: la confirmación post-pickup+efectivo muestra "Retiro en local — Pagás al retirar"
- [ ] 12.3 Tests RED: NO se muestra botón "Ir a pagar" en ninguno de los dos casos
- [ ] 12.4 Tests RED: fallback sin location state muestra "Pedido creado" con botón "Ver mis pedidos"
- [ ] 12.5 Implementar cambios en `OrderConfirmationPage.tsx`. GREEN

## 13. Validación cross-stack

- [ ] 13.1 Levantar back (`uv run uvicorn ...`) y front (`pnpm dev`) en local
- [ ] 13.2 Smoke test manual: checkout online con tarjeta sandbox APPROVED → pedido creado en `PENDIENTE`, redirige a confirmación, carrito vacío
- [ ] 13.3 Smoke test: checkout online REJECTED (tarjeta sandbox de rechazo) → NO se crea pedido, toast claro, usuario en CheckoutPage
- [ ] 13.4 Smoke test: checkout online PENDING (sandbox MP con tarjeta de pending) → NO se crea pedido (modo estricto), toast claro
- [ ] 13.5 Smoke test: checkout online con MP unreachable simulado (corta la red, mock) → NO se crea pedido, 502, retry funciona con mismo idempotency_key
- [ ] 13.6 Smoke test: checkout pickup+efectivo → pedido creado en `PENDIENTE` sin Pago, redirige a confirmación
- [ ] 13.7 Smoke test: avanzar un pedido del FSM completo `PENDIENTE → CONFIRMADO → EN_PREPARACION → TERMINADO → ENTREGADO` con rol PEDIDOS — verificar que los labels en UI son consistentes y el rename quedó aplicado en todos lados
- [ ] 13.8 Verificar OpenAPI en `/docs`: `POST /checkout/online`, `POST /checkout/pickup-efectivo` visibles; `POST /pedidos/` y `POST /pagos/` ausentes
- [ ] 13.9 Verificar que las opciones de pago aparecen UNA SOLA vez en el front (manual con browser DevTools — contar elementos `<input type="radio">`)
- [ ] 13.10 Verificar que "Mis pedidos" del cliente no muestra pedidos huérfanos (tras cleanup script, debería ser 0 fantasmas)

## 14. Documentación de specs vivas y decisiones

- [ ] 14.1 (Se ejecuta solo durante el archive, NO ahora.) Aplicar deltas a `openspec/specs/order-creation/spec.md` según el archivo del change
- [ ] 14.2 (Archive) Aplicar deltas a `openspec/specs/order-creation-frontend/spec.md`
- [ ] 14.3 (Archive) Aplicar deltas a `openspec/specs/order-state-machine/spec.md` (incluye rename EN_CAMINO → TERMINADO)
- [ ] 14.4 (Archive) Aplicar deltas a `openspec/specs/payment-mercadopago-frontend/spec.md`
- [ ] 14.5 (Archive) Aplicar deltas a `openspec/specs/payments-checkout-api/spec.md`
- [ ] 14.6 (Archive) Aplicar deltas a `openspec/specs/checkout-validation/spec.md`
- [ ] 14.7 (Archive) Crear `openspec/specs/checkout/spec.md` con los requirements del nuevo capability
- [ ] 14.8 Crear `docs/decisions/2026-05-17-checkout-strict-mode.md` documentando D3 (modo estricto MP) con rationale del usuario y trade-offs
- [ ] 14.9 Crear `docs/decisions/2026-05-17-rename-en-camino-to-terminado.md` documentando D13 (vocabulario unificado retiro/envío) con justificación
- [ ] 14.10 Actualizar `docs/CHANGES.md` mencionando este change como "refactor transversal" fuera del slot del roadmap original

## 15. Cleanup y commits

- [ ] 15.1 Borrar código muerto: `useCreateOrder`, `useInitPayment` independiente, `PaymentPage`, `PaymentResultPage` (si aplica), `orders.service.ts` viejo, `payments.service.ts` viejo
- [ ] 15.2 Borrar tests obsoletos correspondientes
- [ ] 15.3 Commits agrupados por capa (conventional commits, SIN "Co-Authored-By"):
  - `feat(checkout): add CheckoutService with pay-first atomic flow`
  - `feat(checkout): add POST /api/v1/checkout/online and /pickup-efectivo endpoints`
  - `refactor(orders): rename EN_CAMINO state to TERMINADO for unified pickup/delivery vocabulary`
  - `refactor(payments): remove POST /pagos/ endpoint, migrate logic to CheckoutService`
  - `refactor(orders): remove POST /pedidos/ endpoint`
  - `feat(frontend): integrate PaymentForm into CheckoutPage as inline step`
  - `fix(frontend): eliminate duplicated payment method options in checkout`
  - `refactor(frontend): rename EN_CAMINO to TERMINADO in types, badges, filters and chart`
  - `refactor(frontend): remove standalone PaymentPage and replace useCreateOrder with useCheckoutOnline/useCheckoutPickupEfectivo`
  - `docs: redefine PENDIENTE semantics, document strict MP mode (D3) and TERMINADO rename (D13)`
  - `chore(scripts): add cleanup_orphan_orders.sql for dev/testing`
- [ ] 15.4 Push a branch `feat/checkout-pay-first-flow`
- [ ] 15.5 NO archivar el change — esperar OK explícito del usuario tras revisión humana
