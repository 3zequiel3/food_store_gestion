## Context

### Estado actual del proyecto

- El modelo `Ingrediente` ya existe en `backend/features/catalog/models.py` (líneas 137-151) con dos columnas de dominio: `nombre VARCHAR(255) UNIQUE NOT NULL` y `es_alergeno BOOLEAN NOT NULL DEFAULT false`. Hereda de `BaseModel` → trae `id`, `creado_en`, `actualizado_en`, `eliminado_en`.
- La tabla `ingredients` fue creada por la migración `20260428_0001_initial_schema.py` (líneas 285-308) con: `id BIGSERIAL`, `nombre VARCHAR(255) NOT NULL UNIQUE` (constraint `uq_ingredients_nombre`), `es_alergeno BOOLEAN NOT NULL DEFAULT false`, `creado_en/actualizado_en/eliminado_en TIMESTAMPTZ`.
- La tabla `product_ingredients` (líneas 376-406 de la misma migración) existe como pivote M:N con FK `ingredient_id` ON DELETE RESTRICT, `product_id` ON DELETE CASCADE. **No tiene la columna `es_removible` que menciona el ERD del Integrador** — gap identificado y explícitamente out-of-scope (ver Non-Goals).
- `BaseRepository[T]` (`backend/shared/repository.py`) ya provee `create/read/update/delete/list/count` con soft-delete genérico. Los bugs originales ya fueron corregidos en `fix-base-repository-soft-delete` y `fix-base-repository-immutable-fields` (ambos archivados el 2026-05-08).
- `UnitOfWork` (`backend/shared/unit_of_work.py`) NO es context manager — el lifecycle se maneja vía `Depends(get_uow)` en `backend/dependencies.py` (generator con commit/rollback/close).
- `require_role(*roles)` y `get_current_user` viven en `backend/features/auth/dependencies.py`, totalmente operativos.
- Los handlers RFC 7807 ya están registrados en `main.py` para `NotFoundError`, `ConflictError`, `BusinessRuleError`, `ValidationError`, `ForbiddenError`, `UnauthorizedError` y catch-all.
- El conftest de tests de integración ya overridea `get_uow` correctamente — los tests con SQLite in-memory funcionan.
- **Patrón canónico recién archivado**: `backend/features/categories/` tiene la estructura exacta a clonar (sin la lógica de jerarquía/CTE que NO aplica acá).

### Capabilities reusadas

- `auth/spec.md` — `require_role` factory, `get_current_user` dependency.
- `base-entities/spec.md` — `BaseModel` con `eliminado_en`, modelo `Ingrediente` completo.
- `error-handling/spec.md` — RFC 7807 mandato.
- `database-migrations/spec.md` — schema actual de `ingredients`.
- `categories/spec.md` — patrón de capability CRUD que se replica con adaptaciones.

### Stakeholders

- **ADMIN** y **STOCK** — escriben ingredientes (POST/PUT/DELETE). Anticipa el RBAC final que `admin-catalog-permissions` (#24) verificará.
- **CLIENT** y anónimo — leen el listado y el detalle (GET / y GET /{id} públicos).
- **products-backend (#11)** — bloqueado por este change. Necesita `GET /{id}` para validar que un ingrediente existe antes de asociarlo, y `GET /` para alimentar la UI de selección de ingredientes en el form de producto.

## Goals / Non-Goals

**Goals:**

- Habilitar las 5 operaciones CRUD planas (POST, GET list, GET by id, PUT, DELETE) exigidas por US-011 a US-014, más el `GET /{id}` por costo cero.
- Implementar paginación básica (`page`, `limit`) y filtro por `es_alergeno` en el listado, ambos requeridos textualmente por US-012.
- Cumplir la regla de oro de imports `Router → Service → UoW → Repository → Model` sin ninguna excepción.
- Adelantar el RBAC final (`require_role("ADMIN", "STOCK")`) en escrituras para no acumular deuda hacia `admin-catalog-permissions` (#24).
- Mantener el soft delete como única vía de borrado (RN-CA09).
- Reutilizar el constraint `uq_ingredients_nombre` de la DB como segunda línea de defensa, con check previo en service para mensaje de error claro.

**Non-Goals:**

- NO refactorizar `UnitOfWork` para hacerlo context manager — se documenta como deuda técnica idéntica a la de `categories` (D6) y se mantiene el patrón actual.
- NO incluir el query param `incluir_eliminados` (RN-CA10). No se implementó en categories tampoco. Diferido a un change de vista admin del catálogo.
- NO modificar el modelo `Ingrediente` ni la migración `20260428_0001`. La tabla está bien y el constraint UNIQUE en `nombre` ya existe.
- NO agregar el campo `ProductoIngrediente.es_removible` que aparece en el ERD del Integrador. Pertenece a `products-backend` (#11) cuando extienda la tabla pivote.
- NO implementar guards en el DELETE (a diferencia de categories) — la spec US-014 dice textualmente "se mantiene en productos existentes" y eso lo cumple el soft delete naturalmente. Bloquear el delete cuando hay productos asociados sería sobre-restringir.
- NO implementar caché HTTP en el endpoint de listado.
- NO crear endpoint `GET /productos/{id}/ingredientes` — pertenece a `products-backend` (#11).
- NO crear frontend de ingredientes — no está planificado en el roadmap actual.

## Decisions

### D1 — Ubicación del módulo: `backend/features/ingredients/`

Crear módulo propio en `backend/features/ingredients/` siguiendo el patrón de `categories/`, `auth/`, `users/`, `orders/` (feature-first). El modelo `Ingrediente` se importa desde `backend/features/catalog/models.py` (líneas 137-151). NO se crea un nuevo archivo `models.py` dentro del módulo.

**Alternativa descartada:** ampliar `backend/features/catalog/` agregando router/service/repository allí. Quedaría confuso porque `catalog/` mezcla múltiples entidades (Rol, FormaPago, EstadoPedido, Categoria, Ingrediente) y violaría el principio de un módulo = un dominio de negocio. Categories ya hizo el mismo movimiento.

**Por qué:** consistencia con el resto del backend, evita acoplar `ingredients` a `categories` o a `products`, deja `catalog/` como contenedor de tablas de referencia compartidas.

### D2 — Endpoints públicos para lectura (GET / y GET /{id})

`GET /api/v1/ingredientes` y `GET /api/v1/ingredientes/{id}` son **públicos** (sin `Depends(require_role)`). Mismo patrón que `categories.GET /api/v1/categorias`.

**Alternativa descartada:** restringir a STOCK. Las US-012 dicen "Como Gestor de Stock... para gestionar su asociación" pero no exigen autenticación. El Integrador §5.2 muestra `GET /productos/{id}/ingredientes` como Público. Mantener consistencia con categories.

**Por qué:** los ingredientes son metadata pública del catálogo (los clientes ven los nombres en la descripción del producto y los badges de alérgeno). No hay PII ni datos sensibles. Forzar auth es fricción innecesaria.

### D3 — Incluir `GET /{id}` aunque las US no lo piden

US-011..014 no piden explícitamente `GET /api/v1/ingredientes/{id}`. Aun así, lo incluimos por dos razones:

1. **Cero costo de implementación**: `BaseRepository.read(id)` ya hace todo el trabajo. El endpoint es 3 líneas en el router.
2. **Utilidad real para el siguiente change**: `products-backend` (#11) necesita validar que un `ingredient_id` existe antes de asociarlo a un producto. Sin `GET /{id}`, products-backend tendría que importar `IngredientRepository` directamente o reusar el listado paginado.

**Alternativa descartada:** omitirlo y forzar a products-backend a usar el repo directamente. Acopla módulos innecesariamente.

### D4 — DELETE sin guards de productos asociados

A diferencia de `categories.DELETE` (que bloquea si hay productos activos), `DELETE /api/v1/ingredientes/{id}` **no chequea** la tabla `product_ingredients`. Solo hace soft delete vía `BaseRepository.delete()`.

**Alternativa descartada:** clonar el guard de categories. Implementaría un `has_active_products` análogo y lanzaría `BusinessRuleError` si hay productos activos asociados. Es más restrictivo que lo que pide la spec.

**Por qué:** US-014 dice textualmente "se mantiene en productos existentes pero deja de aparecer para nuevas asociaciones". El soft delete cumple esto exactamente:
- El `BaseRepository.list_all()` filtra `eliminado_en IS NULL` → no aparece en futuras búsquedas para asociar.
- La fila sigue en la tabla → los registros de `product_ingredients` que la referencian no se rompen (`ON DELETE RESTRICT` solo aplica a hard delete, que nunca ocurre).
- El ingrediente sigue siendo visible en los productos donde ya estaba asociado (si el frontend lee `Producto.ingredientes` con un join, va a aparecer).

### D5 — RBAC: `require_role("ADMIN", "STOCK")` desde este change

El RBAC final por la matriz de US-064 dice que ADMIN y STOCK pueden gestionar el catálogo. Aplicarlo desde aquí evita que `admin-catalog-permissions` (#24) tenga que hacer cambios destructivos en ingredients. Mismo razonamiento y trade-off que en `categories-backend` D7.

**Tradeoff aceptado:** si más adelante US-064 cambia (improbable — ya está en spec final), habría que tocar este módulo. El riesgo es bajo y el beneficio (cero deuda) es alto.

### D6 — UoW: usar el patrón actual `Depends(get_uow)` (deuda técnica reconocida)

Decisión idéntica a `categories-backend` D6. El código actual usa el generator `get_uow()` en `backend/dependencies.py`:

```python
def get_uow() -> Generator[UnitOfWork, None, None]:
    session = get_session_factory()()
    uow = UnitOfWork(session)
    try:
        yield uow
    except Exception:
        uow.rollback()
        raise
    finally:
        uow.close()
```

La spec del integrador (`docs/Integrador.txt §7.1`) muestra ejemplos con `with UnitOfWork() as uow:` (context manager). **No son equivalentes textuales pero sí semánticos:**

- Ambos garantizan rollback en excepción.
- Ambos garantizan close al final.
- El `commit()` lo hace el router explícitamente (no el `__exit__`/finally) — esto coincide en los dos patrones.

**Decisión:** mantener `Depends(get_uow)` y registrar la diferencia léxica como deuda técnica abierta. Refactorizar `UnitOfWork` para que también funcione como context manager es out-of-scope (afectaría todos los módulos existentes y cualquier change futuro debería usar el nuevo API). El refactor irá en un mini-change futuro `refactor-uow-to-context-manager` cuando el usuario lo decida.

**Patrón concreto en el router** (clonado de `categories/router.py`):

```python
@router.post("/", status_code=201, response_model=IngredienteRead)
async def crear_ingrediente(
    payload: IngredienteCreate,
    uow: UnitOfWork = Depends(get_uow),
    _user=Depends(require_role("ADMIN", "STOCK")),
) -> IngredienteRead:
    service = IngredientService(uow)
    ing = service.create(payload)
    uow.commit()  # service does NOT commit — router decides the boundary
    return IngredienteRead.model_validate(ing)
```

> **Nota:** el commit del router (no del service) es el patrón explícito de la spec. El service queda agnóstico del lifecycle de la transacción.

### D7 — Schemas Pydantic v2: 4 schemas + `model_dump(exclude_unset=True)` en update

```python
class IngredienteCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    es_alergeno: bool = False  # default explícito; columna NOT NULL con default false en DB

class IngredienteUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=255)
    es_alergeno: bool | None = None
    # NOTA: el service usa model_dump(exclude_unset=True) para distinguir
    # "no enviado" de "enviado explícitamente". Esto importa especialmente
    # para es_alergeno: si el cliente solo envía {"nombre": "X"}, NO queremos
    # que es_alergeno se reinicie a False.

class IngredienteRead(BaseModel):
    id: int
    nombre: str
    es_alergeno: bool
    creado_en: datetime
    actualizado_en: datetime
    model_config = {"from_attributes": True}

class PaginatedIngredientes(BaseModel):
    items: list[IngredienteRead]
    total: int
    page: int
    limit: int
```

**Por qué `model_dump(exclude_unset=True)` en update:** Pydantic v2 trata `es_alergeno: None` o `False` como un valor explícito si está en el modelo. Si el cliente envía `{"nombre": "Tomate Cherry"}` sin `es_alergeno`, el dump por defecto incluiría `es_alergeno: None`, lo que en `BaseRepository.update(**data)` setearía la columna a `NULL` o (con coerción) a `False`, sobreescribiendo silenciosamente el valor anterior. Con `exclude_unset=True`, la key directamente no está en el dict y la fila conserva su valor.

**Por qué `max_length=255`:** la columna en la migración es `VARCHAR(255)` (línea 291). El Integrador tabla ERD dice `VARCHAR(100)` pero la migración es la implementación real — no creamos una migración nueva para corregir esto.

**Por qué un schema `PaginatedIngredientes` separado:** US-012 exige paginación. El service devuelve `(items, total)` y el router empaqueta en este wrapper. Permite a la UI mostrar "página 2 de 7".

### D8 — Paginación y filtro: `page` + `limit` + `es_alergeno` como query params

`GET /api/v1/ingredientes?page=1&limit=20&es_alergeno=true`

- `page: int` ≥ 1, default 1.
- `limit: int` entre 1 y 100, default 20.
- `es_alergeno: bool | None`, default None (sin filtro).
- El repositorio convierte `page` a `skip = (page - 1) * limit` internamente.

**Alternativa descartada:** usar `skip` + `limit` directamente como en muchas APIs públicas (DRF, FastAPI tutorial). Es válido pero menos amigable para frontends que paginan con números de página.

**Implementación en repo:**

```python
def list_paginated(
    self,
    *,
    skip: int,
    limit: int,
    es_alergeno: bool | None = None,
) -> tuple[list[Ingrediente], int]:
    """Return (items, total) for paginated list, optionally filtered by es_alergeno."""
    base = self._get_base_query()  # ya filtra eliminado_en IS NULL
    if es_alergeno is not None:
        base = base.where(Ingrediente.es_alergeno == es_alergeno)

    # Total count (separate query)
    count_query = select(func.count()).select_from(base.subquery())
    total = self.session.execute(count_query).scalar() or 0

    # Paginated items
    items_query = base.order_by(Ingrediente.nombre).offset(skip).limit(limit)
    items = self.session.execute(items_query).scalars().all()
    return list(items), total
```

> **Nota:** la query del count usa `select(func.count()).select_from(base.subquery())` para reusar exactamente los filtros del listado. Si en el futuro se agregan más filtros, se mantienen consistentes entre items y total automáticamente.

### D9 — Manejo de errores

| Excepción | Cuándo | Status RFC 7807 |
|-----------|--------|----------------|
| `NotFoundError` | `repo.read(id)` retorna None (ya soft-deleted o nunca existió) | 404 |
| `ConflictError` | Nombre duplicado (chequeo previo en service y/o `IntegrityError` del UNIQUE) | 409 |
| `BusinessRuleError` | Nombre vacío después de strip (defensa adicional a `min_length=1`) | 422 |
| `ValidationError` | Pydantic atrapa antes en el router (longitud, tipos) | 422 |
| `ForbiddenError` | RBAC falla en `require_role` | 403 |
| `UnauthorizedError` | Sin token o token inválido | 401 |

Todos los handlers ya están registrados en `main.py` — no hay que agregar nada nuevo.

**Sobre el `IntegrityError` del UNIQUE:** el constraint `uq_ingredients_nombre` lanza `IntegrityError` si una carrera permite que dos POST simultáneos pasen el check `find_by_nombre`. El handler global de `main.py` actualmente devuelve 500 para `IntegrityError` no capturado. **Decisión:** confiar en el chequeo previo en service como primera línea (igual que categories). Si más adelante aparece un test concurrent que demuestre el problema, se agrega un handler específico. Riesgo bajo en proyecto académico mono-usuario.

### D10 — `BaseRepository` heredado sin overrides defensivos

Los bugs originales de `BaseRepository` ya fueron corregidos a nivel raíz:

- `fix-base-repository-soft-delete` (archivado 2026-05-08) — `_has_deleted_at` usa `eliminado_en` correctamente.
- `fix-base-repository-immutable-fields` (archivado 2026-05-08) — `update()` protege `creado_en`.

`IngredientRepository` hereda `_get_base_query()`, `delete()`, `update()` sin necesidad de sobrescribir nada. La regla: **no agregar overrides defensivos**.

### D11 — Tests de integración: clonar `test_categories.py` con adaptaciones

El conftest ya overridea `get_uow` correctamente (post `fix-test-setup-uow-override`), por lo que los tests de integración corren con SQLite in-memory. **Atención al patrón `literal()` vs `func.literal()`** — categories tuvo un bug donde `func.literal(0)` rompía en SQLite (sección 10 de `categories-backend/tasks.md`). Ingredients NO usa CTE, por lo que no debería necesitar `literal`, pero si en algún punto se agrega, importarlo directamente desde `sqlalchemy` (`from sqlalchemy import literal`), NO usar `func.literal(...)`.

**Tests sugeridos** (adaptados de `test_categories.py`):

- Happy path: `test_create_as_admin`, `test_create_as_stock`, `test_get_by_id`, `test_list_default_pagination`, `test_update_nombre_only`, `test_update_es_alergeno_only`, `test_update_both_fields`, `test_delete_soft`.
- RBAC: `test_create_unauthenticated_returns_401`, `test_create_as_client_returns_403`, `test_put_as_client_returns_403`, `test_delete_as_client_returns_403`, `test_get_list_is_public`, `test_get_by_id_is_public`.
- Validación: `test_create_empty_nombre_returns_422`, `test_create_nombre_too_long_returns_422` (256 chars), `test_create_duplicate_name_returns_409`, `test_update_to_existing_name_returns_409`.
- Filtros y paginación: `test_list_filter_es_alergeno_true`, `test_list_filter_es_alergeno_false`, `test_list_pagination_respects_limit`, `test_list_pagination_page_2`, `test_list_default_page_and_limit`.
- 404s: `test_get_by_id_not_found`, `test_update_not_found`, `test_delete_not_found`, `test_get_by_id_soft_deleted_returns_404`.
- Soft delete: `test_delete_does_not_hard_delete` (verificar fila sigue en tabla con `eliminado_en` set), `test_delete_then_get_returns_404`, `test_delete_then_create_same_name_succeeds_or_409` (decisión: soft-deleted bloquea o no? Ver scenario abajo).
- Routing: `test_endpoint_uses_v1_prefix_and_spanish_path` (verificar que `/api/v1/ingredients` y `/api/ingredientes` devuelven 404).

> **Decisión sobre nombre soft-deleted:** el constraint UNIQUE de DB es sobre `nombre` SIN filtrar por `eliminado_en`. Eso significa que si se soft-deletea un ingrediente "Tomate" y se intenta crear otro "Tomate", la DB lanza IntegrityError. **Esto es diferente de categories**, que filtra por `eliminado_en` en `find_by_nombre_y_padre`. Hay dos opciones:
>
> 1. Mantener el constraint DB tal cual y aceptar que el nombre queda "reservado" hasta que se haga hard delete (que nunca ocurre). El usuario tendría que renombrar el ingrediente borrado o usar otro nombre.
> 2. Filtrar `eliminado_en IS NULL` en el check de service y capturar el `IntegrityError` con un handler que devuelva 409 con un mensaje claro "Existe un ingrediente eliminado con ese nombre — restaurelo o use otro nombre".
>
> **Decisión:** opción 1 (más simple, alineada al constraint DB existente). El service hace `find_by_nombre` SIN filtrar por `eliminado_en`, devuelve `ConflictError` si encuentra cualquier match (deleted o no). Esto evita la necesidad de capturar `IntegrityError` y simplifica el flujo. Documentar en spec que el nombre queda reservado tras el soft delete.

## Risks / Trade-offs

- **[Riesgo] Constraint UNIQUE en DB no filtra por `eliminado_en`.** → Mitigación: `find_by_nombre` en repo NO filtra por soft-delete (busca en toda la tabla), service devuelve 409 si encuentra cualquier match. El nombre queda reservado tras un soft delete. Documentado en spec scenario.
- **[Riesgo] Race condition en POST simultáneo con mismo nombre.** → Mitigación aceptada como teoría: el `find_by_nombre` chequea antes, el constraint UNIQUE de DB es la red de seguridad. Si dos POST corren simultáneamente y ambos pasan el check, el segundo INSERT falla con `IntegrityError` y el handler global devuelve 500. Riesgo bajo en proyecto académico mono-usuario; si se materializa, agregar `try/except IntegrityError` en service.
- **[Riesgo] `model_dump()` por defecto incluye `es_alergeno: False` en updates parciales.** → Mitigación: usar `model_dump(exclude_unset=True)` y testear explícitamente con un test que envíe solo `{"nombre": "X"}` y verifique que `es_alergeno` no cambió.
- **[Riesgo] Performance de `total` count en listas grandes.** → Mitigación aceptada: el catálogo de un Food Store tiene 50-200 ingredientes típicamente. Si crece a miles, considerar cursor-based pagination o caché del count en un change posterior.
- **[Trade-off] Anticipar US-064 con `require_role("ADMIN", "STOCK")` aquí.** → Si la matriz cambia, retrabajamos. Probabilidad baja (spec final).
- **[Trade-off] No bloquear DELETE con productos asociados.** → US-014 no lo exige y el soft delete cumple la regla "se mantiene en productos existentes". Si más adelante se descubre un caso de borrado fantasma (ingrediente desaparece de pedidos viejos), hay que revisar el join en `Producto.ingredientes`.
- **[Trade-off] No incluir `incluir_eliminados` (RN-CA10).** → Diferido a un change de vista admin del catálogo. La rúbrica no lo exige para US-011/012/013/014.
- **[Trade-off] Incluir `GET /{id}` aunque las US no lo piden.** → Cuesta 3 líneas y desbloquea `products-backend`. Tradeoff aceptable.

## Migration Plan

No hay migración Alembic nueva. La tabla `ingredients` ya está poblada por la migración inicial.

**Despliegue:**

1. Mergear el módulo `backend/features/ingredients/`.
2. El registro del router en `main.py` activa los endpoints inmediatamente.
3. No hay datos a migrar — la tabla existe y está vacía o con seed.

**Rollback:**

- Revertir el commit del módulo + las dos líneas en `main.py` (import + include_router).
- El estado de DB no cambia (no se agregaron columnas ni constraints).

## Open Questions

Ninguna. Las decisiones D1-D11 están cerradas.

> **Deuda técnica reconocida y registrada:**
> 1. `UnitOfWork` no es context manager (D6). Compartida con todos los módulos. Refactor diferido a `refactor-uow-to-context-manager`.
> 2. `incluir_eliminados` (RN-CA10) diferido a vista admin del catálogo.
> 3. Constraint UNIQUE de DB no filtra por `eliminado_en` — nombre queda reservado tras soft delete (D9 / Risks).
> 4. Campo `ProductoIngrediente.es_removible` del ERD del Integrador NO está implementado — pertenece a `products-backend` (#11).
