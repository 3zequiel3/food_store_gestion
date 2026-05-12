## Context

Sprint 5 #17 cierra el ciclo de pedidos: ya se pueden crear (#14) y transicionar (#15, #16), pero no consultar. US-049 a US-052 son prioridad **Alta** y todas dependen de la lectura role-aware.

Restricciones del proyecto que condicionan el diseño:

- **Spec canónica > Historias**. `docs/Descripcion.txt:285` define **un solo endpoint** `GET /api/v1/pedidos` con comportamiento role-aware. Las "Notas Técnicas" de US-051 sugieren un `/api/admin/pedidos` separado, pero la regla del repo (`CLAUDE.md` §"Spec canónica") manda usar la versión técnica unificada.
- **Architecture**: Router → Service → UoW → Repository → Model. No se puede saltear capas. Toda lógica role-aware vive en el service; el router solo extrae `current_user` y delega.
- **Anti-leak 404** ya consolidado en archives previos (`order-state-machine`, `order-creation`): cuando un CLIENT pide un recurso ajeno, la respuesta es 404 (no 403) para no filtrar existencia. Esta capability extiende ese patrón a GETs de pedidos.
- **Decimal end-to-end** para montos (`total`, `costo_envio`, `precio_snapshot`, `monto` de pago). No flotantes.
- **`expire_on_commit=False`** en el sessionmaker (ya configurado). El detalle se devuelve **después** del commit del UoW; sin esa flag, acceder a relaciones cargadas levantaría DetachedInstanceError. Esta change depende de esa configuración.
- **Convención de paginación** del proyecto (ya validada en productos/categorias): `{items, total, page, limit}`. Mantenerla acá da consistencia y permite reutilizar componentes de frontend.
- **`get_pedido_completo(pedido_id, user_id)`** ya existe en `repository.py:287` con `selectinload(items, historial)`. Fue dejado preparado para este change — la extensión es agregar `selectinload(pagos)` y soportar `user_id=None`.

## Goals / Non-Goals

**Goals:**

- G1. Habilitar US-049, US-050, US-051, US-052 con dos endpoints role-aware en una sola capability.
- G2. Anti-leak verbatim: CLIENT viendo pedido ajeno → 404 (no 403) y MISMO timing que "no existe" (R4).
- G3. Performance previsible: lista sin N+1 (no eager-load de relaciones); detalle con `selectinload` controlado.
- G4. Tipado estricto Pydantic para filtros (Literal de estados, validación `desde <= hasta`, `page`/`limit` con rangos).
- G5. Reutilizar `get_pedido_completo` existente — no duplicar acceso a BD.
- G6. Cobertura: pytest interno por escenario + suite TestSprite end-to-end contra Postgres real.

**Non-Goals:**

- N1. Export a CSV (no está en ninguna US, mencionado por error en explore — fuera de scope).
- N2. Endpoint `/admin/pedidos` separado (spec canónica gana sobre US-051 nota técnica).
- N3. Métricas agregadas / dashboard de KPIs — eso es change #20 `admin-metrics-backend`.
- N4. Real-time updates (WebSocket / SSE) sobre cambios de estado — no está en ninguna US del MVP.
- N5. Modificar `PedidoRead` actual o tocar capabilities `order-creation`/`order-state-machine`. Esta change es aditiva.
- N6. Crear índice GIN trigram sobre `usuario.nombre || apellido` — se documenta como known limitation (R2), no se migra ahora.
- N7. Permitir acceso STOCK al endpoint — STOCK ve productos, no pedidos. Si pide, 403 explícito.

## Decisions

### D1. Un endpoint role-aware vs dos endpoints separados (admin/client)

**Decisión**: un solo `GET /api/v1/pedidos` y un solo `GET /api/v1/pedidos/{id}`. El comportamiento (qué pedidos ve, qué filtros aplican) se decide en el service según `current_user.roles`.

**Por qué**: `docs/Descripcion.txt:285` lo manda explícitamente, y CLAUDE.md fija "spec canónica > historias". Beneficios concretos:
- Una sola URL en el frontend, que sirve a CLIENT y a operadores PEDIDOS/ADMIN. La diferenciación es por JWT, no por path.
- El service queda como único punto de RBAC dinámico — más simple de auditar.
- No hay duplicación de schemas ni de paginación.

**Alternativa descartada**: `/api/admin/pedidos` separado (como decía US-051 nota técnica). Implicaría duplicar router + service path; el router tendría que decidir si delegar al "admin path" o al "client path" según rol — exactamente el split que el endpoint role-aware evita.

### D2. Anti-leak 404 cuando CLIENT pide pedido ajeno

**Decisión**: si CLIENT (sin PEDIDOS ni ADMIN) llama `GET /api/v1/pedidos/{id}` y el pedido existe pero `pedido.user_id != current_user.id`, responder 404 con `NotFoundError("Pedido no encontrado")`. Idéntico al caso de pedido inexistente.

**Por qué**: la regla ya está consolidada (`order-state-machine` Req. "Ownership CLIENT en cancelaciones propias" + RN-RB05 + `order-creation` Req. "Validación de propiedad de la dirección"). Devolver 403 filtra que el ID existe — un atacante puede enumerar IDs y diferenciar "existe pero ajeno" vs "no existe". 404 oculta esa señal.

**Implementación**: `OrderService.get_pedido_detalle` invoca `repository.get_pedido_completo(pedido_id, user_id)` pasando `user_id = current_user.id` para CLIENT y `user_id = None` para PEDIDOS/ADMIN. El método ya filtra `WHERE pedido.user_id = :user_id` cuando `user_id is not None`. Si retorna `None`, el service raise `NotFoundError`.

**Alternativa descartada**: devolver 403 cuando se detecta ownership mismatch. Filtra existencia → no cumple anti-leak.

### D3. `q` único auto-detect (int vs string) vs dos params separados

**Decisión**: un solo `q: str | None` query param. El service intenta `int(q)`; si parsea → busca por `pedido.id == int(q)`; si no → ILIKE `'%q%'` sobre `usuario.nombre || ' ' || usuario.apellido`.

**Por qué**:
- US-051 dice "buscar por número de pedido o nombre de cliente". Un único campo de texto en la UI es lo natural.
- Evita un param `numero_pedido` y otro `cliente_nombre` que el frontend tendría que routear. Convención HTTP típica de search.
- Para CLIENT, el filtro por nombre es trivial (siempre es su propio nombre) pero no daña; aplica igual para consistencia.

**Alternativa descartada**: dos params (`numero_pedido: int | None`, `cliente_nombre: str | None`). Más superficie de validación y de combinatoria de queries.

### D4. Lista NO eager-loadea relaciones; detalle SÍ

**Decisión**:
- `list_with_filter` ejecuta un solo `SELECT` sobre `orders` con joins solo para filtros (`JOIN usuarios` cuando `q` es string), SIN `selectinload`. Devuelve campos compactos: `id`, `estado_codigo`, `total`, `creado_en`, `forma_pago_codigo`. `items_count` se obtiene con `func.count(DetallePedido.id)` agregado por subquery — opcional pero barato.
- `get_pedido_completo` (detalle) sí ejecuta `selectinload(items, historial, pagos)`.

**Por qué (R1)**: si la lista eager-loadeara items/historial/pagos, un usuario con 100 pedidos dispararía 3 queries adicionales × 100 filas. `selectinload` agrupa en 3 queries totales pero eso ya es overhead innecesario para una lista. La lista solo necesita campos del pedido para renderizar.

**Trade-off**: el detalle hace `selectinload` × 3 (items, historial, pagos). Para un pedido típico (~5 items, ~3 transiciones, 0-1 pago) son 4 queries muy chicas — aceptable.

**Alternativa descartada**: `joinedload` en lista. Generaría un Cartesian product feísimo (items × historial × pagos) y duplicaría filas.

### D5. Reutilizar `get_pedido_completo` con `user_id=None` para path admin

**Decisión**: extender la firma actual de `get_pedido_completo(pedido_id: int, user_id: int) -> Pedido | None` a `get_pedido_completo(pedido_id: int, user_id: int | None) -> Pedido | None`. Cuando `user_id is None`, la query NO filtra por ownership.

**Por qué**: la lógica de eager loading ya está implementada y testeada. Duplicar un `get_pedido_completo_admin` sería copy-paste con un único cambio (el filtro WHERE). El cambio es de una sola línea en el repo.

**Compatibilidad**: el único llamador actual de `get_pedido_completo` está en este change (no se rompe ningún consumer). Si en el futuro otro feature requiere "siempre filtrar por user_id", se puede mantener la API o agregar un alias estricto.

### D6. Paginación `{items, total, page, limit}` (mismo shape que productos/categorias)

**Decisión**: `PaginatedPedidos = {items: list[PedidoListItem], total: int, page: int, limit: int}`. `total` es el conteo sin paginar (para que el frontend calcule `total_pages`).

**Por qué**: convención ya validada en productos y categorías (también pasó TestSprite). Reusar = menos código en frontend (`hooks/usePaginated` ya está parametrizado a este shape).

**Trade-off**: `count_with_filter` ejecuta un `SELECT COUNT(*)` adicional. Aceptable para listas <10k pedidos; si el dataset crece, considerar cursor pagination en v2 (out of scope).

### D7. Order by `creado_en DESC` fijo

**Decisión**: la lista siempre ordena por `creado_en DESC` (más recientes primero). No es configurable en v1.

**Por qué**: US-049 lo manda literalmente ("Ordenados por fecha descendente"). Configuración adicional (`?sort=...`) es over-engineering — si en v2 piden ordenar por `total` se agrega entonces.

### D8. `estado` como Literal estricto de 6 códigos

**Decisión**: el query param `estado` es `Literal["PENDIENTE", "CONFIRMADO", "EN_PREPARACION", "EN_CAMINO", "ENTREGADO", "CANCELADO"] | None`. Cualquier otro valor → 422 Pydantic antes del service.

**Por qué**: alinea con la FSM de `order-state-machine`. Si en v2 se agregan estados, la lista se actualiza en un solo lugar (idealmente extraída a `state_machine.py:ESTADOS_CODIGOS`).

### D9. Validación cruzada `desde <= hasta` con `model_validator`

**Decisión**: el schema de filtros (Pydantic model que agrupa los query params) tiene un `@model_validator(mode='after')` que lanza `ValueError("desde no puede ser posterior a hasta")` si ambos están presentes y `desde > hasta`. Pydantic lo convierte a 422.

**Por qué (R5)**: si la combinación viaja al service y de ahí al repo, el `WHERE creado_en BETWEEN desde AND hasta` con `desde > hasta` devuelve lista vacía silenciosamente — UX confusa. Mejor 422 con mensaje claro en el borde.

## Risks / Trade-offs

- **R1. N+1 latente si se agrega cliente.nombre al PedidoListItem.** Hoy la lista NO incluye nombre de cliente. Si en v2 el frontend lo pide, hay que eager-loadear `usuario` (`selectinload(Pedido.usuario)`). → **Mitigación**: documentar en docstring del repo (`list_with_filter`) que cualquier nuevo campo proveniente de relaciones requiere su correspondiente eager-load. Test de regresión con `sqlalchemy.event.listen("before_cursor_execute")` que cuente queries (out of scope v1, anotar para v2).

- **R2. ILIKE sobre `usuario.nombre || ' ' || usuario.apellido` sin índice trigram.** Para datasets pequeños (<10k usuarios) es aceptable; con 100k+ se vuelve lento (full table scan). → **Mitigación**: known limitation documentada. Si el dataset crece, agregar migration con `CREATE INDEX ... USING GIN ... pg_trgm`. No es bloqueante para MVP.

- **R3. Decimal precision en serialización.** Pydantic v2 por default serializa `Decimal` como string en JSON (correcto para no perder precisión). El frontend tiene que parsear strings → numbers, no asumir float. → **Mitigación**: mantener la convención del proyecto (ya implementada en `PedidoRead`). Documentar en el spec que `total`, `costo_envio`, `monto` son strings en JSON.

- **R4. Timing leak en anti-leak 404.** Si CLIENT pide pedido ajeno y la query corre `WHERE id=:id AND user_id=:user_id`, el latency profile es idéntico al de "id no existe" (ambos hacen el mismo path, sin branching condicional). → **Mitigación**: NO agregar lógica del tipo "primero veo si existe sin filtro, después checkeo ownership y decido". El service llama directamente a `get_pedido_completo(pedido_id, user_id)` y mapea `None → 404` sin importar la causa. Test pytest verifica que en ambos casos (id inexistente / id existente ajeno) la respuesta es estructuralmente idéntica.

- **R5. Filtros combinados rotos (desde > hasta).** Sin validación cruzada, devuelve lista vacía sin error → UX confusa. → **Mitigación**: D9, `model_validator` en Pydantic. Test que verifica respuesta 422 con error claro.

## Migration Plan

No hay migración de datos ni de schema — esta change es puramente backend aditiva.

**Pasos de deploy:**
1. Merge del PR → CI verde (pytest + TestSprite).
2. Deploy backend; los nuevos endpoints quedan disponibles inmediatamente.
3. No requiere coordinación con frontend (consumer es change posterior; los endpoints expuestos son nuevos, no rompen contratos existentes).

**Rollback:**
- Revert del commit. Los endpoints desaparecen; el resto del sistema sigue funcionando (no hay dependencias upstream).
- No hay cambios en BD que rollbackear.

## Open Questions

- **¿Incluir `cliente_nombre` y `cliente_email` en `PedidoListItem` para PEDIDOS/ADMIN?** Hoy no, para evitar N+1 (R1). Si UX lo pide, agregar en v2 con eager-load de `usuario`. Por ahora la lista muestra solo info del pedido; los datos del cliente aparecen en el detalle.
- **¿Soportar export CSV en el futuro?** No bloqueante. Si llega como historia, se agrega en su propio change. No se diseña ahora para no over-engineer.
- **¿Cursor pagination en v2?** Si el dataset supera 10k pedidos y `COUNT(*)` se vuelve costoso, migrar a cursor-based. Por ahora la página + total funciona bien.
