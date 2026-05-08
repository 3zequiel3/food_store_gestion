## 1. Scaffolding del módulo

- [x] 1.1 Crear directorio `backend/features/categories/` con `__init__.py` vacío.
- [x] 1.2 Crear archivos vacíos `router.py`, `service.py`, `repository.py`, `schemas.py` para fijar la estructura.
- [x] 1.3 Verificar que NO se crea un nuevo archivo `models.py` en `categories/` — el modelo `Categoria` se importa desde `backend.features.catalog.models`.

## 2. Schemas Pydantic v2

- [x] 2.1 En `schemas.py`: definir `CategoriaCreate(BaseModel)` con `nombre: str = Field(..., min_length=1, max_length=100)` y `padre_id: int | None = None`.
- [x] 2.2 Definir `CategoriaUpdate(BaseModel)` con `nombre: str | None = Field(None, min_length=1, max_length=100)` y `padre_id: int | None = None`. Documentar en docstring que el service debe usar `model_dump(exclude_unset=True)` para distinguir "no enviado" de "null explícito".
- [x] 2.3 Definir `CategoriaRead(BaseModel)` con `id`, `nombre`, `padre_id`, `creado_en: datetime`, `actualizado_en: datetime` y `model_config = {"from_attributes": True}`.
- [x] 2.4 Definir `CategoriaTreeNode(BaseModel)` recursivo con `id`, `nombre`, `padre_id`, `subcategorias: list["CategoriaTreeNode"] = Field(default_factory=list)` y `model_config = {"from_attributes": True}`. Llamar `CategoriaTreeNode.model_rebuild()` al final del archivo para resolver la referencia adelantada.
- [x] 2.5 Definir un dataclass interno `CategoryFlatRow` (o `NamedTuple`) con `(id: int, nombre: str, padre_id: int | None, depth: int)` para tipar el retorno de la CTE — vivirá en `schemas.py` dentro de `categories/`.

## 3. Repository

- [x] 3.1 En `repository.py`: importar `Categoria` desde `backend.features.catalog.models`, `BaseRepository` desde `backend.shared.repository`, y los componentes SQLAlchemy 2.0 necesarios (`select`, `func`, `and_`, `union_all`, `text`).
- [x] 3.2 Crear clase `CategoryRepository(BaseRepository[Categoria])` con `__init__(self, session: Session)` que llame `super().__init__(session, Categoria)`.
- [x] 3.3 Implementar `find_by_nombre_y_padre(self, nombre: str, padre_id: int | None) -> Categoria | None` usando `_get_base_query()` (heredado de `BaseRepository`) con `where(Categoria.nombre == nombre)` y manejo correcto de NULL en `padre_id` (usar `is_(None)` cuando aplique).
- [x] 3.4 Implementar `has_active_children(self, categoria_id: int) -> bool` con `select(func.count()).select_from(Categoria).where(Categoria.padre_id == categoria_id, Categoria.eliminado_en.is_(None))` y comparar con `> 0`.
- [x] 3.5 Implementar `has_active_products(self, categoria_id: int) -> bool` con un join entre `product_categories` y `products` filtrando `products.eliminado_en IS NULL`. Usar `select` del Core con `text` o joinedload — cualquiera que produzca un único query. NO instanciar `ProductRepository`.
- [x] 3.6 Implementar `would_create_cycle(self, categoria_id: int, new_padre_id: int | None) -> bool`:
  - Si `new_padre_id is None`: retornar `False` directo.
  - Si `new_padre_id == categoria_id`: retornar `True` directo.
  - Si no: ejecutar la CTE recursiva (ver shape exacto en `design.md` D4) que parte de `new_padre_id` y sube por `padre_id`. Retornar `True` si encuentra `categoria_id` en la cadena.
- [x] 3.7 Implementar `get_tree_cte(self) -> list[CategoryFlatRow]` con la CTE recursiva (ver shape exacto en `design.md` D2). Anchor: `padre_id IS NULL AND eliminado_en IS NULL`. Recursive: child se une por `padre_id = parent.id`. Devolver lista plana ordenada determinísticamente (por `depth` y luego por `nombre` o por `path` si se logra construir).
- [x] 3.8 Documentar cada método público con docstring breve incluyendo precondiciones y excepciones esperadas (none para los repos — los errores los levanta el service).

## 4. Service

- [x] 4.1 En `service.py`: importar `UnitOfWork`, `CategoryRepository`, las excepciones tipadas (`NotFoundError`, `ConflictError`, `BusinessRuleError`) y los schemas.
- [x] 4.2 Crear clase `CategoryService` con `__init__(self, uow: UnitOfWork)` que registra el repo: `uow.register_repository("categorias", CategoryRepository(uow.session))`.
- [x] 4.3 Implementar `create(self, payload: CategoriaCreate) -> Categoria`:
  - Validar `nombre` trimmed (no espacios sólo).
  - Si `padre_id is not None`: verificar que existe vía `uow.categorias.read(padre_id)`, si no → `BusinessRuleError("Categoría padre no encontrada")`.
  - Llamar `uow.categorias.find_by_nombre_y_padre(payload.nombre, payload.padre_id)`. Si retorna no-None → `ConflictError("Ya existe una categoría con ese nombre en este nivel")`.
  - Crear vía `uow.categorias.create(nombre=payload.nombre, padre_id=payload.padre_id)`. Devolver la entidad.
- [x] 4.4 Implementar `update(self, categoria_id: int, payload: CategoriaUpdate) -> Categoria`:
  - Leer la categoría: `current = uow.categorias.read(categoria_id)`. Si None → `NotFoundError("Categoría no encontrada")`.
  - Volcar payload: `data = payload.model_dump(exclude_unset=True)`.
  - Si `"padre_id" in data` y `data["padre_id"] != current.padre_id`:
    - Si `data["padre_id"] is not None`: verificar que existe la categoría padre.
    - Llamar `uow.categorias.would_create_cycle(categoria_id, data["padre_id"])`. Si True → `BusinessRuleError("El cambio de padre crearía un ciclo en la jerarquía")` o `BusinessRuleError("Una categoría no puede ser padre de sí misma")` cuando `padre_id == categoria_id`.
  - Calcular el nombre y padre_id efectivos (usando los actuales como fallback) y validar unicidad por nivel: `find_by_nombre_y_padre(effective_nombre, effective_padre_id)` y, si retorna no-None con `id != categoria_id` → `ConflictError`.
  - Llamar `uow.categorias.update(categoria_id, **data)`. Devolver la entidad.
- [x] 4.5 Implementar `delete(self, categoria_id: int) -> None`:
  - Leer la categoría → `NotFoundError` si no existe (o ya está soft-deleted).
  - Si `uow.categorias.has_active_children(categoria_id)` → `BusinessRuleError("No se puede eliminar la categoría: tiene subcategorías activas. Reasignelas o eliminelas primero")`.
  - Si `uow.categorias.has_active_products(categoria_id)` → `BusinessRuleError("No se puede eliminar la categoría: tiene productos activos asociados. Reasigne los productos primero")`.
  - Llamar `uow.categorias.delete(categoria_id)` (soft delete heredado de `BaseRepository`).
- [x] 4.6 Implementar `get_tree(self) -> list[CategoriaTreeNode]`:
  - Llamar `flat = uow.categorias.get_tree_cte()`.
  - Construir un dict `{id: CategoriaTreeNode}` con todos los nodos.
  - En un segundo pase, asignar cada nodo a `subcategorias` de su `padre_id` (si existe en el dict).
  - Retornar la lista de nodos raíz (los que tienen `padre_id is None` o cuyo padre no quedó en el dict).
- [x] 4.7 Verificar que NINGÚN método del service llama `uow.commit()` ni `session.commit()`. El commit es responsabilidad del router (D6).

## 5. Router

- [x] 5.1 En `router.py`: importar `APIRouter`, `Depends`, `status`, `UnitOfWork`, `get_uow`, `require_role`, los schemas y `CategoryService`.
- [x] 5.2 Crear `router = APIRouter()` (sin `prefix` aquí — el prefix se aplica en `main.py`).
- [x] 5.3 Implementar `POST /` con response_model=CategoriaRead, status_code=201:
  - Dependencias: `payload: CategoriaCreate`, `uow: UnitOfWork = Depends(get_uow)`, `user: Usuario = Depends(require_role("ADMIN", "STOCK"))`.
  - Llamar `service.create(payload)`, hacer `uow.commit()`, retornar `CategoriaRead.model_validate(cat)`.
- [x] 5.4 Implementar `GET /` con response_model=list[CategoriaTreeNode] (público, sin `Depends(require_role)`):
  - Dependencia `uow: UnitOfWork = Depends(get_uow)`.
  - Llamar `service.get_tree()`. NO hacer commit (es read-only). Retornar la lista.
- [x] 5.5 Implementar `PUT /{categoria_id}` con response_model=CategoriaRead, status_code=200:
  - Dependencias: `categoria_id: int`, `payload: CategoriaUpdate`, `uow`, `user: require_role("ADMIN", "STOCK")`.
  - Llamar `service.update(categoria_id, payload)`, `uow.commit()`, retornar `CategoriaRead.model_validate(cat)`.
- [x] 5.6 Implementar `DELETE /{categoria_id}` con status_code=204, response_class=Response:
  - Dependencias: `categoria_id: int`, `uow`, `user: require_role("ADMIN", "STOCK")`.
  - Llamar `service.delete(categoria_id)`, `uow.commit()`, retornar `Response(status_code=204)`.
- [x] 5.7 Verificar que NINGÚN endpoint levanta `HTTPException` directamente — todos los errores vienen del service vía las exceptions tipadas.

## 6. Wiring en main.py

- [x] 6.1 Agregar import side-effect: ya está cubierto por `from backend.features.catalog import models as _catalog_models`. NO agregar un import nuevo de `categories/models` (no existe).
- [x] 6.2 Agregar `from backend.features.categories.router import router as categories_router` en la sección de imports de routers en `main.py`.
- [x] 6.3 Agregar `app.include_router(categories_router, prefix="/api/v1/categorias", tags=["categories"])` en la sección de registro de routers en `main.py`.
- [x] 6.4 Verificar que el orden de registro coincide con el patrón actual (después de `payments_router` y antes del bloque `if __name__ == "__main__"`).

## 7. Tests de integración

- [x] 7.1 Crear `backend/tests/integration/test_categories.py` con fixtures que provean un cliente FastAPI autenticado como ADMIN y como STOCK (reusar las fixtures de auth si existen, sino crearlas a medida).
- [x] 7.2 Test: `test_create_root_categoria_as_admin` — POST con nombre y padre_id=null → 201 + body correcto.
- [x] 7.3 Test: `test_create_subcategoria_as_stock` — crear raíz, luego POST con padre_id apuntando a la raíz → 201.
- [x] 7.4 Test: `test_create_unauthenticated_returns_401` — POST sin token → 401.
- [x] 7.5 Test: `test_create_as_client_returns_403` — POST con token de CLIENT → 403.
- [x] 7.6 Test: `test_create_empty_nombre_returns_422` — POST con `nombre=""` → 422.
- [x] 7.7 Test: `test_create_nombre_too_long_returns_422` — POST con nombre 101 chars → 422.
- [x] 7.8 Test: `test_create_duplicate_root_name_returns_409` — crear `Bebidas`, intentar crear otro `Bebidas` con padre_id=null → 409.
- [x] 7.9 Test: `test_create_duplicate_sibling_name_returns_409` — dentro del mismo padre, dos hijos con mismo nombre → 409.
- [x] 7.10 Test: `test_create_same_name_different_levels_allowed` — `Promos` raíz y `Promos` bajo otra categoría → ambos 201.
- [x] 7.11 Test: `test_create_with_nonexistent_parent_returns_422` — POST con padre_id=99999 → 422 BusinessRuleError.
- [x] 7.12 Test: `test_get_tree_empty_returns_empty_list` — GET sobre tabla vacía (o solo soft-deleted) → 200 + `[]`.
- [x] 7.13 Test: `test_get_tree_returns_nested_structure` — crear una jerarquía de 3 niveles vía repo directo, GET, validar que `subcategorias` está bien anidado.
- [x] 7.14 Test: `test_get_tree_excludes_soft_deleted` — soft-deletear un nodo intermedio, GET, validar exclusión.
- [x] 7.15 Test: `test_get_tree_is_public` — GET sin token → 200.
- [x] 7.16 Test: `test_update_nombre_only` — PUT con solo nombre → 200, padre_id sin cambios.
- [x] 7.17 Test: `test_update_padre_id_to_another_category` — PUT con nuevo padre → 200.
- [x] 7.18 Test: `test_update_promote_to_root` — PUT con `padre_id: null` → 200 + `padre_id == null` en body.
- [x] 7.19 Test: `test_update_self_parent_returns_422` — PUT con `padre_id == self.id` → 422.
- [x] 7.20 Test: `test_update_creates_direct_cycle_returns_422` — A→B, intentar PUT A con padre_id=B → 422.
- [x] 7.21 Test: `test_update_creates_indirect_cycle_returns_422` — A→B→C, intentar PUT A con padre_id=C → 422.
- [x] 7.22 Test: `test_update_nonexistent_returns_404` — PUT a id inexistente → 404.
- [x] 7.23 Test: `test_update_soft_deleted_returns_404` — PUT a id soft-deleted → 404.
- [x] 7.24 Test: `test_delete_leaf_succeeds` — DELETE en hoja sin productos → 204 + `eliminado_en IS NOT NULL`.
- [x] 7.25 Test: `test_delete_does_not_hard_delete` — verificar que la fila sigue en la tabla con `eliminado_en` set.
- [x] 7.26 Test: `test_delete_with_active_children_returns_422` — DELETE de un padre con hijo no-borrado → 422.
- [x] 7.27 Test: `test_delete_after_children_soft_deleted_succeeds` — soft-deletear hijos primero, luego padre → 204.
- [x] 7.28 Test: `test_delete_with_active_products_returns_422` — crear categoría, asociar producto activo (insert directo en `product_categories`), DELETE → 422.
- [x] 7.29 Test: `test_delete_already_deleted_returns_404` — DELETE dos veces → 2da vez 404.
- [x] 7.30 Test: `test_endpoints_use_v1_prefix_and_spanish_path` — `/api/v1/categories` → 404, `/api/categorias` → 404.

## 8. Documentación y wrap-up

- [x] 8.1 Crear `backend/features/categories/README.md` breve (5-10 líneas) describiendo el módulo, los 4 endpoints, y el patrón de UoW. Incluir ejemplo de curl para POST.
- [ ] 8.2 Verificar manualmente con un curl de smoke (o pytest -k categories) que los 4 endpoints responden correctamente — NO ejecutar build, solo `pytest backend/tests/integration/test_categories.py`.
- [ ] 8.3 Mostrar resumen al usuario: archivos creados, paths exactos, link a la primera CTE del proyecto en `repository.py`. ESPERAR REVISIÓN HUMANA antes de cualquier `/opsx:archive`.

## 9. Notas de implementación

> **Recordatorio para el apply-agent:**
> - Regla de oro de imports: `Router → Service → UoW → Repository → Model`. Verificar que `repository.py` no importa nada de `service.py` ni `router.py`.
> - El service NUNCA hace `uow.commit()`. El router lo decide.
> - El soft delete usa `eliminado_en = datetime.now(timezone.utc)`, NUNCA `session.delete()`.
> - `padre_id == 0`, `padre_id < 0` y `padre_id` no existente son todos rechazos del service (no del repo).
> - Si la CTE de SQLAlchemy con `array` se complica, se puede simplificar a `(id, nombre, padre_id, depth)` sin `path` y ordenar por `depth ASC, nombre ASC`. El nesting en Python no necesita `path` para ser correcto.

## 10. Fix post-implementación — `func.literal(0)` rompe en SQLite

> Bug detectado al correr el suite con SQLite in-memory después de aplicar `fix-test-setup-uow-override`. El design.md D2 especificaba `literal(0)` (constructor SQLAlchemy que inlinea valores), pero la implementación usó `func.literal(0)` (llamada a una función SQL `literal()` que no existe en SQLite). Síntoma: 5 tests de `TestTree` y `TestRouting` fallan con `sqlite3: no such function: literal`.

- [x] 10.1 En `backend/features/categories/repository.py`: agregar `literal` al import existente desde `sqlalchemy` (la línea cerca de `select`, `func`, etc.).
- [x] 10.2 Reemplazar en línea ~176 (anchor de la CTE de árbol en `get_tree_cte`): `func.literal(0).label("depth")` → `literal(0).label("depth")`.
- [x] 10.3 Verificar con `rg "func\.literal" backend/features/categories/` que no quedan otras referencias residuales (la CTE de ciclos en `would_create_cycle` no usa literal — verificar igual).
- [x] 10.4 Correr `pytest backend/tests/integration/test_categories.py -v` y validar **31/31 PASSED**.
- [x] 10.5 Si algún test sigue fallando por OTRO motivo (no relacionado al `literal`), reportarlo SIN arreglarlo — queda fuera del scope de este fix puntual.
