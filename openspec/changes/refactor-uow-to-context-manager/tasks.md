# Tasks: refactor-uow-to-context-manager

> **Estrategia (D10)**: Step 1 prepara el terreno (UoW backward-compatible + conftest con monkeypatch agregado, sin remover el override viejo). Step 2 migra los 5 features uno a uno (tests verdes después de cada sub-step). Step 3 cierra eliminando `get_uow`, la rama backward-compat del UoW, y simplifica el conftest.
>
> **Regla de oro**: 256/256 tests verdes después de CADA task de validación. Si algo falla, `git revert` del commit más reciente y debug.

## 1. Step 1 — Core + Conftest (preparación, NO migra features)

- [x] 1.1 Editar `backend/shared/unit_of_work.py`: agregar import `from typing import Any, Callable, Optional` y `from backend.shared.database import get_session_factory`.
- [x] 1.2 Editar `backend/shared/unit_of_work.py`: cambiar `__init__` a versión backward-compatible que acepta `Session` directa, `Callable` (factory) o `None` (default → `get_session_factory()`). Mantener detección por tipo: `isinstance(arg, Session)` → modo legacy; `callable(arg)` → factory; `None` → default.
- [x] 1.3 Editar `backend/shared/unit_of_work.py`: agregar `__enter__(self) -> "UnitOfWork": return self`.
- [x] 1.4 Editar `backend/shared/unit_of_work.py`: agregar `__exit__(self, exc_type, exc_val, exc_tb)` con `try: commit/rollback finally: close; return False`.
- [x] 1.5 Editar `backend/tests/conftest.py`: AGREGAR fixture `_patch_uow_session_factory(monkeypatch, test_db_session)` con `autouse=True` que hace `monkeypatch.setattr(_uow_mod, "get_session_factory", lambda: lambda: test_db_session)`. NO eliminar el `app.dependency_overrides[get_uow] = override_get_uow` todavía.
- [x] 1.6 Editar `backend/tests/integration/test_conftest_overrides.py`: extender el test para verificar AMBOS overrides — el legacy `get_uow` (sigue activo) y el nuevo monkeypatch sobre `unit_of_work.get_session_factory`. Marcar el test legacy con un comentario `# TODO: remove after Step 3`.
- [x] 1.7 Correr `pytest backend/tests/ -q` localmente — los 256 tests deben seguir verdes.
- [x] 1.8 Commit: `refactor(uow): add context manager protocol and self-creating session (backward-compat)`.

## 2. Step 2.1 — Migrar `categories`

- [x] 2.1.1 Refactor `backend/features/categories/service.py`: cambiar `class CategoryService: def __init__(self, uow): ...` a `def __init__(self): pass`. Eliminar `self.repo`, `self.uow` como atributos de instancia.
- [x] 2.1.2 Refactor `backend/features/categories/service.py`: envolver el cuerpo de cada método público (`create`, `update`, `delete`, `get_tree`) en `with UnitOfWork() as uow:`. Mover `uow.register_repository("categorias", CategoryRepository(uow.session))` al inicio del bloque. Reemplazar accesos a `self.repo` por `repo = uow.categorias`.
- [x] 2.1.3 Actualizar el docstring de `CategoryService`: invertir el comentario "NEVER calls uow.commit() — that is the router's responsibility (D6)" a "Each public method opens its own UnitOfWork context. Commit is performed by `__exit__` on clean exit."
- [x] 2.1.4 Refactor `backend/features/categories/router.py`: eliminar `uow: UnitOfWork = Depends(get_uow)` de las 4 firmas de endpoint. Eliminar el import de `UnitOfWork` y `get_uow` si quedan huérfanos.
- [x] 2.1.5 Refactor `backend/features/categories/router.py`: cambiar `service = CategoryService(uow)` por `service = CategoryService()` en los 4 endpoints. Eliminar las 3 ocurrencias de `uow.commit()`.
- [x] 2.1.6 Correr `pytest backend/tests/test_categories.py -q` — los 31 tests deben pasar.
- [x] 2.1.7 Correr suite completa `pytest backend/tests/ -q` — 256/256 verdes.
- [x] 2.1.8 Commit: `refactor(categories): move uow lifecycle from router to service`.

## 3. Step 2.2 — Migrar `ingredients`

- [x] 3.1 Refactor `backend/features/ingredients/service.py`: `__init__` sin argumentos. Envolver los 5 métodos públicos (`create`, `get_by_id`, `list_paginated`, `update`, `delete`) en `with UnitOfWork() as uow:`. Mover `register_repository` al inicio de cada bloque.
- [x] 3.2 Actualizar docstring del service análogamente.
- [x] 3.3 Refactor `backend/features/ingredients/router.py`: eliminar `Depends(get_uow)` en las 5 firmas, cambiar `IngredientService(uow)` por `IngredientService()`, eliminar las 3 `uow.commit()` (POST/PUT/DELETE).
- [x] 3.4 Limpiar imports huérfanos en router (si `UnitOfWork`, `get_uow` ya no se usan).
- [x] 3.5 Correr `pytest backend/tests/test_ingredients.py -q` — los 39 tests deben pasar.
- [x] 3.6 Correr suite completa — 256/256 verdes.
- [x] 3.7 Commit: `refactor(ingredients): move uow lifecycle from router to service`.

## 4. Step 2.3 — Migrar `products` (más complejo: 3 repos + double-read)

- [x] 4.1 Refactor `backend/features/products/service.py`: `__init__(self)` sin argumentos. Eliminar `self.repo`, `self.cat_repo`, `self.ing_repo`.
- [x] 4.2 Refactor `backend/features/products/service.py`: envolver los 12 métodos públicos en `with UnitOfWork() as uow:`. En cada bloque registrar los repos necesarios: para los métodos que solo tocan productos basta `uow.register_repository("productos", ProductRepository(uow.session))`. Para `set_categorias` registrar también `categorias`. Para `add_ingrediente` / `remove_ingrediente` / `list_ingredientes` registrar también `ingredientes`.
- [x] 4.3 **Colapsar double-read en `set_categorias`**: el método debe reemplazar el pivote `product_categories` Y devolver el `Producto` con categorias e ingredientes hidratados, todo dentro del mismo `with`. El return type pasa a ser el `Producto` (o detail object) ya cargado, no `None`.
- [x] 4.4 Verificar que `ProductRepository.get_detail` (o equivalente) usa `selectinload` para evitar `DetachedInstanceError` al hacer `model_validate` después del `with`.
- [x] 4.5 Actualizar docstring del service.
- [x] 4.6 Refactor `backend/features/products/router.py`: eliminar `Depends(get_uow)` en las 11 firmas, cambiar `ProductService(uow)` por `ProductService()`, eliminar las 8 `uow.commit()`.
- [x] 4.7 Refactor `PUT /{producto_id}/categorias` (líneas 248-274): eliminar la segunda llamada `service.get_detail(producto_id)`. El response viene directamente del valor de retorno de `service.set_categorias(...)`.
- [x] 4.8 Limpiar imports huérfanos.
- [x] 4.9 Correr `pytest backend/tests/test_products.py -q` — los 89 tests deben pasar (especialmente los que cubren `set_categorias`).
- [x] 4.10 Correr suite completa — 256/256 verdes.
- [x] 4.11 Commit: `refactor(products): move uow lifecycle from router to service and collapse set_categorias double-read`.

## 5. Step 2.4 — Migrar `users` (double-read en update_profile)

- [x] 5.1 Refactor `backend/features/users/service.py`: `__init__(self)` sin argumentos. Eliminar atributos legacy.
- [x] 5.2 Refactor `backend/features/users/service.py`: envolver los 3 métodos públicos (`get_profile`, `update_profile`, `change_password`) en `with UnitOfWork() as uow:`. Registrar `usuarios` y `refresh_tokens` dentro del bloque cuando aplique.
- [x] 5.3 **Colapsar double-read en `update_profile`**: el método actualiza el perfil Y retorna el `Usuario` con las relationships necesarias para el `UserProfileRead` schema, todo dentro del mismo `with`. El router NO vuelve a llamar a `get_profile`.
- [x] 5.4 Validar que el `flush()` intermedio en `change_password` (`uow.session.flush()` antes de la revocación masiva de refresh tokens) sigue ejecutándose dentro del `with` y NO interfiere con el `commit()` final del `__exit__`.
- [x] 5.5 Actualizar docstring del service.
- [x] 5.6 Refactor `backend/features/users/router.py`: eliminar `Depends(get_uow)` en las 3 firmas, cambiar `UserProfileService(uow)` por `UserProfileService()`, eliminar las 2 `uow.commit()`.
- [x] 5.7 Refactor `PATCH /me` (líneas 77-80): eliminar la segunda llamada `service.get_profile(...)`. El response viene del retorno de `service.update_profile(...)`.
- [x] 5.8 Limpiar imports huérfanos.
- [x] 5.9 Correr `pytest backend/tests/test_user_profile.py -q` — los 34 tests deben pasar.
- [x] 5.10 Correr suite completa — 256/256 verdes.
- [x] 5.11 Commit: `refactor(users): move uow lifecycle from router to service and collapse update_profile double-read`.

## 6. Step 2.5 — Migrar `addresses`

- [x] 6.1 Refactor `backend/features/addresses/service.py`: `__init__(self)` sin argumentos.
- [x] 6.2 Refactor `backend/features/addresses/service.py`: envolver los 5 métodos públicos (`create`, `list_for_user`, `update`, `delete`, `set_principal`) en `with UnitOfWork() as uow:`. Validar que `set_principal` ejecuta sus 2 ops (clear + set) dentro del MISMO `with` para preservar atomicidad.
- [x] 6.3 Actualizar docstring del service (especialmente la nota sobre atomicidad de `set_principal`).
- [x] 6.4 Refactor `backend/features/addresses/router.py`: eliminar `Depends(get_uow)` en las 5 firmas, cambiar `AddressService(uow)` por `AddressService()`, eliminar las 4 `uow.commit()`.
- [x] 6.5 Limpiar imports huérfanos.
- [x] 6.6 Correr `pytest backend/tests/test_delivery_addresses.py -q` — los 36 tests deben pasar.
- [x] 6.7 Correr suite completa — 256/256 verdes.
- [x] 6.8 Commit: `refactor(addresses): move uow lifecycle from router to service`.

## 7. Step 3 — Cierre (eliminar legacy)

- [ ] 7.1 Editar `backend/dependencies.py`: eliminar la función `get_uow` y sus imports relacionados (`UnitOfWork` si quedó huérfano, `get_session_factory` si solo se usaba ahí).
- [ ] 7.2 Editar `backend/shared/unit_of_work.py`: simplificar `__init__` a la firma final `__init__(self, session_factory: Optional[Callable] = None)`. Eliminar la rama de backward-compat (`isinstance(arg, Session)`). Eliminar el import de `Session` si quedó huérfano.
- [ ] 7.3 Editar `backend/tests/conftest.py`: eliminar la función `override_get_uow` y la línea `app.dependency_overrides[get_uow] = override_get_uow`. Eliminar el import de `get_uow`. La fixture `_patch_uow_session_factory` queda como único mecanismo de inyección de session.
- [ ] 7.4 Editar `backend/tests/integration/test_conftest_overrides.py`: eliminar las assertions del legacy `get_uow` override. Dejar solo las assertions sobre el monkeypatch de `unit_of_work.get_session_factory`. Quitar el comentario `# TODO: remove after Step 3`.
- [ ] 7.5 Correr suite completa — 256/256 verdes.
- [ ] 7.6 Verificar con `rg "Depends\(get_uow\)" backend/` — debe retornar 0 matches.
- [ ] 7.7 Verificar con `rg "uow\.commit\(\)" backend/features/` — debe retornar 0 matches en routers (los services tampoco llaman `uow.commit()` explícito porque `__exit__` lo hace).
- [ ] 7.8 Verificar con `rg "from backend.dependencies import get_uow" backend/` — debe retornar 0 matches.
- [ ] 7.9 Commit: `refactor(uow): remove get_uow dependency and legacy session injection`.

## 8. Verificación final

- [ ] 8.1 Correr suite completa una última vez: `pytest backend/tests/ -q` — 256/256 verdes.
- [ ] 8.2 Correr `openspec validate refactor-uow-to-context-manager --strict` — sin errores ni warnings.
- [ ] 8.3 `rg "Depends\(get_uow\)|get_uow\(\)" backend/` — 0 matches en código de producción y tests.
- [ ] 8.4 `rg "Session\)" backend/shared/unit_of_work.py` — el `__init__` ya NO acepta `Session` directa.
- [ ] 8.5 Smoke test manual de los 5 features: levantar el backend localmente (`uvicorn backend.app:app --reload`), ejecutar 1 request CRUD por feature contra Postgres dev, verificar que persisten cambios y que rollback en error funciona.
- [ ] 8.6 **ESPERAR REVISIÓN HUMANA del usuario antes de invocar `/opsx:archive`.** Mostrar este checklist completado y esperar OK explícito.
