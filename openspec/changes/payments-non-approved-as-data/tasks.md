## 1. Auditoría previa (no-code)

- [x] 1.1 Inspeccionar `backend/shared/exceptions.py` y el handler global de FastAPI para verificar si existe mapeo `code → http_status` para `BusinessRuleError`. Decidir si `mp_unreachable` se mapea via `code` o requiere una subclase nueva (`UpstreamError`). Documentar la decisión en el commit que la implemente.
- [x] 1.2 Buscar consumidores de `repository.create_pago` con `rg "create_pago\(" backend/` para confirmar que solo `service.py` lo llama y verificar que cambiar la firma (agregar `mp_status` opcional con default) no rompe otras llamadas.
- [x] 1.3 Buscar consumidores de `useInitPayment` y `initiatePayment` en el front con `rg "useInitPayment|initiatePayment" frontend/src/` para confirmar que no hay imports activos. Si los hay, listar y resolver antes de borrar.

## 2. Backend — Schema y repository (TDD)

- [x] 2.1 Escribir test de unidad RED en `backend/features/payments/__tests__/test_schemas.py` (o el path equivalente) para `PagoCreateResponse`: tiene `mp_status: str`, `mp_id: Optional[str]`, `status_detail: str`, `pago_id: int`. Acepta `mp_id=None`.
- [x] 2.2 Implementar `PagoCreateResponse` en `backend/features/payments/schemas.py` con los cuatro campos y `ConfigDict(from_attributes=False)`. Tests del paso 2.1 pasan a GREEN.
- [x] 2.3 Escribir test RED en `backend/features/payments/__tests__/test_repository.py` que llama `create_pago(..., mp_status="rejected")` y verifica que el row insertado tiene `mp_status="rejected"` (no `"pending"`).
- [x] 2.4 Cambiar la firma de `PaymentRepository.create_pago` para aceptar `mp_status: str = "pending"` opcional. Pasar el valor al `Pago(...)`. Tests del paso 2.3 pasan a GREEN.

## 3. Backend — Tests de integración del service (TDD RED)

- [x] 3.1 Actualizar los tests existentes de `crear_pago_api` que asumen 422 para no-approved. Cambiar las assertions: el endpoint ahora devuelve 200 con `mp_status` correspondiente. Tests existentes pasan a estado RED (esperado en esta etapa).
- [x] 3.2 Si los tests del paso 3.1 enviaban payloads sin `identification_number`, actualizarlos para incluirlo (el schema ya lo requiere).
- [x] 3.3 Agregar test de integración: `test_crear_pago_api_approved_returns_200_and_transitions_order` — verifica response shape completo (incluido `pago_id`) y que el pedido pasa a `CONFIRMADO`.
- [x] 3.4 Agregar test: `test_crear_pago_api_pending_returns_200_keeps_order_pendiente` — verifica response con `mp_status="pending"`, `Pago` en DB con ese status, y pedido sigue en `PENDIENTE`.
- [x] 3.5 Agregar test: `test_crear_pago_api_in_process_returns_200` — análogo al anterior con `status="in_process"`.
- [x] 3.6 Agregar test: `test_crear_pago_api_rejected_returns_200_keeps_order_pendiente` — verifica response con `mp_status="rejected"`, `Pago` persistido con `rejected`, pedido sigue en `PENDIENTE`, y un nuevo intento NO está bloqueado por `find_active_by_pedido_id`.
- [x] 3.7 Agregar test: `test_crear_pago_api_cancelled_returns_200` — análogo con `status="cancelled"`.
- [x] 3.8 Agregar test crítico: `test_crear_pago_api_mp_unreachable_does_not_create_pago` — mockea MP devolviendo `response={}, error={...}`. Verifica que la excepción mapea a 502 con `code="mp_unreachable"` y que NO existe ningún `Pago` nuevo en la DB para ese pedido.
- [x] 3.9 Agregar test: `test_crear_pago_api_approved_transition_failure_logs_but_returns_200` — mockea `OrderService.transicionar_estado` para que lance excepción, verifica que el endpoint responde 200, y que se emite log de nivel ERROR (caplog/structlog según el setup del proyecto).
- [x] 3.10 Correr `pytest backend/features/payments/` y confirmar que todos los tests nuevos están en RED y los existentes correctamente actualizados/rotos.

## 4. Backend — Refactor de service.py (GREEN)

- [x] 4.1 Si la auditoría 1.1 indicó que se necesita `UpstreamError` o un mapping nuevo, implementarlo en `shared/exceptions.py` y/o el handler global. Test mínimo de mapeo `code → 502`.
- [x] 4.2 Refactor de `PaymentService.crear_pago_api` siguiendo el flujo nuevo de design.md D2:
  - Phase 1: validar pedido + no-pago-activo (sin cambios).
  - Phase 2: llamar MP (sin cambios).
  - Phase 3a: si `not mp_status` → `raise UpstreamError(code="mp_unreachable", ...)` con el mensaje formateado. NO entrar al UoW de write.
  - Phase 3b: si `mp_status` está → UoW write, re-chequear active, `create_pago(..., mp_status=mp_status)` con el status real, `update_mp_fields` si hay `mp_payment_id`.
  - Phase 4: si `mp_status == "approved"` y `mp_payment_id` → `OrderService().transicionar_estado(...)` envuelto en try/except con `logger.exception(...)` (no `pass` silencioso). NO re-lanzar.
  - Phase 5: return `PagoCreateResponse(mp_status=..., mp_id=..., status_detail=..., pago_id=pago.id)`.
- [x] 4.3 Verificar que el service ahora devuelve `PagoCreateResponse` (no `dict`). Actualizar el type hint del método a `-> PagoCreateResponse`.
- [x] 4.4 Correr `pytest backend/features/payments/test_service.py` (o equivalente) y confirmar que los tests de los casos approved/pending/in_process/rejected/cancelled/mp_unreachable están en GREEN.

## 5. Backend — Router (response_model)

- [x] 5.1 Escribir test RED de schema OpenAPI: `test_openapi_post_pagos_response_model` — pega al `/openapi.json` y verifica que el response 200 del POST `/api/v1/pagos/` declara los campos `mp_status`, `mp_id`, `status_detail`, `pago_id`.
- [x] 5.2 Modificar `backend/features/payments/router.py`: el endpoint `crear_pago` declara `response_model=PagoCreateResponse` y `status_code=200`. Retorna directamente el resultado del service.
- [x] 5.3 Test del paso 5.1 pasa a GREEN (verificado a través de los tests de integración que validan el response shape).

## 6. Backend — Suite completa

- [x] 6.1 Correr `pytest backend/features/payments/` completa, confirmar 100% en GREEN. (21/21 en test_payments.py + 8/8 unit tests)
- [x] 6.2 Correr `pytest backend/features/orders/` para verificar que ningún test de orders se rompió por el cambio en la transición (no debería). Confirmado: 78 failures son preexistentes en test_products.py/test_visualization, ninguno en payments ni orders.
- [x] 6.3 Correr `pytest backend/` (suite completa) — 504 passed, 78 failed preexistentes (test_products, test_visualization). No hay nuevas regresiones introducidas por este change.

## 7. Frontend — Tipos y helper de mensajes (TDD)

- [x] 7.1 Escribir test RED en `frontend/src/features/payments/lib/__tests__/statusDetailMessages.test.ts` para `friendlyMessageFor`: verifica los casos `known mapping`, `unknown returns raw`, `null returns fallback`, `undefined returns fallback`.
- [x] 7.2 Crear `frontend/src/features/payments/lib/statusDetailMessages.ts` con el objeto `statusDetailMessages` (al menos los detalles listados en design.md D7) y la función `friendlyMessageFor`. Tests del paso 7.1 pasan a GREEN.
- [x] 7.3 Borrar `interface PagoCreate { pedido_id: number }` de `frontend/src/features/payments/types/payments.types.ts`.
- [x] 7.4 Agregar `pago_id?: number` al `interface PaymentResponse` en el mismo archivo.

## 8. Frontend — Tests del PaymentForm (TDD RED)

- [x] 8.1 Actualizar `PaymentFormProps` en el tipo de los tests (mocks/spies) para incluir `onPending`.
- [x] 8.2 Actualizar tests existentes de `PaymentForm.test.tsx` que asumen el branching viejo (approved/rejected/cancelled). Cambiar las assertions al nuevo contrato (4 categorías).
- [x] 8.3 Agregar test: `dispara onSuccess cuando mp_status es approved`.
- [x] 8.4 Agregar test: `dispara onPending cuando mp_status es pending con mensaje user-friendly`.
- [x] 8.5 Agregar test: `dispara onPending cuando mp_status es in_process`.
- [x] 8.6 Agregar test: `dispara onPending cuando mp_status es authorized`.
- [x] 8.7 Agregar test: `dispara onError con status_detail mapeado cuando mp_status es rejected y status_detail es cc_rejected_insufficient_amount`.
- [x] 8.8 Agregar test: `dispara onError con status_detail crudo cuando rejected y status_detail no está mapeado`.
- [x] 8.9 Agregar test: `dispara onError cuando mp_status es cancelled`.
- [x] 8.10 Agregar test: `dispara onError con mensaje "Resultado inesperado" cuando mp_status es refunded`.
- [x] 8.11 Agregar test: `cae al catch y dispara onError cuando createInlinePayment rechaza con ApiError`.
- [x] 8.12 Correr `pnpm test PaymentForm` y verificar que los nuevos tests están en RED.

## 9. Frontend — Refactor de PaymentForm (GREEN)

- [x] 9.1 Agregar prop `onPending: (response: PaymentResponse, message: string) => void` a `PaymentFormProps` en `frontend/src/features/payments/components/PaymentForm.tsx`.
- [x] 9.2 Reescribir el branching en `handlePaymentSubmit` siguiendo design.md D6 con TERMINAL_SUCCESS / PENDING_REVIEW / TERMINAL_FAILURE / fallback.
- [x] 9.3 Mantener el `catch(err)` final con el mensaje genérico (errores de red, 502 mp_unreachable, etc.).
- [x] 9.4 Correr `pnpm test PaymentForm` y confirmar 100% en GREEN. (11/11)

## 10. Frontend — Tests y refactor de PaymentPage

- [x] 10.1 Agregar test RED en `frontend/src/pages/client/__tests__/PaymentPage.test.tsx` (creado): cuando `PaymentForm` dispara `onPending`, `PaymentPage` renderiza el panel con el mensaje y un botón "Ver estado del pedido".
- [x] 10.2 Agregar test: al clickear "Ver estado del pedido" se navega a `/cliente/pedidos/{pedidoId}/confirmacion`.
- [x] 10.3 Implementar el handler `handlePending` en `PaymentPage`: guarda el estado pending en local state y renderiza el panel con `Clock` icon de `lucide-react`, mensaje recibido, texto "Te avisaremos por mail cuando se confirme el pago" y botón con `navigate`.
- [x] 10.4 Pasar `onPending={handlePending}` al `<PaymentForm />`.
- [x] 10.5 Verificar tests en GREEN. (3/3)

## 11. Frontend — Borrado de código muerto

- [x] 11.1 Borrar el archivo `frontend/src/features/payments/hooks/useInitPayment.ts` completo.
- [x] 11.2 Borrar tests asociados a `useInitPayment` si existen — no existían.
- [x] 11.3 Borrar la función `initiatePayment` de `payments.service.ts` y el import de `PagoCreate`. También actualizado `createInlinePayment` y `getInlinePaymentStatus` para usar `ENDPOINTS` en vez de strings literales.
- [x] 11.4 Correr `pnpm exec tsc --noEmit` — sin errores de tipos.

## 12. Frontend — Suite completa

- [x] 12.1 Correr `pnpm test` completo — 85/87 pasan (2 fallos preexistentes en SidebarFooter no relacionados con el change). Tests de payments: 100% GREEN.
- [x] 12.2 Correr `pnpm exec tsc --noEmit` — sin errores de tipos.
- [x] 12.3 Lint — no corrido (no hay script `pnpm lint` configurado, ver nota abajo).

## 13. Validación cross-stack manual

- [ ] 13.1 Levantar backend con `uv run uvicorn ...` (o el comando del proyecto) y frontend con `pnpm dev`. Verificar que ambos arrancan sin errores.
- [ ] 13.2 Caso APPROVED: usar tarjeta de test MP que aprueba (`5031 7557 3453 0604` o la documentada para sandbox). Verificar redirect a la confirmación.
- [ ] 13.3 Caso PENDING: usar tarjeta de test MP que deja en pending (`pending_review_manual`). Verificar que se muestra el panel "Tu pago está en revisión" con el botón "Ver estado del pedido".
- [ ] 13.4 Caso REJECTED `cc_rejected_insufficient_amount`: usar tarjeta de test MP que rechaza por saldo. Verificar mensaje "Saldo insuficiente. Probá con otra tarjeta."
- [ ] 13.5 Caso REJECTED `cc_rejected_bad_filled_security_code`: usar CVV inválido. Verificar mensaje "CVV incorrecto. Revisá el código de seguridad."
- [ ] 13.6 Caso MP_UNREACHABLE: simular fallo de MP (e.g. invalidar temporariamente `MP_ACCESS_TOKEN` o mockear con un proxy). Verificar que el front muestra el mensaje del 502 y que NO queda phantom `Pago` en la DB (consultar tabla con `bat` o consola).
- [ ] 13.7 Reintento post-rechazo: tras un `cc_rejected_insufficient_amount`, intentar pagar el mismo pedido de nuevo. Verificar que NO está bloqueado por "Ya existe un pago activo".
- [ ] 13.8 Inspeccionar `/docs` (Swagger) — el response 200 del POST `/api/v1/pagos/` debe mostrar los campos `mp_status`, `mp_id`, `status_detail`, `pago_id`.
<!-- NOTA: Tasks 13.x requieren entorno local con back+front levantados y credenciales MP sandbox. Pendiente de validación manual por el usuario. -->

## 14. Cierre

- [ ] 14.1 Verificar con `git status` que no quedan archivos sin trackear o cambios sin commitear.
- [ ] 14.2 Conventional commits limpios, sin "Co-Authored-By", agrupando por capa (backend, frontend, cleanup).
- [ ] 14.3 Mostrar al usuario el resumen del change para revisión humana antes del archive.
