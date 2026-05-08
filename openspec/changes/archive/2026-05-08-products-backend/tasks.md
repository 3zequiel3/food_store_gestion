## 1. Migración Alembic — `es_removible`

- [x] 1.1 Editar `backend/features/products/models.py`: en la clase `ProductoIngrediente` agregar el atributo `es_removible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa.false())`. Importar `false` desde `sqlalchemy` si no está. Mantener el formato del archivo (líneas <80, docstring intacta).
- [x] 1.2 Verificar que `backend/alembic/env.py` línea 78 ya importa `backend.features.products.models` (debería estar — confirmar antes de generar la revisión).
- [x] 1.3 Generar revisión Alembic: `cd backend && alembic revision --autogenerate -m "add es_removible to product_ingredients"`. El archivo nuevo aparecerá en `backend/alembic/versions/`.
- [x] 1.4 Abrir el archivo generado y validar que:
  - `down_revision = '77bcb99d97db'` (la migración de refresh_tokens es el head actual).
  - El `upgrade()` contiene `op.add_column("product_ingredients", sa.Column("es_removible", sa.Boolean(), server_default=sa.false(), nullable=False))`.
  - El `downgrade()` contiene `op.drop_column("product_ingredients", "es_removible")`.
  - **Si autogenerate NO detectó el cambio** (a veces pasa con compare_server_default), escribir manualmente el upgrade/downgrade con el snippet del design D1.
- [x] 1.5 Aplicar la migración localmente contra Postgres dev: `alembic upgrade head`. Verificar con `psql foodstore_dev -c "\d product_ingredients"` que la columna existe con `boolean DEFAULT false NOT NULL`.
- [x] 1.6 Probar el rollback: `alembic downgrade -1`, verificar que la columna desaparece, luego `alembic upgrade head` para volver al estado actual.

## 2. Schemas Pydantic v2

- [x] 2.1 Crear el contenido de `backend/features/products/schemas.py` con imports: `from __future__ import annotations`, `from datetime import datetime`, `from decimal import Decimal`, `from pydantic import BaseModel, Field, ConfigDict`.
- [x] 2.2 Definir `ProductoCreate(BaseModel)` con campos:
  - `nombre: str = Field(..., min_length=1, max_length=255)`
  - `descripcion: str | None = None`
  - `precio: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)`
  - `stock_cantidad: int = Field(0, ge=0)`
  - `disponible: bool = True`
  - `imagen_url: str | None = Field(None, max_length=500)`
  - `categoria_ids: list[int] | None = None`
- [x] 2.3 Definir `ProductoUpdate(BaseModel)` con TODOS los campos como `... | None = None` excepto NO incluir `categoria_ids` (gestión de categorías va por endpoint dedicado). `precio: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)`. `stock_cantidad: int | None = Field(None, ge=0)`. Documentar en docstring que el service usa `model_dump(exclude_unset=True)`.
- [x] 2.4 Definir `ProductoRead(BaseModel)` con `model_config = ConfigDict(from_attributes=True)` y campos: `id`, `nombre`, `descripcion`, `precio: Decimal`, `stock_cantidad`, `disponible`, `imagen_url`, `creado_en`, `actualizado_en`.
- [x] 2.5 Definir `CategoriaRead(BaseModel)` (nested DTO local) con `id`, `nombre`, `padre_id` y `model_config = ConfigDict(from_attributes=True)`. **NO importar** desde `categories.schemas` para evitar acoplamiento — es un DTO de salida específico del producto.
- [x] 2.6 Definir `IngredienteAsociadoRead(BaseModel)` con `id`, `nombre`, `es_alergeno: bool`, `es_removible: bool`. SIN `from_attributes` porque se construye manualmente desde `tuple[Ingrediente, bool]` en el service.
- [x] 2.7 Definir `ProductoDetail(ProductoRead)` que extiende `ProductoRead` agregando `categorias: list[CategoriaRead]` e `ingredientes: list[IngredienteAsociadoRead]`. Mantener `model_config` heredado.
- [x] 2.8 Definir `PaginatedProductos(BaseModel)` con `items: list[ProductoRead]`, `total: int`, `page: int`, `limit: int`. Sin `model_config` adicional.
- [x] 2.9 Definir `PatchDisponibilidad(BaseModel)` con `disponible: bool`.
- [x] 2.10 Definir `PatchStock(BaseModel)` con `stock_cantidad: int = Field(..., ge=0)`.
- [x] 2.11 Definir `AsociarIngrediente(BaseModel)` con `ingrediente_id: int`, `es_removible: bool = False`.
- [x] 2.12 Definir `SetCategorias(BaseModel)` con `categoria_ids: list[int]`.

## 3. Repository

- [x] 3.1 Crear el contenido de `backend/features/products/repository.py` con imports: `from __future__ import annotations`, `from sqlalchemy import and_, exists, func, literal, select`, `from sqlalchemy.orm import Session, selectinload`, `from datetime import datetime, timezone`, `from backend.features.products.models import Producto, ProductoCategoria, ProductoIngrediente`, `from backend.features.catalog.models import Categoria, Ingrediente`, `from backend.shared.repository import BaseRepository`, `from backend.shared.exceptions import ConflictError`.
- [x] 3.2 Crear clase `ProductRepository(BaseRepository[Producto])` con `__init__(self, session: Session)` que llame `super().__init__(session, Producto)`.
- [x] 3.3 Implementar `find_by_nombre(self, nombre: str) -> Producto | None`:
  - Usa `_get_base_query()` (filtra `eliminado_en IS NULL`) + `.where(Producto.nombre == nombre)`.
  - Devuelve `scalar_one_or_none()`.
  - Documentar en docstring que está reservado para uso futuro (no hay UNIQUE en `products.nombre`).
- [x] 3.4 Implementar `list_paginated_with_filters(self, *, skip: int, limit: int, categoria_id: int | None = None, search: str | None = None, disponible: bool | None = None, excluir_alergenos: bool = False) -> tuple[list[Producto], int]`:
  - Empezar con `base = self._get_base_query()`.
  - Si `categoria_id is not None`: hacer `base = base.join(ProductoCategoria, and_(ProductoCategoria.product_id == Producto.id, ProductoCategoria.eliminado_en.is_(None), ProductoCategoria.category_id == categoria_id))`.
  - Si `search` (post-strip no vacío): `pattern = f"%{search.strip()}%"`; `base = base.where(func.lower(Producto.nombre).like(func.lower(pattern)))`. Usar `func.lower(...)` + `.like(...)` (NO `ilike` — incompat SQLite).
  - Si `disponible is not None`: `base = base.where(Producto.disponible == disponible)`.
  - Si `excluir_alergenos`: subquery `NOT EXISTS (SELECT 1 FROM product_ingredients pi JOIN ingredients i ON pi.ingredient_id = i.id WHERE pi.product_id = Producto.id AND pi.eliminado_en IS NULL AND i.eliminado_en IS NULL AND i.es_alergeno = true AND pi.es_removible = false)`. Construir con `~exists(...)` o `.where(not_(exists(...)))`.
  - Calcular total: `count_query = select(func.count()).select_from(base.subquery())` → `total = self.session.execute(count_query).scalar() or 0`.
  - Items: `items_query = base.order_by(Producto.nombre).offset(skip).limit(limit)`.
  - Ejecutar y devolver `(list(items), total)`.
- [x] 3.5 Implementar `get_with_associations(self, id: int) -> Producto | None`:
  - `query = self._get_base_query().where(Producto.id == id).options(selectinload(Producto.categorias), selectinload(Producto.ingredientes))`.
  - Devolver `scalar_one_or_none()`.
- [x] 3.6 Implementar `list_ingredientes(self, producto_id: int) -> list[tuple[Ingrediente, bool]]`:
  - `query = select(Ingrediente, ProductoIngrediente.es_removible).join(ProductoIngrediente, ProductoIngrediente.ingredient_id == Ingrediente.id).where(ProductoIngrediente.product_id == producto_id, ProductoIngrediente.eliminado_en.is_(None), Ingrediente.eliminado_en.is_(None))`.
  - Ejecutar `self.session.execute(query).all()`. Devolver `[(row[0], row[1]) for row in result]` (cada row es `Row(Ingrediente, bool)`).
- [x] 3.7 Implementar `replace_categorias(self, producto_id: int, categoria_ids: list[int]) -> None`:
  - `now = datetime.now(timezone.utc)`.
  - **Paso 1**: leer todas las pivot rows existentes (activas y soft-deleted) para `product_id == producto_id`: `existing = self.session.execute(select(ProductoCategoria).where(ProductoCategoria.product_id == producto_id)).scalars().all()`.
  - **Paso 2**: para cada existente con `category_id NOT IN categoria_ids` y `eliminado_en is None` → setear `eliminado_en = now` (soft delete).
  - **Paso 3**: para cada `cat_id` en `categoria_ids`:
    - Buscar match en `existing`: si existe activo → no hacer nada.
    - Si existe soft-deleted → reactivar (`eliminado_en = None`, actualizar `actualizado_en = now`).
    - Si no existe → INSERT `ProductoCategoria(product_id=producto_id, category_id=cat_id)`.
  - `self.session.flush()` al final. NO commit.
- [x] 3.8 Implementar `add_ingrediente(self, producto_id: int, ingrediente_id: int, es_removible: bool) -> ProductoIngrediente`:
  - Buscar pivot row existente (activa o soft-deleted): `existing = self.session.execute(select(ProductoIngrediente).where(ProductoIngrediente.product_id == producto_id, ProductoIngrediente.ingredient_id == ingrediente_id)).scalar_one_or_none()`.
  - Si existing y `eliminado_en is None` → raise `ConflictError("El ingrediente ya está asociado al producto")`.
  - Si existing y soft-deleted → reactivar: `existing.eliminado_en = None`, `existing.es_removible = es_removible`, `existing.actualizado_en = datetime.now(timezone.utc)`. `self.session.flush()`. Devolver `existing`.
  - Si no existing → INSERT `pi = ProductoIngrediente(product_id=producto_id, ingredient_id=ingrediente_id, es_removible=es_removible)`. `self.session.add(pi); self.session.flush()`. Devolver `pi`.
- [x] 3.9 Implementar `remove_ingrediente(self, producto_id: int, ingrediente_id: int) -> bool`:
  - Buscar pivot row activa: `query = select(ProductoIngrediente).where(ProductoIngrediente.product_id == producto_id, ProductoIngrediente.ingredient_id == ingrediente_id, ProductoIngrediente.eliminado_en.is_(None))`.
  - Si no encuentra → devolver `False`.
  - Si encuentra → `row.eliminado_en = datetime.now(timezone.utc)`, `self.session.flush()`. Devolver `True`.
- [x] 3.10 Verificar (lectura) que NO se sobrescriben `delete()`, `update()`, `read()`, `list()`, `_get_base_query()` — todos heredan de `BaseRepository`.
- [x] 3.11 NO usar `func.literal(...)` en ningún lado — usar `literal(...)` directo si hace falta. Anti-pattern documentado en categories tasks §10.

## 4. Service

- [x] 4.1 Crear el contenido de `backend/features/products/service.py` con imports: `UnitOfWork`, `ProductRepository`, `CategoryRepository` (`backend.features.categories.repository`), `IngredientRepository` (`backend.features.ingredients.repository`), excepciones tipadas (`NotFoundError`, `ConflictError`, `BusinessRuleError`) desde `backend.shared.exceptions`, los schemas, `from datetime import datetime, timezone`.
- [x] 4.2 Crear clase `ProductService` con `__init__(self, uow: UnitOfWork)`:
  - `uow.register_repository("productos", ProductRepository(uow.session))`
  - `uow.register_repository("categorias", CategoryRepository(uow.session))`
  - `uow.register_repository("ingredientes", IngredientRepository(uow.session))`
  - Guardar `self.uow`, `self.repo`, `self.cat_repo`, `self.ing_repo`.
- [x] 4.3 Implementar `create(self, payload: ProductoCreate) -> Producto`:
  - Trim nombre: `nombre = payload.nombre.strip()`. Si vacío → `BusinessRuleError("El nombre del producto no puede estar vacío")`.
  - Si `payload.categoria_ids is not None`: para cada id, llamar `self.cat_repo.read(id)` — si None → `BusinessRuleError(f"Categoría {id} no encontrada")`.
  - Crear producto via `self.repo.create(nombre=nombre, descripcion=payload.descripcion, precio=payload.precio, stock_cantidad=payload.stock_cantidad, disponible=payload.disponible, imagen_url=payload.imagen_url)`.
  - Si `payload.categoria_ids is not None`: `self.repo.replace_categorias(producto.id, payload.categoria_ids)`.
  - Devolver el producto.
- [x] 4.4 Implementar `get_by_id(self, producto_id: int) -> Producto`:
  - `current = self.repo.read(producto_id)`. Si None → `NotFoundError("Producto no encontrado")`.
  - Devolver.
- [x] 4.5 Implementar `get_detail(self, producto_id: int) -> tuple[Producto, list[Categoria], list[tuple[Ingrediente, bool]]]`:
  - `producto = self.repo.get_with_associations(producto_id)`. Si None → `NotFoundError("Producto no encontrado")`.
  - `categorias = list(producto.categorias)` — filtrar las que tienen `eliminado_en IS NULL` (defensivo, las relaciones no filtran soft-delete).
  - `ingredientes_with_flag = self.repo.list_ingredientes(producto_id)`.
  - Devolver `(producto, categorias, ingredientes_with_flag)`.
- [x] 4.6 Implementar `list_paginated(self, *, page: int, limit: int, categoria_id: int | None, search: str | None, disponible: bool | None, excluir_alergenos: bool) -> tuple[list[Producto], int]`:
  - `skip = (page - 1) * limit`.
  - Llamar `self.repo.list_paginated_with_filters(skip=skip, limit=limit, categoria_id=categoria_id, search=search, disponible=disponible, excluir_alergenos=excluir_alergenos)`.
  - Devolver el tuple.
- [x] 4.7 Implementar `update(self, producto_id: int, payload: ProductoUpdate) -> Producto`:
  - `current = self.repo.read(producto_id)`. Si None → `NotFoundError`.
  - `data = payload.model_dump(exclude_unset=True)`.
  - Si `"nombre" in data`: trim, si vacío → `BusinessRuleError`.
  - Aplicar `return self.repo.update(producto_id, **data)`.
- [x] 4.8 Implementar `set_disponibilidad(self, producto_id: int, disponible: bool) -> Producto`:
  - `current = self.repo.read(producto_id)`. Si None → `NotFoundError`.
  - `return self.repo.update(producto_id, disponible=disponible)`.
- [x] 4.9 Implementar `set_stock(self, producto_id: int, stock_cantidad: int) -> Producto`:
  - Si `stock_cantidad < 0` → `BusinessRuleError("El stock no puede ser negativo")`. (Pydantic ya valida en el schema, pero defensivo.)
  - `current = self.repo.read(producto_id)`. Si None → `NotFoundError`.
  - `return self.repo.update(producto_id, stock_cantidad=stock_cantidad)`.
- [x] 4.10 Implementar `delete(self, producto_id: int) -> None`:
  - `current = self.repo.read(producto_id)`. Si None → `NotFoundError`.
  - `self.repo.delete(producto_id)` (soft delete heredado). **Sin guards** — D11 del design.
- [x] 4.11 Implementar `set_categorias(self, producto_id: int, categoria_ids: list[int]) -> None`:
  - `current = self.repo.read(producto_id)`. Si None → `NotFoundError`.
  - **Validar TODAS las categorías ANTES de tocar pivots**: para cada id en `categoria_ids`, `self.cat_repo.read(id)`. Si alguno None → `BusinessRuleError(f"Categoría {id} no encontrada")`. NO modificar nada hasta validar todas.
  - `self.repo.replace_categorias(producto_id, categoria_ids)`.
- [x] 4.12 Implementar `add_ingrediente(self, producto_id: int, ingrediente_id: int, es_removible: bool) -> ProductoIngrediente`:
  - `producto = self.repo.read(producto_id)`. Si None → `NotFoundError("Producto no encontrado")`.
  - `ingrediente = self.ing_repo.read(ingrediente_id)`. Si None → `BusinessRuleError(f"Ingrediente {ingrediente_id} no encontrado")`.
  - `return self.repo.add_ingrediente(producto_id, ingrediente_id, es_removible)` — el repo levanta `ConflictError` si ya está activo.
- [x] 4.13 Implementar `remove_ingrediente(self, producto_id: int, ingrediente_id: int) -> None`:
  - `producto = self.repo.read(producto_id)`. Si None → `NotFoundError("Producto no encontrado")`.
  - `removed = self.repo.remove_ingrediente(producto_id, ingrediente_id)`. Si False → `NotFoundError("Asociación de ingrediente no encontrada")`.
- [x] 4.14 Implementar `list_ingredientes(self, producto_id: int) -> list[tuple[Ingrediente, bool]]`:
  - `producto = self.repo.read(producto_id)`. Si None → `NotFoundError("Producto no encontrado")`.
  - `return self.repo.list_ingredientes(producto_id)`.
- [x] 4.15 Verificar (lectura) que NINGÚN método llama `uow.commit()` ni `session.commit()`. Commit es responsabilidad del router (D6 del design).

## 5. Router — 11 endpoints

- [x] 5.1 Reemplazar completamente `backend/features/products/router.py` (el stub actual de 39 líneas se descarta). Imports: `APIRouter`, `Depends`, `Query`, `Response`, `status` de fastapi; `UnitOfWork` de `backend.shared.unit_of_work`; `get_uow` de `backend.dependencies`; `require_role` de `backend.features.auth.dependencies`; los schemas; `ProductService`. Crear `router = APIRouter()`.

### 5.1 Endpoints producto base (CRUD + PATCHes + DELETE)

- [x] 5.2 Implementar `POST /` (crear producto) con `response_model=ProductoRead, status_code=201`:
  - Deps: `payload: ProductoCreate`, `uow: UnitOfWork = Depends(get_uow)`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - `service = ProductService(uow); producto = service.create(payload); uow.commit(); return ProductoRead.model_validate(producto)`.
- [x] 5.3 Implementar `GET /` (listar paginado) con `response_model=PaginatedProductos` (público):
  - Query params: `page: int = Query(1, ge=1)`, `limit: int = Query(20, ge=1, le=100)`, `categoria_id: int | None = Query(None)`, `search: str | None = Query(None)`, `disponible: bool | None = Query(None)`, `excluir_alergenos: bool = Query(False)`.
  - Dep: `uow: UnitOfWork = Depends(get_uow)`.
  - **Default de `disponible`**: si `disponible is None`, asignar `disponible = True` ANTES de pasar al service (RN-CA08, default público). Documentar en docstring.
  - Llamar `items, total = service.list_paginated(...)`. Retornar `PaginatedProductos(items=[ProductoRead.model_validate(p) for p in items], total=total, page=page, limit=limit)`.
- [x] 5.4 Implementar `GET /{producto_id}` (detalle) con `response_model=ProductoDetail` (público):
  - Dep: `producto_id: int`, `uow`.
  - Llamar `producto, categorias, ingredientes_with_flag = service.get_detail(producto_id)`.
  - Construir `ProductoDetail` manualmente:
    ```python
    return ProductoDetail(
        id=producto.id, nombre=producto.nombre, descripcion=producto.descripcion,
        precio=producto.precio, stock_cantidad=producto.stock_cantidad,
        disponible=producto.disponible, imagen_url=producto.imagen_url,
        creado_en=producto.creado_en, actualizado_en=producto.actualizado_en,
        categorias=[CategoriaRead.model_validate(c) for c in categorias],
        ingredientes=[IngredienteAsociadoRead(id=i.id, nombre=i.nombre, es_alergeno=i.es_alergeno, es_removible=removible) for (i, removible) in ingredientes_with_flag],
    )
    ```
- [x] 5.5 Implementar `PUT /{producto_id}` (update) con `response_model=ProductoRead`:
  - Deps: `producto_id: int`, `payload: ProductoUpdate`, `uow`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - `producto = service.update(producto_id, payload); uow.commit(); return ProductoRead.model_validate(producto)`.
- [x] 5.6 Implementar `PATCH /{producto_id}/disponibilidad` con `response_model=ProductoRead`:
  - Deps: `producto_id: int`, `payload: PatchDisponibilidad`, `uow`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - `producto = service.set_disponibilidad(producto_id, payload.disponible); uow.commit(); return ProductoRead.model_validate(producto)`.
- [x] 5.7 Implementar `PATCH /{producto_id}/stock` con `response_model=ProductoRead`:
  - Deps: `producto_id: int`, `payload: PatchStock`, `uow`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - `producto = service.set_stock(producto_id, payload.stock_cantidad); uow.commit(); return ProductoRead.model_validate(producto)`.
- [x] 5.8 Implementar `DELETE /{producto_id}` con `status_code=204`:
  - Deps: `producto_id: int`, `uow`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - `service.delete(producto_id); uow.commit(); return Response(status_code=status.HTTP_204_NO_CONTENT)`.

### 5.2 Endpoint de categorías M:N

- [x] 5.9 Implementar `PUT /{producto_id}/categorias` con `response_model=ProductoDetail`:
  - Deps: `producto_id: int`, `payload: SetCategorias`, `uow`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - `service.set_categorias(producto_id, payload.categoria_ids); uow.commit()`.
  - Re-leer detail: `producto, categorias, ingredientes = service.get_detail(producto_id)` — devolver `ProductoDetail` con asociaciones actualizadas (igual que 5.4).

### 5.3 Endpoints de ingredientes M:N

- [x] 5.10 Implementar `GET /{producto_id}/ingredientes` con `response_model=list[IngredienteAsociadoRead]` (público):
  - Dep: `producto_id: int`, `uow`.
  - `result = service.list_ingredientes(producto_id)`.
  - Retornar `[IngredienteAsociadoRead(id=i.id, nombre=i.nombre, es_alergeno=i.es_alergeno, es_removible=rem) for (i, rem) in result]`.
- [x] 5.11 Implementar `POST /{producto_id}/ingredientes` con `response_model=IngredienteAsociadoRead, status_code=201`:
  - Deps: `producto_id: int`, `payload: AsociarIngrediente`, `uow`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - `pi = service.add_ingrediente(producto_id, payload.ingrediente_id, payload.es_removible); uow.commit()`.
  - Re-leer el ingrediente para construir el response: `ingrediente = ing_repo.read(payload.ingrediente_id)` — pero NO tenemos `ing_repo` directo en el router. Solución: el service devuelve la `ProductoIngrediente` y el router accede a `pi.ingredient_id`. Para evitar segunda query, modificar el service para devolver `tuple[ProductoIngrediente, Ingrediente]` en `add_ingrediente`. Documentar este pequeño cambio en el design D11. **Alternativa más simple**: el router llama `service.list_ingredientes(producto_id)` después del commit y filtra por `ingrediente_id`. Aceptable porque el endpoint es admin (low traffic).
  - Decisión recomendada: usar la alternativa simple (re-leer y filtrar) para no romper la signatura del service.
- [x] 5.12 Implementar `DELETE /{producto_id}/ingredientes/{ingrediente_id}` con `status_code=204`:
  - Deps: `producto_id: int`, `ingrediente_id: int`, `uow`, `_user=Depends(require_role("ADMIN", "STOCK"))`.
  - `service.remove_ingrediente(producto_id, ingrediente_id); uow.commit(); return Response(status_code=status.HTTP_204_NO_CONTENT)`.

### 5.4 Verificación general del router

- [x] 5.13 Verificar (lectura) que NINGÚN endpoint levanta `HTTPException` directamente — todos los errores vienen del service vía exceptions tipadas.
- [x] 5.14 Verificar que cada endpoint público (GETs y `GET /{id}/ingredientes`) NO tiene `Depends(require_role(...))`.
- [x] 5.15 Verificar que cada mutation tiene `Depends(require_role("ADMIN", "STOCK"))` y hace `uow.commit()` después del service call.

## 6. Wiring en main.py

- [x] 6.1 Modificar `backend/main.py` línea 197: cambiar `prefix="/api/v1/products"` a `prefix="/api/v1/productos"`. Mantener `tags=["products"]` (el tag interno OpenAPI sigue en inglés porque es el nombre del módulo).
- [x] 6.2 Verificar (lectura) que el import `from backend.features.products.router import router as products_router` (línea 68) sigue intacto.
- [x] 6.3 NO tocar el orden de los `include_router` — el cambio es solo de prefix.

## 7. Tests de integración

- [x] 7.1 Crear `backend/tests/integration/test_products.py` reusando las fixtures `admin_user`, `stock_user`, `client_user`, `_admin_headers`, `_stock_headers`, `_client_headers` del conftest (las mismas que `test_categories.py` y `test_ingredients.py`).

### 7.1 Helpers de fixtures de productos

- [x] 7.2 Helper `_create_product(client, headers, **overrides)` que hace POST con defaults razonables (`nombre="P-{uuid}"`, `precio=10.00`, `stock_cantidad=20`, `disponible=True`) y devuelve el response body. Usar para tests que necesitan productos pre-existentes.
- [x] 7.3 Helper `_create_categoria(session, nombre="Cat-X")` y `_create_ingrediente(session, nombre="Ing-X", es_alergeno=False)` para insertar directo via session (bypassing API) cuando se necesitan dependencias.

### 7.2 CRUD básico

- [x] 7.4 Test: `test_create_as_admin` — POST con payload mínimo → 201 con body correcto.
- [x] 7.5 Test: `test_create_as_stock` — POST con stock como STOCK → 201.
- [x] 7.6 Test: `test_create_with_categoria_ids` — crear 2 categorías, POST con `categoria_ids: [1,2]` → 201 + verificar via SQL que existen 2 rows en `product_categories`.
- [x] 7.7 Test: `test_create_with_empty_categoria_ids` — POST con `categoria_ids: []` → 201 + 0 rows en pivote.
- [x] 7.8 Test: `test_create_categoria_inexistente_returns_422` — POST con `categoria_ids: [99999]` → 422 con `BusinessRuleError` y producto NO creado (verificar via SQL).
- [x] 7.9 Test: `test_create_precio_zero_returns_422` — POST con `precio: 0` → 422.
- [x] 7.10 Test: `test_create_precio_negative_returns_422` — POST con `precio: -1` → 422.
- [x] 7.11 Test: `test_create_stock_negative_returns_422` — POST con `stock_cantidad: -1` → 422.
- [x] 7.12 Test: `test_create_nombre_empty_returns_422` — POST con `nombre: ""` → 422.
- [x] 7.13 Test: `test_create_nombre_too_long_returns_422` — POST con nombre 256 chars → 422.
- [x] 7.14 Test: `test_create_imagen_url_too_long_returns_422` — POST con `imagen_url` 501 chars → 422.
- [x] 7.15 Test: `test_get_by_id_returns_detail` — crear, GET por id → 200 con `categorias` e `ingredientes` arrays presentes.
- [x] 7.16 Test: `test_get_by_id_not_found` — GET id inexistente → 404.
- [x] 7.17 Test: `test_get_by_id_soft_deleted_returns_404` — soft-deletear, GET → 404.
- [x] 7.18 Test: `test_update_nombre_only` — PUT con solo `{"nombre": "X"}` → 200, otros campos preservados.
- [x] 7.19 Test: `test_update_precio_only` — PUT con solo `{"precio": 15.50}` → 200.
- [x] 7.20 Test: `test_update_precio_zero_returns_422` — PUT con `precio: 0` → 422.
- [x] 7.21 Test: `test_update_stock_negative_returns_422` — PUT con `stock_cantidad: -1` → 422.
- [x] 7.22 Test: `test_update_not_found_returns_404` — PUT id inexistente → 404.
- [x] 7.23 Test: `test_update_soft_deleted_returns_404` — soft-deletear, PUT → 404.
- [x] 7.24 Test: `test_patch_disponibilidad_to_false` — PATCH `/disponibilidad` con `false` → 200, `disponible: false`. Luego `GET /` (default) NO incluye el producto.
- [x] 7.25 Test: `test_patch_disponibilidad_to_true` — toggle de vuelta → 200 + visible.
- [x] 7.26 Test: `test_patch_stock_set_value` — PATCH `/stock` con `{stock_cantidad: 50}` → 200, valor exacto.
- [x] 7.27 Test: `test_patch_stock_zero` — PATCH con `0` → 200.
- [x] 7.28 Test: `test_patch_stock_negative_returns_422` — PATCH con `-1` → 422.
- [x] 7.29 Test: `test_delete_soft` — DELETE → 204, fila persiste con `eliminado_en NOT NULL` (verificar via SQL directa).
- [x] 7.30 Test: `test_delete_already_deleted_returns_404` — DELETE 2 veces → 2da vez 404.
- [x] 7.31 Test: `test_delete_not_found_returns_404` — DELETE id inexistente → 404.
- [x] 7.32 Test: `test_delete_does_not_cascade_to_pivots` — crear producto + categoría + asociación, DELETE producto → 204 + verificar que la fila en `product_categories` sigue intacta (la pivote no se modifica).

### 7.3 RBAC

- [x] 7.33 Test: `test_post_unauthenticated_returns_401`.
- [x] 7.34 Test: `test_post_as_client_returns_403`.
- [x] 7.35 Test: `test_put_unauthenticated_returns_401`.
- [x] 7.36 Test: `test_put_as_client_returns_403`.
- [x] 7.37 Test: `test_patch_disponibilidad_unauthenticated_returns_401`.
- [x] 7.38 Test: `test_patch_disponibilidad_as_client_returns_403`.
- [x] 7.39 Test: `test_patch_stock_unauthenticated_returns_401`.
- [x] 7.40 Test: `test_patch_stock_as_client_returns_403`.
- [x] 7.41 Test: `test_delete_unauthenticated_returns_401`.
- [x] 7.42 Test: `test_delete_as_client_returns_403`.
- [x] 7.43 Test: `test_get_list_is_public` — GET sin token → 200.
- [x] 7.44 Test: `test_get_by_id_is_public` — GET sin token → 200.
- [x] 7.45 Test: `test_get_ingredientes_is_public` — GET `/ingredientes` sin token → 200.
- [x] 7.46 Test: `test_put_categorias_unauthenticated_returns_401`.
- [x] 7.47 Test: `test_put_categorias_as_client_returns_403`.
- [x] 7.48 Test: `test_post_ingredientes_unauthenticated_returns_401`.
- [x] 7.49 Test: `test_post_ingredientes_as_client_returns_403`.
- [x] 7.50 Test: `test_delete_ingrediente_unauthenticated_returns_401`.
- [x] 7.51 Test: `test_delete_ingrediente_as_client_returns_403`.

### 7.4 Filtros de catálogo público

- [x] 7.52 Test: `test_list_default_excludes_unavailable` — crear 3 disponibles + 2 no-disponibles, GET → `total=3`.
- [x] 7.53 Test: `test_list_filter_disponible_false_explicit` — GET `?disponible=false` → `total=2`.
- [x] 7.54 Test: `test_list_filter_categoria_id` — crear 3 productos, asociar 1 a cat 5, GET `?categoria_id=5` → 1 item.
- [x] 7.55 Test: `test_list_filter_search_case_insensitive` — productos "Pizza Margherita", "Pizza Napolitana", "Hamburguesa", GET `?search=PIZZA` → 2 items.
- [x] 7.56 Test: `test_list_filter_search_substring` — productos "Pizza Especial", "Especial del día", GET `?search=especial` → 2 items.
- [x] 7.57 Test: `test_list_filter_search_no_match` — GET `?search=zzzzzz` → 0 items.
- [x] 7.58 Test: `test_list_filter_excluir_alergenos_with_non_removable` — crear producto P1 con ingrediente alergénico no removible (`es_removible=false`), P2 sin alérgenos. GET `?excluir_alergenos=true` → solo P2.
- [x] 7.59 Test: `test_list_filter_excluir_alergenos_with_removable` — crear producto P1 con ingrediente alergénico **removible** (`es_removible=true`). GET `?excluir_alergenos=true` → P1 SÍ aparece (es removible).
- [x] 7.60 Test: `test_list_filter_excluir_alergenos_default_false` — GET sin el param → comportamiento default (no filtra alérgenos).
- [x] 7.61 Test: `test_list_combined_filters` — crear setup complejo, GET con `categoria_id` + `search` + `disponible` + `excluir_alergenos` → resultado correcto.
- [x] 7.62 Test: `test_list_pagination_default` — crear 25, GET → `items.length=20, total=25, page=1, limit=20`.
- [x] 7.63 Test: `test_list_pagination_page_2` — crear 25, GET `?page=2` → `items.length=5, page=2`.
- [x] 7.64 Test: `test_list_pagination_limit` — GET `?limit=5` → `items.length=5`.
- [x] 7.65 Test: `test_list_pagination_limit_above_100_returns_422`.
- [x] 7.66 Test: `test_list_pagination_page_zero_returns_422`.
- [x] 7.67 Test: `test_list_excludes_soft_deleted` — crear 3, soft-deletear 1, GET → `total=2`.

### 7.5 Asociaciones M:N de categorías

- [x] 7.68 Test: `test_put_categorias_replaces_set` — crear producto asociado a [1,2], PUT `/categorias` con `[2,3]` → 200, asociaciones finales [2,3].
- [x] 7.69 Test: `test_put_categorias_empty_removes_all` — PUT con `[]` → 200, sin asociaciones.
- [x] 7.70 Test: `test_put_categorias_inexistente_returns_422_no_partial_changes` — PUT con `[1, 99999]` → 422, asociación previa intacta.
- [x] 7.71 Test: `test_put_categorias_reactivates_soft_deleted` — crear producto, asociar, soft-deletear pivote manualmente, PUT con esa misma cat_id → 200, pivote reactivada (no duplicada).
- [x] 7.72 Test: `test_put_categorias_not_found_returns_404`.

### 7.6 Asociaciones M:N de ingredientes

- [x] 7.73 Test: `test_post_ingrediente_happy_path` — POST con `{ingrediente_id: 10, es_removible: true}` → 201 con flag.
- [x] 7.74 Test: `test_post_ingrediente_default_es_removible_false` — POST sin el flag → 201 con `false`.
- [x] 7.75 Test: `test_post_ingrediente_duplicate_returns_409` — POST 2 veces → 2da 409.
- [x] 7.76 Test: `test_post_ingrediente_inexistente_returns_422`.
- [x] 7.77 Test: `test_post_ingrediente_reactivates_soft_deleted` — asociar, eliminar, asociar de nuevo con `es_removible` distinto → 201 + flag actualizado, fila reutilizada (verificar via SQL conteo de filas pivote).
- [x] 7.78 Test: `test_delete_ingrediente_happy_path` — DELETE → 204, fila pivote con `eliminado_en NOT NULL`.
- [x] 7.79 Test: `test_delete_ingrediente_already_deleted_returns_404`.
- [x] 7.80 Test: `test_delete_ingrediente_not_associated_returns_404`.
- [x] 7.81 Test: `test_delete_ingrediente_does_not_modify_ingredient_row` — DELETE asociación → fila en `ingredients` intacta.
- [x] 7.82 Test: `test_get_ingredientes_returns_flag` — asociar 2 ingredientes con flags distintos, GET → ambos con `es_removible` correcto.
- [x] 7.83 Test: `test_get_ingredientes_excludes_soft_deleted_pivot`.
- [x] 7.84 Test: `test_get_ingredientes_excludes_soft_deleted_ingredient`.
- [x] 7.85 Test: `test_get_ingredientes_empty_when_no_associations` → 200 + `[]`.
- [x] 7.86 Test: `test_get_ingredientes_product_not_found_returns_404`.

### 7.7 Routing

- [x] 7.87 Test: `test_endpoint_responds_at_productos_es` — GET `/api/v1/productos` → 200.
- [x] 7.88 Test: `test_endpoint_does_not_respond_at_products_en` — GET `/api/v1/products` → 404.
- [x] 7.89 Test: `test_endpoint_does_not_respond_without_v1_prefix` — GET `/api/productos` → 404.

### 7.8 Precision Decimal y migración

- [x] 7.90 Test: `test_precio_preserves_decimal_precision` — POST con `precio: 19.99`, GET → response trae exactamente `19.99` (no `19.989...` ni `19.99000...`). Comparar con `Decimal("19.99")`.
- [x] 7.91 Test: `test_es_removible_column_exists_in_pivot` — usar `inspect(engine).get_columns("product_ingredients")` para verificar que `es_removible` existe con tipo Boolean y default false.
- [x] 7.92 Test: `test_es_removible_default_false_on_insert` — INSERT directo en `product_ingredients` sin pasar `es_removible` → fila con `es_removible: false` (server_default).

## 8. Documentación y wrap-up

- [x] 8.1 Crear `backend/features/products/README.md` (10-15 líneas) describiendo el módulo, los 11 endpoints agrupados (CRUD producto / pivots de categorías / pivots de ingredientes / patches / migración nueva), el patrón UoW y los filtros del catálogo. Incluir 2 ejemplos de curl: POST con `categoria_ids` + GET con todos los filtros combinados.
- [x] 8.2 Verificar manualmente con `pytest backend/tests/integration/test_products.py -v` que TODOS los tests pasan. NO ejecutar build, solo el suite específico.
- [x] 8.3 Mostrar resumen al usuario: archivos creados, paths exactos, link a `list_paginated_with_filters` en `repository.py`, link a la migración nueva. ESPERAR REVISIÓN HUMANA antes de cualquier `/opsx:archive`.

## 9. Notas de implementación

> **Recordatorios para el apply-agent:**
>
> - **Regla de oro de imports**: `Router → Service → UoW → Repository → Model`. Verificar que `repository.py` no importa nada de `service.py` ni `router.py`. El service importa `CategoryRepository` e `IngredientRepository` directamente (NO sus services).
> - **El service NUNCA hace `uow.commit()`**. El router lo decide.
> - **El soft delete usa `eliminado_en = datetime.now(timezone.utc)`**, NUNCA `session.delete()`. Aplica al producto Y a las pivotes.
> - **NO usar `func.literal(...)`** — usar `literal(...)` directo desde `sqlalchemy`. Bug histórico de categories tasks §10.
> - **`func.lower(...)` + `.like(...)` en lugar de `ilike(...)`** para que los tests con SQLite in-memory funcionen.
> - **`model_dump(exclude_unset=True)` en `update`** es CRÍTICO para preservar campos no enviados. Hay tests específicos (7.18-7.19, 7.27).
> - **`Decimal` en schemas de precio**, NO `float`. Test 7.90 valida la precisión.
> - **Validación de FKs ANTES de mutar**: `set_categorias` valida TODOS los ids antes de tocar pivots. Si uno falla → 422 sin cambios parciales (test 7.70).
> - **`replace_categorias` reactiva soft-deleted en lugar de duplicar** (test 7.71). Esta es la lógica más sutil del módulo.
> - **`add_ingrediente` reactiva soft-deleted con flag actualizado** (test 7.77). Misma lógica.
> - **Default de `disponible` en GET /**: si no se pasa el query param → service recibe `True` (RN-CA08). El router hace el default, NO el service.
> - **El cambio de prefix `/products` → `/productos`** afecta solo a `main.py` línea 197. Nada más cambia en main.
> - **Migración Alembic**: si autogenerate no detecta el cambio (raro pero posible), escribir `upgrade`/`downgrade` a mano siguiendo el snippet de design D1.
> - **`server_default=sa.false()`** en el modelo ORM matchea la migración para que SQLAlchemy no marque drift al comparar con la DB.
> - **`inspect(engine)`** para el test 7.91: importar de `sqlalchemy.inspection` o usar `inspect(uow.session.bind)` desde un fixture.
