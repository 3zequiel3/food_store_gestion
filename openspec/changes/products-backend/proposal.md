## Why

`products-backend` es el **corazón del catálogo** y el primer change que abre el camino al flujo de pedidos completo (Sprints 4-6) y al frontend de catálogo (Sprint 7). Sin este módulo: (1) no hay forma de listar/crear/editar productos por API, (2) `order-creation-backend` no puede leer precio ni stock para snapshot ni validar disponibilidad al armar pedidos, (3) `payment-mercadopago-backend` no tiene producto que cobrar, (4) la rúbrica académica del integrador queda sin el módulo central de catálogo. Es change único del Sprint 3 (Productos Backend) y bloquea cuatro changes posteriores. Además requiere la **primera migración Alembic de feature post-initial** para agregar `es_removible` a `product_ingredients` (gap del schema 0001), lo que prueba que el flujo de Alembic está sano antes de los demás features.

## What Changes

- Nuevo módulo `backend/features/products/` con las 5 capas pobladas (`router.py`, `service.py`, `repository.py`, `schemas.py`) — el modelo `Producto` y los pivotes ya existen en `backend/features/products/models.py` (creados en `base-entities`/`database-migrations`), NO se redefinen.
- **Nueva migración Alembic** `add_es_removible_to_product_ingredients`: agrega `es_removible BOOLEAN NOT NULL DEFAULT false` a `product_ingredients` (gap entre ERD §3.2 del integrador y la migración inicial `20260428_0001`).
- Modificación menor del modelo ORM `ProductoIngrediente` (`backend/features/products/models.py`) para reflejar la nueva columna `es_removible`.
- 11 endpoints REST bajo `/api/v1/productos`:
  - `POST /` — crear producto con `categoria_ids` opcional en el body (auth: ADMIN | STOCK).
  - `GET /` — listar paginado con filtros `?categoria_id`, `?search` (busca en `nombre`), `?disponible`, `?excluir_alergenos`, `?page`, `?limit` (público).
  - `GET /{id}` — detalle con categorías + ingredientes populados (público).
  - `PUT /{id}` — actualizar nombre, descripción, precio, stock, disponible, imagen_url (auth: ADMIN | STOCK).
  - `PATCH /{id}/disponibilidad` — toggle del flag `disponible` (auth: ADMIN | STOCK).
  - `PATCH /{id}/stock` — seteo absoluto de `stock_cantidad` (auth: ADMIN | STOCK).
  - `DELETE /{id}` — soft delete (auth: ADMIN | STOCK).
  - `PUT /{id}/categorias` — reemplazar el set de categorías de un producto (auth: ADMIN | STOCK).
  - `GET /{id}/ingredientes` — listar ingredientes asociados con flag `es_removible` (público).
  - `POST /{id}/ingredientes` — asociar un ingrediente individual con `es_removible` (auth: ADMIN | STOCK).
  - `DELETE /{id}/ingredientes/{ing_id}` — desasociar un ingrediente (auth: ADMIN | STOCK).
- `ProductRepository(BaseRepository[Producto])` con métodos especializados: `find_by_nombre`, `list_paginated_with_filters` (la query más compleja del proyecto: 4 filtros combinables), `get_with_associations` (eager load), `replace_categorias`, `add_ingrediente`, `remove_ingrediente`, `list_ingredientes`.
- `ProductService` que orquesta validación (precio > 0, stock ≥ 0, FKs a categories e ingredients), soft delete sin guards y replace bulk de categorías. NO hace `uow.commit()`.
- Schemas Pydantic v2 separados: `ProductoCreate`, `ProductoUpdate`, `ProductoRead`, `ProductoDetail` (con relaciones populadas), `PaginatedProductos`, `PatchDisponibilidad`, `PatchStock`, `AsociarIngrediente`, `IngredienteAsociadoRead` (incluye `es_removible`), `SetCategorias`. Todos los schemas que exponen `precio` usan `Decimal`, NO `float`, para preservar precisión NUMERIC(10,2) (RN-CA04).
- Wiring del router en `backend/main.py`: cambiar el prefijo del router `products` de `/api/v1/products` (inglés) a `/api/v1/productos` (español, alineado con `/categorias`, `/ingredientes` y la spec textual del integrador §5.2).
- Spec delta nueva: capability `products` con requirements derivados de US-015 a US-023, RN-CA04 a RN-CA09.
- Tests de integración cubriendo: CRUD completo, RBAC en cada mutation, los 4 filtros de catálogo combinados, soft delete, asociaciones M2M de categorías e ingredientes, migración aplicada.

## Capabilities

### New Capabilities

- `products`: Catálogo de productos con CRUD completo, paginación + filtros combinables (categoría, búsqueda textual, disponibilidad, exclusión por alérgenos), gestión M2M de categorías e ingredientes (con flag `es_removible`), seteo absoluto de stock, toggle de disponibilidad, soft delete y RBAC (ADMIN | STOCK) en todas las escrituras. Cubre US-015, US-016, US-017, US-018, US-019, US-020, US-021, US-022, US-023 y RN-CA04 a RN-CA09.

### Modified Capabilities

Ninguna. Las capabilities existentes (`auth`, `base-entities`, `error-handling`, `database-migrations`, `categories`, `ingredients`) ya cubren los prerrequisitos sin cambios. La nueva migración del campo `es_removible` extiende la `database-migrations` capability vía un archivo de revisión nuevo, pero no modifica los requirements ya escritos en su spec (que sólo cubren la migración inicial 0001 y el alineamiento de refresh_tokens).

## Impact

**Code afectado:**

- Nuevos archivos:
  - `backend/features/products/{router.py, service.py, repository.py, schemas.py}` (los archivos existen vacíos hoy — se rellenan).
  - `backend/alembic/versions/<rev>_add_es_removible_to_product_ingredients.py` (nueva migración).
  - `backend/tests/integration/test_products.py` (suite nuevo).
  - `backend/features/products/README.md` breve.
- Modificación de `backend/features/products/models.py`: agregar atributo `es_removible: Mapped[bool]` a `ProductoIngrediente`.
- Modificación de `backend/main.py`: cambiar el prefix del `products_router` de `/api/v1/products` a `/api/v1/productos` (línea 197). El import y el include se mantienen idénticos en cuanto a estructura.
- Reemplazo total del router stub en `backend/features/products/router.py` (los 3 stubs actuales que devuelven `{"status": "not_implemented"}` son descartados).

**Dependencias resueltas (todos archivados):**

- `auth-backend` y `auth-backend-stabilization` — `require_role`, `get_current_user`, RFC 7807, exceptions tipadas.
- `database-migrations` — schema base con `products`, `product_categories`, `product_ingredients`.
- `base-entities` — `BaseModel`, `PivotBaseModel`, modelos `Producto`/`ProductoCategoria`/`ProductoIngrediente`, `Categoria`, `Ingrediente`.
- `categories-backend` — provee `Categoria` consultable y endpoints públicos para validar `categoria_ids`. Patrón canónico de CRUD a clonar.
- `ingredients-backend` — provee `Ingrediente` consultable y `GET /{id}` para validar `ingrediente_id` antes de asociar; flag `es_alergeno` ya disponible.
- `fix-base-repository-soft-delete`, `fix-base-repository-immutable-fields`, `fix-test-setup-uow-override` — `BaseRepository[T]` limpio, override de `get_uow` en conftest.

**Bloqueado por este change (en orden de roadmap):**

- `order-creation-backend` (#13) — necesita leer `Producto` para hacer snapshot de precio/nombre y validar `disponible` + `stock_cantidad >= cantidad_pedida`.
- `payment-mercadopago-backend` (#14) — necesita el listado de items con sus precios snapshot.
- `order-state-machine-fsm` (#15) — depende del flujo de creación, que depende de productos.
- `products-frontend-catalog` (#21) — consumirá los 11 endpoints para armar el catálogo público y el panel admin.

**Historias cubiertas:** US-015, US-016, US-017, US-018, US-019, US-020, US-021, US-022, US-023.

**Estimación:** 6-7 horas (el roadmap dice 5-6 h; la diferencia se justifica por la migración Alembic + los 4 endpoints M2M dedicados + los tests de los 4 filtros combinados, que son más densos que cualquier suite anterior).

**Out-of-scope explícito (registrado para cerrar ambigüedad con el integrador):**

- **`es_principal` en `product_categories`**: el ERD textual §3.2 lo lista pero ni la migración inicial ni US-016 ni §5.2 lo exigen. Se difiere indefinidamente — si alguna vez se necesita, será un mini-change propio.
- **Image upload real (S3/local storage)**: el campo `imagen_url` recibe una URL string. La spec dice "URL o upload" para v1; usamos URL.
- **Snapshot de precio/nombre al crear pedido**: patrón documentado pero NO activado acá. Es responsabilidad de `order-creation-backend` (#13). El producto sólo expone los campos que el snapshot leerá.
- **Optimistic locking de stock (`SELECT FOR UPDATE`)**: las race conditions se aceptan para v1 mono-usuario académico. El `PATCH /stock` usa `UPDATE WHERE` atómico contra una sola fila, suficiente para el alcance.
- **Refactor de `UnitOfWork` a context manager**: deuda técnica D6 idéntica a la de `categories-backend` e `ingredients-backend`. NO se refactoriza acá.
- **Frontend del catálogo**: pertenece al Sprint 7 (`products-frontend-catalog` #21).
- **Param admin `incluir_eliminados` (RN-CA10)**: no se implementó en categories ni ingredients tampoco. Se difiere a un change futuro de vista admin.

**Anticipaciones intencionales (deuda anotada):**

- **RBAC `require_role("ADMIN", "STOCK")` en TODAS las mutations**: §5.2 indica sólo ADMIN para crear/editar/eliminar producto. Mantenemos la consistencia con `categories-backend` e `ingredients-backend` (que ya usan ADMIN+STOCK) y anticipamos US-064 (`admin-catalog-permissions` #19) que define la matriz final con ambos roles. Si US-064 cambia (improbable), tocaríamos este módulo.
