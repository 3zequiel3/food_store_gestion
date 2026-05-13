## Context

El backend del catálogo (Sprint 3) ya está vivo, archivado y en uso: `Producto`, `Categoria`, `Ingrediente` con sus pivotes (`ProductoCategoria`, `ProductoIngrediente`) y un árbol de categorías autoreferencial con CTE recursivo para `GET /categorias`. La exploración de Sprint 7 (`sdd/products-frontend-catalog/explore`) reveló dos brechas reales contra la UX objetivo: filtros de categoría no recursivos y filtro de alérgenos solo booleano. Sumamos reglas de negocio nuevas (productos solo se asignan a categorías hoja) para evitar incoherencias jerárquicas tipo "cerveza en Bebidas" en lugar de "Bebidas → Alcohólicas".

El stack es FastAPI 0.115.6 + SQLAlchemy 2.0.41 + Pydantic 2.11.4, con PostgreSQL en runtime y SQLite en algunos tests (esto último impacta D1: las CTEs recursivas tienen sintaxis sutilmente distinta — ya hay precedente con `CategoryRepository.get_tree_cte()` que funciona en ambos). Todo el código respeta el UoW como context manager y la regla de oro de imports.

## Goals / Non-Goals

**Goals:**

- Filtros recursivos por categoría y granulares por alérgeno en `GET /productos`.
- Validación de hoja al asignar categorías a un producto (create + replace).
- Auto-`disponible=false` cuando un producto queda sin categoría hoja activa.
- Endpoint plano `GET /categorias?solo_hojas=true` para dropdowns de asignación.
- Guard que impide convertir una categoría hoja en interna si tiene productos activos.
- Cero migraciones de schema: toda la lógica se monta sobre tablas y columnas ya existentes.

**Non-Goals:**

- Admin frontend que consuma estos endpoints (Sprint 12).
- Subida de imágenes de productos.
- Filtros por rango de precio en `GET /productos` (sin param backend hoy; cae a Sprint 7 si se decide hacerlo client-side).
- Cascadeo automático de productos cuando una categoría pasa de hoja a interna (rechazado por D6).
- Reassignment masivo de productos entre categorías (UI/UX de Sprint 12).
- Cambios en el árbol recursivo `GET /categorias` sin params (sigue devolviendo el tree completo — ese es el que consume el filtro lateral estilo ML del frontend).

## Decisions

### D1: Filtro recursivo de `categoria_id` con CTE en repository

**Decisión**: Implementar la expansión recursiva en `ProductRepository.list_paginated_with_filters` usando una CTE recursiva SQL (no expansión Python-side via `CategoryService`).

**Patrón SQL** (PostgreSQL + SQLite compatible — usamos `union_all` como en `CategoryRepository.get_tree_cte()`):

```sql
WITH RECURSIVE category_subtree AS (
    SELECT id FROM categories WHERE id = :categoria_id AND eliminado_en IS NULL
    UNION ALL
    SELECT c.id FROM categories c
    INNER JOIN category_subtree cs ON c.padre_id = cs.id
    WHERE c.eliminado_en IS NULL
)
SELECT ... FROM products p
INNER JOIN product_categories pc ON pc.product_id = p.id
WHERE pc.category_id IN (SELECT id FROM category_subtree)
  AND pc.eliminado_en IS NULL
```

**Por qué CTE y no expansión Python**:

1. **Single round-trip**: la expansión Python-side hace `GET categorías → expand IDs → query` (2 queries; con árboles profundos crece). La CTE corre todo en una sola query.
2. **No N+1 escondido**: el service no tiene que conocer la estructura del árbol — la responsabilidad de "qué es descendiente de X" queda 100% en el repo.
3. **Precedente vivo**: `CategoryRepository.get_tree_cte()` ya usa CTE recursiva y funciona en PostgreSQL y SQLite.
4. **Pruebas más simples**: testeamos el comportamiento (productos de descendientes aparecen) sin tener que mockear el cálculo intermedio de IDs.

**Alternativas consideradas**:

- **A. Expansión Python via `CategoryRepository.get_descendant_ids(id)`**: viable pero suma N+1 en repos profundos y mete lógica de árbol en el service de productos. Rechazada.
- **B. Columna `categoria_root_id` denormalizada en producto**: rápido en lectura pero duplica datos y obliga a reindexar al mover categorías. Rechazada (over-engineering para este scope).
- **C. Materialized path o nested set en `categories`**: cambio estructural mayor, fuera de scope. Rechazada.

### D2: Exclusión granular de alérgenos con `excluir_alergeno_ids: list[int]`

**Decisión**: Agregar `excluir_alergeno_ids: list[int] = Query(default=[])` (FastAPI 0.115.6 ya soporta `list[int]` directo en `Query` sin `Annotated`). El viejo `excluir_alergenos: bool = False` queda intacto como atajo de compatibilidad. Cuando ambos se envían, se combinan con AND (raro pero válido: "excluir todos los alérgenos por defecto Y además estos IDs específicos").

**Lógica**: NOT EXISTS subquery análoga a la actual de `excluir_alergenos`, pero filtrando por `pi.ingredient_id IN :ids` en lugar de `ing.es_alergeno = true`:

```python
if excluir_alergeno_ids:
    ban_subq = (
        select(pi.c.product_id)
        .where(
            pi.c.product_id == Producto.id,
            pi.c.eliminado_en.is_(None),
            pi.c.es_removible.is_(False),
            pi.c.ingredient_id.in_(excluir_alergeno_ids),
        )
    )
    base = base.where(~exists(ban_subq))
```

Nota crítica: la condición `es_removible=False` se mantiene — si el usuario marcó "no quiero maní" pero el producto permite quitarlo, el producto SÍ aparece (lógica RN-CA08 ya existente).

**Por qué dos params en vez de uno**:

- `excluir_alergenos=true` ya está en el contrato público y se usa en tests; quitarlo es breaking.
- `excluir_alergeno_ids=[]` (omitido) significa "no filtres por IDs específicos"; mantener el booleano como shortcut "excluir todos los alérgenos" sigue siendo útil para un toggle UI rápido.
- Frontend Sprint 7 puede usar uno, el otro o ambos según la UX.

**Alternativas consideradas**:

- **A. Reemplazar `excluir_alergenos: bool` por `excluir_alergeno_ids: list[int]`** (breaking): rechazada — el contrato actual ya está consumido (US-023 boolean).
- **B. Usar header `X-Excluded-Allergens` en lugar de query param**: feo, no compatible con `<a href>` para shareable URLs (RN frontend de URL state).

### D3: Validación leaf-only en asignación de categorías a producto

**Decisión**: Helper `_validate_categorias_are_leaves(categoria_ids: list[int], session) -> None` en `ProductService` que se invoca en `create()` antes de `replace_categorias()` y en `set_categorias()` antes del replace. Si alguna categoría tiene hijas activas → `BusinessRuleError` (422) con mensaje accionable que incluye el nombre de la categoría ofensora y los nombres de sus hijas activas.

**Por qué un helper único y no validación inline**:

1. **DRY**: dos call-sites (`create` y `set_categorias`).
2. **Testabilidad**: se puede testear independientemente del flujo de creación.
3. **Mensaje accionable**: error 422 con detalle "La categoría 'Bebidas' no es hoja — tiene hijas activas: 'Gaseosas', 'Alcohólicas'. Asigná el producto a una de ellas." Sin esto, el admin frontend muestra un genérico inútil.

**Implementación**: la validación se ejecuta DESPUÉS de validar que cada ID existe (lógica ya viva). Una sola query por todas las IDs:

```python
hijas_query = (
    select(Categoria.padre_id, Categoria.nombre)
    .where(Categoria.padre_id.in_(categoria_ids))
    .where(Categoria.eliminado_en.is_(None))
)
```

Si la query devuelve rows → al menos una de las categorías solicitadas no es hoja → armar mensaje y `raise BusinessRuleError`.

**Alternativas consideradas**:

- **A. CHECK constraint en `product_categories`**: imposible (CHECK no puede subconsultar).
- **B. Trigger DB**: posible pero opaco — preferimos lógica en el service donde es auditable y testeable.
- **C. Validar solo en el router con dependency injection**: pierde acceso al `session` actual del UoW (rompe la atomicidad — si la categoría se vuelve hoja entre la dependency y el service, hay race condition).

### D4: Hook auto-`disponible=false` después de mutar categorías

**Decisión**: Tras cualquier operación que cambie el set de categorías de un producto (`create` con `categoria_ids=[]`, `set_categorias` que vacíe el set, o un futuro `delete categoría` que dejara al producto sin asignaciones), `ProductService` llama a `_auto_disable_if_no_leaf_categoria(product_id, session)`. Si `count_leaf_active_categories(product_id) == 0` → setea `disponible=false` y emite log INFO "Producto {id} desactivado: sin categoría hoja activa".

Esto es un **post-mutation hook en service**, NO un trigger de DB.

**Por qué post-hook y no trigger**:

1. **Auditabilidad**: el log queda en la app, ligado al request — más fácil de rastrear que un statement de trigger en logs de Postgres.
2. **Testabilidad**: testeamos con mocks de session, sin pelearnos con migraciones de triggers.
3. **Coherencia con el resto del backend**: nada acá usa triggers de Postgres — todas las reglas viven en services.
4. **Reactivación manual**: el admin reactiva con `PATCH /disponibilidad` después de reasignar categoría (UX explícita, no mágica).

**Query nuevo en repository** (`count_leaf_active_categories`): cuenta cuántas categorías activas asociadas al producto NO tienen hijas activas.

```python
# leaf = sin hijas activas. Antijoin contra categories self-ref.
sub = (
    select(ProductoCategoria.category_id)
    .where(
        ProductoCategoria.product_id == product_id,
        ProductoCategoria.eliminado_en.is_(None),
    )
)
hoja_count = (
    select(func.count())
    .select_from(Categoria)
    .where(
        Categoria.id.in_(sub),
        Categoria.eliminado_en.is_(None),
        ~exists(
            select(literal(1))
            .where(Categoria.padre_id == Categoria.id_outer)  # alias necesario
            .where(Categoria.eliminado_en.is_(None))
        ),
    )
)
```

**Alternativas consideradas**:

- **A. Trigger Postgres `AFTER INSERT/UPDATE/DELETE ON product_categories`**: rechazado por las razones de arriba.
- **B. Recalcular `disponible` en cada `GET /productos`**: caro y ensucia el modelo (la verdad pasa a depender del momento de lectura, no del estado real persistido).
- **C. Auto-`disponible=false` también al borrar una categoría (DELETE /categorias/{id})**: el guard de delete de categoría ya bloquea si tiene productos activos, así que este caso no se da hoy. Si el día de mañana se relaja el guard, el hook hay que invocarlo desde `CategoryService.delete()`. Lo dejamos documentado pero fuera de scope.

### D5: Filtro `sin_categoria=true` en `GET /productos`

**Decisión**: Nuevo query param boolean `sin_categoria: bool = False`. Si `true`, agrega NOT EXISTS contra `product_categories`:

```python
if sin_categoria:
    no_cat_subq = (
        select(ProductoCategoria.product_id)
        .where(
            ProductoCategoria.product_id == Producto.id,
            ProductoCategoria.eliminado_en.is_(None),
        )
    )
    base = base.where(~exists(no_cat_subq))
```

**Interacción con `disponible` default**: el router sigue aplicando `disponible=True` cuando viene `None` (RN-CA08). En la vista admin "productos sin categorizar" lo natural es `?sin_categoria=true&disponible=false&incluir_eliminados=false` — combina perfecto con el hook D4 (productos auto-desactivados por quedar sin categoría) sin requerir cambios extra.

**Alternativas consideradas**:

- **A. Endpoint separado `GET /productos/sin-categoria`**: rechazado — sobrecarga la API surface; lo natural es un filtro más en el listado paginado.
- **B. Filtro inverso `con_categoria=false`**: rechazado por menos legible; `sin_categoria` se entiende solo.

### D6: Guard contra promover categoría hoja a interna (block-on-promote)

**Decisión**: En `CategoryService.create()`, antes de insertar la nueva categoría, si `payload.padre_id is not None`, contar productos activos asociados directamente al padre. Si `count > 0` → `BusinessRuleError` (422) con detalle "No se puede subcategorizar 'X' — tiene N productos asignados. Reasigná los productos a una subcategoría existente primero." Esto vive en `CategoryService.create()` (no en `update()` porque mover padres es otro caso — ver alternativa B).

**Por qué bloquear**:

1. **Coherencia con D3**: si validamos leaf-only al asignar productos, dejar que el árbol "se desmadre" agregando hijas a un padre con productos crearía un set de productos en una categoría que ya no es hoja. Estado zombie.
2. **Sin cascadeo mágico**: la alternativa "auto-mover productos a la nueva hija" requiere decidir a CUÁL hija — imposible sin UI dedicada.
3. **Auto-`disponible=false` no aplica**: el producto sigue asignado al padre (que ahora es interno), no quedó sin categoría. Necesitamos prevenir, no recuperar.

**Alternativas consideradas (todas rechazadas)**:

- **A. Permitir + auto-`disponible=false` para los productos del padre**: desactiva productos que el admin no pidió desactivar. Mal UX.
- **B. Cascadeo automático: mover todos los productos del padre a la nueva hija**: invasivo; ¿y si el admin crea dos hijas seguidas?
- **C. Validar también en `update(categoria_id, {padre_id: X})`**: futuro change si aparece la necesidad. Hoy mover categorías ya tiene cycle detection — agregar este guard requiere más casos (¿qué pasa si X tiene productos? ¿la propia categoría tiene productos?). Out of scope.

### D7: `GET /categorias?solo_hojas=true` devuelve lista plana

**Decisión**: Nuevo query param `solo_hojas: bool = False`. Cuando `true`, el endpoint devuelve `list[CategoriaRead]` (plano), filtrando categorías activas sin hijas activas. Cuando `false` (default), sigue devolviendo `list[CategoriaTreeNode]` (árbol recursivo). El response_model tiene que ser `list[CategoriaRead] | list[CategoriaTreeNode]` — usamos `Union` en el endpoint con la docstring explicando el contrato dual.

**Por qué flat y no árbol**:

1. **UX del admin**: el `<select>` o autocomplete para "elegí categoría del producto" no renderiza árbol — necesita opciones planas (con `padre_id` para mostrar "Bebidas › Gaseosas" si se quiere prefijo).
2. **Separación de concerns**: el árbol completo lo consume el filtro lateral del catálogo cliente (Sprint 7), que sí necesita la jerarquía. El select admin no.
3. **Red de seguridad coherente con D3**: el frontend admin no puede elegir una raíz porque no aparece. La validación 422 queda como defensa en profundidad.

**Implementación**: nuevo `CategoryRepository.list_leaf_categories() -> list[Categoria]`:

```python
leaves = (
    select(Categoria)
    .where(Categoria.eliminado_en.is_(None))
    .where(
        ~exists(
            select(literal(1))
            .where(Categoria.padre_id == "id_outer")  # alias correcto
            .where(Categoria.eliminado_en.is_(None))
        )
    )
    .order_by(Categoria.nombre)
)
```

**Alternativas consideradas**:

- **A. Endpoint separado `GET /categorias/hojas`**: rechazada — duplicación; el router actual ya filtra por activos y el agregado es trivial.
- **B. Filtro client-side**: el frontend tendría que aplanar el árbol y filtrar — más lógica, más bugs.

### D8: `GET /ingredientes?es_alergeno=true` ya existe — solo documentar

**Confirmado en código**: `backend/features/ingredients/router.py:53` ya expone `es_alergeno: bool | None = Query(None)`. Sprint 3 lo implementó pero el spec actual de `ingredients` no lo formaliza como contrato público para el filtro UI.

**Acción**: agregar Requirement + Scenarios en delta spec `specs/ingredients/spec.md` que documenten el contrato (sin cambios de código). Esto cubre el caso "el frontend Sprint 7 espera este filtro" y deja el spec alineado con la realidad.

**Si en review aparece que el filtro NO está**: agregar como tarea de código en `tasks.md`. Por la lectura ya hecha, no hay que agregar nada — solo documentar.

## Risks / Trade-offs

- **CTE recursivo en SQLite (tests)**: PostgreSQL y SQLite difieren en sintaxis sutil de CTE recursiva. **Mitigación**: usar `union_all` y `cte(recursive=True)` de SQLAlchemy como hace `get_tree_cte()` ya vivo — esa abstracción genera SQL compatible. Test de integración cubre ambos drivers según conftest.

- **Seed data con productos en categorías raíz**: si el seed actual tiene productos asignados directo a "Bebidas" (raíz con hijas), un `PUT /categorias` posterior sobre ese producto lo rechazaría. **Mitigación**: tarea de audit en `tasks.md` — listar productos seed con `categoria_padre_id IS NOT NULL` que estén asignados a categorías con hijas activas; corregir el seed o el script de bootstrap si aparecen.

- **Auto-`disponible=false` puede sorprender al admin**: si el admin reemplaza categorías con `[]` esperando solo limpiar pivotes, el producto se desactiva. **Mitigación**: documentado en el response (log + spec scenario), y la reactivación es 1 click via `PATCH /disponibilidad`. El comportamiento es preferible a quedar con productos "activos pero invisibles" (porque no aparecen sin filtro de categoría en el catálogo cliente).

- **`excluir_alergeno_ids=[]` vs sin enviar**: ambos significan "no excluyas por IDs". FastAPI los normaliza al mismo `[]`, así que no hay edge case.

- **Performance CTE recursivo + JOIN producto_categoria**: para árboles de 3-5 niveles y miles de productos no hay drama. Si el árbol explota a 10+ niveles + 100k productos, hay que revisar (no es el caso del proyecto). **Mitigación**: índice en `categories.padre_id` (ya existe via FK) + índice compuesto en `product_categories(product_id, category_id, eliminado_en)` (ya existe — verificar en migration `20260428_0001`).

- **No hay schema change → no migration**: bajo riesgo de regresión por DDL, pero alto riesgo de regresión silenciosa por SQL. **Mitigación**: TDD estricto si está activo en el proyecto + tests de integración con casos borde (categoría sin productos, producto sin categoría, árbol vacío, categoría raíz hoja).

## Migration Plan

Sin DDL. Toda la entrega es código + tests:

1. Implementar feature por feature en el orden de `tasks.md`.
2. Cada feature: red-green-refactor (TDD) si strict_tdd está activo; tests primero igual.
3. Audit de seed antes de mergear: ejecutar query contra dev DB para listar productos asignados a categorías no-hoja; corregir seed o documentar excepciones.
4. Rollback: revertir el commit. Sin operaciones manuales sobre DB necesarias (no hay datos nuevos persistidos por este change).

## Open Questions

(ninguna — las 8 decisiones están cerradas según `sdd/catalog-filters-and-leaf-categories-backend/decisions`)
