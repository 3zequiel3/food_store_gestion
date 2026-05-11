## Why

El integrador (`docs/Integrador.txt`) usa léxico castellano para los recursos del dominio (`/api/v1/productos`, `/api/v1/pedidos`, `/api/v1/pagos`, `/api/v1/direcciones`, `/api/v1/categorias`, `/api/v1/ingredientes`) y describe el módulo conceptual como `usuarios` (`app/modules/usuarios/`, Integrador.txt:91). El commit `b8968e0` ya alineó `/orders → /pedidos` y `/payments → /pagos`. La última inconsistencia es `/api/v1/users`, justificada en la spec vigente con un argumento circular ("consistent with the existing router mount") que la regla del proyecto invalida: **"si una instrucción de los `.md` entra en conflicto con los `.txt`, gana la spec"** (CLAUDE.md). Esta es una pequeña deuda técnica que conviene saldar ahora, antes de que más superficie (frontend, admin) se acople al path inglés.

## What Changes

- **BREAKING** (interno) Renombrar el mount prefix `/api/v1/users` → `/api/v1/usuarios` en `backend/main.py:197`.
- **BREAKING** (interno) Renombrar el tag de OpenAPI `users` → `usuarios` en el mismo mount, para que `/docs` muestre la sección con el mismo lexicón castellano que los demás recursos del dominio.
- Actualizar la spec vigente `openspec/specs/user-profile/spec.md` (delta MODIFIED): todos los `Requirements` y `Scenarios` que citan `/api/v1/users/me`, `/api/v1/users/me/password`, `/api/v1/users/*` pasan a `/api/v1/usuarios/...`. El requirement "API path and version" queda con justificación contra el integrador (no contra el mount existente). El escenario "English-Spanish ambiguity rejected" se **invierte**: ahora es `GET /api/v1/users/me` el que debe devolver 404.
- Actualizar la referencia cruzada en `openspec/specs/delivery-addresses/spec.md:214` (`NOT a sub-path of /api/v1/users/me` → `/api/v1/usuarios/me`).
- Actualizar docstrings y README del feature (`backend/features/users/router.py:9`, `backend/features/users/README.md` — 4 referencias).
- Actualizar `backend/tests/test_main.py:67` (lista `expected_paths`).
- Reemplazo masivo en `backend/tests/integration/test_user_profile.py` (44 ocurrencias verificadas con `rg -c`).
- **NO se renombra el módulo Python** `backend/features/users/` (decisión D4, design.md): el path HTTP es la API pública; el package en inglés es convención técnica interna válida y mantenerlo evita ruido de imports en tests, services y dependencies.

No hay compatibilidad backwards (D2): no existen clientes externos en producción; el frontend no consume `/users/*` (verificado con `rg /api/v1/users frontend/` → 0 hits).

## Capabilities

### New Capabilities
<!-- None — esta es una modificación de una capability existente. -->

### Modified Capabilities
- `user-profile`: el path mount y el tag de OpenAPI cambian de `/api/v1/users` + `users` a `/api/v1/usuarios` + `usuarios`. Todos los `Requirements` y `Scenarios` que referencian el path inglés se actualizan; el `Requirement: API path and version` recibe nueva justificación (alineación con el patrón castellano del integrador) y el `Scenario: English-Spanish ambiguity rejected` se invierte.

## Impact

**Código backend afectado** (verificado con `rg -l "/api/v1/users" backend/`):
- `backend/main.py:197` — 1 línea (prefix + tag)
- `backend/features/users/router.py:9` — 1 línea (docstring)
- `backend/features/users/README.md` — 4 referencias
- `backend/tests/test_main.py:67` — 1 entrada en `expected_paths`
- `backend/tests/integration/test_user_profile.py` — 44 ocurrencias hardcodeadas

**Specs afectadas** (verificado con `rg -l "/api/v1/users" openspec/specs/`):
- `openspec/specs/user-profile/spec.md` — 18 ocurrencias (delta MODIFIED completo)
- `openspec/specs/delivery-addresses/spec.md` — 1 referencia cruzada

**Frontend**: ninguno (`rg /api/v1/users frontend/` = 0 hits).

**OpenAPI**: el grupo de endpoints en `/docs` se renombra de "users" a "usuarios". Cualquier consumidor que use el schema OpenAPI debe regenerar clientes; no aplica en este proyecto porque no hay consumidores externos.

**Base de datos / migraciones**: ninguno.

**Compatibilidad**: no se mantiene redirect 301 (D2). El cambio es atómico.

**Tests**: suite actual 286/286 debe permanecer en verde tras el rename. No se agregan tests nuevos — solo se actualizan los paths.

**Estimación**: 30–60 min (mayoría es find-replace con `sd`; spec update requiere atención).
