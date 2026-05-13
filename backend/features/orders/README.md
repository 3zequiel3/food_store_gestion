# Orders Feature

Implementa `POST /api/v1/pedidos` — creación atómica de pedidos (Sprint 5, change #14).

## Arquitectura

```
router.py  →  service.py  →  repository.py  →  models.py
                   ↓
             UnitOfWork
            /          \
  OrderRepository   AddressRepository
```

- **D3 (Service-driven UoW)**: el router NO abre UoW. `OrderService.crear_pedido()` abre `with UnitOfWork() as uow:` y cierra la transacción.
- **D7 (dos repos en el mismo UoW)**: `OrderRepository` (pedido, items, historial) + `AddressRepository` (ownership enforcement). Misma transacción, cero duplicación de lógica.
- **D8 (un solo repo por agregado)**: `OrderRepository` maneja `Pedido`, `DetallePedido` y `HistorialEstadoPedido`. No hay micro-repos.

## Decisiones relevantes

### D2 — `personalizacion: ARRAY(Integer)` (pg_only)

`DetallePedido.personalizacion` es `ARRAY(Integer)` — tipo nativo de PostgreSQL definido por la spec (RN-PE07). SQLite no soporta este tipo. En consecuencia:
- El conftest excluye `order_items` de `create_all` en SQLite (`pg_only = {"order_items"}`).
- Los tests que insertan en `order_items` (happy path, snapshots, atomicidad, precision decimal) están marcados `@pytest.mark.pg_only`.
- Los tests de validación (anti-smuggling, pydantic, auth, stock, forma_pago, ownership) NO necesitan PG porque fallan antes de llegar a `order_items`.

Para correr los pg_only tests: `DATABASE_URL=postgresql://... uv run pytest`.

### D5 — `costo_envio` fijo v1

`costo_envio = Decimal("50.00")` con dirección, `Decimal("0.00")` sin dirección (retiro en local).

**Deuda técnica**: constante definida en `service.py::SHIPPING_COST_DEFAULT`. Para cálculo dinámico por zona, agregar un change futuro `shipping-pricing`.

### D11 — Decimal end-to-end

Todos los cálculos monetarios usan `decimal.Decimal`. El modelo usa `Numeric(10, 2)`. Pydantic v2 serializa `Decimal` como string (sin pérdida de precisión). **Nunca usar `float` para dinero.**

### D1 — nullable FK `direccion_entrega_id`

`orders.direccion_entrega_id` y `orders.direccion_snapshot` son `nullable=True`. `NULL` = retiro en local (modalidad válida según la spec). La FK usa `ON DELETE SET NULL` para preservar el snapshot histórico cuando el usuario borra la dirección (RN-DA06).

Migration: `20260511_2315_512cfb7c337d_orders_direccion_nullable.py`.

## Flujo UoW de 9 pasos (spec §7.1)

1. Validar `forma_pago_codigo` — `BusinessRuleError` → 422 si inválida.
2. Validar `direccion_id` ownership — `NotFoundError` → 404 si no pertenece al user (D6 anti-leak).
3. Build `direccion_snapshot` — texto inmutable, `None` para retiro en local.
4. Validar cada producto con `SELECT FOR UPDATE` — stock, disponibilidad.
5. Calcular `subtotal` y `total` con `Decimal`.
6. `INSERT Pedido` — flush para obtener `id`.
7. `INSERT DetallePedido` × N — snapshots de precio y nombre desde el ORM.
8. `INSERT HistorialEstadoPedido` — `estado_anterior=None`, `estado_nuevo=PENDIENTE`.
9. `refresh(pedido, ["creado_en"])` — para que el campo esté disponible después del cierre.

`UoW.__exit__` hace `commit()` en salida limpia o `rollback()` ante cualquier excepción.

## Endpoints

| Método | Path | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/v1/pedidos/` | CLIENT | Crear pedido |

Endpoints de lectura (`GET`) pertenecen a `order-visualization-backend` (#17).
