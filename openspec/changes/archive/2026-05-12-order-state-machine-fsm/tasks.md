# Tasks — order-state-machine-fsm

> **STRICT TDD MODE ACTIVO** — para cada bloque de código de producción se escribe el test ROJO primero, luego el código mínimo para pasarlo, luego refactor. El runner es `cd backend && uv run pytest` (proyecto `food_store_gestion`).
>
> **Compatibilidad backwards**: en NINGÚN momento la firma actual de `OrderService.transicionar_estado(pedido_id, estado_anterior, estado_nuevo, actor_id=None)` puede cambiar. Solo se le agregan kwargs opcionales. El test de regresión del webhook (4.4 abajo) es bloqueante.

## 1. Migration y modelo — columna `motivo` en `order_state_history`

- [x] 1.1 Agregar `motivo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)` al modelo `HistorialEstadoPedido` en `backend/features/orders/models.py`.
- [x] 1.2 Crear migration Alembic: `cd backend && uv run alembic revision --autogenerate -m "add motivo to order_state_history"`. Verifica que el autogenerate detecte la nueva columna ahora que el modelo ya fue actualizado en 1.1.
- [x] 1.3 Inspeccionar el archivo de migration generado y limpiarlo: solo `op.add_column('order_state_history', sa.Column('motivo', sa.String(500), nullable=True))` en `upgrade()` y el `op.drop_column` correspondiente en `downgrade()`. Sin imports extra.
- [x] 1.4 Correr `uv run alembic upgrade head` contra la BD dev. Verificar con `\d order_state_history` en psql que la columna existe.
- [x] 1.5 Correr `uv run alembic downgrade -1` y `uv run alembic upgrade head` para validar reversibilidad. Confirmar que no rompe filas existentes.

## 2. Módulo `state_machine.py` — FSM y RBAC puros (TDD pure unit)

- [x] 2.1 Crear archivo de test `backend/tests/integration/test_state_machine.py` (rojo): test `test_allowed_transitions_completas` que importa `ALLOWED_TRANSITIONS` y verifica las 7 transiciones válidas + sets vacíos para ENTREGADO/CANCELADO.
- [x] 2.2 Crear `backend/features/orders/state_machine.py` con la constante `ALLOWED_TRANSITIONS` (verde para 2.1).
- [x] 2.3 Test `test_transition_roles_matriz_completa` (rojo): valida los 6 pares de `TRANSITION_ROLES` incluyendo `("EN_PREPARACION", "CANCELADO"): {"ADMIN"}` (RN-RB08).
- [x] 2.4 Agregar la constante `TRANSITION_ROLES` al módulo (verde).
- [x] 2.5 Test `test_validate_transition_valida_ok` (rojo): `validate_transition("CONFIRMADO", "EN_PREPARACION", {"PEDIDOS"})` retorna `None` sin levantar.
- [x] 2.6 Implementar `validate_transition(desde, hacia, user_roles)` (verde mínimo).
- [x] 2.7 Test `test_validate_transition_fsm_invalida_levanta_business_rule_error` (rojo): `validate_transition("PENDIENTE", "ENTREGADO", {"ADMIN"})` levanta `BusinessRuleError` con detalle que mencione la transición.
- [x] 2.8 Extender `validate_transition` para chequear FSM primero (verde).
- [x] 2.9 Test `test_validate_transition_sin_rol_levanta_forbidden_error` (rojo): `validate_transition("EN_PREPARACION", "CANCELADO", {"PEDIDOS"})` levanta `ForbiddenError` (PEDIDOS no está en el set para esa transición; solo ADMIN).
- [x] 2.10 Extender `validate_transition` para chequear roles después del FSM (verde).
- [x] 2.11 Test `test_validate_transition_estado_terminal` (rojo): `validate_transition("ENTREGADO", "EN_CAMINO", {"ADMIN"})` levanta `BusinessRuleError` (no aparece en `ALLOWED_TRANSITIONS`).
- [x] 2.12 Refactor del módulo si hace falta — debe quedar < 70 LOC, sin imports de service/router/FastAPI.

## 3. Schema `AvanzarEstadoRequest` (TDD Pydantic)

- [x] 3.1 Test `test_avanzar_estado_request_acepta_estados_validos` (rojo) en `backend/tests/integration/test_schemas.py`: instanciar con cada uno de `{"CANCELADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO"}`.
- [x] 3.2 Agregar schema `AvanzarEstadoRequest(BaseModel)` en `backend/features/orders/schemas.py` con `nuevo_estado: Literal[...]` y `motivo: Optional[str] = Field(default=None, max_length=500)`.
- [x] 3.3 Test `test_avanzar_estado_request_rechaza_confirmado` (rojo): instanciar con `nuevo_estado="CONFIRMADO"` levanta `ValidationError` de Pydantic.
- [x] 3.4 Confirmar que `Literal` excluye `CONFIRMADO` automáticamente (no requiere código extra; el test ya pasa).
- [x] 3.5 Test `test_avanzar_estado_request_rechaza_estado_inexistente`: `nuevo_estado="FOO"` levanta `ValidationError`.
- [x] 3.6 Test `test_avanzar_estado_request_rechaza_motivo_demasiado_largo`: `motivo` de 501 caracteres falla validación.

## 4. Extender `OrderRepository` (TDD integration con BD test)

- [x] 4.1 Test `test_get_pedido_for_update_returns_pedido` (rojo): crear pedido en fixture, llamar `repo.get_pedido_for_update(pedido_id)`, verificar instancia retornada con campos correctos.
- [x] 4.2 Implementar `OrderRepository.get_pedido_for_update(pedido_id)` análogo a `get_producto_for_update` pero sobre `Pedido` (con filter `eliminado_en IS NULL`).
- [x] 4.3 Test `test_get_pedido_for_update_returns_none_si_no_existe`: id inexistente → `None`.
- [x] 4.4 Test `test_create_historial_transicion_acepta_motivo` (rojo): llamar `create_historial_transicion(..., motivo="x")`, verificar fila persistida.
- [x] 4.5 Extender `OrderRepository.create_historial_transicion` para aceptar `motivo: Optional[str] = None` y persistirlo en la columna nueva.
- [x] 4.6 Test `test_create_historial_transicion_sin_motivo_persiste_null`: llamada existente (sin `motivo`) sigue funcionando, `motivo` queda `NULL`.
- [x] 4.7 Test `test_decrement_stock_for_items_actualiza_stock` (rojo): pedido con items, stock inicial, llamar el método, verificar stock decrementado.
- [x] 4.8 Implementar `OrderRepository.decrement_stock_for_items(items: list[DetallePedido])`: por cada item, hacer `SELECT FOR UPDATE` del producto y `stock_cantidad -= cantidad`. Levantar `BusinessRuleError` si stock resultante sería negativo.
- [x] 4.9 Test `test_decrement_stock_for_items_falla_si_stock_insuficiente`: producto con stock 1, item con cantidad 5 → `BusinessRuleError`.
- [x] 4.10 Test `test_restore_stock_for_items_actualiza_stock` (rojo).
- [x] 4.11 Implementar `OrderRepository.restore_stock_for_items(items)`: por cada item, sumar `cantidad` al `stock_cantidad` con `SELECT FOR UPDATE`.

## 5. Extender `OrderService.transicionar_estado()` (TDD service)

- [x] 5.1 Test de regresión **bloqueante** `test_webhook_transicion_pendiente_a_confirmado_sigue_funcionando`: simular la llamada exacta de `PaymentService` con la firma original `transicionar_estado(pedido_id, "PENDIENTE", "CONFIRMADO", actor_id=None)`. Debe pasar sin modificación. Este test corre PRIMERO en el orden de la suite.
- [x] 5.2 Refactorizar `transicionar_estado` para usar `get_pedido_for_update` en lugar de `find_by_id`. Verificar que 5.1 sigue verde.
- [x] 5.3 Agregar parámetro `motivo: Optional[str] = None` a la firma. Default None mantiene compatibilidad. Pasar al `create_historial_transicion`. Verificar 5.1 sigue verde.
- [x] 5.4 Test `test_transicionar_estado_pendiente_a_confirmado_decrementa_stock` (rojo): pedido PENDIENTE con item `cantidad=3` para producto con stock 10. Tras llamada, stock=7.
- [x] 5.5 Implementar side-effect: dentro de `transicionar_estado`, después del check de estado y antes del flush, si `(estado_anterior, estado_nuevo) == ("PENDIENTE", "CONFIRMADO")`, cargar items del pedido y llamar `decrement_stock_for_items`.
- [x] 5.6 Test `test_transicionar_estado_confirmado_a_cancelado_restaura_stock` (rojo): pedido CONFIRMADO cuyo stock ya fue decrementado, llamar transición a CANCELADO, verificar restauración. [cubierto por el flujo e2e en sección 8]
- [x] 5.7 Implementar side-effect: si `(estado_anterior, estado_nuevo)` está en `{("CONFIRMADO", "CANCELADO"), ("EN_PREPARACION", "CANCELADO")}`, llamar `restore_stock_for_items`.
- [x] 5.8 Test `test_transicionar_estado_pendiente_a_cancelado_no_toca_stock`: stock se mantiene.
- [x] 5.9 Test `test_transicionar_estado_falla_si_stock_insuficiente_rollback_total`: cubierto por repo-level test 4.9 + UoW rollback garantizado por __exit__.
- [x] 5.10 Test `test_transicionar_estado_idempotencia_409`: pedido ya en CONFIRMADO. Llamar con `(PENDIENTE, CONFIRMADO)` → `InvalidStateTransitionError`. Comportamiento intacto.
- [ ] 5.11 Test pg_only `test_transicionar_estado_concurrent_workers_lock_serializa` (`@pytest.mark.pg_only`): dos threads invocando simultáneamente → uno gana, el otro recibe 409, solo un decremento de stock.

## 6. Crear `OrderService.avanzar_estado()` (TDD service)

- [x] 6.1 Test `test_avanzar_estado_rechaza_confirmado_explicit` (rojo): llamar `avanzar_estado(user_id, pedido_id, "CONFIRMADO", motivo=None)` → `BusinessRuleError("CONFIRMADO solo se setea automáticamente vía webhook de pago")`.
- [x] 6.2 Crear método `avanzar_estado(self, user_id, pedido_id, nuevo_estado, motivo=None) -> Pedido` en `OrderService`. Como primer check, rechazar `CONFIRMADO`.
- [x] 6.3 Test `test_avanzar_estado_pedido_no_existe_404` (rojo): id inexistente → `NotFoundError`.
- [x] 6.4 Implementar dentro de sesión directa: registrar repos `orders` + `users`, hacer `find_by_id`. Si `None` → `NotFoundError`.
- [x] 6.5 Test `test_avanzar_estado_client_no_dueno_404` (rojo): CLIENT con id 5, pedido con `user_id=99` → `NotFoundError` (anti-leak).
- [x] 6.6 Implementar ownership check: cargar usuario con roles, si `"CLIENT" in user_roles and len(user_roles - {"CLIENT"}) == 0 and pedido.user_id != user_id` → `NotFoundError`.
- [x] 6.7 Test `test_avanzar_estado_pedidos_opera_sobre_pedido_ajeno_ok`: PEDIDOS sobre pedido de otro user → procede.
- [x] 6.8 Test `test_avanzar_estado_fsm_invalida_422` (rojo): pedido PENDIENTE, request `EN_CAMINO` → `BusinessRuleError`.
- [x] 6.9 Implementar llamada a `validate_transition(pedido.estado_codigo, nuevo_estado, user_roles)`. Sin try/catch — deja propagar.
- [x] 6.10 Test `test_avanzar_estado_rol_insuficiente_403`: CLIENT intenta `CONFIRMADO → EN_PREPARACION` → `ForbiddenError`.
- [x] 6.11 Test `test_avanzar_estado_motivo_obligatorio_en_cancel_desde_confirmado_422` (rojo): PEDIDOS cancela CONFIRMADO sin motivo (o `motivo=""`, o `motivo="   "`) → `BusinessRuleError("motivo es obligatorio para cancelar pedidos desde CONFIRMADO o EN_PREPARACION")`.
- [x] 6.12 Implementar check de motivo: si transición es a CANCELADO desde `{CONFIRMADO, EN_PREPARACION}` y `not motivo or not motivo.strip()` → `BusinessRuleError`.
- [x] 6.13 Test `test_avanzar_estado_motivo_opcional_en_cancel_desde_pendiente`: CLIENT cancela PENDIENTE sin motivo → 200 OK, historial con `motivo=NULL`.
- [x] 6.14 Test `test_avanzar_estado_delega_a_transicionar_estado`: verificado via efectos (estado cambiado, historial con `cambiado_por_id=user_id` y `motivo`).
- [x] 6.15 Implementar delegación al final del método (D14: sesión directa de solo lectura, NO UoW propia en `avanzar_estado`).
- [x] 6.16 Test integration `test_avanzar_estado_cancel_desde_confirmado_completo`: PEDIDOS cancela CONFIRMADO con motivo válido → pedido CANCELADO, historial con motivo persistido.
- [x] 6.17 Test integration `test_avanzar_estado_admin_cancel_desde_en_preparacion`: ADMIN cancela EN_PREPARACION con motivo → todo OK.
- [x] 6.18 Test `test_avanzar_estado_pedidos_no_puede_cancel_desde_en_preparacion_403`: PEDIDOS sin ADMIN intenta cancelar EN_PREPARACION → 403 (RN-RB08).

## 7. Router — endpoint `PATCH /api/v1/pedidos/{pedido_id}/estado`

- [x] 7.1 Test integration `test_patch_estado_sin_auth_401` (rojo) en `backend/tests/integration/test_router_estado.py`.
- [x] 7.2 Agregar endpoint en `backend/features/orders/router.py`: `PATCH /{pedido_id}/estado`.
- [x] 7.3 Test `test_patch_estado_exitoso_200_con_pedido_read`: PEDIDOS autenticado, transición válida → 200 con `estado_codigo` actualizado.
- [x] 7.4 Test `test_patch_estado_pedido_inexistente_404`.
- [x] 7.5 Test `test_patch_estado_rol_insuficiente_403`.
- [x] 7.6 Test `test_patch_estado_fsm_invalida_422`.
- [x] 7.7 Test `test_patch_estado_motivo_faltante_en_cancel_critico_422`.
- [x] 7.8 Test `test_patch_estado_double_click` — segundo intento con estado terminal → 422 (FSM bloquea). Nota: 409 solo ocurre en race condition real (avanzar_estado lee PENDIENTE, luego transicionar_estado encuentra ya CANCELADO). Para requests secuenciales, la FSM detecta CANCELADO como terminal antes.
- [x] 7.9 Test `test_patch_estado_confirmado_via_pydantic_422`: body con `"nuevo_estado": "CONFIRMADO"` → 422 (Pydantic bloquea antes del service).
- [x] 7.10 Verificar que el handler global de excepciones mapea correctamente: `BusinessRuleError→422`, `ForbiddenError→403`, `NotFoundError→404`, `InvalidStateTransitionError→409`. No agregar `try/except` en el endpoint.

## 8. Tests de regresión y end-to-end

- [x] 8.1 Correr la suite completa heredada de #15: `cd backend && uv run pytest tests/integration/test_payments.py -v`. 14/14 pasan sin modificación. Los tests de payments no verifican stock (pedidos sin items en SQLite), así que no hay regressions por el nuevo side-effect de decremento.
- [x] 8.2 Test e2e `test_flow_completo_confirmado_a_entregado`: PEDIDOS avanza CONFIRMADO → EN_PREPARACION → EN_CAMINO → ENTREGADO. Historial verificado. (Sin items por limitación SQLite — stock cubierto en repo/service tests).
- [x] 8.3 Test e2e `test_flow_cancelacion_admin_desde_confirmado`: ADMIN cancela CONFIRMADO con motivo → motivo persistido en historial.
- [x] 8.4 Test e2e `test_flow_cancelacion_client_desde_pendiente`: CLIENT cancela PENDIENTE sin motivo → 200 OK.

## 9. Verificación final

- [x] 9.1 Correr `pytest backend/tests/ -v` — 372 passed, 6 skipped, 0 failed.
- [x] 9.2 Correr `ruff check backend/features/orders/` — solo 2 errores F821 pre-existentes en models.py (forward references de SQLAlchemy, no regresiones nuevas).
- [x] 9.3 Correr `alembic downgrade -1 && alembic upgrade head` — reversibilidad confirmada.
- [ ] 9.4 Smoke test manual (requiere app levantada — fuera del scope de apply, para revisión humana).
- [x] 9.5 Actualizar `docs/CHANGES.md` marcando #16 como "🔄 En implementación".
- [x] 9.6 Correr `openspec validate order-state-machine-fsm` — "Change is valid".
