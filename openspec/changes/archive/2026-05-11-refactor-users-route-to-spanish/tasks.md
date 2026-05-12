## 1. Actualizar specs vigentes (orden: spec primero, código después — D3)

- [x] 1.1 Editar `openspec/specs/user-profile/spec.md`: reemplazar 18 ocurrencias de `/api/v1/users` por `/api/v1/usuarios`. Verificar con `rg -c "/api/v1/users" openspec/specs/user-profile/spec.md` que el conteo final sea 0. Verificar que no haya quedado `/api/v1/usuariosuarios` (doble reemplazo).
- [x] 1.2 En el mismo archivo, actualizar el Requirement "API path and version" (línea 231): reemplazar la justificación circular "consistent with the existing router mount" por la justificación arquitectónica contra el integrador (citar `Integrador.txt:91` y la lista de prefijos castellanos `/productos`, `/pedidos`, `/pagos`, `/direcciones`, `/categorias`, `/ingredientes`). El tag SIGUE siendo `users` (inglés), consistente con los otros 6 tags del proyecto.
- [x] 1.3 En el mismo archivo, invertir el escenario "English-Spanish ambiguity rejected" (línea 238-240): ahora es `GET /api/v1/users/me` el que debe devolver 404 (no `/api/v1/usuarios/me`). Renombrar el scenario a algo como "Legacy English path returns 404".
- [x] 1.4 Editar `openspec/specs/delivery-addresses/spec.md:214`: cambiar la referencia cruzada `NOT a sub-path of /api/v1/users/me` por `NOT a sub-path of /api/v1/usuarios/me`. Verificar con `rg -c "/api/v1/users" openspec/specs/delivery-addresses/spec.md` que el conteo final sea 0.

## 2. Actualizar código de producción

- [x] 2.1 Editar `backend/main.py:197`: cambiar `prefix="/api/v1/users"` por `prefix="/api/v1/usuarios"`. **Mantener `tags=["users"]` sin cambios** (decisión D1 del design: consistencia con los otros tags en inglés del proyecto).
- [x] 2.2 Editar `backend/features/users/router.py:9`: actualizar el docstring que dice `Mounted at /api/v1/users by backend/main.py` → `Mounted at /api/v1/usuarios by backend/main.py`.
- [x] 2.3 Editar `backend/features/users/README.md`: reemplazar las 4 ocurrencias de `/api/v1/users` por `/api/v1/usuarios` (línea 4 prosa + líneas 18, 24, 30 ejemplos curl).

## 3. Actualizar tests

- [x] 3.1 Editar `backend/tests/test_main.py:67`: cambiar la entrada `"/api/v1/users"` en `expected_paths` por `"/api/v1/usuarios"`.
- [x] 3.2 Reemplazo masivo en `backend/tests/integration/test_user_profile.py`: usar `sd '/api/v1/users' '/api/v1/usuarios' backend/tests/integration/test_user_profile.py`. Verificar con `rg -c "/api/v1/users" backend/tests/integration/test_user_profile.py` que el conteo final sea 0 y con `rg -c "/api/v1/usuarios" backend/tests/integration/test_user_profile.py` que el conteo final sea 44.

## 4. Verificación final

- [x] 4.1 Sanity-check global de búsqueda residual (excluyendo archive): `rg -l "/api/v1/users" backend/ openspec/specs/ openspec/changes/refactor-users-route-to-spanish/`. El comando debe devolver **0 archivos**. Si hay matches, revisar y corregir antes de continuar.
- [x] 4.2 Sanity-check que no haya doble reemplazo: `rg -l "/api/v1/usuariosuarios" backend/ openspec/specs/`. Debe devolver 0 archivos.
- [x] 4.3 Ejecutar suite: `cd backend && uv run pytest`. Resultado esperado: **286 passed** (mismo conteo que antes del refactor).
- [x] 4.4 Validar el change OpenSpec: `openspec validate refactor-users-route-to-spanish --strict`. Debe pasar sin errores.
- [ ] 4.5 Inspección manual de `/docs` (opcional, no bloqueante): `uv run uvicorn main:app --reload` y abrir `http://localhost:8000/docs`. Verificar que la sección "users" muestre los 3 endpoints bajo `/api/v1/usuarios/me*`.

## 5. Commit y revisión humana

- [ ] 5.1 Stage cambios: `git add backend/ openspec/specs/user-profile/ openspec/specs/delivery-addresses/ openspec/changes/refactor-users-route-to-spanish/`.
- [ ] 5.2 Commit con mensaje conventional: `refactor(routes): align /users prefix with Spanish lexicon (/usuarios)`. **NO incluir `Co-Authored-By`**.
- [ ] 5.3 **STOP** — esperando revisión humana. NO archivar automáticamente. El usuario corre `/opsx:archive refactor-users-route-to-spanish` después de revisar.
