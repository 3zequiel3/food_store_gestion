## Context

`order-creation-backend` es el primer change del Sprint 5 y el corazón del dominio. Las dependencias upstream (`auth-backend`, `products-backend`, `delivery-addresses-backend`, `database-schema-seed`, `refactor-uow-to-context-manager`) están **archivadas** y el backend ya está sobre service-driven UoW limpio (286/286 tests verdes). Los modelos `Pedido`, `DetallePedido` y `HistorialEstadoPedido` existen en `backend/features/orders/models.py`; el resto del feature (`schemas.py`, `repository.py`, `service.py`) está vacío y `router.py` tiene tres stubs `not_implemented`.

**Estado relevante del repo**:
- `backend/shared/unit_of_work.py` — `UnitOfWork` como context manager. `__enter__` abre sesión; `__exit__` hace `commit()` en salida limpia o `rollback()` ante excepción y siempre cierra la sesión. Los services llaman `with UnitOfWork() as uow:` y registran repos vía `uow.register_repository("nombre", Repo(uow.session))`.
- `backend/shared/repository.py` — `BaseRepository[T]` con `get_by_id`, `create`, `update`, `soft_delete`, `hard_delete`. Sin commits internos: la atomicidad la dicta el UoW.
- `backend/features/addresses/service.py` — referencia canónica del patrón: `find_by_id_and_user(addr_id, user_id)` devuelve `None` para "no existe" y "pertenece a otro usuario", y el service mapea ambos casos a `NotFoundError` (404) — D6 anti-leak.
- `backend/features/products/models.py` — `Producto` tiene `precio: Numeric(10, 2)`, `stock_cantidad: Integer` con check `>= 0`, `disponible: Boolean` y `eliminado_en` (soft delete).
- `backend/features/catalog/models.py` — `FormaPago` (`payment_methods.codigo` UQ, `habilitada` boolean), `EstadoPedido` (`order_states.codigo` UQ con `orden` y `es_terminal`). Seed inserta 6 estados (`PENDIENTE`, `CONFIRMADO`, `EN_PREPARACION`, `EN_CAMINO`, `ENTREGADO`, `CANCELADO`) y 3 formas de pago (`MERCADOPAGO`, `EFECTIVO`, `TRANSFERENCIA`).
- `backend/tests/conftest.py` — patcha `get_session_factory` para que cada `UnitOfWork()` use SQLite in-memory, con `pg_only = {"order_items"}` que excluye `order_items` del `create_all` por el `ARRAY(Integer)`.

**Spec canónica relevante**:
- §3.3 — `Pedido.direccion_id: BIGINT FK SET NULL — NULL = retiro en local (válido)`.
- §6.2 — schemas `CrearPedidoRequest`, `ItemPedidoRequest`, `PedidoRead`, `PedidoDetail`, `DetallePedidoRead`.
- §7.1 — flujo UoW de 9 pasos para creación de pedido (diagrama de secuencia incluido).
- Reglas RN-PE01..08, RN-02, RN-DA05, RN-DA06.

**Hallazgo bloqueante (D1)**: el modelo actual tiene `direccion_entrega_id` y `direccion_snapshot` `nullable=False`, en conflicto directo con la spec que requiere `SET NULL` para habilitar "retiro en local". Esta migration nace dentro del scope del change.

## Goals / Non-Goals

**Goals**

1. Implementar `POST /api/v1/pedidos` end-to-end (router → service → repository → modelos) siguiendo el flujo UoW de 9 pasos de la spec §7.1.
2. Garantizar atomicidad: `Pedido` + N × `DetallePedido` + `HistorialEstadoPedido` se persisten en una sola transacción. Si cualquier paso falla, **nada** persiste.
3. Capturar snapshots inmutables: `precio_snapshot`, `nombre_snapshot` (DetallePedido), `direccion_snapshot` (Pedido). Cambios futuros en producto o dirección **no** alteran pedidos existentes (RN-DA06).
4. Validar stock con lock pesimista (`SELECT FOR UPDATE`) **dentro** de la transacción, antes de cualquier INSERT. Si algún item no tiene stock o no está disponible: 422 sin escribir nada (RN-PE05, todo o nada).
5. Inicializar historial con `estado_anterior_codigo=None`, `estado_nuevo_codigo="PENDIENTE"`, `cambiado_por_id=user_id` (RN-02, RN-PE06).
6. Anti-smuggling: `extra="forbid"` en `CrearPedidoRequest` e `ItemPedidoRequest`. El cliente nunca puede inyectar `total`, `estado_codigo`, `usuario_id`, `precio_snapshot`, etc.
7. Anti-leak (D6, ya canónico en `delivery-addresses-backend`): una `direccion_id` que no existe o pertenece a otro usuario devuelve **404**, no 403.
8. Cobertura TDD-first robusta — happy path + atomicidad + edge cases + anti-smuggling + auth.
9. Cerrar la discrepancia D1 con una migration nueva en el mismo change.

**Non-Goals**

- Transiciones de estado posteriores (`PENDIENTE → CONFIRMADO`, etc.). Vive en `order-state-machine-fsm` (#16). Acá sólo se inserta el primer registro `None → PENDIENTE`.
- Decremento de stock al confirmar pago. Vive en `order-state-machine-fsm`. Acá `stock_cantidad` se **lee** con lock pero **no se modifica**.
- Endpoints de lectura (`GET /api/v1/pedidos`, `GET /api/v1/pedidos/{id}`). Viven en `order-visualization-backend` (#17).
- Integración MercadoPago. Vive en `payment-mercadopago-backend` (#15).
- Cálculo dinámico de `costo_envio` por zona/distancia. v1 fija 50.00 / 0.00; lógica posterior queda como deuda.
- Cancelación por parte del cliente (`DELETE /api/v1/pedidos/{id}`). Vive en `order-state-machine-fsm`.
- UI / frontend. La Fase B arranca después del Sprint 6.

## Decisions

### D1 — Alinear `direccion_entrega_id` y `direccion_snapshot` a la spec §3.3 (nullable, ON DELETE SET NULL)

**Decisión**: emitir una migration nueva `2026MMDD_xxxx_orders_direccion_nullable.py` que altere:
- `orders.direccion_entrega_id`: `NOT NULL` → `NULL`, con `ON DELETE SET NULL` (cuando se borra la dirección referenciada, el pedido conserva el snapshot histórico pero pierde la FK viva).
- `orders.direccion_snapshot`: `NOT NULL` → `NULL`.

Y editar `backend/features/orders/models.py` para reflejar:
```python
direccion_entrega_id: Mapped[Optional[int]] = mapped_column(
    Integer,
    ForeignKey("delivery_addresses.id", ondelete="SET NULL"),
    nullable=True,
)
direccion_snapshot: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
```

**Why**: la spec del integrador es la fuente de verdad (CLAUDE.md, regla "si los .md entran en conflicto con los .txt, gana la spec"). Además, la consigna de la cátedra menciona explícitamente "retiro en local" como modalidad válida — sin esto, el endpoint no podría representar ese caso de negocio.

**Alternatives considered**:
- *No-op (mantener `NOT NULL`)*: bloqueado por spec. Además obligaría a crear una "dirección sintética de retiro" o un texto sentinela como `"RETIRO_EN_LOCAL"` — hack que rompe la semántica del snapshot.
- *Hacer sólo `direccion_entrega_id` nullable, mantener `direccion_snapshot NOT NULL` y guardar `"RETIRO EN LOCAL"` literal cuando no hay dirección*: simplifica queries downstream pero ensucia el snapshot histórico con datos sintéticos. La spec no lo manda y el frontend puede manejar el `None` perfectamente bien con un fallback en UI.
- *Postergar la migration a un change posterior y arrancar bloqueando retiro en local con 422 a nivel service*: deuda inmediata, contradice la spec y obliga a frontend a no enviar `direccion_id=null`. Rechazado.

**Consequences**:
- + Spec alineada al 100%.
- + Habilita retiro en local sin trampas.
- + `ON DELETE SET NULL` preserva el snapshot histórico aunque el cliente borre la dirección — coherente con RN-DA06 (snapshots inmutables).
- − Es una migration estructural mid-development, pero sin datos productivos = bajo riesgo.
- − Cualquier código futuro que asuma `Pedido.direccion_entrega_id is not None` debe revisar — irrelevante hoy porque no hay código consumiendo `orders` todavía.

### D2 — `personalizacion`: mantener `INTEGER[]` con tests Postgres-only (Opción B)

**Decisión**: dejar `DetallePedido.personalizacion` como `ARRAY(Integer)` (Postgres-only). El conftest ya excluye `order_items` del `create_all` SQLite (`pg_only = {"order_items"}`). Los tests de items de pedido se marcan `@pytest.mark.pg_only` y se ejecutan contra Postgres en CI (o se skipean si el entorno es SQLite-only). El resto del integration suite sigue corriendo en SQLite in-memory.

**Why**: RN-PE07 dice literal "INTEGER[] (array de PostgreSQL)". La spec es taxativa. Cambiar a `JSON` rompe la semántica del tipo y la documentación de la cátedra: un evaluador que ejecute `\d order_items` esperaría ver un `integer[]`.

**Alternatives considered**:
- **Opción A — `JSON` column (portable, SQLite-friendly)**: `personalizacion: Mapped[Optional[list[int]]] = mapped_column(JSON, nullable=True)`.
  - Pros: tests corren en SQLite sin saltos. Cero infra extra para tests.
  - Cons: se pierde la tipificación estricta `INTEGER[]` que la spec exige (RN-PE07). En PG, `json` no permite operadores de array nativos (`= ANY(...)`, `@>`, `<@`). Para una query de "pedidos que personalizaron el ingrediente X" hay que usar `json_array_elements`, más caro y menos legible.
  - Veredicto: rechazada — sacrifica fidelidad de spec por comodidad de testing.

- **Opción C — `JSONB` column (compromiso)**: `JSONB` permite operadores tipo `@>` y es indexable. Pero sigue siendo `jsonb`, no `integer[]`. Misma objeción de spec.

- **Opción D — Tabla pivot `order_item_personalizaciones`**: una tabla puente `(order_item_id, ingredient_id)`. Pros: portable, indexable, FK válida. Cons: rompe RN-PE07 al cambiar la representación y es overkill para v1.

**Decisión final**: Opción B. Es la única que respeta la spec literal. El coste es bajo (los tests `pg_only` se decoran con un marker que skipea si no hay Postgres disponible) y se documenta en `backend/features/orders/README.md` como tradeoff conocido. Si en futuras iteraciones la cátedra acepta `JSONB`, se puede migrar con una migration `ALTER COLUMN ... USING ...`.

**Consequences**:
- + Spec respetada al 100%.
- + Queries futuras (analytics, "qué ingredientes se piden más con tal producto") se hacen con operadores de array nativos.
- − Tests de `DetallePedido` requieren Postgres. Se mitiga con marker y `pytest.mark.skip` si SQLite. Los tests de `Pedido` propiamente dichos (atomicidad, snapshots, validaciones) sí pueden seguir en SQLite siempre que **no inserten DetallePedido** — y como toda la operación es atómica, la mayoría de los tests acaban siendo pg_only.

**Implementación práctica del marker**:
```python
# backend/tests/conftest.py
def pytest_collection_modifyitems(config, items):
    if not _postgres_available():
        skip_pg = pytest.mark.skip(reason="Requires PostgreSQL (ARRAY(Integer))")
        for item in items:
            if "pg_only" in item.keywords:
                item.add_marker(skip_pg)
```

Y `_postgres_available()` chequea `DATABASE_URL` env var o un `pytest --pg` flag.

### D3 — Service-driven UoW idéntico al patrón canónico

**Decisión**: `OrderService.crear_pedido(user_id: int, payload: CrearPedidoRequest) -> Pedido` abre su propio `with UnitOfWork() as uow:`, registra un único repository (`uow.register_repository("orders", OrderRepository(uow.session))`) y ejecuta todos los pasos dentro de ese contexto. El router **nunca** abre UoW. `__exit__` decide commit/rollback.

**Why**: es el patrón establecido tras `refactor-uow-to-context-manager` y replicado por `addresses`, `products`, `users`, `auth`. Romper con él para órdenes generaría inconsistencia arquitectónica y obligaría a futuros mantenedores a entender dos patrones.

**Alternatives considered**:
- *Router maneja UoW*: derogado por el refactor.
- *Múltiples repos (`orders`, `pedido_items`, `historial`)*: ver D8.
- *Repository abre su propia transacción*: viola la separación de niveles del Unit of Work; los repos no deben saber de transacciones.

**Consequences**:
- + Consistencia 1:1 con el resto del backend.
- + Tests reusan `_patch_uow_session_factory` sin tocar nada.
- − Ninguna desventaja material.

### D4 — Validación de stock con `SELECT FOR UPDATE` dentro de la transacción (RN-PE04)

**Decisión**: para cada item del request, ejecutar:
```python
producto = uow.orders.get_producto_for_update(item.producto_id)
```
Donde `get_producto_for_update` hace:
```python
return self.session.execute(
    select(Producto)
    .where(Producto.id == producto_id, Producto.eliminado_en.is_(None))
    .with_for_update()
).scalar_one_or_none()
```

Si `producto is None` → `NotFoundError("Producto no encontrado")` (404).
Si `not producto.disponible` → `BusinessRuleError("Producto no disponible")` (422).
Si `producto.stock_cantidad < item.cantidad` → `BusinessRuleError("Stock insuficiente para X")` (422, mensaje incluye `nombre`).

**Why**: RN-PE04 lo exige literal. Sin `FOR UPDATE`, dos pedidos concurrentes que peleen por el último item pueden leer el mismo stock y ambos validar OK, lo que genera oversell. PG resuelve el lock por fila → el segundo pedido espera hasta el commit/rollback del primero y entonces ve el estado real.

**Alternatives considered**:
- *Optimistic locking con `version`*: no hay columna `version` en `products`, agregarla es out-of-scope.
- *Validar fuera de la transacción*: viola RN-PE04. Race condition.
- *Locking de fila aplicación-side con Valkey*: out-of-scope, agrega dependencia externa.

**Consequences**:
- + Correctitud absoluta bajo concurrencia.
- + Se decremento real del stock vive en `order-state-machine-fsm` cuando el pago confirma — acá sólo se **valida**. Es un lock optimista temporal (mientras dure la transacción de creación).
- − En SQLite `with_for_update()` es no-op (SQLite no soporta `FOR UPDATE`). En tests, esto significa que los tests de concurrencia real deben correrse en Postgres (`pg_only`). Los tests de "stock insuficiente" en SQLite seguirán pasando porque no involucran concurrencia.

### D5 — `costo_envio` v1 fijo: 50.00 con dirección, 0.00 sin dirección

**Decisión**: en el service, antes de calcular el total:
```python
costo_envio = Decimal("50.00") if direccion is not None else Decimal("0.00")
```

Constante en `backend/features/orders/service.py` (o en `backend/shared/constants.py` si se reusa).

**Why**: la spec no define una tabla de tarifas. Construir un módulo de cálculo dinámico es out-of-scope del Sprint 5 y nadie lo está pidiendo. Mantener un valor fijo respeta RN-PE08 (`total = sum(precio × cantidad) + costo_envio`) sin abrir alcance.

**Alternatives considered**:
- *`costo_envio` siempre 0 v1*: rompe la semántica del campo (existe en el modelo, hay que poblarlo razonablemente).
- *Calculado por zona o distancia*: requeriría tabla de tarifas, geocoding o flat-rate por código postal. Out-of-scope.
- *Configurable vía `system-configuration`*: ese change está marcado "postergable". No bloquea.

**Consequences**:
- + Cero overhead arquitectónico.
- + Deja la puerta abierta a un change futuro `shipping-pricing` sin romper el contrato del POST.
- − Es una simplificación visible. Se documenta como deuda explícita en el README del feature.

### D6 — Anti-leak ownership: 404 (no 403) ante dirección de otro usuario

**Decisión**: si `direccion_id` viene en el payload, validar con `uow.direcciones.find_by_id_and_user(direccion_id, user_id)` (ya existe en `addresses-backend`). Si devuelve `None`, lanzar `NotFoundError("Dirección no encontrada")` → 404. El service **no** diferencia entre "no existe" y "pertenece a otro usuario".

**Why**: D6 ya está canonizado en `delivery-addresses-backend`. Devolver 403 filtraría que el ID existe pero pertenece a otro — superficie de enumeración.

**Alternatives considered**:
- *403 cuando pertenece a otro*: rechazado por leak.
- *400 (Bad Request) genérico*: confunde semántica HTTP.

**Consequences**:
- + Anti-enumeration consistente con el resto del backend.
- + Reuso de `AddressRepository.find_by_id_and_user` sin duplicar lógica.

### D7 — Registrar `AddressRepository` dentro del UoW del service de órdenes

**Decisión**: el `OrderService` registra **dos** repositories en el mismo UoW: `orders` (`OrderRepository`) y `direcciones` (`AddressRepository`). Esto preserva D8 (un repository por agregación pero sirve sub-registros) y reutiliza la lógica anti-leak sin duplicar código:
```python
with UnitOfWork() as uow:
    uow.register_repository("orders", OrderRepository(uow.session))
    uow.register_repository("direcciones", AddressRepository(uow.session))
    ...
```

**Why**: tampoco se va a abrir un sub-UoW para una sola lectura — eso rompería la atomicidad. Cross-feature repository reuse es esperable y trivial bajo este patrón.

**Alternatives considered**:
- *Duplicar `find_by_id_and_user` en `OrderRepository`*: viola DRY y crea drift.
- *Query directo desde el service*: viola la regla de oro (service no toca la sesión directamente, sólo a través de repositories).

**Consequences**:
- + Reuso limpio.
- + Misma transacción → consistencia.

### D8 — `OrderRepository` único para `Pedido + DetallePedido + HistorialEstadoPedido`

**Decisión**: un único `OrderRepository(BaseRepository[Pedido])` que expone métodos para las tres entidades:
- `get_producto_for_update(producto_id) -> Producto | None` — lock pesimista sobre catálogo.
- `find_forma_pago(codigo) -> FormaPago | None` — validar código existe y está habilitado.
- `create_pedido(...) -> Pedido` — INSERT + flush para conseguir `pedido.id`.
- `create_detalle(pedido_id, producto, cantidad, personalizacion) -> DetallePedido` — INSERT con snapshots.
- `create_historial_inicial(pedido_id, user_id) -> HistorialEstadoPedido` — INSERT con `estado_anterior_codigo=None`, `estado_nuevo_codigo="PENDIENTE"`.

**Why**: `Pedido` es la agregación raíz. `DetallePedido` y `HistorialEstadoPedido` no tienen identidad fuera del pedido (`pedido_id` es parte de su clave de negocio, CASCADE en FK). Mantenerlos en un solo repo evita micro-repositories que confunden el grafo de dependencias.

**Alternatives considered**:
- *Repos separados (`OrderRepository`, `OrderItemRepository`, `OrderHistoryRepository`)*: cuatro líneas de `register_repository` por método del service, sin valor de aislamiento real.
- *`OrderRepository` sólo + queries inline del service*: viola la regla de oro (service no toca la sesión).

**Consequences**:
- + Un solo repo para un agregado coherente.
- + Cuando llegue `order-visualization-backend` (#17), agregar `get_pedido_completo(pedido_id, user_id)` y `list_pedidos(user_id, filters)` al mismo repo.
- − El repo crece, pero sigue siendo manejable (~150-200 LOC esperadas).

### D9 — Naming en castellano del endpoint y schemas

**Decisión**: el endpoint vive en `/api/v1/pedidos` (no `/orders`). Los schemas Pydantic se nombran `CrearPedidoRequest`, `ItemPedidoRequest`, `PedidoRead`, `PedidoDetail`, `DetallePedidoRead`, `HistorialEstadoRead` — todos en castellano. Las clases internas SQLAlchemy mantienen su nombre actual (`Pedido`, `DetallePedido`, `HistorialEstadoPedido`).

**Why**: convenio del proyecto (Food Store v5, dominio en castellano para reflejar el lenguaje del negocio argentino). Es coherente con `direcciones`, `productos`, `categorias`, `ingredientes` ya implementados.

**Consequences**: ninguna negativa. Los schemas se mapean directo desde los modelos con `model_validate`.

### D10 — Validaciones Pydantic estrictas con `extra="forbid"` y constraints

**Decisión** — `CrearPedidoRequest`:
```python
class CrearPedidoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    items: list[ItemPedidoRequest] = Field(..., min_length=1, max_length=50)
    forma_pago_codigo: str = Field(..., min_length=1, max_length=50)
    direccion_id: int | None = Field(default=None, ge=1)
    notas: str | None = Field(default=None, max_length=500)
```

`ItemPedidoRequest`:
```python
class ItemPedidoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    producto_id: int = Field(..., ge=1)
    cantidad: int = Field(..., ge=1, le=999)
    personalizacion: list[int] | None = Field(default=None, max_length=20)

    @field_validator("personalizacion")
    @classmethod
    def _ids_positivos(cls, v):
        if v is None:
            return v
        if any(i <= 0 for i in v):
            raise ValueError("ingredient_id debe ser >= 1")
        return v
```

**Why**:
- `extra="forbid"` corta el anti-smuggling de raíz (no se acepta `total`, `estado_codigo`, `usuario_id`, etc.).
- `min_length=1` en items previene pedidos vacíos.
- `max_length=50` en items y `le=999` en cantidad son sanity caps.
- `direccion_id: int | None` con `ge=1` cuando se manda (sin `None`) → habilita retiro en local sin ambigüedad.
- `str_strip_whitespace` evita códigos con padding.

**Alternatives considered**:
- *`extra="ignore"` (Pydantic default)*: filtra silenciosamente extras pero no protege contra confusión del lado del frontend.
- *Sin caps*: invita a abuso (pedidos de 100k items, cantidad 10⁹).

**Consequences**: validaciones de schema antes de tocar BD, fail-fast con 422 automático.

### D11 — `Numeric(10, 2)` y `Decimal` end-to-end (sin floats)

**Decisión**: los cálculos de `subtotal_item = precio × cantidad` y `total = sum(subtotales) + costo_envio` se hacen con `decimal.Decimal`. Pydantic devuelve `Decimal` cuando el campo es `condecimal` o `Annotated[Decimal, ...]`. Convertir a `float` sólo en la frontera de serialización si fuera necesario — pero Pydantic v2 serializa `Decimal` como string por default, lo cual es **deseable** (no pierde precisión).

**Why**: usar `float` para dinero introduce errores acumulativos (clásico). El modelo ya usa `Numeric(10, 2)` justamente por eso. Mantener `Decimal` end-to-end.

**Alternatives considered**:
- *`float` con `round(x, 2)`*: error acumulativo demostrable.
- *Cents como `int`*: viola el modelo (`Numeric(10, 2)`).

**Consequences**:
- + Precisión exacta.
- − Hay que escribir `Decimal("50.00")` y no `50.00` en tests. Trivial.

### D13 — Items con mismo `producto_id` se aceptan como filas separadas (no deduplicación)

**Decisión**: si el request envía dos o más items con el mismo `producto_id` (con personalización distinta o idéntica), el sistema acepta el request y crea **una fila por cada item en `order_items`**. NO se hace deduplicación ni agregación de cantidades.

**Why**: el modelo SQLAlchemy permite múltiples `DetallePedido` por mismo `(pedido_id, producto_id)` — la FK no tiene UQ. Caso de uso real: el cliente pide 2 milanesas SIN cebolla y 1 milanesa CON cebolla — son dos líneas porque tienen personalización distinta. Forzar deduplicación rompería este caso de negocio.

**Alternatives considered**:
- *Deduplicar por `producto_id` + agregar cantidades*: rompe el caso de personalización distinta.
- *Deduplicar por `(producto_id, personalizacion)`*: complica el service y el orden de comparación de arrays. Costo > beneficio.
- *Rechazar con 422 si hay duplicados de `producto_id`*: arbitrario y restrictivo, contradice el caso de uso real.

**Consequences**:
- + Cero lógica adicional en el service — la suma del total funciona naturalmente.
- + El frontend puede armar el carrito como quiera; el backend persiste fielmente.
- − El frontend debería ser responsable de mostrar la UI agrupada si quiere. No es preocupación del backend.

Test cubierto en spec por el scenario "Items con mismo producto_id pero distinta personalización" del Requirement "Crear pedido desde el carrito".

### D12 — RBAC: `CLIENT` obligatorio en `POST /pedidos`

**Decisión**: el endpoint usa `Depends(get_current_user)` (autenticación obligatoria) **y** valida que el rol del usuario incluya `CLIENT`. Reusa el helper `require_role("CLIENT")` ya existente en `backend/features/auth/dependencies.py` (si está) o, si no existe, valida explícitamente en el router con un `HTTPException(403)`.

**Why**: aunque un ADMIN podría técnicamente crear un pedido en nombre propio, la spec §5 define el endpoint como "CLIENT". Para minimizar superficie de uso, lo mantenemos en CLIENT en v1. Una futura historia `admin crea pedidos por teléfono` se manejará como un endpoint distinto si llega.

**Alternatives considered**:
- *Cualquier user autenticado*: incumple el contrato del row "POST /api/v1/pedidos" en §5 de la spec.
- *Sólo CLIENT puro (sin ADMIN)*: aceptable. Un admin que quiera probar usa una cuenta CLIENT secundaria. Más simple.

**Consequences**: tests deben crear un usuario con rol CLIENT (la fixture `sample_user` ya lo hace) y verificar 403 para roles no-CLIENT.

## Risks / Trade-offs

| # | Risk | Probabilidad | Impacto | Mitigación |
|---|------|--------------|---------|------------|
| 1 | **Oversell por race condition en stock** | Media (sin lock) | Alto (corrupción de negocio) | `SELECT FOR UPDATE` en cada producto dentro de la transacción (D4). Test pg_only de concurrencia. |
| 2 | **Pérdida de precisión en `total` por floats** | Media | Medio | `Decimal` end-to-end, `Numeric(10, 2)` en modelo, `Decimal` en service (D11). Test que crea pedido con precios fraccionarios (19.99 × 3) y verifica el total exacto. |
| 3 | **Snapshot mutable accidentalmente** | Baja | Alto (rompe RN-DA06) | `precio_snapshot`, `nombre_snapshot`, `direccion_snapshot` se calculan al crear y nunca se updatean. Test que crea pedido → cambia precio del producto → verifica que el snapshot del pedido sigue igual. |
| 4 | **Anti-smuggling: cliente inyecta `total` o `estado_codigo`** | Media (intencional o accidental) | Alto (corrupción de datos) | `extra="forbid"` en `CrearPedidoRequest` e `ItemPedidoRequest` (D10). Tests dedicados que envían `total`, `estado_codigo`, `usuario_id` y esperan 422. |
| 5 | **Dirección de otro usuario filtra existencia** | Baja | Medio | D6 anti-leak: 404 en lugar de 403 cuando la dirección no existe O pertenece a otro user (D6). Test dedicado. |
| 6 | **Rollback parcial: pedido creado pero historial falla** | Baja | Crítico | El UoW asegura atomicidad (D3). Test "atomicidad rollback": forzar un error en la creación del historial (mock interno) y verificar que no quedó ni el `Pedido` ni los `DetallePedido` en BD. |
| 7 | **Pedido sin items aceptado** | Baja | Medio | Pydantic `min_length=1` en `items` (D10). Test 422 con `items=[]`. |
| 8 | **`forma_pago_codigo` inexistente o deshabilitada acepta el pedido** | Media | Medio | `OrderRepository.find_forma_pago(codigo)` valida existencia + `habilitada=True`. Test 422 con código falso y código deshabilitado. |
| 9 | **`personalizacion` con IDs que no existen como `Ingrediente`** | Media | Bajo | v1 no valida FK porque PG no permite FK sobre arrays. Trade-off documentado en el modelo (`# FK integrity at application level only`). Validación rigurosa se delega a un change futuro de `cart-validation`. Test sólo verifica tipos (`list[int]`). |
| 10 | **Migration D1 falla en producción con datos existentes** | Nula | N/A | No hay datos productivos en `orders` hoy (todo el feature está stub). Migration `ALTER COLUMN ... DROP NOT NULL` es segura y reversible. |
| 11 | **Tests de items pg_only ocultan bugs en SQLite-only CI** | Media | Medio | Marker `pg_only` se documenta en README del feature. CI debería ejecutar Postgres si el alcance lo justifica; mientras tanto, los tests core (atomicidad, validaciones, schemas) corren en SQLite y los pg_only se skipean explícitamente. Plan: agregar GH Actions con servicio Postgres en un change futuro `ci-postgres-integration`. |
| 12 | **El service abre dos repositories (`orders` + `direcciones`) y crece la superficie** | Baja | Bajo | D7 ya es un patrón aceptado para cross-feature reuse. Documentado en el header del service. |

## Migration Plan

1. **Crear migration**: `backend/alembic/versions/2026MMDD_xxxx_orders_direccion_nullable.py`.
   - `op.alter_column("orders", "direccion_entrega_id", existing_type=BigInteger(), nullable=True)`.
   - Drop la FK existente y recrearla con `ondelete="SET NULL"` (si la migration inicial la creó con `RESTRICT`).
   - `op.alter_column("orders", "direccion_snapshot", existing_type=String(500), nullable=True)`.
   - `downgrade`: revertir ambas columnas a `NOT NULL` (asume que no hay rows con NULL — válido en este punto del desarrollo).
2. **Aplicar**: `uv run alembic upgrade head` en dev y CI.
3. **Editar `models.py`**: `Optional[int]`, `Optional[str]`, `nullable=True`, `ondelete="SET NULL"`.
4. **Verificar**: `uv run pytest backend/tests` — el resto de los tests sigue pasando (286/286).
5. **Rollback strategy**: si algún consumer descubre que necesita `direccion_entrega_id NOT NULL`, `alembic downgrade -1` revierte. No hay datos productivos.

## Open Questions

- **¿RBAC con `require_role("CLIENT")` o sólo `get_current_user`?** — **RESUELTO**: `require_role` existe en `backend/features/auth/dependencies.py` con firma `def require_role(*required_roles: str)` y se usa como `Depends(require_role("CLIENT"))`. Verificado con `rg "def require_role"` antes del apply. No requiere implementación nueva.
- **¿`costo_envio` debe estar parametrizado por env var en v1?** — Recomendación: constante de módulo. Si surge la necesidad, una `SHIPPING_COST_DEFAULT` env var es trivial de agregar.
- **¿Necesita el response `PedidoRead` incluir el total ya calculado?** — Sí (spec §6.2): `PedidoRead: id, estado_codigo, total, created_at`. Lo añadimos al schema.
