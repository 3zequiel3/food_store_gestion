# Tasks: refactor-auth-to-uow

> **Estrategia (D7)**: Step 1 refactoriza `AuthService` y `dependencies.py` (sin tocar router todavía — el router viejo sigue funcionando porque el service nuevo es invocable con `AuthService()`). Step 2 refactoriza `router.py` y verifica los 15 tests de auth + smoke de los 22 endpoints downstream. Step 3 elimina `get_db()`, `override_get_db` y docstrings obsoletos. Step 4 verificación final.
>
> **Regla de oro**: la suite completa (`pytest backend/tests/ -q`) debe quedar verde después de CADA commit de los 4 steps. Si algo falla, `git revert` del último commit y debug.

## 1. Step 1 — Refactor de `AuthService` y `auth/dependencies.py` (core service-driven UoW)

- [x] 1.1 Editar `backend/features/auth/service.py`: cambiar `class AuthService: def __init__(self, session: Session): ...` a `def __init__(self) -> None: pass`. Eliminar `self.session` y `self.refresh_token_repo` como atributos de instancia.
- [x] 1.2 Editar `backend/features/auth/service.py`: convertir los 5 métodos de `async def` a `def` sync (`register`, `login`, `refresh`, `logout`, `_create_token_pair`). Verificar que NO hay `await` real adentro (ya verificado en explore, pero re-chequear).
- [x] 1.3 Refactor `register(self, data: RegisterRequest) -> TokenPairResponse` (cambia tipo de retorno, **breaking interno**): envolver el cuerpo en `with UnitOfWork() as uow:`. Registrar `uow.register_repository("refresh_tokens", RefreshTokenRepository(uow.session))`. Mover el check de email existente, el `add(user)`, el `flush()`, el `add(UsuarioRol)`, el `flush()`, el `refresh(user)`, y la llamada a `self._create_token_pair(user, uow.session)` DENTRO del mismo `with`. Retornar el `TokenPairResponse` que viene de `_create_token_pair`.
- [x] 1.4 Refactor `login(self, data: LoginRequest, client_ip: Optional[str] = None) -> TokenPairResponse`: envolver en `with UnitOfWork() as uow:`. El `_get_user_by_email` pasa a aceptar `session` o se reescribe inline como `uow.session.execute(...)`. Llamar `self._create_token_pair(user, uow.session)` dentro del `with`.
- [x] 1.5 Refactor `refresh(self, refresh_token_str: str) -> TokenPairResponse`: envolver en `with UnitOfWork() as uow:`. Registrar `uow.register_repository("refresh_tokens", RefreshTokenRepository(uow.session))`. Preservar los `uow.session.flush()` intermedios después de `revoke_all_user_tokens` y `mark_token_as_revoked` (R5). Llamar `_create_token_pair(user, uow.session)` dentro del `with`.
- [x] 1.6 Refactor `logout(self, refresh_token_str: str) -> None`: envolver en `with UnitOfWork() as uow:`. Registrar el repo. El `flush()` final puede eliminarse (el `__exit__` comitea) o preservarse — preservar por consistencia y porque no daña.
- [x] 1.7 Refactor `_create_token_pair(self, user: Usuario, session: Session) -> TokenPairResponse`: cambia firma para recibir `session: Session` explícita. Todo el body usa `session` en lugar de `self.session`. Eliminar `async`/`await` si quedan.
- [x] 1.8 Refactor `_get_user_by_email`: si se mantiene como helper, cambia firma a `_get_user_by_email(self, session: Session, email: str) -> Optional[Usuario]`. Alternativa: inlinear las 4 líneas en cada caller (`register`, `login`) — preferido por simplicidad si el caller queda legible. **Decisión tomada: inlineado en register y login.**
- [x] 1.9 Editar `backend/features/auth/dependencies.py`: refactor `get_current_user`. Eliminar el parámetro `db: Session = Depends(get_db)`. Adentro, abrir sesión directa: `session = get_session_factory()(); try: ... finally: session.close()`. Mantener firma pública: `def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Usuario:` (convertir a `def` sync, NO async — `await` no se usa). Importar `get_session_factory` de `backend.shared.database`.
- [x] 1.10 Editar `backend/features/auth/dependencies.py`: agregar al docstring de `get_current_user` la nota explícita "READ-ONLY: this dependency opens a session for a single SELECT. Do NOT perform writes — no commit is issued." (D1, R2).
- [x] 1.11 Editar `backend/features/auth/dependencies.py`: refactor `get_optional_user`. Eliminar el parámetro `db: Session = Depends(get_db)`. La función pasa a `def get_optional_user(request: Request) -> Optional[Usuario]:`. Internamente extrae el token del header, y si existe llama `get_current_user(token)` (sin pasar `db`) envuelto en try/except.
- [x] 1.12 Editar `backend/features/auth/dependencies.py`: convertir `require_role` para que el `role_checker` interno sea `def` sync (no `async def`). Es coherente con `get_current_user` siendo sync ahora. NO tocar la firma pública (D2).
- [x] 1.13 Correr `pytest backend/tests/integration/test_auth.py -q` — los 15 tests deben pasar. **NOTA**: en este punto el router viejo (`router.py`) sigue llamando `AuthService(db)` con `db=Depends(get_db)` — DEBE FALLAR. Step 1 NO deja la suite verde por sí solo. Se valida en Step 2. **Implementado: Steps 1 y 2 se aplicaron juntos para dejar la suite verde.**
- [x] 1.14 NO commitear todavía si la suite no está verde. Confirmar que estamos al final del refactor del service y dependencies, listos para tocar el router.

## 2. Step 2 — Refactor de `auth/router.py` y verificación end-to-end

- [x] 2.1 Editar `backend/features/auth/router.py`: eliminar `from backend.shared.database import get_db` (queda huérfano).
- [x] 2.2 Refactor endpoint `register` (líneas 37-55): eliminar `db=Depends(get_db)`. Cambiar el body a `service = AuthService(); return service.register(data)` (una sola llamada al service, sin el segundo `_create_token_pair` que ya está dentro de `register`).
- [x] 2.3 Refactor endpoint `login` (líneas 65-82): eliminar `db=Depends(get_db)`. Cambiar a `service = AuthService(); return service.login(data, client_ip=client_ip)`.
- [x] 2.4 Refactor endpoint `refresh` (líneas 92-106): eliminar `db=Depends(get_db)`. Cambiar a `service = AuthService(); return service.refresh(data.refresh_token)`.
- [x] 2.5 Refactor endpoint `logout` (líneas 115-129): eliminar `db=Depends(get_db)`. Cambiar a `service = AuthService(); service.logout(data.refresh_token); return None`.
- [x] 2.6 Refactor endpoint `get_me` (líneas 138-157): eliminar `db=Depends(get_db)`. Eliminar el `import get_current_user` inline y reemplazar por import top-level. Cambiar `user = await get_current_user(token, db)` por `user = get_current_user(token)` (sync, sin `db`).
- [x] 2.7 Verificar imports finales del router: NO debe haber `get_db`, `Session`, ni `Depends` huérfanos (`Depends` se mantiene si `oauth2_scheme` lo usa).
- [x] 2.8 Correr `pytest backend/tests/integration/test_auth.py -q` — los 15 tests deben pasar verdes.
- [x] 2.9 Correr `pytest backend/tests/integration/test_categories.py -q` — verificar que los 31 tests downstream que dependen de `require_role` siguen pasando.
- [x] 2.10 Correr `pytest backend/tests/integration/test_products.py -q` — 89 tests deben pasar (8 endpoints downstream con `require_role`).
- [x] 2.11 Correr `pytest backend/tests/integration/test_ingredients.py -q` — 39 tests (3 endpoints downstream).
- [x] 2.12 Correr `pytest backend/tests/integration/test_delivery_addresses.py -q` — 36 tests (5 endpoints downstream con `get_current_user`).
- [x] 2.13 Correr `pytest backend/tests/integration/test_user_profile.py -q` — 34 tests (3 endpoints downstream con `get_current_user`).
- [x] 2.14 Correr suite completa `pytest backend/tests/ -q` — todos los tests verdes.
- [x] 2.15 Commit: `refactor(auth): migrate AuthService to service-driven UoW pattern`.

## 3. Step 3 — Eliminar `get_db()`, `override_get_db` y docstrings obsoletos

- [x] 3.1 Editar `backend/tests/conftest.py`: eliminar la función `override_get_db` (si existe como función nombrada) y la línea `app.dependency_overrides[get_db] = override_get_db`. Eliminar el import `from backend.shared.database import get_db` si queda huérfano. La fixture `_patch_uow_session_factory` (existente) queda como único mecanismo de inyección de session para tests.
- [x] 3.2 Editar `backend/shared/database.py`: eliminar la función `get_db()` completa (líneas ~90-119). Eliminar el `from typing import Generator` si queda huérfano. Eliminar el import de `Session` si queda huérfano (`sessionmaker` aún se usa).
- [x] 3.3 Editar `backend/dependencies.py`: revisar el docstring/NOTE en la línea 4 que menciona "use from backend.shared.database import get_db". Si todo el archivo quedó vacío post-refactor anterior (`get_uow` ya eliminado), eliminar el archivo. Si queda contenido legítimo, actualizar el comentario para reflejar el patrón actual (`UnitOfWork()` o `get_session_factory()()`).
- [x] 3.4 Verificar con `rg "get_db" backend/` — debe retornar 0 matches en código de producción. Permitido: matches en `openspec/specs/auth/spec.md` o docstrings que mencionen el historial.
- [x] 3.5 Verificar con `rg "from backend.shared.database import get_db" backend/` — 0 matches.
- [x] 3.6 Verificar con `rg "Depends\(get_db\)" backend/` — 0 matches.
- [x] 3.7 Correr suite completa `pytest backend/tests/ -q` — todos los tests verdes (no debe romperse nada, el path ya estaba muerto).
- [x] 3.8 Commit: `refactor(database): remove get_db dependency injection helper`.

## 4. Step 4 — Verificación final

- [x] 4.1 Correr suite completa una última vez: `pytest backend/tests/ -q`.
- [x] 4.2 Correr `openspec validate refactor-auth-to-uow --strict` — sin errores ni warnings.
- [x] 4.3 Verificación de invariantes con grep:
  - `rg "AuthService\(.*\)" backend/features/auth/router.py` → solo `AuthService()` (sin args).
  - `rg "async def" backend/features/auth/service.py` → 0 matches.
  - `rg "Depends\(get_db\)" backend/` → 0 matches.
- [ ] 4.4 Smoke test manual (opcional, requiere Postgres dev): levantar el backend (`uvicorn backend.app:app --reload`), ejecutar:
  - `POST /api/v1/auth/register` con email nuevo → 201 con TokenPair.
  - `POST /api/v1/auth/login` con esas credenciales → 200.
  - `POST /api/v1/auth/refresh` con el refresh recibido → 200 con nuevo pair.
  - `POST /api/v1/auth/refresh` reutilizando el refresh viejo → 401 (replay).
  - `POST /api/v1/auth/logout` → 204.
  - Verificar que los 3 row counts (users, user_roles, refresh_tokens) son consistentes con un register exitoso (1, 1, 1) y un register fallido (0, 0, 0).
- [ ] 4.5 **ESPERAR REVISIÓN HUMANA del usuario antes de invocar `/opsx:archive`.** Mostrar el checklist completado y esperar OK explícito.
