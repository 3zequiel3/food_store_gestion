## Why

El catálogo del Food Store necesita gestión de ingredientes para componer productos y exhibir los flags de alérgenos exigidos por US-011 a US-014. Sin este módulo, `products-backend` (#11) no puede asociar ingredientes a productos vía la M:N `ProductoIngrediente` y la UI de catálogo no puede mostrar el badge de alérgeno requerido por la rúbrica. Es el segundo y último change del Sprint 2 (Catálogo Base), tras `categories-backend` recién archivado.

## What Changes

- Nuevo módulo `backend/features/ingredients/` con las 5 capas (router, service, repository, schemas, `__init__`) — el modelo `Ingrediente` se importa desde `backend/features/catalog/models.py` (líneas 137-151), NO se redefine.
- 5 endpoints REST bajo `/api/v1/ingredientes`:
  - `POST /` — crear ingrediente (auth: `require_role("ADMIN", "STOCK")`).
  - `GET /` — listar ingredientes paginados con filtro opcional `?es_alergeno=true|false` (público).
  - `GET /{id}` — obtener ingrediente por id (público) — incluido por costo cero (D3) y necesario para `products-backend`.
  - `PUT /{id}` — editar nombre y/o `es_alergeno` (auth: `require_role("ADMIN", "STOCK")`).
  - `DELETE /{id}` — soft delete sin guards (auth: `require_role("ADMIN", "STOCK")`).
- `IngredientRepository(BaseRepository[Ingrediente])` con dos métodos especializados: `find_by_nombre`, `list_paginated`.
- `IngredientService` que recibe `uow: UnitOfWork` y orquesta validación de unicidad por nombre y soft delete sin guards adicionales.
- Schemas Pydantic v2: `IngredienteCreate`, `IngredienteUpdate`, `IngredienteRead`, `PaginatedIngredientes` (response wrapper con `items`, `total`, `page`, `limit`).
- Wiring del router en `backend/main.py` con prefijo `/api/v1/ingredientes` y tag `ingredients`.
- Spec delta nueva: capability `ingredients` con requirements derivados de US-011 a US-014, RN-CA07 y RN-CA09.
- Tests de integración cubriendo CRUD completo, RBAC, filtro `es_alergeno`, paginación, unicidad de nombre, soft delete.

## Capabilities

### New Capabilities

- `ingredients`: CRUD plano de ingredientes con flag `es_alergeno`, paginación, filtro por alérgeno, soft delete y RBAC para escritura (ADMIN | STOCK). Cubre US-011, US-012, US-013, US-014, RN-CA07 (flag de alérgeno) y RN-CA09 (soft delete).

### Modified Capabilities

Ninguna. Las capabilities existentes (`auth`, `base-entities`, `error-handling`, `database-migrations`, `categories`) ya cubren los prerrequisitos sin cambios.

## Impact

**Code afectado:**
- Nuevos archivos: `backend/features/ingredients/{__init__.py, router.py, service.py, repository.py, schemas.py}`.
- Modificación de `backend/main.py`: agregar `from backend.features.ingredients.router import router as ingredients_router` (junto al import de `categories_router`, línea ~71) y `app.include_router(ingredients_router, prefix="/api/v1/ingredientes", tags=["ingredients"])` después de la línea 199.
- Tests nuevos: `backend/tests/integration/test_ingredients.py`.
- No se requiere migración Alembic — la tabla `ingredients` ya existe (migración `20260428_0001_8d61b8e48f6b_initial_schema.py` líneas 285-308).

**Dependencias resueltas:**
- `auth-backend` archivado (provee `require_role` y `get_current_user`).
- `auth-backend-stabilization` archivado (RFC 7807, exceptions tipadas).
- `database-migrations` archivado (tabla `ingredients` con `id`, `nombre VARCHAR(255) UNIQUE`, `es_alergeno BOOLEAN`, timestamps).
- `base-entities` archivado (`BaseModel` con `eliminado_en`, `Ingrediente` ORM completo).
- `categories-backend` archivado (provee el patrón exacto a clonar — `BaseRepository[T]` corregido, conftest con override de `get_uow`).
- `fix-base-repository-soft-delete` y `fix-base-repository-immutable-fields` archivados (heredamos `BaseRepository` sin overrides defensivos).
- `fix-test-setup-uow-override` archivado (los tests de integración corren con SQLite in-memory).

**Bloqueado por este change:**
- `products-backend` (#11) — necesita poder leer ingredientes individualmente (`GET /{id}`) y listarlos para asociarlos a productos vía `ProductoIngrediente`.
- `admin-catalog-permissions` (#24) — verificará el RBAC de ingredientes como ya cumplido.

**Historias cubiertas:** US-011, US-012, US-013, US-014.

**Estimación:** 1.5-2 horas (incluye tests). Es más simple que `categories-backend` (2.5-3.5 h) porque no hay CTE recursiva, no hay árbol, no hay cycle detection, no hay guards de borrado.

**Decisiones cerradas previo al propose** (registradas en `design.md`):
- Módulo en `backend/features/ingredients/` (D1).
- GET / y GET /{id} públicos (D2). GET /{id} incluido aunque las US no lo piden (D3).
- DELETE sin guards de productos asociados — el soft delete cumple US-014 textual (D4).
- RBAC `require_role("ADMIN", "STOCK")` desde este change, anticipando US-064 (D5).
- UoW: usar patrón actual `Depends(get_uow)` — deuda técnica reconocida idéntica a categories (D6).
- Schemas separados con `model_dump(exclude_unset=True)` en update para preservar `es_alergeno` cuando no se envía (D7).
- Paginación con `page` + `limit` (offset interno) y filtro `es_alergeno` opcional como query params (D8).

**Out-of-scope explícito:**
- Campo `ProductoIngrediente.es_removible` — el ERD del Integrador (§3.2) lo lista pero ni la migración ni el modelo actual lo tienen. Pertenece a `products-backend` (#11) cuando extienda la tabla pivote.
- Refactor de `UnitOfWork` a context manager — irá en un mini-change futuro `refactor-uow-to-context-manager` cuando el usuario lo decida.
- Frontend de ingredientes — no existe ni está planificado en el roadmap actual; los ingredientes solo aparecen en frontend dentro del producto (Sprint 3).
- `incluir_eliminados` admin param (RN-CA10) — no se implementó en categories tampoco; se difiere a un change de vista admin.
- Endpoint `GET /productos/{id}/ingredientes` — pertenece a `products-backend` (#11).
