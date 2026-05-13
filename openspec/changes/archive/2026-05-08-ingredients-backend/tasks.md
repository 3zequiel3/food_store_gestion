## 1. Scaffolding del módulo

- [x] 1.1 Crear directorio `backend/features/ingredients/` con `__init__.py` vacío.
- [x] 1.2 Crear archivos vacíos `router.py`, `service.py`, `repository.py`, `schemas.py` para fijar la estructura.
- [x] 1.3 Verificar que NO se crea un nuevo archivo `models.py` en `ingredients/` — el modelo `Ingrediente` se importa desde `backend.features.catalog.models` (líneas 137-151).

## 2. Schemas Pydantic v2

- [x] 2.1 En `schemas.py`: definir `IngredienteCreate(BaseModel)` con `nombre: str = Field(..., min_length=1, max_length=255)` y `es_alergeno: bool = False`.
- [x] 2.2 Definir `IngredienteUpdate(BaseModel)` con `nombre: str | None = Field(None, min_length=1, max_length=255)` y `es_alergeno: bool | None = None`. Documentar en docstring que el service DEBE usar `model_dump(exclude_unset=True)` para distinguir "no enviado" de "enviado explícitamente" — crítico para `es_alergeno`.
- [x] 2.3 Definir `IngredienteRead(BaseModel)` con `id: int`, `nombre: str`, `es_alergeno: bool`, `creado_en: datetime`, `actualizado_en: datetime` y `model_config = {"from_attributes": True}`.
- [x] 2.4 Definir `PaginatedIngredientes(BaseModel)` con `items: list[IngredienteRead]`, `total: int`, `page: int`, `limit: int`. Sin `model_config` adicional — los items ya son Pydantic.

## 3. Repository

- [x] 3.1 En `repository.py`: importar `Ingrediente` desde `backend.features.catalog.models`, `BaseRepository` desde `backend.shared.repository`, y los componentes SQLAlchemy 2.0 necesarios (`select`, `func`, `Session`).
- [x] 3.2 Crear clase `IngredientRepository(BaseRepository[Ingrediente])` con `__init__(self, session: Session)` que llame `super().__init__(session, Ingrediente)`.
- [x] 3.3 Implementar `find_by_nombre(self, nombre: str) -> Ingrediente | None`:
  - **Importante:** este método NO filtra por `eliminado_en` (a diferencia de `categories.find_by_nombre_y_padre`). El constraint UNIQUE de DB cubre toda la tabla, así que el chequeo de service debe ver soft-deleted también.
  - Implementación: `select(Ingrediente).where(Ingrediente.nombre == nombre)` ejecutado contra `self.session` y devolviendo `scalar_one_or_none()`.
- [x] 3.4 Implementar `list_paginated(self, *, skip: int, limit: int, es_alergeno: bool | None = None) -> tuple[list[Ingrediente], int]`:
  - Empezar con `base = self._get_base_query()` (heredado, ya filtra `eliminado_en IS NULL`).
  - Si `es_alergeno is not None`: agregar `.where(Ingrediente.es_alergeno == es_alergeno)`.
  - Calcular total: `count_query = select(func.count()).select_from(base.subquery())` → `total = self.session.execute(count_query).scalar() or 0`.
  - Paginar: `items_query = base.order_by(Ingrediente.nombre).offset(skip).limit(limit)`.
  - Ejecutar items: `items = self.session.execute(items_query).scalars().all()`.
  - Devolver `(list(items), total)`.
- [x] 3.5 Documentar cada método público con docstring breve incluyendo precondiciones y excepciones esperadas (none para los repos — los errores los levanta el service).
- [x] 3.6 Verificar (via lectura del código) que NO se sobrescribe `delete()`, `update()`, `read()`, `list_all()` ni `_get_base_query()` — todos heredan correctamente de `BaseRepository`.

## 4. Service

- [x] 4.1 En `service.py`: importar `UnitOfWork`, `IngredientRepository`, las excepciones tipadas (`NotFoundError`, `ConflictError`, `BusinessRuleError`) y los schemas (`IngredienteCreate`, `IngredienteUpdate`).
- [x] 4.2 Crear clase `IngredientService` con `__init__(self, uow: UnitOfWork)` que registra el repo: `uow.register_repository("ingredientes", IngredientRepository(uow.session))`. Guardar `self.repo` y `self.uow`.
- [x] 4.3 Implementar `create(self, payload: IngredienteCreate) -> Ingrediente`:
  - Trim el nombre: `nombre = payload.nombre.strip()`. Si `not nombre` → `BusinessRuleError("El nombre del ingrediente no puede estar vacío")`.
  - Chequeo de unicidad: `existing = self.repo.find_by_nombre(nombre)`. Si `existing is not None` → `ConflictError("Ya existe un ingrediente con ese nombre")`.
  - Crear: `return self.repo.create(nombre=nombre, es_alergeno=payload.es_alergeno)`.
- [x] 4.4 Implementar `get_by_id(self, ingrediente_id: int) -> Ingrediente`:
  - `current = self.repo.read(ingrediente_id)`. Si `None` → `NotFoundError("Ingrediente no encontrado")`.
  - Devolver `current`.
- [x] 4.5 Implementar `list_paginated(self, *, page: int, limit: int, es_alergeno: bool | None) -> tuple[list[Ingrediente], int]`:
  - Convertir `page` a `skip = (page - 1) * limit`.
  - Llamar `self.repo.list_paginated(skip=skip, limit=limit, es_alergeno=es_alergeno)`.
  - Devolver el tuple.
- [x] 4.6 Implementar `update(self, ingrediente_id: int, payload: IngredienteUpdate) -> Ingrediente`:
  - `current = self.repo.read(ingrediente_id)`. Si `None` → `NotFoundError("Ingrediente no encontrado")`.
  - `data = payload.model_dump(exclude_unset=True)` — esto preserva `es_alergeno` cuando no se envía.
  - Si `"nombre" in data`:
    - Trim: `data["nombre"] = data["nombre"].strip()`. Si vacío → `BusinessRuleError`.
    - Chequear unicidad solo si el nombre cambió: `if data["nombre"] != current.nombre:` → `existing = self.repo.find_by_nombre(data["nombre"])`. Si `existing` y `existing.id != ingrediente_id` → `ConflictError`.
  - Aplicar update: `return self.repo.update(ingrediente_id, **data)`.
- [x] 4.7 Implementar `delete(self, ingrediente_id: int) -> None`:
  - `current = self.repo.read(ingrediente_id)`. Si `None` → `NotFoundError`.
  - **NO chequear** `product_ingredients` (ver D4 en design.md — no hay guards).
  - `self.repo.delete(ingrediente_id)` (soft delete heredado).
- [x] 4.8 Verificar (lectura) que NINGÚN método del service llama `uow.commit()` ni `session.commit()`. El commit es responsabilidad del router (D6).

## 5. Router

- [x] 5.1 En `router.py`: importar `APIRouter`, `Depends`, `Query`, `Response`, `status` desde fastapi; `UnitOfWork` desde `backend.shared.unit_of_work`; `get_uow` desde `backend.dependencies`; `require_role` desde `backend.features.auth.dependencies`; los schemas (`IngredienteCreate`, `IngredienteUpdate`, `IngredienteRead`, `PaginatedIngredientes`); y `IngredientService`.
- [x] 5.2 Crear `router = APIRouter()` (sin `prefix` aquí — el prefix se aplica en `main.py`).
- [x] 5.3 Implementar `POST /` con `response_model=IngredienteRead`, `status_code=status.HTTP_201_CREATED`:
  - Dependencias: `payload: IngredienteCreate`, `uow: UnitOfWork = Depends(get_uow)`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - Llamar `service.create(payload)`, hacer `uow.commit()`, retornar `IngredienteRead.model_validate(ing)`.
- [x] 5.4 Implementar `GET /` con `response_model=PaginatedIngredientes` (público, sin `Depends(require_role)`):
  - Query params: `page: int = Query(1, ge=1)`, `limit: int = Query(20, ge=1, le=100)`, `es_alergeno: bool | None = Query(None)`.
  - Dependencia: `uow: UnitOfWork = Depends(get_uow)`.
  - Llamar `items, total = service.list_paginated(page=page, limit=limit, es_alergeno=es_alergeno)`. NO hacer commit.
  - Retornar `PaginatedIngredientes(items=[IngredienteRead.model_validate(i) for i in items], total=total, page=page, limit=limit)`.
- [x] 5.5 Implementar `GET /{ingrediente_id}` con `response_model=IngredienteRead` (público):
  - Dependencias: `ingrediente_id: int`, `uow: UnitOfWork = Depends(get_uow)`.
  - Llamar `ing = service.get_by_id(ingrediente_id)`. NO hacer commit.
  - Retornar `IngredienteRead.model_validate(ing)`.
- [x] 5.6 Implementar `PUT /{ingrediente_id}` con `response_model=IngredienteRead`:
  - Dependencias: `ingrediente_id: int`, `payload: IngredienteUpdate`, `uow`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - Llamar `service.update(ingrediente_id, payload)`, `uow.commit()`, retornar `IngredienteRead.model_validate(ing)`.
- [x] 5.7 Implementar `DELETE /{ingrediente_id}` con `status_code=status.HTTP_204_NO_CONTENT`:
  - Dependencias: `ingrediente_id: int`, `uow`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - Llamar `service.delete(ingrediente_id)`, `uow.commit()`, retornar `Response(status_code=status.HTTP_204_NO_CONTENT)`.
- [x] 5.8 Verificar (lectura) que NINGÚN endpoint levanta `HTTPException` directamente — todos los errores vienen del service vía las exceptions tipadas que tienen handlers globales en `main.py`.

## 6. Wiring en main.py

- [x] 6.1 Verificar que el modelo `Ingrediente` ya está cargado por side-effect via `from backend.features.catalog import models as _catalog_models` (línea 57 de `main.py`). NO agregar un import nuevo de `ingredients/models` (no existe).
- [x] 6.2 Agregar `from backend.features.ingredients.router import router as ingredients_router` en la sección de imports de routers (después de la línea 71 que importa `categories_router`).
- [x] 6.3 Agregar `app.include_router(ingredients_router, prefix="/api/v1/ingredientes", tags=["ingredients"])` en la sección de registro de routers, después de la línea 199 que registra `categories_router`.
- [x] 6.4 Verificar que el orden de registro coincide con el patrón actual (después de `categories_router` y antes del bloque `if __name__ == "__main__"`).

## 7. Tests de integración

- [x] 7.1 Crear `backend/tests/integration/test_ingredients.py` reusando las fixtures `admin_user`, `stock_user`, `client_user`, `_admin_headers`, `_stock_headers`, `_client_headers` del conftest (las mismas que `test_categories.py` usa).

### 7.1 Happy path CRUD
- [x] 7.2 Test: `test_create_as_admin` — POST con `{"nombre": "Tomate", "es_alergeno": false}` → 201 con body correcto.
- [x] 7.3 Test: `test_create_as_stock_with_alergeno_true` — POST con `{"nombre": "Mani", "es_alergeno": true}` → 201.
- [x] 7.4 Test: `test_create_default_es_alergeno_false` — POST con solo `{"nombre": "Lechuga"}` → 201 con `es_alergeno: false`.
- [x] 7.5 Test: `test_get_by_id_returns_ingredient` — crear, GET por id → 200 con body correcto.
- [x] 7.6 Test: `test_list_default_pagination` — crear 3 ingredientes, GET sin params → 200 con `total=3, page=1, limit=20, items.length=3`.
- [x] 7.7 Test: `test_update_nombre_only_preserves_alergeno` — crear con `es_alergeno=true`, PUT con solo `{"nombre": "X"}` → 200, `es_alergeno` sigue `true`.
- [x] 7.8 Test: `test_update_alergeno_only_preserves_nombre` — crear con `nombre="Mani"`, PUT con solo `{"es_alergeno": true}` → 200, `nombre` sigue `"Mani"`.
- [x] 7.9 Test: `test_update_both_fields` — PUT con ambos campos → 200, ambos cambiados.
- [x] 7.10 Test: `test_delete_soft` — crear, DELETE → 204, fila sigue en tabla con `eliminado_en IS NOT NULL`.

### 7.2 RBAC
- [x] 7.11 Test: `test_create_unauthenticated_returns_401` — POST sin token → 401.
- [x] 7.12 Test: `test_create_as_client_returns_403` — POST con token de CLIENT → 403.
- [x] 7.13 Test: `test_put_as_client_returns_403` — PUT con CLIENT → 403.
- [x] 7.14 Test: `test_delete_as_client_returns_403` — DELETE con CLIENT → 403.
- [x] 7.15 Test: `test_get_list_is_public` — GET sin token → 200.
- [x] 7.16 Test: `test_get_by_id_is_public` — GET sin token → 200.

### 7.3 Validación y unicidad
- [x] 7.17 Test: `test_create_empty_nombre_returns_422` — POST con `nombre=""` → 422.
- [x] 7.18 Test: `test_create_nombre_too_long_returns_422` — POST con nombre de 256 chars → 422.
- [x] 7.19 Test: `test_create_duplicate_name_returns_409` — crear "Tomate", intentar crear otro "Tomate" → 409.
- [x] 7.20 Test: `test_create_duplicate_of_soft_deleted_returns_409` — crear "Pimienta", soft-deletear, intentar crear otra "Pimienta" → 409 (constraint UNIQUE no filtra `eliminado_en`).
- [x] 7.21 Test: `test_update_to_existing_name_returns_409` — crear A y B, PUT B con nombre de A → 409.
- [x] 7.22 Test: `test_update_to_same_name_succeeds` — PUT con el mismo nombre actual → 200 (no debería disparar conflict).
- [x] 7.23 Test: `test_update_empty_nombre_returns_422` — PUT con `nombre=""` → 422.

### 7.4 Filtros y paginación
- [x] 7.24 Test: `test_list_filter_es_alergeno_true` — crear 3 con `true` y 7 con `false`, GET `?es_alergeno=true` → `total=3`, todos los items con `es_alergeno: true`.
- [x] 7.25 Test: `test_list_filter_es_alergeno_false` — mismo setup, GET `?es_alergeno=false` → `total=7`.
- [x] 7.26 Test: `test_list_pagination_respects_limit` — crear 25, GET `?limit=10` → `items.length=10, total=25, page=1, limit=10`.
- [x] 7.27 Test: `test_list_pagination_page_2` — crear 25, GET `?page=2&limit=10` → `items.length=10, page=2`.
- [x] 7.28 Test: `test_list_pagination_last_page_partial` — crear 25, GET `?page=3&limit=10` → `items.length=5, page=3`.
- [x] 7.29 Test: `test_list_limit_above_100_returns_422` — GET `?limit=200` → 422.
- [x] 7.30 Test: `test_list_page_zero_returns_422` — GET `?page=0` → 422.
- [x] 7.31 Test: `test_list_excludes_soft_deleted` — crear 3, soft-deletear 1, GET → `total=2`.

### 7.5 404s
- [x] 7.32 Test: `test_get_by_id_not_found` — GET id inexistente → 404.
- [x] 7.33 Test: `test_get_by_id_soft_deleted_returns_404` — soft-deletear, GET → 404.
- [x] 7.34 Test: `test_update_not_found_returns_404` — PUT id inexistente → 404.
- [x] 7.35 Test: `test_update_soft_deleted_returns_404` — soft-deletear, PUT → 404.
- [x] 7.36 Test: `test_delete_not_found_returns_404` — DELETE id inexistente → 404.
- [x] 7.37 Test: `test_delete_already_deleted_returns_404` — DELETE dos veces → 2da vez 404.

### 7.6 Soft delete sin guards
- [x] 7.38 Test: `test_delete_does_not_hard_delete` — verificar via query SQL directa que la fila sigue en tabla con `eliminado_en IS NOT NULL`.
- [x] 7.39 Test: `test_delete_with_associated_products_succeeds` — crear ingrediente, insertar fila en `product_ingredients` apuntando a un producto activo, DELETE el ingrediente → 204 (sin guard). Verificar que la fila en `product_ingredients` sigue intacta. **Nota:** este test requiere un producto seed; usar inserts directos vía `session.execute(text(...))` o reusar fixtures de productos si existen.

### 7.7 Routing
- [x] 7.40 Test: `test_endpoint_uses_v1_prefix_and_spanish_path` — verificar que `GET /api/v1/ingredients` (inglés) → 404 y `GET /api/ingredientes` (sin v1) → 404.

## 8. Documentación y wrap-up

- [x] 8.1 Crear `backend/features/ingredients/README.md` breve (5-10 líneas) describiendo el módulo, los 5 endpoints, el patrón de UoW y el filtro `es_alergeno`. Incluir ejemplo de curl para POST y GET con filtro.
- [x] 8.2 Verificar manualmente con `pytest backend/tests/integration/test_ingredients.py -v` que los 5 endpoints responden correctamente — NO ejecutar build, solo el suite de tests específico.
- [x] 8.3 Mostrar resumen al usuario: archivos creados, paths exactos, link al `list_paginated` en `repository.py`. ESPERAR REVISIÓN HUMANA antes de cualquier `/opsx:archive`.

## 9. Notas de implementación

> **Recordatorio para el apply-agent:**
> - Regla de oro de imports: `Router → Service → UoW → Repository → Model`. Verificar que `repository.py` no importa nada de `service.py` ni `router.py`.
> - El service NUNCA hace `uow.commit()`. El router lo decide.
> - El soft delete usa `eliminado_en = datetime.now(timezone.utc)`, NUNCA `session.delete()`.
> - **`find_by_nombre` NO filtra por `eliminado_en`** — diferencia clave vs `categories.find_by_nombre_y_padre`. El constraint UNIQUE de DB cubre toda la tabla, así que el chequeo de service debe replicarlo.
> - **`model_dump(exclude_unset=True)` en update es CRÍTICO** — sin él, `es_alergeno` se sobreescribe silenciosamente cuando el cliente solo envía `nombre`. Hay un test específico (7.7 y 7.8) que valida esto.
> - **NO uses `func.literal(...)`** — categories tuvo un bug por esto (sección 10 de su tasks.md). Si necesitás `literal`, importalo directo desde `sqlalchemy`. Ingredients no debería necesitarlo (no hay CTE).
> - **NO agregues guards en DELETE** — D4 explícito. El soft delete cumple US-014 sin necesidad de bloquear cuando hay productos asociados.
> - El conftest ya overridea `get_uow` para SQLite — los tests funcionan out-of-the-box.
