## Why

El catálogo del Food Store gira alrededor de la entidad `Categoria` — sin CRUD jerárquico de categorías no se puede dar de alta productos (US-013) ni navegar el catálogo desde el frontend (US-022). Este change desbloquea el Sprint 2 (Catálogo Base) y es prerrequisito de `products-backend` (#11). El modelo ORM `Categoria` y la tabla `categories` ya existen (migración `20260428_0001`); falta el módulo feature (router/service/repository/schemas) y la lógica jerárquica con CTE recursiva — la primera del proyecto, mencionada explícitamente en la rúbrica como evidencia técnica esperada.

## What Changes

- Nuevo módulo `backend/features/categories/` con las 5 capas (router, service, repository, schemas, `__init__`) — el modelo `Categoria` se importa desde `backend/features/catalog/models.py`, NO se redefine.
- 4 endpoints REST bajo `/api/v1/categorias`:
  - `POST /` — crear categoría (auth: ADMIN o STOCK).
  - `GET /` — listar árbol completo anidado vía CTE recursiva (público).
  - `PUT /{id}` — editar nombre y/o `padre_id` con validación de ciclos vía CTE.
  - `DELETE /{id}` — soft delete con guards (no subcategorías activas, no productos activos asociados).
- `CategoryRepository(BaseRepository[Categoria])` con métodos especializados: `get_tree_cte`, `would_create_cycle`, `find_by_nombre_y_padre`, `has_active_children`, `has_active_products`.
- `CategoryService` que orquesta la lógica de negocio recibiendo `uow: UnitOfWork` (validación de unicidad por nivel, ciclos antes de persistir, guards de delete).
- Schemas Pydantic v2: `CategoriaCreate`, `CategoriaUpdate`, `CategoriaRead`, `CategoriaTreeNode` (recursivo con `subcategorias: list["CategoriaTreeNode"]`).
- Wiring del router en `backend/main.py` con prefijo `/api/v1/categorias` y tag `categories`.
- Spec delta nueva: capability `categories` con requirements derivados de US-007 a US-010 y RN-CA01 a RN-CA10.
- Tests de integración cubriendo happy path + edge cases (ciclo, auto-padre, delete con hijos, delete con productos, nombre duplicado en mismo nivel).

## Capabilities

### New Capabilities

- `categories`: CRUD jerárquico de categorías de catálogo con árbol anidado vía CTE recursiva, validación de ciclos, soft delete con guards, y RBAC para escritura (ADMIN | STOCK). Cubre US-007, US-008, US-009, US-010 y RN-CA01 a RN-CA10.

### Modified Capabilities

Ninguna. Las capabilities existentes (`auth`, `base-entities`, `error-handling`, `database-migrations`) ya cubren los prerrequisitos sin cambios.

## Impact

**Code afectado:**
- Nuevos archivos: `backend/features/categories/{__init__.py, router.py, service.py, repository.py, schemas.py}`.
- Modificación de `backend/main.py`: agregar `from backend.features.categories.router import router as categories_router` y `app.include_router(categories_router, prefix="/api/v1/categorias", tags=["categories"])`.
- Tests nuevos: `backend/tests/integration/test_categories.py`.
- No se requiere migración Alembic — la tabla `categories` ya existe y no cambia.

**Dependencias resueltas:**
- `auth-backend` archivado (provee `require_role` y `get_current_user`).
- `auth-backend-stabilization` archivado (RFC 7807, exceptions tipadas).
- `database-migrations` archivado (tabla `categories` con `id`, `nombre`, `padre_id`, timestamps).
- `base-entities` archivado (`BaseModel` con `eliminado_en`, `Categoria` ORM completo con relaciones `padre`/`hijos`).

**Bloqueado por este change:**
- `products-backend` (#11) — lo necesita para asociar productos a categorías vía `ProductoCategoria`.
- `admin-catalog-permissions` (#24) — verificará el RBAC de categorías como ya cumplido y replicará el patrón a productos/ingredientes.

**Historias cubiertas:** US-007, US-008, US-009, US-010.

**Estimación:** 2.5-3.5 horas (incluye tests).

**Decisiones cerradas previo al propose** (registradas en `design.md`):
- Módulo en `backend/features/categories/` (D1).
- Árbol vía CTE recursiva en repository, no nesting Python (D2).
- Unicidad de nombre por nivel: validación en service, NO UNIQUE constraint en DB (D3).
- Validación de ciclos: `repo.would_create_cycle(...)` con CTE, llamado desde service antes de persistir (D4).
- Delete con subcategorías o productos activos: rechazar (no cascade) (D5).
- UoW: usar patrón actual `Depends(get_uow)` — generator equivalente a `with UnitOfWork()`. Documentado como deuda técnica (D6).
- RBAC: `require_role("ADMIN", "STOCK")` desde este change, anticipando US-064.
- Endpoints: 4 (no se incluye `GET /{id}` — no lo pide la spec).
