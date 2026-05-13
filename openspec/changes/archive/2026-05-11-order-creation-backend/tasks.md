## 1. Alembic — Migration para nullable de direccion (D1)

- [x] 1.1 Generar el archivo `backend/alembic/versions/2026MMDD_xxxx_orders_direccion_nullable.py` con `revises` apuntando a la última migration vigente (`20260508_0002_piso_depto_to_delivery_addresses`).
- [x] 1.2 En `upgrade()`: dropear la FK existente sobre `orders.direccion_entrega_id` y recrearla con `ondelete="SET NULL"`; luego `op.alter_column("orders", "direccion_entrega_id", existing_type=sa.BigInteger(), nullable=True)` y `op.alter_column("orders", "direccion_snapshot", existing_type=sa.String(500), nullable=True)`.
- [x] 1.3 En `downgrade()`: revertir ambas columnas a `nullable=False` y recrear la FK con `ondelete="RESTRICT"` (asume que no hay rows con NULL).
- [x] 1.4 Actualizar `backend/features/orders/models.py`: `direccion_entrega_id: Mapped[Optional[int]]` con `nullable=True` y `ondelete="SET NULL"`; `direccion_snapshot: Mapped[Optional[str]]` con `nullable=True`. Reflejar el cambio en el docstring del modelo.
- [x] 1.5 Ejecutar `uv run alembic upgrade head` en local y verificar que aplica sin errores.
- [x] 1.6 Correr `uv run pytest` (smoke): 286/286 tests previos deben seguir verdes — esto valida que ningún test asumía `direccion_entrega_id NOT NULL`.

## 2. Schemas — Pydantic v2 anti-smuggling (D10)

- [x] 2.1 Crear `backend/features/orders/schemas.py`. Importar `BaseModel`, `ConfigDict`, `Field`, `field_validator` de `pydantic`, `Decimal` y `datetime`.
- [x] 2.2 Escribir `ItemPedidoRequest` con `model_config = ConfigDict(extra="forbid")`, campos `producto_id: int (ge=1)`, `cantidad: int (ge=1, le=999)`, `personalizacion: list[int] | None = Field(default=None, max_length=20)` + validator que rechace IDs `<= 0`.
- [x] 2.3 Escribir `CrearPedidoRequest` con `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)`, campos `items: list[ItemPedidoRequest] = Field(min_length=1, max_length=50)`, `forma_pago_codigo: str (min_length=1, max_length=50)`, `direccion_id: int | None = Field(default=None, ge=1)`, `notas: str | None = Field(default=None, max_length=500)`.
- [x] 2.4 Escribir `PedidoRead` compacto (`model_config = ConfigDict(from_attributes=True)`): `id: int`, `estado_codigo: str`, `total: Decimal`, `created_at: datetime`.
- [x] 2.5 Verificar imports y que `schemas.py` no tenga dependencias circulares con `service.py` o `models.py`. (Schemas `DetallePedidoRead`, `HistorialEstadoRead`, `PedidoDetail` quedan FUERA de scope — corresponden a `order-visualization-backend` #17 que es quien los consume.)

## 3. Repository — OrderRepository unificado (D8)

- [x] 3.1 Crear `backend/features/orders/repository.py`. Imports: `Session`, `select`, `Producto`, `FormaPago`, `EstadoPedido`, `Pedido`, `DetallePedido`, `HistorialEstadoPedido`, `BaseRepository`.
- [x] 3.2 Definir `class OrderRepository(BaseRepository[Pedido])` con `__init__` que llama `super().__init__(session, Pedido)`.
- [x] 3.3 Implementar `get_producto_for_update(producto_id: int) -> Producto | None`: `select(Producto).where(id == producto_id, eliminado_en.is_(None)).with_for_update()`. Documentar que en SQLite `with_for_update()` es no-op (D4).
- [x] 3.4 Implementar `find_forma_pago(codigo: str) -> FormaPago | None`: `select(FormaPago).where(codigo == codigo, habilitada.is_(True), eliminado_en.is_(None))`.
- [x] 3.5 Implementar `create_pedido(user_id, direccion_id, direccion_snapshot, total, costo_envio, forma_pago_codigo, notas) -> Pedido`: instancia `Pedido(...)` con `estado_codigo="PENDIENTE"`, `session.add`, `session.flush`, `session.refresh`. Retornar el pedido con `id` asignado.
- [x] 3.6 Implementar `create_detalle(pedido_id, producto, cantidad, personalizacion) -> DetallePedido`: captura `nombre_snapshot=producto.nombre`, `precio_snapshot=producto.precio` desde el ORM (NO desde el request). `session.add`, `session.flush`.
- [x] 3.7 Implementar `create_historial_inicial(pedido_id, user_id) -> HistorialEstadoPedido`: `HistorialEstadoPedido(pedido_id, estado_anterior_codigo=None, estado_nuevo_codigo="PENDIENTE", cambiado_por_id=user_id)`. `session.add`, `session.flush`.
- [x] 3.8 Implementar `get_pedido_completo(pedido_id: int, user_id: int) -> Pedido | None`: eager-load `selectinload(Pedido.items)` y `selectinload(Pedido.historial)`, filtrar `user_id` y `eliminado_en IS NULL`. Reservado para usos futuros (visualization), pero útil para fixtures de test.

## 4. Service — OrderService.crear_pedido con UoW (D3, D4, D5, D6, D7, D11)

- [x] 4.1 Crear `backend/features/orders/service.py`. Imports: `Decimal`, `UnitOfWork`, `OrderRepository`, `AddressRepository`, `CrearPedidoRequest`, `Pedido`, `BusinessRuleError`, `NotFoundError`.
- [x] 4.2 Definir `class OrderService` con `__init__(self) -> None: pass` (stateless) y constante `SHIPPING_COST_DEFAULT = Decimal("50.00")`.
- [x] 4.3 Implementar `crear_pedido(self, user_id: int, payload: CrearPedidoRequest) -> Pedido`. Abrir `with UnitOfWork() as uow:` y registrar `orders` (`OrderRepository`) y `direcciones` (`AddressRepository`).
- [x] 4.4 Paso 1 — validar `forma_pago_codigo`: `forma = uow.orders.find_forma_pago(payload.forma_pago_codigo)`. Si `None` → `BusinessRuleError("Forma de pago no válida o no disponible")` (mapea a 422).
- [x] 4.5 Paso 2 — validar `direccion_id` si viene: si `payload.direccion_id is not None`, `direccion = uow.direcciones.find_by_id_and_user(payload.direccion_id, user_id)`. Si `None` → `NotFoundError("Dirección no encontrada")` (D6, mapea a 404). Si viene `None`, `direccion = None`.
- [x] 4.6 Paso 3 — armar `direccion_snapshot` si hay dirección: formato `f"{calle} {numero}{piso_depto?}, {ciudad} {codigo_postal}{referencia?}"` o el formato consistente del proyecto. Si `direccion is None`, `direccion_snapshot = None`.
- [x] 4.7 Paso 4 — para cada `item` en `payload.items`: `producto = uow.orders.get_producto_for_update(item.producto_id)`. Si `None` → `NotFoundError("Producto no encontrado")`. Si `not producto.disponible` → `BusinessRuleError("Producto no disponible: {nombre}")`. Si `producto.stock_cantidad < item.cantidad` → `BusinessRuleError("Stock insuficiente para {nombre}")`. Acumular `(producto, item)` en una lista local.
- [x] 4.8 Paso 5 — calcular `subtotal = sum(Decimal(producto.precio) * item.cantidad for producto, item in items_validados)`. `costo_envio = SHIPPING_COST_DEFAULT if direccion else Decimal("0.00")`. `total = subtotal + costo_envio`.
- [x] 4.9 Paso 6 — `pedido = uow.orders.create_pedido(user_id, direccion_id, direccion_snapshot, total, costo_envio, payload.forma_pago_codigo, payload.notas)`. Después de `flush()`, `pedido.id` está disponible.
- [x] 4.10 Paso 7 — iterar `items_validados` y llamar `uow.orders.create_detalle(pedido.id, producto, item.cantidad, item.personalizacion)` por cada uno.
- [x] 4.11 Paso 8 — `uow.orders.create_historial_inicial(pedido.id, user_id)`.
- [x] 4.12 Paso 9 — `uow.session.refresh(pedido, attribute_names=["created_at"])` para que `created_at` esté disponible después del cierre del UoW. Retornar `pedido`. El `__exit__` hace commit.

## 5. Router — POST /api/v1/pedidos (D9, D12)

- [x] 5.1 Editar `backend/features/orders/router.py`. Borrar los tres stubs `not_implemented`. Mantener `router = APIRouter()` para que `backend/main.py` lo siga montando.
- [x] 5.2 Importar `Depends`, `status`, `CrearPedidoRequest`, `PedidoRead`, `OrderService`, `get_current_user`, `Usuario`.
- [x] 5.3 Usar `Depends(require_role("CLIENT"))` — `require_role` ya existe en `backend/features/auth/dependencies.py` con firma `def require_role(*required_roles: str)` (verificado durante review del propose). NO implementar nada nuevo.
- [x] 5.4 Escribir el endpoint:
  ```python
  @router.post("/", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
  async def crear_pedido(
      payload: CrearPedidoRequest,
      current_user: Usuario = Depends(require_client),
  ) -> PedidoRead:
      service = OrderService()
      pedido = service.crear_pedido(current_user.id, payload)
      return PedidoRead.model_validate(pedido)
  ```
- [x] 5.5 Verificar que `backend/main.py` ya incluye el router con prefijo `/api/v1/pedidos` (montado en `database-schema-seed` inicial); si no, registrarlo.
- [ ] 5.6 Confirmar manualmente con `uv run uvicorn backend.main:app` + `curl` que el endpoint responde algo coherente (smoke test rápido — no es validación final).

## 6. Fixtures de conftest — catálogos y productos para tests

- [x] 6.1 En `backend/tests/conftest.py`, añadir fixture `sample_estados_pedido(test_db_session)` que inserta los 6 estados seedeados (`PENDIENTE` orden 1, `CONFIRMADO` orden 2, `EN_PREPARACION` orden 3, `EN_CAMINO` orden 4, `ENTREGADO` orden 5 terminal, `CANCELADO` orden 6 terminal) y los commitea.
- [x] 6.2 Añadir fixture `sample_formas_pago(test_db_session)` que inserta `MERCADOPAGO`, `EFECTIVO`, `TRANSFERENCIA` con `habilitada=True`. Retornar la lista de instancias.
- [x] 6.3 Añadir fixture `sample_producto_disponible(test_db_session)` (function-scoped, parametrizable con marker o factory): crea un `Producto` con `nombre="Producto Test"`, `precio=Decimal("100.00")`, `stock_cantidad=10`, `disponible=True`. Opcional: aceptar overrides via inner factory pattern.
- [x] 6.4 Añadir fixture `sample_address(test_db_session, sample_user)` reutilizando el helper `_seed_address` de `test_delivery_addresses.py` (extraerlo a conftest o duplicar mínimo). Devuelve una dirección activa del `sample_user`.
- [x] 6.5 Añadir hook `pytest_collection_modifyitems` (o configurar en `pyproject.toml`) que skipea tests marcados `@pytest.mark.pg_only` cuando no hay Postgres disponible. Detectar via env var `DATABASE_URL` que apunte a PG o flag `--pg`. Documentar el marker en el header del archivo.
- [x] 6.6 Registrar el marker `pg_only` en `pyproject.toml` (`[tool.pytest.ini_options] markers = ["pg_only: tests que requieren PostgreSQL"]`) para evitar warnings. (Se usó pytest.ini en lugar de pyproject.toml — mismo efecto, rootdir compatible.)

## 7. Tests de integración — TDD-first (Strict TDD activo)

> **STRICT TDD ACTIVO — orden de trabajo real**: aunque las secciones 1-6 están listadas estructuralmente (migration → schemas → repo → service → router → fixtures), el apply DEBE intercalar tests-first con cada vertical:
>
> 1. Step 2 (schemas) ← escribir primero tests 7.16–7.22 (anti-smuggling + validaciones Pydantic), correrlos en rojo, después implementar schemas hasta verlos en verde.
> 2. Step 3 (repository) ← escribir primero los tests que tocan repo methods (`find_forma_pago`, `get_producto_for_update`) como tests de service-level que fallan por falta de implementación; implementar repo.
> 3. Step 4 (service) ← escribir tests 7.3, 7.4, 7.6, 7.7, 7.10–7.15, 7.26 (happy path + stock + forma_pago + ownership + atomicidad) en rojo; implementar service en verde.
> 4. Step 5 (router) ← escribir tests 7.23–7.25 (auth/auth) en rojo; implementar router en verde.
>
> NO escribir código de producción sin un test que falle previamente. Esto es no negociable.

- [x] 7.1 Crear `backend/tests/integration/test_orders.py` con docstring de las secciones (7.1 happy path, 7.2 stock, 7.3 disponibilidad, 7.4 forma_pago, 7.5 dirección ownership, 7.6 retiro local, 7.7 atomicidad, 7.8 anti-smuggling, 7.9 validaciones Pydantic, 7.10 auth).
- [x] 7.2 Helper `_payload_valido(producto_id, direccion_id=None, cantidad=1)` que arma un body válido reusable.
- [x] 7.3 **TEST (7.1.a) — Happy path con dirección**: cliente autenticado envía pedido con 2 items y dirección propia → 201, response con `id`, `estado_codigo="PENDIENTE"`, `total` correcto. Verificar BD: 1 row en `orders`, N en `order_items` (pg_only), 1 en `order_state_history` con `estado_anterior_codigo=None`. Verificar `direccion_snapshot` capturado.
- [x] 7.4 **TEST (7.1.b) — Happy path retiro en local**: pedido sin `direccion_id` → 201, `orders.direccion_entrega_id=NULL`, `direccion_snapshot=NULL`, `costo_envio=0.00`, `total = sum(cantidad * precio)`.
- [x] 7.5 **TEST (7.1.c) — Snapshots inmutables**: crear pedido → actualizar el `precio` del producto en BD → re-leer el `DetallePedido` → `precio_snapshot` no cambió. Pg_only por dependencia de `order_items`.
- [x] 7.6 **TEST (7.2.a) — Stock insuficiente rechaza todo**: pedido con item de cantidad 100 (stock 10) → 422 con mensaje claro. Verificar BD: 0 rows en `orders`, `order_items`, `order_state_history`. Verificar `producto.stock_cantidad` sigue en 10.
- [x] 7.7 **TEST (7.2.b) — Producto no disponible rechaza**: producto con `disponible=False` → 422. BD limpia.
- [x] 7.8 **TEST (7.2.c) — Producto inexistente rechaza**: `producto_id=99999` → 404. BD limpia.
- [x] 7.9 **TEST (7.2.d) — Stock NO se decrementa al crear**: pedido happy path → re-leer producto → `stock_cantidad` igual al inicial.
- [x] 7.10 **TEST (7.4.a) — forma_pago_codigo inexistente**: `"BITCOIN"` → 422. BD limpia.
- [x] 7.11 **TEST (7.4.b) — forma_pago_codigo deshabilitada**: marcar `EFECTIVO.habilitada=False` en BD → pedido con `forma_pago_codigo="EFECTIVO"` → 422.
- [x] 7.12 **TEST (7.5.a) — Dirección de otro usuario responde 404**: cliente A intenta usar `direccion_id` del cliente B → 404 (no 403), mensaje genérico.
- [x] 7.13 **TEST (7.5.b) — Dirección inexistente responde 404**: `direccion_id=999999` → 404.
- [x] 7.14 **TEST (7.5.c) — Dirección soft-deleted del propio usuario responde 404**: soft-delete la dirección → request con su id → 404.
- [x] 7.15 **TEST (7.7) — Atomicidad rollback**: forzar excepción en `create_historial_inicial` (monkeypatch del método del repository para que tire `RuntimeError`) → request responde 500/error → BD: 0 rows en `orders` y `order_items`. (marcado pg_only — el flujo completo de 9 pasos requiere PG para order_items)
- [x] 7.16 **TEST (7.8.a) — Anti-smuggling `total`**: body con `"total": 0.01` → 422 con error Pydantic `extra fields not permitted`.
- [x] 7.17 **TEST (7.8.b) — Anti-smuggling `estado_codigo`**: body con `"estado_codigo": "CONFIRMADO"` → 422.
- [x] 7.18 **TEST (7.8.c) — Anti-smuggling `usuario_id`**: body con `"usuario_id": 999` → 422.
- [x] 7.19 **TEST (7.8.d) — Anti-smuggling `precio_snapshot` en item**: item con `"precio_snapshot": 0.01` → 422 (forbid en `ItemPedidoRequest`).
- [x] 7.20 **TEST (7.9.a) — Items vacío rechaza**: `"items": []` → 422 con `min_length=1`.
- [x] 7.21 **TEST (7.9.b) — Cantidad cero/negativa rechaza**: `"cantidad": 0` → 422.
- [x] 7.22 **TEST (7.9.c) — Sin `items` rechaza**: body sin `items` → 422 con campo requerido.
- [x] 7.23 **TEST (7.10.a) — Sin Authorization responde 401**: `POST /api/v1/pedidos` sin header → 401.
- [x] 7.24 **TEST (7.10.b) — Token inválido responde 401**: header `Bearer xxxxxxx` → 401.
- [x] 7.25 **TEST (7.10.c) — Usuario sin rol CLIENT responde 403**: crear usuario ADMIN-only → 403 al intentar crear pedido.
- [x] 7.26 **TEST (7.11) — Total con precios fraccionarios**: 2 items (19.99 × 3 = 59.97) + (10.50 × 2 = 21.00) + costo_envio 50.00 → 201 y `total == Decimal("130.97")` (sin pérdida de precisión). Pg_only por items. NOTA: si el stock no alcanza, el test debe armar el producto con stock suficiente — el assertion es sobre el total, no sobre el error.
- [x] 7.27 Marcar con `@pytest.mark.pg_only` todos los tests que inserten `order_items` (la mayoría de los happy path + atomicidad). Los tests de validación Pydantic puros (anti-smuggling, items vacíos, auth) pueden correr en SQLite porque nunca llegan a la BD.

## 8. Verify — pytest + sanity de migration

- [x] 8.1 Ejecutar `uv run pytest backend/tests/integration/test_orders.py -v` y verificar que todos los tests pasan (algunos skipean si no hay PG — ese skip está esperado y debe loggearse claramente). Resultado: 18 passed, 6 skipped.
- [x] 8.2 Ejecutar `uv run pytest backend/tests -v` (suite completa) y verificar que los 286 tests previos siguen pasando (no debe haber regresiones en otros features). Resultado: 304 passed, 6 skipped.
- [x] 8.3 Ejecutar `uv run alembic downgrade -1` y verificar que revierte limpiamente. Luego `uv run alembic upgrade head` y verificar que vuelve a aplicar sin errores. Es opcional pero highly recommended para validar la migration.
- [ ] 8.4 (Opcional) Smoke test manual con `uvicorn`: arrancar el server, hacer login como CLIENT, `POST /api/v1/pedidos` con un body razonable y verificar 201 + payload. Documentar el output en el PR.
- [ ] 8.5 Validar el change con `openspec validate order-creation-backend` antes de marcarlo como listo para apply.
- [x] 8.6 Actualizar (o crear) `backend/features/orders/README.md` documentando: arquitectura del feature, decisión D2 (pg_only), decisión D5 (`costo_envio` fijo), patrón D7 (dos repositories en el mismo UoW).
- [x] 8.7 No archivar — esperar revisión humana del usuario antes de `/opsx:archive`.
