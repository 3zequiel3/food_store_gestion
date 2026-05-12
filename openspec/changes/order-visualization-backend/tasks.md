## 1. Schemas Pydantic (sin tocar PedidoRead existente)

- [ ] 1.1 Agregar `PedidoListItem` en `backend/features/orders/schemas.py` con campos `id`, `estado_codigo`, `total: Decimal`, `costo_envio: Decimal`, `forma_pago_codigo`, `creado_en`, `items_count: int`. Usar `model_config = ConfigDict(from_attributes=True)`.
- [ ] 1.2 Agregar `PaginatedPedidos` con `items: list[PedidoListItem]`, `total: int`, `page: int`, `limit: int`.
- [ ] 1.3 Agregar `ItemDetalle` con `id`, `producto_id`, `nombre_snapshot`, `precio_snapshot: Decimal`, `cantidad`, `personalizacion: list[int] | None`.
- [ ] 1.4 Agregar `HistorialItem` con `id`, `estado_anterior_codigo: str | None`, `estado_nuevo_codigo: str`, `cambiado_por_id: int | None`, `motivo: str | None`, `creado_en`.
- [ ] 1.5 Agregar `PagoSummary` con `id`, `status: str`, `monto: Decimal`, `fecha`.
- [ ] 1.6 Agregar `PedidoDetalle` con todos los campos del pedido (`id`, `user_id`, `estado_codigo`, `total`, `costo_envio`, `forma_pago_codigo`, `direccion_snapshot`, `notas`, `creado_en`, `actualizado_en`) + `items: list[ItemDetalle]` + `historial: list[HistorialItem]` + `pagos: list[PagoSummary]`.
- [ ] 1.7 Agregar `PedidoListFilters` (no expuesto al cliente, uso interno en service) con `estado: Literal[...] | None`, `desde: date | None`, `hasta: date | None`, `q: str | None`, `page: int = 1`, `limit: int = 20`. Validar con `Field(ge=1, le=100)` en `limit` y `Field(ge=1)` en `page`. Agregar `@model_validator(mode='after')` que verifique `desde <= hasta` cuando ambos están seteados (lanza `ValueError` si no, Pydantic lo convierte a 422).
- [ ] 1.8 Verificar que `PedidoRead` existente NO se modifica (sigue usado por POST/PATCH).

## 2. Repository — listado role-aware y conteo

- [ ] 2.1 Agregar `OrderRepository.list_with_filter(*, user_id: int | None, estado: str | None, desde: date | None, hasta: date | None, q: str | None, page: int, limit: int) -> list[Pedido]` en `backend/features/orders/repository.py`. Construir el query con SQLAlchemy 2.0 `select(Pedido)`:
  - Si `user_id is not None`: aplicar `where(Pedido.user_id == user_id)`.
  - Si `estado is not None`: aplicar `where(Pedido.estado_codigo == estado)`.
  - Si `desde is not None`: aplicar `where(Pedido.creado_en >= datetime.combine(desde, time.min))`.
  - Si `hasta is not None`: aplicar `where(Pedido.creado_en < datetime.combine(hasta + timedelta(days=1), time.min))` (rango inclusivo del día).
  - Si `q is not None`: si `q.isdigit()` aplicar `where(Pedido.id == int(q))`; en otro caso `join(Pedido.usuario).where(func.concat(Usuario.nombre, ' ', Usuario.apellido).ilike(f'%{q}%'))`.
  - `order_by(Pedido.creado_en.desc())`.
  - `offset((page - 1) * limit).limit(limit)`.
  - Soft-delete: respetar el filtro `eliminado_en IS NULL` (heredado del BaseRepository si aplica).
- [ ] 2.2 Agregar `OrderRepository.count_with_filter(*, user_id, estado, desde, hasta, q) -> int` que aplica los mismos `WHERE` que `list_with_filter` pero ejecuta `select(func.count(Pedido.id))`. Mismo manejo del `q` (int vs ILIKE con join). NO aplica offset ni limit.
- [ ] 2.3 Agregar subquery para `items_count` en `list_with_filter`. Opción recomendada: `select(Pedido, func.count(DetallePedido.id).label("items_count")).outerjoin(DetallePedido).group_by(Pedido.id)`. Devolver tuplas y mappear en el service, O agregar `items_count` como `@property` no persistida en el modelo y poblarla en el service.
- [ ] 2.4 Extender `OrderRepository.get_pedido_completo(pedido_id: int, user_id: int | None) -> Pedido | None`: cambiar el tipo de `user_id` a `int | None`. Si `user_id is not None`, mantener el filtro `where(Pedido.user_id == user_id)`; si `None`, omitirlo. Agregar `selectinload(Pedido.pagos)` a los `options(...)` existentes (que ya tienen `selectinload(items, historial)`).

## 3. Service — RBAC dinámico y mapeo a schemas

- [ ] 3.1 Definir `_is_admin_view(user) -> bool` privada en `OrderService` que devuelve `True` si el usuario tiene rol `PEDIDOS` o `ADMIN`, `False` si solo tiene `CLIENT`, y RAISE `ForbiddenError` si solo tiene `STOCK` (sin CLIENT/PEDIDOS/ADMIN).
- [ ] 3.2 Implementar `OrderService.listar_pedidos(user, filtros: PedidoListFilters) -> PaginatedPedidos`:
  - Determinar `user_id` con `_is_admin_view`: si admin view → `user_id = None`; si CLIENT → `user_id = user.id`.
  - Dentro del UoW: invocar `repo.count_with_filter(user_id=..., **filtros sin page/limit)` para obtener `total`.
  - Si `total == 0`: retornar `PaginatedPedidos(items=[], total=0, page=filtros.page, limit=filtros.limit)` (skip query de listado).
  - En otro caso: invocar `repo.list_with_filter(...)` con los filtros completos.
  - Mapear cada resultado a `PedidoListItem` (asegurar `items_count` poblado según la opción elegida en 2.3).
  - Retornar `PaginatedPedidos(items=..., total=..., page=filtros.page, limit=filtros.limit)`.
- [ ] 3.3 Implementar `OrderService.get_pedido_detalle(user, pedido_id: int) -> PedidoDetalle`:
  - `_is_admin_view(user)` para validar acceso (rechaza STOCK).
  - `user_id_filter = None if admin_view else user.id`.
  - Dentro del UoW: `pedido = repo.get_pedido_completo(pedido_id, user_id=user_id_filter)`.
  - Si `pedido is None`: raise `NotFoundError("Pedido no encontrado")` — MISMO mensaje y status independientemente de si el pedido no existe o existe pero es ajeno (anti-leak R4).
  - Construir `PedidoDetalle` mapeando los campos del pedido + `items` ordenados por `id ASC` + `historial` ordenado por `creado_en ASC` + `pagos` ordenados por `fecha DESC`.
  - Retornar `PedidoDetalle`.

## 4. Router — endpoints role-aware

- [ ] 4.1 En `backend/features/orders/router.py`, agregar `@router.get("", response_model=PaginatedPedidos)`:
  - Recibir `current_user: Annotated[Usuario, Depends(get_current_user)]`.
  - Recibir los query params como `Annotated[PedidoListFilters, Query()]` para que FastAPI los aplane y Pydantic valide (incluyendo el `model_validator` de `desde <= hasta`).
  - Invocar `service.listar_pedidos(current_user, filtros)`.
  - Mapear excepciones: `ForbiddenError → 403` (delegar al exception handler global si existe).
- [ ] 4.2 Agregar `@router.get("/{pedido_id}", response_model=PedidoDetalle)`:
  - Recibir `pedido_id: int` (FastAPI valida que sea entero — si no, 422 automático).
  - Recibir `current_user: Annotated[Usuario, Depends(get_current_user)]`.
  - Invocar `service.get_pedido_detalle(current_user, pedido_id)`.
  - Mapear excepciones: `NotFoundError → 404`, `ForbiddenError → 403` (delegar al handler global).
- [ ] 4.3 Verificar que los endpoints existentes (POST `/api/v1/pedidos` y PATCH `/api/v1/pedidos/{id}/estado`) siguen funcionando — esta change es aditiva.

## 5. Tests pytest internos (TDD: escribir RED, hacer GREEN)

- [ ] 5.1 `tests/features/orders/test_visualization_list.py`:
  - `test_client_solo_ve_sus_propios_pedidos`: crea 3 pedidos de user A y 2 de user B; user A consulta y recibe solo sus 3.
  - `test_pedidos_role_ve_todos`: con 5 pedidos de distintos users, un PEDIDOS recibe los 5.
  - `test_admin_role_ve_todos`: ídem con ADMIN.
  - `test_stock_role_rechazado_403`: usuario con rol STOCK exclusivo recibe 403.
  - `test_sin_auth_retorna_401`: sin Authorization header → 401.
  - `test_filtro_por_estado`: con 3 CONFIRMADO y 2 ENTREGADO, `?estado=CONFIRMADO` retorna 3.
  - `test_filtro_estado_invalido_422`: `?estado=PAGADO` → 422.
  - `test_filtro_por_rango_fechas`: pedidos en 3 fechas distintas, filtro de mes intermedio.
  - `test_desde_mayor_que_hasta_retorna_422`: `?desde=2026-12-31&hasta=2026-01-01` → 422 con mensaje claro.
  - `test_filtro_q_numerico_busca_por_id`: `?q=42` retorna solo el pedido id=42.
  - `test_filtro_q_string_busca_por_nombre_ilike`: crear cliente "Juan Pérez", `?q=pérez` (lowercase) retorna sus pedidos.
  - `test_paginacion_page_2`: 25 pedidos, `?page=2&limit=10` retorna items 11..20 en orden DESC.
  - `test_paginacion_fuera_de_rango`: `?page=10&limit=10` → `items=[]`, `total=25`.
  - `test_orden_creado_en_desc`: 3 pedidos en t1<t2<t3 → primer item es el de t3.
  - `test_total_respeta_filtros_de_ownership`: CLIENT con 3 pedidos propios + 10 ajenos → `total=3` (no 13).
  - `test_lista_no_eager_loadea_relaciones`: assertion con `sqlalchemy.event.listen("before_cursor_execute")` que verifica que el número de queries no escala con el número de pedidos en `items`.
  - `test_limit_fuera_de_rango_422`: `?limit=500` → 422; `?limit=0` → 422.
  - `test_items_count_correcto`: pedido con 3 DetallePedido → `items_count=3` en el response.
- [ ] 5.2 `tests/features/orders/test_visualization_detail.py`:
  - `test_client_consulta_su_propio_pedido_200`: CLIENT dueño obtiene `PedidoDetalle` completo.
  - `test_client_pedido_ajeno_retorna_404_no_403`: CLIENT pidiendo pedido de otro → 404; mensaje EXACTO igual al de pedido inexistente (asserción de equality contra response body de "no existe").
  - `test_pedidos_role_consulta_cualquier_pedido_200`: PEDIDOS no dueño → 200.
  - `test_admin_role_consulta_cualquier_pedido_200`: ADMIN → 200.
  - `test_pedido_inexistente_404`: id=9999 → 404 con `NotFoundError("Pedido no encontrado")`.
  - `test_stock_role_rechazado_403`: STOCK → 403.
  - `test_sin_auth_401`: sin token → 401.
  - `test_detalle_incluye_items_con_snapshots`: pedido con 2 items, response trae los `nombre_snapshot` y `precio_snapshot` originales (aunque el producto haya cambiado de precio después).
  - `test_detalle_incluye_historial_cronologico`: pedido con varias transiciones; `historial` está ordenado por `creado_en ASC`.
  - `test_detalle_incluye_pagos_orden_fecha_desc`: pedido con 1 pago `approved` → `pagos[0].status=="approved"`.
  - `test_detalle_pedido_sin_pagos_devuelve_lista_vacia`: pedido PENDIENTE → `pagos == []` (no `null`).
  - `test_detalle_pedido_retiro_local_direccion_null`: pedido sin `direccion_id` → `direccion_snapshot is None`, `costo_envio == "0.00"`.
  - `test_detalle_motivo_persistido_en_historial`: pedido cancelado con motivo → encontrar entrada en `historial` con `motivo` exacto.
  - `test_detalle_decimal_serializado_como_string`: `response.json()["total"]` es `str`, no `float`.
- [ ] 5.3 `tests/features/orders/test_visualization_repo.py` (unit tests del repository):
  - `test_list_with_filter_user_id_filtra_ownership`: con `user_id=5`, solo retorna pedidos de ese user.
  - `test_list_with_filter_user_id_none_no_filtra`: con `user_id=None`, retorna todos.
  - `test_count_with_filter_consistente_con_list`: para los mismos filtros, `count == len(list)` (sin paginar).
  - `test_get_pedido_completo_user_id_none_no_filtra_ownership`: pedido pertenece a user A, llamar con `user_id=None` → retorna el pedido.
  - `test_get_pedido_completo_user_id_mismatch_retorna_none`: pedido pertenece a A, llamar con `user_id=B.id` → retorna `None`.

## 6. Suite TestSprite (end-to-end contra Postgres real)

- [ ] 6.1 Generar test plan TestSprite para `order-visualization-backend` con 5-6 escenarios end-to-end:
  - E2E-1: CLIENT crea pedido, lo consulta en su listado, y abre el detalle.
  - E2E-2: PEDIDOS consulta listado con filtro `estado=CONFIRMADO` y abre detalle.
  - E2E-3: CLIENT intenta acceder a pedido ajeno → 404 con mensaje exacto "Pedido no encontrado".
  - E2E-4: Búsqueda por `q=<nombre_cliente>` filtra correctamente.
  - E2E-5: Paginación: 25 pedidos creados, `page=2&limit=10` retorna items correctos.
  - E2E-6: STOCK consulta listado → 403.
- [ ] 6.2 Ejecutar la suite TestSprite y adjuntar resultado al PR (badge / link al dashboard).

## 7. Verificación final y limpieza

- [ ] 7.1 Correr `pytest backend/tests/features/orders/ -v` y verificar todos los tests verdes.
- [ ] 7.2 Verificar manualmente con `httpie` o `curl` cada endpoint:
  - `GET /api/v1/pedidos` como CLIENT, PEDIDOS, ADMIN, STOCK (verificar 200/200/200/403).
  - `GET /api/v1/pedidos/{id}` con todos los casos del scenario list.
- [ ] 7.3 Verificar que `openspec validate order-visualization-backend --strict` pasa sin errores.
- [ ] 7.4 Verificar que el `openspec status --change order-visualization-backend --json` reporta `isComplete: true` con todos los `applyRequires` en `done`.
- [ ] 7.5 Actualizar `docs/CHANGES.md` marcando #17 como completado (solo si el roadmap lleva ese registro).
