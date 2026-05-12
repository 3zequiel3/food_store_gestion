## Context

El proyecto Food Store sigue una **convención de léxico castellano para los recursos del dominio HTTP**, derivada del integrador (`docs/Integrador.txt:91` lista el módulo conceptual como `usuarios` y los endpoints `/api/v1/productos`, `/api/v1/pedidos`, `/api/v1/pagos`, `/api/v1/direcciones`, `/api/v1/categorias`, `/api/v1/ingredientes` en castellano). Solo `/api/v1/auth/*` está en inglés, porque "auth" es un término técnico transversal (no un recurso de dominio).

`/api/v1/users` quedó como inconsistencia residual. La spec vigente `openspec/specs/user-profile/spec.md` la justifica con razonamiento circular: "consistent with the existing router mount at backend/main.py:196". La regla del proyecto (CLAUDE.md) es explícita: **"Si una instrucción de los `.md` entra en conflicto con los `.txt`, gana la spec"** — donde "spec" significa `Integrador.txt` / `Descripcion.txt` / `Historias_de_usuario.txt`, no los markdown del repo. Los markdown de OpenSpec son derivados; el integrador es la fuente de verdad.

El commit `b8968e0` (`fix(routes): align orders/payments prefixes with spec del integrador`) ya alineó `/orders → /pedidos` y `/payments → /pagos`. Este change cierra el último gap.

**Estado actual verificado:**
- `backend/main.py:197`: `app.include_router(users_router, prefix="/api/v1/users", tags=["users"])`
- `backend/features/users/router.py:9`: docstring menciona `/api/v1/users`
- `backend/features/users/README.md`: 4 referencias
- `backend/tests/test_main.py:67`: entrada en `expected_paths` para `/api/v1/users`
- `backend/tests/integration/test_user_profile.py`: 44 ocurrencias de `/api/v1/users` (cuenta verificada con `rg -c`)
- `openspec/specs/user-profile/spec.md`: 18 ocurrencias en `Requirements` y `Scenarios`
- `openspec/specs/delivery-addresses/spec.md:214`: 1 referencia cruzada
- Frontend: 0 ocurrencias (verificado con `rg /api/v1/users frontend/`)

## Goals / Non-Goals

**Goals:**
- Alinear el path HTTP del módulo user-profile con el patrón castellano del integrador.
- Mantener la suite de tests en 286/286 verde tras el rename.
- Dejar la spec vigente `user-profile` con justificación arquitectónica sólida (no circular).
- Hacer el cambio atómico — un commit, sin estados intermedios donde ambos paths coexistan.

**Non-Goals:**
- Renombrar el módulo Python `backend/features/users/` → `backend/features/usuarios/` (decisión D4). El package en inglés es convención técnica interna válida.
- Mantener compatibilidad backwards con `/api/v1/users` vía redirect 301 (decisión D2).
- Renombrar el router file `users_router.py` ni el variable `users_router` en `main.py`.
- Tocar `auth` (es un término técnico, no recurso de dominio).
- Migrar la base de datos (este cambio es 100% capa HTTP).
- Agregar tests nuevos — solo se actualizan los paths existentes.

## Decisions

### D1: Renombrar el tag de OpenAPI `users` → `usuarios`

**Decisión**: SÍ renombrar el tag.

**Rationale**: el tag es lo que el usuario ve en `/docs` (Swagger UI) como sección agrupadora. Mantener `tags=["users"]` mientras el mount es `/api/v1/usuarios` genera disonancia visual y rompe la convención que ya siguen los otros tags del proyecto (`products`, `orders`, `payments`, `addresses`, `categories`, `ingredients` — todos en inglés porque el integrador no especifica nombres de tags, solo paths).

Releyendo `main.py:197-203`, los demás tags ya están en inglés: `products`, `orders`, `payments`, `addresses`, `categories`, `ingredients`. **Mantener consistencia con los OTROS tags pesa más** que la coherencia visual entre prefix y tag en este endpoint puntual. **REVERSIÓN**: dejar `tags=["users"]` (inglés, igual que el resto).

**Decisión final D1**: Mantener `tags=["users"]` en inglés (consistente con los otros 6 tags del proyecto). Cambiar SOLO el `prefix`.

**Alternativa descartada**: cambiar tag a `usuarios` rompería el patrón uniforme de tags en inglés del proyecto. La discordancia prefix/tag es aceptable porque los tags son metadata interna de OpenAPI, no parte de la URL pública.

**Impacto**: ninguno en `/docs` más allá del nombre del path en la sección "users".

### D2: ¿Mantener compatibilidad backwards con redirect 301?

**Decisión**: NO.

**Rationale**:
- No hay clientes externos en producción (proyecto académico en desarrollo).
- El frontend no consume `/api/v1/users/*` (verificado: 0 hits con `rg`).
- Un 301 introduce complejidad permanente (un middleware o ruta-puente) que después nadie va a borrar.
- El escenario "English-Spanish ambiguity rejected" en la spec vigente (línea 238-240) ya documenta que el path inglés debe dar 404 — solo invertimos qué path es cuál.

**Alternativa descartada**: agregar un `@app.get("/api/v1/users/{path:path}")` que haga `RedirectResponse` con 301 a `/api/v1/usuarios/{path}`. Descartada por "complejidad permanente sin caso de uso real".

### D3: Orden de las tareas — spec primero o código primero

**Decisión**: SPEC PRIMERO, código después, tests al final.

**Rationale**: si actualizamos primero el código, la suite de tests rompe en seguida (44 ocurrencias). Si actualizamos primero la spec, el código sigue verde y solo se desincroniza la spec con el código — la spec es un documento, no rompe nada en CI. El orden propuesto es:

1. Spec vigente (`openspec/specs/user-profile/spec.md` + cross-ref en `delivery-addresses/spec.md`).
2. Código de producción (`backend/main.py`, router docstring, README).
3. Tests (`test_main.py` primero — solo 1 línea —, después el masivo en `test_user_profile.py`).
4. Verify con `uv run pytest`.

Esto mantiene "el código compila/pasa tests" como invariante durante los primeros pasos, y deja el rename masivo de tests como una sola operación atómica que se valida inmediatamente con la suite.

**Alternativa descartada**: hacer todo en un solo commit gigante con `sd` recursivo sobre todo el repo. Descartada porque mezcla concerns (spec docs vs. código vs. tests) y dificulta el code review.

### D4: ¿Renombrar el módulo Python `backend/features/users/` también?

**Decisión**: NO.

**Rationale**:
- El path HTTP es la **API pública**; el package Python es **detalle interno de implementación**.
- Convención técnica válida: usar inglés para nombres de paquetes/módulos Python (matches PEP 8 implicit guidance, matches el resto del ecosistema FastAPI/SQLModel).
- Renombrar el package implica tocar: el directorio, los `import` en `main.py`, `services.py`, `repositories.py`, `tests/conftest.py`, fixtures, dependencies, `pyproject.toml` (si hubiera entrypoints) — mucho ruido para cero beneficio funcional.
- Precedente: `backend/features/users/` ya alberga lógica que sirve tanto al endpoint de profile como al admin (cuando exista). El nombre del package describe el dominio conceptual ("usuarios"), no el path HTTP.

**Alternativa descartada**: renombrar `backend/features/users/` → `backend/features/usuarios/`. Descartada por ratio costo/beneficio muy alto y por mezclar dos concerns (path HTTP vs. estructura de código).

### D5: ¿Actualizar también `openspec/specs/delivery-addresses/spec.md`?

**Decisión**: SÍ, pero como un cambio mínimo y local — NO se crea un delta spec para `delivery-addresses` en este change.

**Rationale**: la referencia en `delivery-addresses/spec.md:214` dice `"NOT a sub-path of /api/v1/users/me"`. Eso es una **referencia cruzada documental** (explica una decisión histórica), no un requirement de `delivery-addresses` que esté cambiando. Editamos el texto in situ como parte de la consistencia documental del repo, pero no requiere un delta MODIFIED en `specs/delivery-addresses/spec.md` dentro de este change (la capability `delivery-addresses` no cambia su comportamiento).

**Implicación**: este change tiene **una sola** capability modificada (`user-profile`). La edición de `delivery-addresses/spec.md` es housekeeping documental, registrada en `tasks.md` como una tarea explícita.

**Alternativa descartada**: crear `openspec/changes/refactor-users-route-to-spanish/specs/delivery-addresses/spec.md` con un MODIFIED. Descartada porque OpenSpec interpreta eso como "esta capability está cambiando sus requirements" — y no es cierto.

### D6: Citas textuales contra el integrador

Refuerzo de la justificación arquitectónica (para la spec delta):

- `docs/Integrador.txt:91`: `usuarios	app/modules/usuarios/	CRUD usuarios + asignación de roles RBAC. Soft delete.` — el integrador nombra el módulo conceptual como **`usuarios`** (castellano).
- `docs/Integrador.txt` § endpoints: lista `/api/v1/productos`, `/api/v1/pedidos`, `/api/v1/pagos`, `/api/v1/direcciones`, `/api/v1/categorias`, `/api/v1/ingredientes` — todos los recursos del dominio en castellano.
- `docs/Integrador.txt`: NO lista explícitamente `/api/v1/users` ni `/api/v1/usuarios`; el patrón implícito por consistencia es **castellano**.
- `CLAUDE.md`: `"Si una instrucción de los .md entra en conflicto con los .txt, gana la spec"` — la justificación circular de la spec actual ("consistent with the existing router mount") está subordinada al patrón del integrador.

## Risks / Trade-offs

- **[Riesgo]** Olvidar una ocurrencia de `/api/v1/users` en algún test → suite rota localmente → **Mitigación**: usar `rg -c "/api/v1/users" backend/` antes y después del rename y verificar que el contador esté en 0 (excepto en archivos archivados de `openspec/changes/archive/`, que NO se tocan — son historia inmutable).

- **[Riesgo]** Reemplazo accidental en archivos archivados de `openspec/changes/archive/` que rompa la trazabilidad histórica → **Mitigación**: usar `sd` con rutas explícitas (`backend/`, `openspec/specs/`, NO recursivo sobre todo el repo).

- **[Riesgo]** El escenario invertido (`/api/v1/users/me → 404` en vez de `/api/v1/usuarios/me → 404`) podría confundir a un revisor que solo lee el diff de la spec sin contexto → **Mitigación**: el commit message y el proposal explicitan la inversión; el delta MODIFIED muestra el bloque completo, no solo el cambio puntual.

- **[Riesgo]** Romper la integración con un cliente externo (Postman collection, script de smoke test) → **Mitigación**: no aplica, no hay clientes externos. Si en el futuro alguien tenía una colección Postman hardcoded, la regenera desde `/openapi.json`.

- **[Trade-off]** Path HTTP en castellano vs. package Python en inglés → **discordancia visual aceptada** (D4). El package interno usa convención técnica; el path HTTP usa el léxico del dominio del integrador.

- **[Trade-off]** Tag OpenAPI en inglés (`users`) vs. prefix en castellano (`/usuarios`) → **discordancia menor aceptada** (D1). Consistencia con los otros 6 tags del proyecto pesa más; el usuario de `/docs` lee el path completo de todas formas.

## Migration Plan

No hay migración (no hay clientes en producción).

**Plan de aplicación** (orden estricto, D3):

1. Editar `openspec/specs/user-profile/spec.md` (18 ocurrencias).
2. Editar `openspec/specs/delivery-addresses/spec.md:214` (1 ocurrencia).
3. Editar `backend/main.py:197` (prefix; tag se mantiene).
4. Editar `backend/features/users/router.py:9` (docstring).
5. Editar `backend/features/users/README.md` (4 ocurrencias).
6. Editar `backend/tests/test_main.py:67` (`expected_paths`).
7. Reemplazo masivo en `backend/tests/integration/test_user_profile.py` con `sd '/api/v1/users' '/api/v1/usuarios'` (44 ocurrencias).
8. Verificar: `rg -c "/api/v1/users" backend/ openspec/specs/` debe devolver 0 hits en archivos NO-archivados.
9. `uv run pytest` → 286/286.

**Rollback**: `git revert <sha>` del commit del refactor.

## Open Questions

Ninguna. Las cinco decisiones D1–D5 están cerradas en este documento.
