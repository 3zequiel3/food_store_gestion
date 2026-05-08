## Context

### Estado actual del proyecto

- El modelo `Categoria` ya existe en `backend/features/catalog/models.py` (líneas 98-130) con relaciones self-referenciales `padre`/`hijos` configuradas correctamente (`remote_side="Categoria.id"`, `foreign_keys=[padre_id]`).
- La tabla `categories` fue creada por la migración `20260428_0001_initial_schema.py` con: `id BIGSERIAL`, `nombre VARCHAR(255) NOT NULL`, `padre_id INTEGER NULL FK→categories.id ON DELETE SET NULL`, `creado_en/actualizado_en/eliminado_en TIMESTAMPTZ`.
- No hay `UNIQUE(nombre, padre_id)` ni índice sobre `nombre` en la tabla — fue una decisión consciente (ver D3).
- `BaseRepository[T]` (`backend/shared/repository.py`) ya provee `create/read/update/delete/list/count` con soft-delete genérico.
- `UnitOfWork` (`backend/shared/unit_of_work.py`) NO es un context manager — el lifecycle se maneja vía `Depends(get_uow)` en `backend/dependencies.py` (generator con commit/rollback/close en `try/except/finally`).
- `require_role(*roles)` y `get_current_user` viven en `backend/features/auth/dependencies.py`, totalmente operativos.
- Los handlers RFC 7807 ya están registrados en `main.py` para `NotFoundError`, `ConflictError`, `BusinessRuleError`, `ValidationError`, `ForbiddenError`, `UnauthorizedError` y catch-all.

### Capabilities reusadas

- `auth/spec.md` — `require_role` factory, `get_current_user` dependency.
- `base-entities/spec.md` — `BaseModel` con `eliminado_en`, modelo `Categoria` con árbol auto-referencial.
- `error-handling/spec.md` — RFC 7807 mandato.
- `database-migrations/spec.md` — schema actual de `categories`.

### Stakeholders

- **ADMIN** y **STOCK** — escriben categorías (POST/PUT/DELETE). Anticipa el RBAC final que `admin-catalog-permissions` (#24) verificará.
- **CLIENT** y anónimo — leen el árbol (GET público para US-022).
- **products-backend (#11)** — lo bloqueará si este change no exporta `Categoria` correctamente para asociaciones M:N vía `ProductoCategoria`.

## Goals / Non-Goals

**Goals:**
- Habilitar las 4 operaciones CRUD jerárquicas exigidas por US-007 a US-010.
- Implementar la primera CTE recursiva del proyecto, siguiendo el patrón que la rúbrica espera ver textualmente para el árbol y para la validación de ciclos.
- Cumplir la regla de oro de imports `Router → Service → UoW → Repository → Model` sin ninguna excepción.
- Adelantar el RBAC final (`require_role("ADMIN", "STOCK")`) en escrituras para no acumular deuda hacia `admin-catalog-permissions` (#24).
- Mantener el soft delete como única vía de borrado (RN-CA09).

**Non-Goals:**
- NO refactorizar `UnitOfWork` para hacerlo context manager — se documenta como deuda técnica y se mantiene el patrón actual (`Depends(get_uow)`).
- NO incluir el query param `incluir_eliminados` (RN-CA10) en este change — se difiere a un change futuro sobre vista admin de catálogo. La rúbrica no lo exige para US-007/008/009/010.
- NO implementar `GET /api/v1/categorias/{id}` — la spec del integrador no lo pide y no agrega valor sobre `GET /` (que ya devuelve todos los nodos en el árbol).
- NO modificar el modelo `Categoria` ni la migración `20260428_0001`. La tabla está bien.
- NO implementar caché en el endpoint de listado (US-008 dice "cachear si el volumen lo justifica" — diferido).
- NO crear endpoints CRUD de productos ni ingredientes — son changes separados (#10 ingredients-backend, #11 products-backend).

## Decisions

### D1 — Ubicación del módulo: `backend/features/categories/`

Crear módulo propio en `backend/features/categories/` siguiendo el patrón de `auth/`, `users/`, `orders/` (feature-first). El modelo `Categoria` se importa desde `backend/features/catalog/models.py`.

**Alternativa descartada:** ampliar `backend/features/catalog/` agregando router/service/repository. Quedaría confuso porque `catalog` mezcla múltiples entidades (Rol, FormaPago, EstadoPedido, Categoria, Ingrediente) y violaría el principio de un módulo = un dominio de negocio.

**Por qué:** consistencia con el resto del backend, evita acoplar `categories` a `ingredients`, deja `catalog/` como contenedor de tablas de referencia compartidas.

### D2 — Árbol vía CTE recursiva en repository (no nesting Python)

El método `CategoryRepository.get_tree_cte()` ejecuta una `WITH RECURSIVE` de PostgreSQL devolviendo filas planas `(id, nombre, padre_id, depth, path)`. El service (o un helper en `schemas.py`) nest-ifica el resultado en un solo paso O(n) construyendo un mapa `parent_id → list[children]`.

**Alternativa descartada:** cargar todo en memoria con `repo.list()` y nestear en Python sin CTE. Funcional pero la rúbrica espera evidencia textual de CTE recursiva (US-007/008/009 lo mencionan en notas técnicas).

**Por qué:** es la primera CTE del proyecto y la cátedra la evalúa explícitamente. Además, la CTE devuelve `depth` y `path` que serán útiles en el frontend para indentación visual.

#### Shape exacto de la CTE de árbol

```sql
WITH RECURSIVE category_tree AS (
    -- ANCHOR: root nodes (no parent), only non-deleted
    SELECT
        id,
        nombre,
        padre_id,
        0 AS depth,
        ARRAY[id] AS path
    FROM categories
    WHERE padre_id IS NULL
      AND eliminado_en IS NULL

    UNION ALL

    -- RECURSIVE: children join on parent.id = child.padre_id
    SELECT
        c.id,
        c.nombre,
        c.padre_id,
        ct.depth + 1 AS depth,
        ct.path || c.id AS path
    FROM categories c
    INNER JOIN category_tree ct ON c.padre_id = ct.id
    WHERE c.eliminado_en IS NULL
)
SELECT id, nombre, padre_id, depth, path
FROM category_tree
ORDER BY path;
```

**Equivalente SQLAlchemy 2.0 (Core, lo que va en el repo):**

```python
from sqlalchemy import select, literal, ARRAY, Integer
from backend.features.catalog.models import Categoria

def get_tree_cte(self) -> list[CategoryFlatRow]:
    cat = Categoria.__table__

    # Anchor: roots
    anchor = (
        select(
            cat.c.id,
            cat.c.nombre,
            cat.c.padre_id,
            literal(0).label("depth"),
            func.array(cat.c.id).label("path"),  # array_agg-style; see note below
        )
        .where(cat.c.padre_id.is_(None))
        .where(cat.c.eliminado_en.is_(None))
        .cte("category_tree", recursive=True)
    )

    # Recursive part
    parent = anchor.alias("ct")
    child = cat.alias("c")
    recursive = (
        select(
            child.c.id,
            child.c.nombre,
            child.c.padre_id,
            (parent.c.depth + 1).label("depth"),
            (parent.c.path + array([child.c.id])).label("path"),
        )
        .where(child.c.padre_id == parent.c.id)
        .where(child.c.eliminado_en.is_(None))
    )

    cte = anchor.union_all(recursive)

    rows = self.session.execute(
        select(cte.c.id, cte.c.nombre, cte.c.padre_id, cte.c.depth, cte.c.path)
        .order_by(cte.c.path)
    ).all()

    return [CategoryFlatRow(*r) for r in rows]
```

> **Nota implementación:** la construcción del array PostgreSQL en SQLAlchemy puede requerir `sqlalchemy.dialects.postgresql.array` y `cast(ARRAY(Integer))` para que `path` se materialice como `int[]`. Si se complica, una alternativa es prescindir de `path` y devolver solo `(id, nombre, padre_id, depth)` — el orden por `depth` + ordenamiento alfabético por nombre dentro del mismo nivel también funciona para nesting determinístico. La task de implementación valida con un test de integración que el árbol nesteado sea correcto.

### D3 — Unicidad de nombre por nivel: validación en service, NO UNIQUE constraint

La validación `(nombre, padre_id)` único entre hermanos no-eliminados se hace en `CategoryService` antes de crear o actualizar.

**Alternativa descartada:** `UNIQUE(nombre, padre_id)` a nivel DB. Falla porque PostgreSQL trata `NULL` como distinto en UNIQUE — permitiría múltiples raíces con el mismo `nombre`, violando US-007.

**Otra alternativa descartada:** índice parcial `CREATE UNIQUE INDEX ... ON categories(nombre, COALESCE(padre_id, 0)) WHERE eliminado_en IS NULL`. Funcionaría pero requiere migración nueva, complica el rollback, y la rúbrica no lo exige.

**Por qué service:** cero migración nueva, mensaje de error claro al usuario, control total sobre el caso "el conflictivo está soft-deleted" (que se permite — ver scenario en spec).

**Implementación:** método `repo.find_by_nombre_y_padre(nombre: str, padre_id: int | None) -> Categoria | None` que filtra `nombre = ? AND eliminado_en IS NULL AND (padre_id = ? OR (padre_id IS NULL AND ? IS NULL))`. El service llama y, si retorna no-None y `result.id != self_id_being_updated`, levanta `ConflictError`.

### D4 — Validación de ciclos vía CTE recursiva en repository, llamada desde service

El método `CategoryRepository.would_create_cycle(categoria_id: int, new_padre_id: int | None) -> bool` corre una CTE que parte de `new_padre_id` y sube por `padre_id` hasta llegar a `NULL` o encontrar `categoria_id`. Si lo encuentra → ciclo.

**Caso especial:** si `new_padre_id is None`, retorna `False` directamente (root-promotion nunca crea ciclos). Si `new_padre_id == categoria_id`, retorna `True` (auto-padre — ya cubre el primer caso de US-009).

#### Shape exacto de la CTE de ciclo

```sql
WITH RECURSIVE ancestors AS (
    -- Start from the proposed new parent
    SELECT id, padre_id
    FROM categories
    WHERE id = :new_padre_id
      AND eliminado_en IS NULL

    UNION ALL

    -- Walk up the chain
    SELECT c.id, c.padre_id
    FROM categories c
    INNER JOIN ancestors a ON c.id = a.padre_id
    WHERE c.eliminado_en IS NULL
)
SELECT EXISTS (
    SELECT 1 FROM ancestors WHERE id = :categoria_id
) AS has_cycle;
```

**Equivalente SQLAlchemy:**

```python
def would_create_cycle(self, categoria_id: int, new_padre_id: int | None) -> bool:
    if new_padre_id is None:
        return False
    if new_padre_id == categoria_id:
        return True

    cat = Categoria.__table__
    anchor = (
        select(cat.c.id, cat.c.padre_id)
        .where(cat.c.id == new_padre_id)
        .where(cat.c.eliminado_en.is_(None))
        .cte("ancestors", recursive=True)
    )
    parent = anchor.alias("a")
    child = cat.alias("c")
    recursive = (
        select(child.c.id, child.c.padre_id)
        .where(child.c.id == parent.c.padre_id)
        .where(child.c.eliminado_en.is_(None))
    )
    cte = anchor.union_all(recursive)

    result = self.session.execute(
        select(func.count()).select_from(cte).where(cte.c.id == categoria_id)
    ).scalar()
    return result > 0
```

**El service llama así (en `update`):**

```python
if "padre_id" in payload and payload["padre_id"] != current.padre_id:
    if uow.categorias.would_create_cycle(categoria_id, payload["padre_id"]):
        raise BusinessRuleError(
            "El cambio de padre crearía un ciclo en la jerarquía"
        )
```

### D5 — Delete con subcategorías o productos activos: rechazar (no cascade)

El service llama dos guards antes de hacer soft delete:

1. `repo.has_active_children(id)` — `SELECT 1 FROM categories WHERE padre_id = :id AND eliminado_en IS NULL LIMIT 1`.
2. `repo.has_active_products(id)` — `SELECT 1 FROM product_categories pc JOIN products p ON p.id = pc.product_id WHERE pc.category_id = :id AND p.eliminado_en IS NULL LIMIT 1`.

Si cualquiera retorna `True`, levanta `BusinessRuleError` con mensaje específico. US-010 acceptance #2 y #3 lo dicen textual.

**Alternativa descartada:** cascada (soft-delete de hijos al borrar padre). US-010 #3 dice explícitamente "subcategorías deben reasignarse o eliminarse previamente" → implica rechazo, no cascada.

**Implementación del check de productos:** la consulta toca dos tablas (`product_categories` y `products`). Como el `CategoryRepository` solo trabaja con `Categoria`, el método `has_active_products` ejecuta SQL directo vía `self.session.execute(text(...))` o un `select` del Core. NO se inyecta `ProductRepository` en el UoW para este caso — el query es muy específico de la regla de borrado de categorías. Si más adelante `ProductRepository` necesita un método análogo, se refactoriza.

### D6 — UoW: usar el patrón actual `Depends(get_uow)` (deuda técnica reconocida)

El código actual usa el generator `get_uow()` en `backend/dependencies.py`:

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

La spec del integrador (`docs/Integrador.txt §7`) muestra ejemplos con `with UnitOfWork() as uow:` (context manager). **No son equivalentes textuales pero sí semánticos:**
- Ambos garantizan rollback en excepción.
- Ambos garantizan close al final.
- El `commit()` lo hace el service explícitamente (no lo hace el `__exit__`/finally) — esto coincide en los dos patrones.

**Decisión:** mantener `Depends(get_uow)` y registrar la diferencia léxica como deuda técnica abierta. Refactorizar `UnitOfWork` para que también funcione como context manager es out-of-scope (afectaría `auth-backend`, `users-backend`, etc., y cualquier change futuro debería usar el nuevo API). El propio `apply` documentará en una nota dentro del módulo `categories/` que el patrón actual cumple la semántica esperada.

**Patrón concreto en el router:**

```python
@router.post("/", status_code=201, response_model=CategoriaRead)
async def crear_categoria(
    payload: CategoriaCreate,
    uow: UnitOfWork = Depends(get_uow),
    user: Usuario = Depends(require_role("ADMIN", "STOCK")),
) -> CategoriaRead:
    service = CategoryService(uow)
    cat = service.create(payload)
    uow.commit()  # service does NOT commit — router decides the boundary
    return CategoriaRead.model_validate(cat)
```

> **Nota:** el commit del router (no del service) es el patrón explícito de la spec. El service queda agnóstico del lifecycle de la transacción y, en tests unitarios, recibe un UoW mockeado o real sin commit.

### D7 — RBAC: `require_role("ADMIN", "STOCK")` desde este change (anticipa US-064)

El RBAC final por la matriz de US-064 dice que ADMIN y STOCK pueden gestionar el catálogo. Aplicarlo desde aquí evita que `admin-catalog-permissions` (#24) tenga que hacer cambios destructivos en categories.

**Tradeoff aceptado:** si más adelante US-064 cambia (improbable — ya está en spec final), habría que tocar este módulo. El riesgo es bajo y el beneficio (cero deuda) es alto.

### D8 — Schemas Pydantic v2: 4 schemas separados

```python
class CategoriaCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    padre_id: int | None = None

class CategoriaUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    padre_id: int | None = None
    # NOTA: para distinguir "no enviado" de "enviado como null" usamos
    # exclude_unset al volcar a dict en el service (model_dump(exclude_unset=True)).

class CategoriaRead(BaseModel):
    id: int
    nombre: str
    padre_id: int | None
    creado_en: datetime
    actualizado_en: datetime
    model_config = {"from_attributes": True}

class CategoriaTreeNode(BaseModel):
    id: int
    nombre: str
    padre_id: int | None
    subcategorias: list["CategoriaTreeNode"] = Field(default_factory=list)
    model_config = {"from_attributes": True}

CategoriaTreeNode.model_rebuild()
```

**Por qué `model_dump(exclude_unset=True)` en update:** Pydantic v2 trata `padre_id: None` como un valor explícito. Si el cliente envía `{"nombre": "X"}` sin `padre_id`, NO queremos cambiar el padre. Si envía `{"nombre": "X", "padre_id": null}`, SÍ queremos promoverla a raíz. `exclude_unset=True` distingue los dos casos.

### D9 — Manejo de errores

| Excepción | Cuándo | Status RFC 7807 |
|-----------|--------|----------------|
| `NotFoundError` | `repo.read(id)` retorna None (incluye soft-deleted, que el filtro excluye) | 404 |
| `ConflictError` | Nombre duplicado en mismo nivel | 409 |
| `BusinessRuleError` | Auto-padre, ciclo, hijos activos al delete, productos activos al delete, padre inexistente al create | 422 |
| `ValidationError` | (No esperado — Pydantic atrapa antes en el router) | 422 |
| `ForbiddenError` | RBAC falla en `require_role` | 403 |
| `UnauthorizedError` | Sin token o token inválido | 401 |

Todos los handlers ya están registrados en `main.py` — no hay que agregar nada nuevo.

### D10 — `BaseRepository` ya provee soft-delete y protección de campos inmutables correctos

Los bugs originales de `BaseRepository` que motivaban mitigaciones locales en `CategoryRepository` fueron corregidos a nivel raíz en dos changes archivados el 2026-05-08: `fix-base-repository-soft-delete` (corrige `_has_deleted_at` para usar `eliminado_en`) y `fix-base-repository-immutable-fields` (protege `creado_en` en `update()`). El spec vivo `openspec/specs/base-entities/spec.md` ya declara ambos comportamientos como Requirements. `CategoryRepository` hereda `_get_base_query()` y `delete()` sin necesidad de sobrescritura.

## Risks / Trade-offs

- **[Riesgo] CTE recursiva primera del proyecto, sin referencias previas en código.** → Mitigación: incluir un test de integración con un árbol de 3+ niveles que valide `depth`, orden y ausencia de ciclos. Si la sintaxis SQLAlchemy de array-concatenation se complica, descartar `path` y conformarse con `(id, nombre, padre_id, depth)` ordenado por `depth`.
- **[Riesgo] `padre_id` en update con valor `None` vs "no enviado".** → Mitigación: usar `model_dump(exclude_unset=True)` y manejar la presencia de la key explícitamente en el service.
- **[Riesgo] Carrera de inserción duplicada (dos POST simultáneos con mismo `(nombre, padre_id)`).** → Mitigación aceptada como teoría: la transacción usa el nivel de aislamiento default (`READ COMMITTED`) y el chequeo `find_by_nombre_y_padre` puede ser bypasseado en concurrencia extrema. Riesgo bajo en un proyecto académico mono-usuario; si se vuelve real, agregar el índice parcial mencionado en D3.
- **[Riesgo] Performance del árbol con N grande.** → Mitigación aceptada: el catálogo de un Food Store tiene 10-50 categorías típicamente. Si crece a miles, agregar caché HTTP en `GET /` (US-008 lo menciona) en un change posterior.
- **[Trade-off] Anticipar US-064 con `require_role("ADMIN", "STOCK")` aquí.** → Si la matriz cambia, retrabajamos. Si no cambia (lo más probable), `admin-catalog-permissions` (#24) verifica y sigue.
- **[Trade-off] No incluir `incluir_eliminados` (RN-CA10).** → Diferido a un change de vista admin del catálogo. La rúbrica no lo exige para US-007/008/009/010.

## Migration Plan

No hay migración Alembic nueva. La tabla `categories` ya está poblada por la migración inicial.

**Despliegue:**
1. Mergear el módulo `backend/features/categories/`.
2. El registro del router en `main.py` activa los endpoints inmediatamente.
3. No hay datos a migrar — la tabla existe y está vacía o con seed.

**Rollback:**
- Revertir el commit del módulo + la línea del router en `main.py`.
- El estado de DB no cambia (no se agregaron columnas ni constraints).

## Open Questions

Ninguna. Las decisiones D1-D10 están cerradas.

> **Deuda técnica reconocida y registrada:**
> 1. `UnitOfWork` no es context manager (D6). Cumple semántica vía `get_uow()` generator.
> 2. Caché HTTP del árbol diferido.
> 3. `incluir_eliminados` (RN-CA10) diferido.
