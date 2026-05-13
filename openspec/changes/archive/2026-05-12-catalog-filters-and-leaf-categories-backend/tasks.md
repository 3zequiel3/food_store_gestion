> **Modo TDD**: si `sdd-init` cacheó `strict_tdd: true` para `food_store_gestion`, cada feature de las secciones 1–8 sigue red-green-refactor: **primero** test failing, **después** implementación. Para features con repositorio + service + router, el orden mínimo de tests es: (a) repo unit/integration → (b) service unit → (c) router integration.

## 1. Filtro recursivo de `categoria_id` en `GET /productos`

- [x] 1.1 Test integración: producto asignado a categoría nieta (3 niveles) aparece al filtrar por la raíz. Confirmar que es bug-reproducer del estado actual.
- [x] 1.2 Test integración: producto en categoría hermana NO aparece al filtrar por una rama distinta.
- [x] 1.3 Test integración: categoría descendiente soft-deleted se excluye del subtree (sus productos no aparecen).
- [x] 1.4 Refactor `ProductRepository.list_paginated_with_filters`: cuando `categoria_id is not None`, usar CTE recursiva (`select(cat.c.id).where(cat.c.id == categoria_id).cte(recursive=True).union_all(...)`) en lugar del JOIN directo por ID exacto.
- [x] 1.5 Verificar que los tests originales del filtro por categoría (sprint 3) siguen pasando.

## 2. Exclusión granular de alérgenos (`excluir_alergeno_ids`)

- [x] 2.1 Test integración: producto con ingrediente 50 (es_removible=false) se excluye con `?excluir_alergeno_ids=50`.
- [x] 2.2 Test integración: producto con ingrediente 50 (es_removible=true) NO se excluye con `?excluir_alergeno_ids=50`.
- [x] 2.3 Test integración: lista vacía o param omitido = no-op (mismo total que sin filtro).
- [x] 2.4 Test integración: combinación `excluir_alergenos=true&excluir_alergeno_ids=50` aplica AND (filtra por ambos criterios).
- [x] 2.5 Agregar `excluir_alergeno_ids: list[int] = Query(default=[])` al router `listar_productos` y propagarlo por service hasta repository.
- [x] 2.6 En `ProductRepository.list_paginated_with_filters`, agregar bloque NOT EXISTS análogo al de `excluir_alergenos` pero filtrando `pi.ingredient_id.in_(excluir_alergeno_ids)` (sin requerir `es_alergeno=true`).
- [x] 2.7 Smoke test contra OpenAPI generado: el param aparece como `array of integer` repetible.

## 3. Helper leaf-only validation en `ProductService`

- [x] 3.1 Test unit: `_validate_categorias_are_leaves([leaf_id])` no raisea.
- [x] 3.2 Test unit: `_validate_categorias_are_leaves([non_leaf_id])` raisea `BusinessRuleError` con mensaje que contiene el nombre de la categoría y los nombres de sus hijas activas.
- [x] 3.3 Test unit: mezcla de leaf + non-leaf reportar TODAS las non-leaf en un solo error.
- [x] 3.4 Test unit: hija soft-deleted no rompe el leaf-check (categoría con solo hijas soft-deleted cuenta como hoja).
- [x] 3.5 Test unit: lista vacía no dispara query.
- [x] 3.6 Implementar `ProductService._validate_categorias_are_leaves(categoria_ids, session)` con una sola query bulk: `select(Categoria.padre_id, Categoria.nombre).where(Categoria.padre_id.in_(categoria_ids), Categoria.eliminado_en.is_(None))`. Si rows → recolectar nombres del padre (otra query simple por los IDs ofensores) y armar mensaje en Rioplatense.
- [x] 3.7 Invocar el helper en `ProductService.create()` tras la validación de existencia y antes de `replace_categorias`.
- [x] 3.8 Invocar el helper en `ProductService.set_categorias()` tras la validación de existencia y antes de `replace_categorias`.
- [x] 3.9 Test integración: `POST /productos` con categoría no-hoja → 422 con detalle accionable.
- [x] 3.10 Test integración: `PUT /productos/{id}/categorias` con categoría no-hoja → 422 sin mutación de pivot rows (verificar count antes/después).

## 4. Hook auto-`disponible=false`

- [x] 4.1 Test unit: `count_leaf_active_categories(product_id)` devuelve 0 cuando el producto no tiene asociaciones activas.
- [x] 4.2 Test unit: cuenta 1 cuando el producto está asignado a una categoría hoja activa.
- [x] 4.3 Test unit: cuenta 0 cuando la única asociación es a una categoría soft-deleted (no debería pasar porque `replace_categorias` no mete asociaciones a soft-deleted, pero defensa en profundidad).
- [x] 4.4 Test unit: `_auto_disable_if_no_leaf_categoria` con count=0 setea `disponible=false` y emite log INFO con template exacto "Producto {id} desactivado: sin categoría hoja activa".
- [x] 4.5 Test unit: hook con count>0 no muta ni loguea.
- [x] 4.6 Test unit: hook NO re-habilita un producto con `disponible=false` cuando count>0 (sin auto-enable).
- [x] 4.7 Implementar `ProductRepository.count_leaf_active_categories(product_id) -> int` con NOT EXISTS antijoin (ver design.md §D4).
- [x] 4.8 Implementar `ProductService._auto_disable_if_no_leaf_categoria(product_id, session)` que invoca el repo, hace `repo.update(product_id, disponible=False)` si count==0, y emite log con `logger.info(...)`.
- [x] 4.9 Invocar el hook desde `ProductService.create()` tras `replace_categorias` (solo si `categoria_ids` fue provisto explícitamente).
- [x] 4.10 Invocar el hook desde `ProductService.set_categorias()` tras `replace_categorias`.
- [x] 4.11 Test integración: `POST /productos` con `categoria_ids: []` → 201 con `disponible: false` aunque el payload diga `disponible: true`.
- [x] 4.12 Test integración: `PUT /productos/{id}/categorias` con `[]` sobre un producto con `disponible: true` y categoría asignada → 200 con `disponible: false`.

## 5. Filtro `sin_categoria=true` en `GET /productos`

- [x] 5.1 Test integración: producto sin asociaciones activas aparece con `?sin_categoria=true&disponible=false` (override default disponible).
- [x] 5.2 Test integración: producto con asociación soft-deleted (sin activas) también aparece.
- [x] 5.3 Test integración: producto con al menos 1 asociación activa NO aparece con `sin_categoria=true`.
- [x] 5.4 Test integración: `sin_categoria=false` (default) es no-op (mismo resultado que sin el param).
- [x] 5.5 Agregar `sin_categoria: bool = Query(False)` al router `listar_productos` y propagarlo al service y repository.
- [x] 5.6 En `ProductRepository.list_paginated_with_filters`, si `sin_categoria` → agregar `~exists(select(ProductoCategoria.product_id).where(ProductoCategoria.product_id == Producto.id, ProductoCategoria.eliminado_en.is_(None)))`.

## 6. Guard block-on-promote en `CategoryService.create()`

- [x] 6.1 Test unit: `create({nombre: "Gaseosas", padre_id: 5})` cuando categoría 5 tiene 0 productos activos → exitosa.
- [x] 6.2 Test unit: idem cuando categoría 5 tiene 3 productos activos → `BusinessRuleError` con detalle conteniendo "Bebidas", "3", y la palabra "subcategoría" o "subcategorizar".
- [x] 6.3 Test unit: categoría 5 con 2 productos pero ambos soft-deleted → exitosa (no bloquea).
- [x] 6.4 Test unit: categoría 5 con 1 pivot row soft-deleted apuntando a producto activo → exitosa (el pivot row inactivo no cuenta).
- [x] 6.5 Implementar el guard en `CategoryService.create()` ANTES de `repo.create()`. Reusar `repo.has_active_products(padre_id)` (ya existe en `CategoryRepository`) extendido para devolver el count en vez de bool, o agregar `count_active_products(categoria_id) -> int` si el detalle requiere el número en el mensaje.
- [x] 6.6 Test integración: `POST /categorias` con `padre_id` apuntando a categoría con productos → 422.

## 7. `GET /categorias?solo_hojas=true`

- [x] 7.1 Test unit: `CategoryRepository.list_leaf_categories()` devuelve categorías sin hijas activas, ordenadas por nombre.
- [x] 7.2 Test unit: categoría soft-deleted no aparece.
- [x] 7.3 Test unit: categoría con única hija soft-deleted SÍ aparece (es hoja efectiva).
- [x] 7.4 Test unit: tabla vacía → `[]`.
- [x] 7.5 Implementar `CategoryRepository.list_leaf_categories() -> list[Categoria]` con NOT EXISTS antijoin contra `categories` self-ref por `padre_id`, filtrando `eliminado_en IS NULL` en ambos lados, ordenado por `nombre` asc.
- [x] 7.6 Agregar método `CategoryService.list_leaves() -> list[CategoriaRead]` que invoca el repo dentro de un UoW y devuelve el resultado plano.
- [x] 7.7 Agregar query param `solo_hojas: bool = False` al router `listar_categorias`. Si `True`, llamar `service.list_leaves()` y devolver `list[CategoriaRead]`; si `False`, mantener comportamiento actual (`service.get_tree()` → `list[CategoriaTreeNode]`). Ajustar `response_model` para soportar ambos (`response_model=Union[list[CategoriaRead], list[CategoriaTreeNode]]` o sin response_model con OpenAPI docstring).
- [x] 7.8 Test integración: `GET /categorias?solo_hojas=true` devuelve array plano sin `subcategorias`.
- [x] 7.9 Test integración: `GET /categorias` sin param sigue devolviendo árbol con `subcategorias` (regresión).

## 8. Documentar `GET /ingredientes?es_alergeno=true` en spec

- [x] 8.1 Verificar in-source que el filtro ya está implementado (confirmado en `backend/features/ingredients/router.py:53` durante diseño). Si por alguna razón se removió, agregar como tarea de código.
- [x] 8.2 Asegurar que existen tests de integración del filtro `es_alergeno=true` y `es_alergeno=false` (si no existen, agregarlos siguiendo TDD aunque la implementación ya esté).
- [x] 8.3 Si los tests existen pero solo cubren un caso, completar con: filtro=false retorna no-alergenos, omitido retorna todos, combinado con pagination, soft-deleted excluidos por default.

## 9. Audit de seed data

- [x] 9.1 Ejecutar query manual contra dev DB: `SELECT p.id, p.nombre, c.id AS cat_id, c.nombre AS cat_nombre FROM products p JOIN product_categories pc ON pc.product_id = p.id JOIN categories c ON c.id = pc.category_id WHERE pc.eliminado_en IS NULL AND p.eliminado_en IS NULL AND EXISTS (SELECT 1 FROM categories child WHERE child.padre_id = c.id AND child.eliminado_en IS NULL);` para listar productos asignados a categorías no-hoja.
- [x] 9.2 Si la query devuelve rows: documentar en el comentario del PR; opciones (a) corregir el script de seed para que esos productos vayan a categorías hoja, (b) tarea separada de re-asignación manual (NO en este change). Decidir con el usuario antes de aplicar.
- [x] 9.3 Si la query devuelve 0 rows: nota en el PR confirmando "seed audit clean — no hay productos en categorías no-hoja".

## 10. Validación final

- [x] 10.1 Correr la suite de tests del backend (`pytest backend/tests/`) y confirmar 100% verde.
- [x] 10.2 Correr `openspec validate catalog-filters-and-leaf-categories-backend --strict` y confirmar sin warnings ni errores. (verificado 2026-05-12: "Change is valid")
- [x] 10.3 Correr `openspec show catalog-filters-and-leaf-categories-backend --type spec` para inspección manual de los deltas. (OK humano 2026-05-13)
- [x] 10.4 Verificar que el OpenAPI schema generado refleja todos los nuevos query params (`excluir_alergeno_ids`, `sin_categoria`, `solo_hojas`). Inspección por `GET /openapi.json` en dev. (OK humano 2026-05-13)
- [x] 10.5 Inspección manual: ejecutar los flujos extremo a extremo (POST producto con cat raíz → 422 + cuerpo del mensaje en Rioplatense; PUT categorias [] → producto pasa a disponible=false; GET /productos?categoria_id=raíz → matchea descendientes; GET /categorias?solo_hojas=true → flat). (OK humano 2026-05-13)
