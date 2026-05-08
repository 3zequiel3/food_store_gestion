## Context

### Estado actual del proyecto

- **Modelo `Producto` ya existe** en `backend/features/products/models.py` (líneas 82-123) con todos los campos del ERD: `nombre`, `descripcion`, `precio NUMERIC(10,2)`, `stock_cantidad`, `disponible`, `imagen_url`, más los campos heredados de `BaseModel` (`id`, `creado_en`, `actualizado_en`, `eliminado_en`). Las relaciones M:N hacia `Categoria` e `Ingrediente` están declaradas con `secondary="product_categories"` y `secondary="product_ingredients"`. Hay un **smell técnico menor**: el atributo Python es `precio: Mapped[float]` aunque la columna SQL es `Numeric(10,2)`. No requiere migración pero los schemas Pydantic deben usar `Decimal` para no perder precisión.
- **Modelos pivote `ProductoCategoria` y `ProductoIngrediente`** existen en el mismo archivo (líneas 20-43 y 50-75 respectivamente) heredando de `PivotBaseModel` (PK compuesta + `creado_en`/`actualizado_en`/`eliminado_en`). **Ninguno tiene flags de dominio** (`es_principal` ni `es_removible`). Este change agrega `es_removible` al pivote de ingredientes vía migración Alembic nueva.
- **Tablas SQL** creadas en `backend/alembic/versions/20260428_0001_8d61b8e48f6b_initial_schema.py`:
  - `products` (líneas 313-338): `id BIGSERIAL`, `nombre VARCHAR(255) NOT NULL`, `descripcion TEXT`, `precio NUMERIC(10,2) NOT NULL` con `CHECK (precio > 0)`, `stock_cantidad INTEGER NOT NULL DEFAULT 0` con `CHECK (stock_cantidad >= 0)`, `disponible BOOLEAN NOT NULL DEFAULT true` (indexado), `imagen_url VARCHAR(500)`, timestamps `BaseModel`.
  - `product_categories` (líneas 343-373): PK (`product_id`, `category_id`), FK a `products` ON DELETE CASCADE y a `categories` ON DELETE CASCADE. Sin columnas de dominio.
  - `product_ingredients` (líneas 376-406): PK (`product_id`, `ingredient_id`), FK a `products` ON DELETE CASCADE y a `ingredients` ON DELETE RESTRICT. **Sin `es_removible`** — gap a corregir.
- **Migración 0002** (`20260506_1620_77bcb99d97db`) sólo ajusta `refresh_tokens.token_hash`. La nueva migración de este change será la **0003** y la primera de feature post-initial.
- **Router stub existente**: `backend/features/products/router.py` (líneas 1-39) tiene 3 endpoints stub que devuelven `{"status": "not_implemented"}`. El `main.py` ya monta `products_router` en `/api/v1/products` (línea 197) — debe **renombrarse a `/api/v1/productos`** para ser consistente con `/categorias` e `/ingredientes` y con la spec textual del integrador §5.2.
- **`schemas.py`, `service.py`, `repository.py`** del módulo están vacíos (1 línea cada uno) — se rellenan completos en este change.
- **`backend.features.products.models` ya está importado en `alembic/env.py`** (línea 78). La migración auto-generada de `es_removible` debería funcionar; si Alembic no detecta el cambio (compara_type/compare_server_default a veces falla), se escribe a mano siguiendo el patrón de la migración 0002.
- **`BaseRepository[T]`** (`backend/shared/repository.py`) está limpio post-fixes: `_get_base_query()` filtra `eliminado_en IS NULL` automáticamente, `update()` ignora `id` y `creado_en` (immutable fields), `delete()` hace soft delete via `eliminado_en = datetime.now(timezone.utc)`. Heredamos sin overrides.
- **`UnitOfWork`** vía `Depends(get_uow)` en `backend/dependencies.py` — generator con commit/rollback/close. NO context manager (deuda D6 reconocida).
- **`require_role(*roles)` y `get_current_user`** en `backend/features/auth/dependencies.py` totalmente operativos.
- **Conftest** (`backend/tests/integration/conftest.py`) overridea `get_uow` Y `get_db` para SQLite in-memory. Los tests de `categories` e `ingredients` corren con esto sin tocar nada.
- **Patrones canónicos a clonar**: `backend/features/categories/` y `backend/features/ingredients/` recién archivados, ambos con `BaseRepository[T]` heredado limpio + paginación + `find_by_nombre` + RBAC `require_role("ADMIN", "STOCK")` en mutations.

### Capabilities reusadas

- `auth/spec.md` — `require_role`, `get_current_user`, JWT.
- `base-entities/spec.md` — `BaseModel`, `PivotBaseModel`, modelos `Producto`/`ProductoCategoria`/`ProductoIngrediente`/`Categoria`/`Ingrediente`.
- `error-handling/spec.md` — RFC 7807 obligatorio para todos los errores; handlers globales en `main.py` para `NotFoundError`, `ConflictError`, `BusinessRuleError`, `ValidationError`, `ForbiddenError`, `UnauthorizedError`.
- `database-migrations/spec.md` — schema actual de `products`, `product_categories`, `product_ingredients`. La nueva revisión Alembic se suma a esta capability sin modificar requirements existentes.
- `categories/spec.md` — patrón canónico de capability CRUD con guards (no aplica acá, pero se replica el shape del módulo).
- `ingredients/spec.md` — `Ingrediente` ORM disponible, endpoints públicos para validar `ingrediente_id` y leer `es_alergeno`.

### Stakeholders

- **ADMIN** y **STOCK** — escriben productos (POST/PUT/PATCH/DELETE) y gestionan asociaciones M:N.
- **CLIENT** y **anónimo** — leen catálogo (`GET /`, `GET /{id}`, `GET /{id}/ingredientes`). Sin necesidad de autenticación.
- **`order-creation-backend` (#13)** — bloqueado por este change. Necesita leer `Producto` (precio + stock + disponible) y `ProductoIngrediente` (lista de ingredientes con `es_removible`) para hacer snapshot al crear pedido y validar personalización (`OrderItem.personalizacion = INTEGER[]` con IDs de ingredientes removidos — RN-PE07).
- **`payment-mercadopago-backend` (#14)** y **`order-state-machine-fsm` (#15)** — dependen indirectamente vía orders.
- **`products-frontend-catalog` (#21)** — consumirá los 11 endpoints para armar el catálogo público y el panel admin.

## Goals / Non-Goals

**Goals:**

- Habilitar las 11 operaciones REST para gestionar el catálogo (CRUD producto + 3 endpoints M2M de ingredientes + 1 endpoint M2M de categorías + 2 PATCH específicos) cumpliendo US-015 a US-023 y RN-CA04 a RN-CA09.
- Cerrar el gap de schema `es_removible` en `product_ingredients` con una migración Alembic nueva, dejando el modelo ORM y el schema Pydantic alineados con el ERD del integrador §3.2.
- Implementar el listado paginado del catálogo con los 4 filtros combinables (`categoria_id`, `search`, `disponible`, `excluir_alergenos`) en una única query SQL eficiente.
- Cumplir la regla de oro de imports `Router → Service → UoW → Repository → Model` sin excepciones.
- Adelantar el RBAC final `require_role("ADMIN", "STOCK")` en escrituras (anticipa US-064 / `admin-catalog-permissions` #19) — consistencia con `categories-backend` e `ingredients-backend`.
- Mantener el soft delete como única vía de borrado del producto (RN-CA09); las pivote no se tocan en delete del producto (los registros viejos quedan referenciando el producto eliminado).
- Preservar la precisión NUMERIC(10,2) del precio en todos los schemas Pydantic usando `Decimal` (RN-CA04) — el modelo SQLAlchemy tiene un type hint `Mapped[float]` que se documenta como smell pero NO se modifica acá.
- Suite de tests cubriendo CRUD + RBAC + filtros combinados + asociaciones M2M + soft delete + migración aplicada.

**Non-Goals:**

- NO refactorizar `UnitOfWork` para hacerlo context manager (deuda D6 idéntica a `categories` e `ingredients`).
- NO agregar `es_principal` al pivote `product_categories`. El ERD textual lo lista pero ni la migración inicial ni US-016 ni §5.2 lo exigen. Se difiere indefinidamente.
- NO implementar upload real de imagen (S3 / local storage). El campo `imagen_url` recibe URL string.
- NO hacer snapshot de precio/nombre acá — es responsabilidad de `order-creation-backend` (#13). Sólo dejamos `Producto` accesible.
- NO implementar optimistic locking de stock (`SELECT FOR UPDATE`). El `PATCH /stock` usa seteo absoluto via `UPDATE WHERE` sobre una sola fila — atómico y suficiente para v1 mono-usuario académico.
- NO modificar el type hint `precio: Mapped[float]` en el modelo ORM. La conversión a `Decimal` se hace en los schemas Pydantic; cambiar el modelo es alcance de un mini-change futuro.
- NO incluir el query param `incluir_eliminados` para admin (RN-CA10). No se implementó en categories ni ingredients tampoco; va con un change de vista admin.
- NO crear frontend (Sprint 7).
- NO modificar el modelo `Producto` (no requiere cambios).

## Decisions

### D1 — Migración Alembic nueva: `add_es_removible_to_product_ingredients`

Agregar `es_removible BOOLEAN NOT NULL DEFAULT false` a la tabla `product_ingredients` en una migración nueva, con `down_revision = '77bcb99d97db'` (la migración de refresh_tokens).

**Esquema del archivo** (path sugerido: `backend/alembic/versions/<rev>_add_es_removible_to_product_ingredients.py`):

```python
def upgrade() -> None:
    op.add_column(
        "product_ingredients",
        sa.Column(
            "es_removible",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )

def downgrade() -> None:
    op.drop_column("product_ingredients", "es_removible")
```

**Por qué `server_default=sa.false()`**: si la tabla ya tiene filas en algún ambiente, no quedan en estado inválido cuando se aplica el `NOT NULL`. En el ambiente de desarrollo del proyecto la tabla está vacía, pero la práctica correcta es siempre dar default cuando se agrega una NOT NULL column post-creación. Para v1 dejamos el `server_default` para no romper inserts directos del repositorio que no envíen el campo; los schemas Pydantic siempre lo envían explícitamente.

**Cómo generar el archivo**:

1. Editar el modelo `ProductoIngrediente` en `backend/features/products/models.py` agregando `es_removible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa.false())`.
2. Correr `alembic revision --autogenerate -m "add es_removible to product_ingredients"`.
3. Revisar el archivo generado: si Alembic detectó el cambio, queda casi listo (puede faltar `server_default` — agregarlo a mano). Si NO detectó nada (a veces pasa con `compare_server_default`), escribir el upgrade/downgrade manualmente siguiendo el snippet de arriba.
4. **Verificar** que el archivo tenga `down_revision = '77bcb99d97db'` (el último head actual).

**Alternativa descartada**: agregar la columna como NULL para no requerir default. Quedaría inconsistente con el ERD del integrador (§3.2) que la marca explícita como `NOT NULL`. Y el código del service/schema que lee el flag tendría que tolerar `None`, ensuciando el dominio.

### D2 — Modelo ORM `ProductoIngrediente` extiende con `es_removible`

Agregar al modelo en `backend/features/products/models.py` (después del bloque de `ingredient_id`):

```python
es_removible: Mapped[bool] = mapped_column(
    Boolean,
    nullable=False,
    default=False,
    server_default=sa.false(),
)
```

`default=False` aplica cuando se crea la instancia desde Python sin pasar el campo. `server_default=sa.false()` matchea la migración para que SQLAlchemy compare bien con la DB y no marque drift. Esta línea es la única modificación al archivo `models.py`.

### D3 — Gestión de categorías M:N: ambos caminos (body + endpoint dedicado)

`POST /productos` y `PUT /productos/{id}` aceptan `categoria_ids: list[int] | None = None` en el body. Si se pasa `None` no se tocan las asociaciones. Si se pasa una lista (incluso vacía `[]`), reemplaza todo el set de categorías del producto.

Adicionalmente se expone `PUT /productos/{id}/categorias` con body `{categoria_ids: list[int]}` que hace exactamente el mismo `replace`. Este endpoint dedicado es el que pide US-016 textualmente y el que el frontend va a usar para gestión de categorías post-creación (tal como muestra el wireframe §5.2).

**Por qué los dos caminos**:

- El body en POST cubre el caso "creación con categorías ya asociadas" (US-015 + US-016 simultáneo).
- El body en PUT cubre el caso "edito todo el producto y de paso reasigno categorías" — útil para el form del admin.
- El endpoint dedicado cubre el caso "sólo quiero cambiar categorías sin tocar el producto" — más limpio para el flujo de re-categorizar.

**Alternativa descartada**: sólo body en POST/PUT, sin endpoint dedicado. Forzaría al frontend a re-enviar el producto entero cada vez que cambian las categorías. US-016 lo exige explícito.

**Implementación**: ambos caminos llaman al mismo método `ProductService.set_categorias(producto_id, categoria_ids)`, que hace el replace bulk.

### D4 — Gestión de ingredientes M:N: POST/DELETE individuales + GET listado (NO bulk PUT)

Sigue §5.2 textual:

- `GET /productos/{id}/ingredientes` — listado de ingredientes con flag `es_removible`.
- `POST /productos/{id}/ingredientes` con body `{ingrediente_id: int, es_removible: bool}` — agrega una asociación (409 si ya existe activa).
- `DELETE /productos/{id}/ingredientes/{ing_id}` — quita la asociación (soft delete del pivote — `eliminado_en = now()`).

NO hay PUT bulk para ingredientes (a diferencia de categorías). La razón: cada asociación lleva un flag `es_removible` propio, y el bulk sería ambiguo (¿mantener flag previo? ¿pisar todos a `false`?). El form del admin va a usar agregar/quitar individualmente para mantener el flag explícito.

**Alternativa descartada**: PUT bulk con body `[{ingrediente_id, es_removible}, ...]`. Se rechaza por la complejidad del diff (qué quitar, qué actualizar, qué agregar) y porque §5.2 lista explícito los endpoints individuales.

**Implementación**:

- `add_ingrediente(producto_id, ingrediente_id, es_removible)`: si existe activo → 409. Si existe soft-deleted → reactivar (`eliminado_en = NULL`, `es_removible = nuevo_valor`). Si no existe → INSERT.
- `remove_ingrediente(producto_id, ingrediente_id)`: si existe activo → soft delete (set `eliminado_en`). Si soft-deleted o no existe → 404.

### D5 — `PATCH /{id}/stock`: seteo absoluto

Body: `{stock_cantidad: int}` (enteros >= 0). Reemplaza el valor actual.

**Por qué seteo absoluto y no incremento relativo**:

- Más simple para el cliente (no hay que leer el stock antes de actualizar).
- Cero race conditions al pisar el valor (el último escritor gana, pero nadie pierde stock por delta acumulado mal).
- Cumple US-021 textualmente ("Actualizar stock con cantidad absoluta o relativa" — la spec lista las dos opciones, elegimos la simple).
- Atómico via `UPDATE products SET stock_cantidad=:val WHERE id=:id AND eliminado_en IS NULL`.

**Limitación documentada**: si dos admins simultáneamente setean stock de la misma fila, el último escritor gana. Para v1 mono-usuario académico es aceptable. La operación atómica real con incremento (`SET stock_cantidad = stock_cantidad - :cantidad WHERE stock_cantidad >= :cantidad`) la implementará `order-creation-backend` (#13) con `SELECT FOR UPDATE` cuando se descuente stock por venta (RN-PE04).

**Validación**: el service rechaza valores negativos con `BusinessRuleError("El stock no puede ser negativo")` antes de tocar la DB. El CHECK `stock_cantidad >= 0` ya en la DB es segunda línea de defensa.

### D6 — `PATCH /{id}/disponibilidad`: toggle explícito

Body: `{disponible: bool}`. Pisa el valor actual. Endpoint separado del PUT general porque US-022 lo pide explícito y permite que el admin tenga un toggle simple sin tener que enviar todo el producto.

`disponible = false` esconde el producto del catálogo público (`GET /` con default filter `disponible=true`) sin necesidad de soft-delete. Se puede revertir con un PATCH a `true`.

### D7 — Roles para mutations: `require_role("ADMIN", "STOCK")` en TODAS las mutations

Aplicamos ADMIN+STOCK en POST, PUT, PATCH, DELETE y los 4 endpoints M2M.

**Anticipación intencional vs §5.2**: §5.2 indica sólo ADMIN para crear/editar/eliminar producto. El proyecto ya estableció el patrón ADMIN+STOCK en `categories-backend` y `ingredients-backend`, alineado con la matriz final que define US-064 (`admin-catalog-permissions` #19). Si arrancamos con ADMIN solo y después abrimos a STOCK, hay que tocar este módulo dos veces. Anticipamos para cero deuda.

**Tradeoff aceptado**: si US-064 cambia (improbable — está cerrada en spec), tocaríamos este módulo. Riesgo bajo, beneficio alto.

### D8 — Schemas Pydantic v2: separación estricta + `Decimal` para `precio`

Schemas (todos en `backend/features/products/schemas.py`):

- **`ProductoCreate`**: `nombre: str` (1-255), `descripcion: str | None`, `precio: Decimal` (>0, max_digits=10, decimal_places=2), `stock_cantidad: int = 0` (≥0), `disponible: bool = True`, `imagen_url: str | None` (max 500), `categoria_ids: list[int] | None = None` (opcional, ver D3).
- **`ProductoUpdate`**: todos los campos opcionales (`Field(None, ...)`). Usa `model_dump(exclude_unset=True)` en service para distinguir "no enviado" de "enviado None". Sin `categoria_ids` (para eso está el endpoint dedicado y POST).
- **`ProductoRead`**: salida sin relaciones populadas (uso en lista paginada). Campos: `id`, `nombre`, `descripcion`, `precio: Decimal`, `stock_cantidad`, `disponible`, `imagen_url`, `creado_en`, `actualizado_en`. `model_config = {"from_attributes": True}`.
- **`ProductoDetail`**: extiende `ProductoRead` agregando `categorias: list[CategoriaRead]` e `ingredientes: list[IngredienteAsociadoRead]`. Se usa en `GET /{id}`. Las clases de salida `CategoriaRead` e `IngredienteAsociadoRead` se definen acá (no se importan de `categories.schemas` ni `ingredients.schemas` para evitar import circular y porque las usamos sólo como nested DTOs).
- **`IngredienteAsociadoRead`**: `id`, `nombre`, `es_alergeno`, `es_removible` (bool — leído del pivote).
- **`PaginatedProductos`**: `items: list[ProductoRead]`, `total`, `page`, `limit`.
- **`PatchDisponibilidad`**: `disponible: bool`.
- **`PatchStock`**: `stock_cantidad: int = Field(..., ge=0)`.
- **`AsociarIngrediente`**: `ingrediente_id: int`, `es_removible: bool = False`.
- **`SetCategorias`**: `categoria_ids: list[int]`.

**Por qué `Decimal` y no `float`**: el modelo ORM tiene `precio: Mapped[float]` (smell heredado), pero la columna es `NUMERIC(10,2)`. SQLAlchemy devuelve `Decimal` al leer; el type hint de Python es float. En Pydantic v2, declarar el campo del schema como `Decimal` con `model_config = {"from_attributes": True}` fuerza el cast correcto y preserva precisión RN-CA04. Sin esto, `1.99` puede leerse como `1.9900000001`. Probado en el suite.

### D9 — Repository: `ProductRepository(BaseRepository[Producto])` con métodos especializados

Hereda CRUD y `_get_base_query()` (filtra `eliminado_en IS NULL`) sin overrides. Agrega:

- **`find_by_nombre(self, nombre: str) -> Producto | None`** — busca exact match en `nombre`. **Filtra `eliminado_en IS NULL`** porque NO hay UNIQUE constraint en `products.nombre` (a diferencia de `ingredients.nombre`); el service NO usa esto para validar unicidad (no es requirement) sino sólo si quisiéramos chequear duplicados en el futuro. **Decisión: NO validar unicidad de nombre en este change** — US-015 no lo pide y la migración no tiene el constraint. El método queda como utility, NO se invoca en el flujo de POST.

  **Nota**: si más adelante se decide agregar UNIQUE, hay que decidir si filtrar `eliminado_en` o no (analog a la decisión de `categories.find_by_nombre_y_padre` vs `ingredients.find_by_nombre`). Por ahora se documenta como `# Reserved for future use` en el code-review.

- **`list_paginated_with_filters(self, *, skip, limit, categoria_id=None, search=None, disponible=None, excluir_alergenos=False) -> tuple[list[Producto], int]`** — la query más compleja del proyecto. Detalle del SQL en D10.

- **`get_with_associations(self, id: int) -> Producto | None`** — variante de `read()` que hace eager load de `categorias` e `ingredientes` (`selectinload` o `joinedload`) para `ProductoDetail`. Para los ingredientes necesita además leer `es_removible` del pivote, lo cual NO se carga vía la relación M:N (la relación atraviesa el pivote pero no expone sus columnas). Por eso hay un **método separado** `list_ingredientes` que devuelve `tuple[Ingrediente, bool]`.

- **`replace_categorias(self, producto_id: int, categoria_ids: list[int]) -> None`** — bulk replace:
  1. Soft delete (`eliminado_en = now()`) las filas activas en `product_categories` con `product_id == :id` que NO estén en `categoria_ids`.
  2. Para cada `category_id` en `categoria_ids`: si existe soft-deleted → reactivar; si no existe → INSERT; si existe activo → no hace nada.
  3. NO hace commit. El router commitea.

- **`add_ingrediente(self, producto_id: int, ingrediente_id: int, es_removible: bool) -> ProductoIngrediente`** — INSERT con manejo de soft-deleted: si existe activo → raise `ConflictError` (router lo traduce a 409). Si soft-deleted → reactivar y actualizar `es_removible`. Si no existe → INSERT.

- **`remove_ingrediente(self, producto_id: int, ingrediente_id: int) -> bool`** — soft delete del pivote. Devuelve True si se desactivó, False si no existía activo (router → 404).

- **`list_ingredientes(self, producto_id: int) -> list[tuple[Ingrediente, bool]]`** — query JOIN de `product_ingredients` con `ingredients` filtrando `eliminado_en IS NULL` en ambos lados. Devuelve `[(Ingrediente, es_removible), ...]` para que el service arme `IngredienteAsociadoRead`.

### D10 — Query del catálogo público: shape SQL exacto

`list_paginated_with_filters` construye una query base sobre `Producto` con `_get_base_query()` (ya filtra `eliminado_en IS NULL`) y aplica filtros condicionalmente:

**1. Filtro `categoria_id`** (si no None):
```sql
INNER JOIN product_categories pc ON pc.product_id = products.id
  AND pc.eliminado_en IS NULL
  AND pc.category_id = :categoria_id
```

**2. Filtro `search`** (si no None y no vacío post-strip):
```sql
WHERE LOWER(products.nombre) LIKE LOWER(:pattern)
-- pattern = f"%{search}%"
```
**Decisión**: usar `LOWER(...)` + `LIKE` en lugar de `ILIKE` (PG-only). El conftest de tests usa SQLite in-memory y `ILIKE` no existe en SQLite. `LOWER(LIKE)` funciona en ambos motores y es semánticamente equivalente para case-insensitive search en strings Latin-1. Hay un índice `idx_products_nombre` en la migración 0001 — el `LOWER` rompe el uso del índice en PG, pero para v1 con catálogo de hasta cientos de productos es aceptable. Si más adelante hace falta perf, se agrega un functional index `LOWER(nombre)` en una migración nueva.

**3. Filtro `disponible`**:
- Si `disponible` query param NO se pasa: comportamiento depende del role del caller. Para v1, **siempre filtrar `disponible=true`** (RN-CA08 — catálogo público). Si el endpoint admin necesita ver todo, se agrega `?disponible=false` o se usa un endpoint admin separado en un change futuro.
- Si `disponible=true`: `WHERE products.disponible = true`.
- Si `disponible=false`: `WHERE products.disponible = false`.

**Decisión refinada**: el query param `disponible` ES opcional. Si no se pasa → default `true` (RN-CA08, comportamiento del catálogo público). Si se pasa explícito → respetar. Esto deja la puerta abierta para que un endpoint admin futuro pase `?disponible=false` sin cambiar el código.

**4. Filtro `excluir_alergenos`** (booleano, default `false`):
```sql
WHERE NOT EXISTS (
  SELECT 1
  FROM product_ingredients pi
  JOIN ingredients i ON pi.ingredient_id = i.id
  WHERE pi.product_id = products.id
    AND pi.eliminado_en IS NULL
    AND i.eliminado_en IS NULL
    AND i.es_alergeno = true
    AND pi.es_removible = false
)
```
Lógica: excluir productos que tienen al menos un ingrediente alérgeno NO removible. Los productos con alérgenos removibles SÍ aparecen (porque el cliente puede personalizar el pedido para quitarlo — RN-PE07).

**Combinación**: todos los filtros se acumulan con `AND`. La query final es:

```sql
SELECT products.*
FROM products
[INNER JOIN product_categories pc ON ... if categoria_id]
WHERE products.eliminado_en IS NULL
  [AND LOWER(products.nombre) LIKE LOWER(:pattern) if search]
  [AND products.disponible = :disponible]
  [AND NOT EXISTS (...) if excluir_alergenos]
ORDER BY products.nombre
OFFSET :skip LIMIT :limit
```

El count usa `SELECT count(*) FROM (subquery_sin_offset_limit)`.

**Performance**: para v1 con catálogo de hasta unos cientos de productos esto es OK. Indices existentes (`idx_products_nombre`, `idx_products_disponible`) ayudan parcialmente. No hace falta optimizar por ahora.

### D11 — Service: `ProductService` orquesta validaciones + soft delete + replace bulk

Estructura (`backend/features/products/service.py`):

```python
class ProductService:
    def __init__(self, uow: UnitOfWork) -> None:
        uow.register_repository("productos", ProductRepository(uow.session))
        # Necesita acceso a categorías e ingredientes para validar FKs:
        uow.register_repository("categorias", CategoryRepository(uow.session))
        uow.register_repository("ingredientes", IngredientRepository(uow.session))
        self.uow = uow
        self.repo = uow.get_repository("productos")
        self.cat_repo = uow.get_repository("categorias")
        self.ing_repo = uow.get_repository("ingredientes")
```

**Métodos**:

- `create(payload: ProductoCreate) -> Producto`: valida nombre no vacío (post-strip), `precio > 0` (Pydantic), `stock_cantidad >= 0` (Pydantic). Si `payload.categoria_ids` no None, valida que cada id exista en `categorias` (NotFoundError → BusinessRuleError "Categoría {id} no encontrada"). INSERT producto + replace_categorias (si aplica).
- `get_by_id(producto_id) -> Producto`: `repo.read(id)` → 404 si None.
- `get_detail(producto_id) -> tuple[Producto, list[Categoria], list[tuple[Ingrediente, bool]]]`: reutiliza `get_with_associations` + `list_ingredientes`. El router arma el `ProductoDetail`.
- `list_paginated(*, page, limit, categoria_id, search, disponible, excluir_alergenos)`: convierte `page → skip`, llama `list_paginated_with_filters`. **Default de `disponible` viene del router**: si query param no se pasa → True.
- `update(producto_id, payload: ProductoUpdate) -> Producto`: read → 404 si None. `data = payload.model_dump(exclude_unset=True)`. Aplica `repo.update(id, **data)`.
- `set_disponibilidad(producto_id, disponible: bool) -> Producto`: read → 404. `repo.update(id, disponible=disponible)`.
- `set_stock(producto_id, stock: int) -> Producto`: read → 404. Si `stock < 0` → BusinessRuleError. `repo.update(id, stock_cantidad=stock)`.
- `delete(producto_id) -> None`: read → 404 si None. `repo.delete(id)` (soft delete heredado). **Sin guards** — si quedan filas en `product_categories` o `product_ingredients` no se tocan; el catálogo público filtra por `products.eliminado_en IS NULL` así que dejan de aparecer naturalmente.
- `set_categorias(producto_id, categoria_ids: list[int]) -> Producto`: read → 404. Valida cada id en `categorias` (NotFoundError → BusinessRuleError "Categoría {id} no encontrada"). `repo.replace_categorias(producto_id, categoria_ids)`. Devuelve el producto re-leído con eager load (o el mismo con relación refrescada).
- `add_ingrediente(producto_id, ingrediente_id, es_removible) -> ProductoIngrediente`: read producto → 404. Read ingrediente → BusinessRuleError "Ingrediente no encontrado" si None. `repo.add_ingrediente(...)` — propaga ConflictError del repo.
- `remove_ingrediente(producto_id, ingrediente_id) -> None`: read producto → 404. `repo.remove_ingrediente(...)` → 404 si False.
- `list_ingredientes(producto_id) -> list[tuple[Ingrediente, bool]]`: read producto → 404. `repo.list_ingredientes(producto_id)`.

**Ningún método llama `uow.commit()`** — el router lo decide.

### D12 — Router: 11 endpoints + cambio de prefix en main.py

Estructura (`backend/features/products/router.py`):

- Reemplaza completamente el stub actual.
- Patrón canónico de `ingredients/router.py`: `Depends(get_uow)` + `Depends(require_role(...))` cuando aplica.
- `uow.commit()` en cada mutation; sin commit en GETs.
- Errores fluyen del service vía exceptions tipadas — handlers globales en `main.py` ya devuelven RFC 7807.

**Modificación en `main.py`**:

```python
# Antes (línea 197):
app.include_router(products_router, prefix="/api/v1/products", tags=["products"])
# Después:
app.include_router(products_router, prefix="/api/v1/productos", tags=["products"])
```

El cambio del prefix no afecta nada más — no hay frontend que ya esté usando `/products`, y el resto del catálogo ya está en español.

### D13 — Tests: clonar patrón de ingredients + agregar suites M2M

`backend/tests/integration/test_products.py` con bloques:

1. **CRUD básico** (POST/GET list/GET id/PUT/PATCH disponibilidad/PATCH stock/DELETE) — happy paths para cada endpoint.
2. **RBAC** (sin auth → 401, CLIENT → 403, ADMIN → 200/201, STOCK → 200/201) — repetido para cada mutation.
3. **Validación** (precio ≤ 0 → 422, stock < 0 → 422, nombre vacío → 422, categoria_id inexistente → 422, ingrediente_id inexistente → 422).
4. **Filtros del catálogo público** — cada uno aislado y combinaciones de 2/3:
   - Sin filtros → todos los activos (default `disponible=true`).
   - `?categoria_id=N` → sólo los asociados.
   - `?search=pizza` → case-insensitive.
   - `?disponible=false` → sólo no-disponibles.
   - `?excluir_alergenos=true` → excluye productos con alérgenos no-removibles.
   - Combinaciones: `?categoria_id=1&search=pizza`, `?disponible=true&excluir_alergenos=true`, los 4 juntos.
5. **Asociaciones M:N de categorías**:
   - POST con `categoria_ids: [1,2]` → producto creado y asociaciones existen.
   - PUT del producto con nuevo `categoria_ids` (NO incluido — D8) → no afecta categorías.
   - `PUT /{id}/categorias` con set distinto → reemplaza.
   - `PUT /{id}/categorias` con `[]` → quita todas.
   - `PUT /{id}/categorias` con id inexistente → 422.
6. **Asociaciones M:N de ingredientes**:
   - `POST /{id}/ingredientes` happy path → 201 + flag `es_removible`.
   - `POST` duplicado → 409.
   - `POST` con ingrediente inexistente → 422.
   - `POST` reactiva soft-deleted (caso del repo).
   - `DELETE` happy path → 204.
   - `DELETE` ya borrado → 404.
   - `GET /{id}/ingredientes` devuelve flag `es_removible` correcto.
7. **Soft delete del producto**:
   - `DELETE` → 204 + fila persiste con `eliminado_en NOT NULL`.
   - `GET /{id}` después de delete → 404.
   - `GET /` excluye productos eliminados.
   - `DELETE` de producto con asociaciones activas → 204 (sin guard); las pivote no se modifican.
8. **Migración aplicada**:
   - Test de smoke que verifica que la columna `es_removible` existe en `product_ingredients` con default `false`. Se ejecuta vía `inspect()` o `text("SELECT es_removible FROM product_ingredients LIMIT 0")`.
9. **Routing**:
   - `GET /api/v1/products` (inglés, prefix viejo) → 404.
   - `GET /api/v1/productos` → 200.
10. **Precio Decimal** (RN-CA04):
    - POST con `precio: 19.99`, GET → response trae `19.99` exacto (no `19.99000001`).

## Risks / Trade-offs

- **[Riesgo] Migración Alembic no detecta `es_removible` con autogenerate** → **Mitigación**: el design especifica el snippet manual del upgrade/downgrade. Si autogenerate falla, se escribe a mano. Documentado en sección D1.

- **[Riesgo] `LOWER(LIKE)` no usa el índice `idx_products_nombre` en PG** → **Mitigación**: aceptable para v1 (catálogo pequeño). Si la perf se degrada, se agrega functional index `CREATE INDEX ON products (LOWER(nombre))` en migración futura. Anotado como deuda menor.

- **[Riesgo] Smell `precio: Mapped[float]` en el modelo ORM** → **Mitigación**: schemas Pydantic usan `Decimal` con `from_attributes=True` para forzar el cast al leer. Test específico (D13.10) valida la precisión. Cambiar el modelo es alcance futuro.

- **[Riesgo] Race condition en `PATCH /stock` con seteo absoluto** → **Mitigación**: documentado en D5. Aceptable para v1 mono-usuario académico. El locking real (RN-PE04) lo implementará `order-creation-backend`.

- **[Riesgo] Soft delete del producto con pivotes activos** → **Mitigación**: las pivote no se tocan; el catálogo público filtra por `products.eliminado_en IS NULL` así que dejan de aparecer naturalmente. El behavior está documentado en tests (D13.7) y en el spec.

- **[Riesgo] Cambio de prefix `/products` → `/productos` rompe consumidores** → **Mitigación**: NO hay consumidores aún (frontend de catálogo es Sprint 7). El cambio es momento ideal porque el resto del catálogo ya está en español y la spec del integrador §5.2 usa `/productos`. Documentado en `What Changes` del proposal.

- **[Riesgo] `replace_categorias` con id inexistente queda inconsistente** → **Mitigación**: el service valida CADA id antes de tocar el repo. Si alguno falla → BusinessRuleError 422 SIN modificar nada. El repo asume input válido.

- **[Riesgo] `ProductoDetail` con eager load impacta performance del endpoint detalle** → **Mitigación**: `GET /{id}` se llama una vez por click — overhead aceptable. La lista paginada usa `ProductoRead` sin eager load.

- **[Trade-off] RBAC ADMIN+STOCK desde este change vs sólo ADMIN (§5.2)** → consistencia con catálogo previo (categories, ingredients) y anticipa US-064. Si la matriz cambia, hay que tocar este módulo. Riesgo bajo.

## Migration Plan

1. Aplicar la nueva migración Alembic en orden (`alembic upgrade head`). En CI/local de tests, las migraciones corren contra SQLite in-memory desde el conftest (los modelos crean schema con `Base.metadata.create_all()`, así que la nueva columna se materializa automáticamente vía el modelo ORM modificado — la migración Alembic sólo importa para Postgres).
2. Verificar manualmente: `psql foodstore_dev -c "\d product_ingredients"` debe mostrar la columna `es_removible boolean DEFAULT false NOT NULL`.
3. Rollback: `alembic downgrade -1` ejecuta el `op.drop_column("product_ingredients", "es_removible")`. Sin pérdida de datos en otros campos.

## Open Questions

Ninguna pendiente al momento de proponer. Todas las decisiones quedaron cerradas en este design (D1-D13). Si durante el apply surge alguna ambigüedad técnica (por ejemplo: `selectinload` vs `joinedload` en `get_with_associations`), se resuelve in-place y se documenta en el commit; no requiere volver a propose.
