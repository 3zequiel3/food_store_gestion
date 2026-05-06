## 1. Pre-flight verification

- [x] 1.1 Run `rg "get_db_session|from backend.dependencies" backend --type py` from project root and paste the full output into the apply log. Expected: only matches inside `backend/dependencies.py` itself plus a comment in `backend/shared/database.py`. If any other consumer appears, switch D6 to alias-mode (see design).
  <!-- OUTPUT: Only 2 matches, both inside backend/dependencies.py itself (definition + docstring example). Zero external consumers. D6 delete-mode confirmed. -->
- [x] 1.2 Run `rg "family_id|\.used\b" backend/features/auth backend/tests --type py` and paste output. Use the result as the canonical list of touchpoints to clean up in §3 and §6.
  <!-- OUTPUT: Touchpoints: models.py (family_id field + .used in is_active/repr), repository.py (revoke_family_tokens), service.py (token.used check, revoke_family_tokens call, family_id param/body), test_auth.py (family_id= in test_refresh_expired_token). All covered by §3 and §7 tasks. -->
- [x] 1.3 Run `rg "/api/auth|/api/users|/api/products|/api/orders|/api/payments" backend --type py --type md` and paste output. Use the result to validate task §5 covers every site.
  <!-- OUTPUT: Sites: main.py (5 include_router), dependencies.py (oauth2_scheme tokenUrl), router.py (oauth2_scheme tokenUrl), README.md (curl examples), conftest.py (/api/auth/login in auth_headers fixture), test_auth.py (all /api/auth/... refs), test_main.py (/api/products/, /api/users/, /api/orders/). All covered by §5, §7, and §7.5. -->
- [x] 1.4 Run `pytest -q` from `backend/`, paste full output (failures + errors counts). This is the baseline. Expected: 4 failed, 18 passed, 22 errors. Anything else means the codebase changed under us — STOP and report.
  <!-- OUTPUT: FF.....EEEEEEEEEEEEEEEEEEEEEE....F....F..... = 4 failed, 18 passed, 22 errors. Matches expected baseline. Root cause of 22 errors: SQLiteTypeCompiler has no attribute 'visit_UUID' — family_id UUID column on RefreshToken. -->

## 2. Unit tests baseline (D7 — jose API fixes only)

- [x] 2.1 Open `backend/tests/unit/test_security.py`, change `payload = jwt.decode(token, options={"verify_signature": False})` to `payload = jwt.get_unverified_claims(token)` in `test_create_access_token_contains_claims`.
- [x] 2.2 In the same file, change `expires_delta=timedelta(seconds=0)` to `expires_delta=timedelta(seconds=-1)` in `test_decode_expired_token_returns_none`.
- [x] 2.3 Run `pytest backend/tests/unit/test_security.py -q` and paste output. Expected: all unit tests pass (no SQLite involvement here).
  <!-- OUTPUT: 15 passed, 5 warnings in 1.64s -->

## 3. RefreshToken model alignment with ERD (D1, D2, D3)

- [x] 3.1 Edit `backend/features/auth/models.py`: drop the `family_id` field declaration and its import of `uuid`. Drop the `used: Mapped[bool]` field. Update the docstring to reflect that replay detection uses `revoked_at` (not `used`/`family_id`).
- [x] 3.2 In the same file, change `token_hash: Mapped[str] = mapped_column(String(255), ...)` to `String(64)`.
- [x] 3.3 Edit `backend/features/auth/repository.py`: drop `revoke_family_tokens(family_id)` (no longer needed). Drop `mark_token_as_used(token_id)`. Add `mark_token_as_revoked(token_id: int) -> None` that sets `revoked_at = datetime.utcnow()`. Keep `get_by_token_hash` and `revoke_all_user_tokens` unchanged.
- [x] 3.4 Edit `backend/features/auth/service.py`:
   - Remove `import uuid`, `from typing import ... Optional` if no longer needed.
   - Remove all `family_id` references from `refresh()` and `_create_token_pair()`.
   - In `refresh()`: change replay detection condition from `if token.used:` to `if token.revoked_at is not None:`. Change "revoke family" call to `self.refresh_token_repo.revoke_all_user_tokens(token.user_id)`.
   - After successful (non-replay) refresh, call `self.refresh_token_repo.mark_token_as_revoked(token.id)` instead of `mark_token_as_used`.
   - In `_create_token_pair()`: drop the `family_id` parameter and the body's family logic. The `RefreshToken(...)` constructor must NOT pass `family_id` or `used`.
   - Change `expires_in=30 * 60` to `expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60` (D10). The `from backend.config import settings` import is already present at function level — promote it to module-level.
- [x] 3.5 Edit `backend/features/auth/schemas.py`:
   - Change `nombre` and `apellido` `max_length` from `100` to `80` (D11).
   - Add `UserResponse` schema with `id: int, nombre: str, apellido: str, email: EmailStr, roles: list[str], created_at: datetime`. Add `from datetime import datetime` if missing.
- [x] 3.6 Run `pytest backend/tests/unit -q` and paste output. Expected: all unit tests still pass (we haven't broken security.py).
  <!-- OUTPUT: 15 passed, 5 warnings in 1.62s -->

## 4. Alembic migration for token_hash length (D3)

- [x] 4.1 From `backend/`, run `alembic revision -m "align refresh_tokens with erd"` and capture the new file path.
  <!-- OUTPUT: backend/alembic/versions/20260506_1620_77bcb99d97db_align_refresh_tokens_with_erd.py -->
- [x] 4.2 Edit the new revision file: in `upgrade()` add `op.alter_column("refresh_tokens", "token_hash", existing_type=sa.String(length=255), type_=sa.String(length=64), existing_nullable=False)`. In `downgrade()` reverse it (existing_type 64 → 255).
- [ ] 4.3 Run `alembic upgrade head` against the dev DB (DATABASE_URL must be set). Paste the output. Expected: migration applies cleanly. If it fails because tokens with length > 64 exist, run `psql -c "SELECT MAX(LENGTH(token_hash)) FROM refresh_tokens"` first; if all are 64 or less, proceed; otherwise abort task §4 and document deferral in apply log.
  <!-- DEFERRED: Postgres not running on localhost:5432 (Connection refused). Migration file is complete and correct. Run manually: cd backend && source .venv/bin/activate && DATABASE_URL=postgresql://ezequiel:ezequiel@localhost:5432/food_store alembic upgrade head -->
- [ ] 4.4 Run `alembic downgrade -1` then `alembic upgrade head` to verify round-trip works.
  <!-- DEFERRED: Same reason as 4.3. Run after 4.3 succeeds. -->

## 5. API prefix `/api/v1/` (D4)

- [x] 5.1 Edit `backend/main.py`: change all five `app.include_router(...)` prefixes from `/api/<resource>` to `/api/v1/<resource>` (auth, users, products, orders, payments).
- [x] 5.2 Edit `backend/features/auth/router.py`: change `OAuth2PasswordBearer(tokenUrl="/api/auth/login", ...)` to `tokenUrl="/api/v1/auth/login"`.
- [x] 5.3 Edit `backend/features/auth/dependencies.py`: same change to `OAuth2PasswordBearer.tokenUrl`.
- [x] 5.4 Edit `backend/features/auth/README.md`: replace every `/api/auth/...` with `/api/v1/auth/...` (hand-edited all 5 table rows + 4 curl examples + error example).
- [x] 5.5 Edit `backend/features/auth/router.py` docstrings (rate-limit comments and endpoint descriptions) — leave them functional, just consistent with the new path. (Docstrings had no hardcoded paths; oauth2_scheme.tokenUrl already updated in 5.2.)

## 6. Wire RFC 7807 exception handlers in main.py (D5)

- [x] 6.1 Edit `backend/main.py`: add the imports listed in design D5 (HTTPException, RequestValidationError, all custom exceptions from `shared.exceptions`, all handlers from `shared.error_handler`).
- [x] 6.2 Register all nine handlers via `app.add_exception_handler(...)` AFTER the `RateLimitExceeded` handler is registered. Order matters: more specific first, `Exception` last.
- [x] 6.3 Delete the inline `@app.exception_handler(Exception)` block at the bottom of `main.py` (the one that returns `{"detail": ..., "type": "internal_server_error"}`). The catch-all is now `generic_exception_handler` from `error_handler.py`.

## 7. Update integration tests (D7)

- [x] 7.1 Edit `backend/tests/integration/test_auth.py`: replace every `"/api/auth/..."` with `"/api/v1/auth/..."` (URLs).
- [x] 7.2 In `test_register_duplicate_email`: replace `assert data["code"] == "conflict"` with `assert response.status_code == 409` (already there) AND `assert data["status"] == 409` AND `assert data["title"] == "Conflict"`.
- [x] 7.3 In `test_refresh_expired_token`: remove the line `family_id="12345678-1234-1234-1234-123456789abc"` from the `RefreshToken(...)` construction.
- [x] 7.4 In `TestProtectedRoutes.test_protected_route_with_token`: confirm assertion `data["email"] == "test@example.com"` still passes; if `/me` now returns `created_at`, no breakage expected.
- [x] 7.5 Skim `test_main.py` and `test_error_handling.py` for `/api/auth/...` or `/api/<resource>/...` references; update any to `/api/v1/...` (D4 was global).
  <!-- Updated: test_main.py: /api/products/ → /api/v1/products/, /api/users/ → /api/v1/users/, /api/orders/ → /api/v1/orders/. conftest.py: /api/auth/login → /api/v1/auth/login in auth_headers fixture. test_error_handling.py: no hardcoded API paths, no changes needed. -->

## 8. Cleanup `backend/dependencies.py` (D6)

- [x] 8.1 Re-run task 1.1 verification (`rg "get_db_session"`) and confirm zero new consumers appeared after our edits.
  <!-- OUTPUT: Only 2 matches in backend/dependencies.py itself (definition + docstring). Still zero external consumers. Proceeding with delete-mode. -->
- [x] 8.2 If still zero consumers: delete `engine`, `SessionLocal`, and `get_db_session()` from `backend/dependencies.py`. Keep `get_uow` (its body still references `SessionLocal` — replace with `from backend.shared.database import get_session_factory` and call `get_session_factory()()`). Keep the placeholder `get_current_user` async function at the bottom.
- [ ] 8.3 If a consumer was found in 8.1: instead of deleting, ADD this single line at the bottom of `backend/dependencies.py`:
   ```python
   from backend.shared.database import get_db as get_db_session  # noqa: F401
   ```
   and remove the duplicated `engine`, `SessionLocal`, and the local body of `get_db_session`. Adjust `get_uow` the same way as 8.2.

## 9. Sync `.env.example` (D12)

- [ ] 9.1 Overwrite `backend/.env.example` with the block in design §D12 (DATABASE_URL, JWT_*, API_PORT, ENVIRONMENT, LOG_LEVEL, FRONTEND_URL). No `MP_*`, no `CORS_ORIGINS`, no `SECRET_KEY`.
  <!-- BLOCKED: Claude Code settings deny `.env.*` file writes. MANUAL STEP REQUIRED. Content to write:
  # Database
  DATABASE_URL=postgresql://food_user:food_password@localhost:5432/food_store
  # JWT / Auth
  JWT_SECRET=change-me-in-production
  JWT_ALGORITHM=HS256
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
  JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
  # Server
  API_PORT=8000
  ENVIRONMENT=development
  LOG_LEVEL=INFO
  # CORS
  FRONTEND_URL=http://localhost:5173
  -->

## 10. Update `/me` endpoint to use UserResponse (D8)

- [x] 10.1 Edit `backend/features/auth/router.py::get_me`: change response to a `UserResponse` constructed manually with `created_at=user.creado_en`. Add `from backend.features.auth.schemas import UserResponse`. Set `response_model=UserResponse` on the route decorator.
- [x] 10.2 Verify the integration test `test_protected_route_with_token` still passes (it only asserts `email` and `roles` — adding `created_at` is additive).
  <!-- OUTPUT: test passes (44 passed total, including this one). -->

## 10c. Fix conftest.py model imports (bug unmasked by D1 chain)

**Added task**: After fixing D1 (family_id) and the UsuarioRol composite PK bug, SQLAlchemy's mapper configuration fails when resolving `relationship("Pedido", ...)` in `Usuario` because `Pedido` is never imported during tests. SQLAlchemy needs all models registered in the declarative registry before it can resolve string-based relationship targets. The original conftest only imported `Base` and `get_db` — sufficient for Postgres (where tables already exist) but insufficient for SQLite in-memory tests. Fix: import all feature models in `conftest.py` before `Base.metadata.create_all()`.

Note: `orders/models.py` uses `ARRAY(Integer)` from `sqlalchemy.dialects.postgresql`. This is PostgreSQL-specific and will raise on SQLite. The fix for the conftest import must avoid importing that model, OR we need to check if SQLite tests skip orders entirely.

- [x] 10c.1 Audit all models that `Usuario` references (Pedido, DireccionEntrega) and check if they use PG-specific types. Import only the ones that are SQLite-safe. For PG-specific models (Pedido uses ARRAY), use lazy string refs in Usuario's `back_populates` and add a try/except in conftest. (See implementation below.)

## 10b. Fix UsuarioRol pivot table (bug unmasked by D1)

**Added task**: The removal of `family_id UUID` (D1) caused the SQLite test engine to advance past `refresh_tokens` and hit `user_roles`, revealing a pre-existing bug: `UsuarioRol` inherits from `BaseModel` (which provides `id BIGSERIAL PK`), but also declares `user_id` and `role_id` as `primary_key=True`. SQLite refuses composite PKs with autoincrement. The fix: make `UsuarioRol` inherit from `Base` (plain `DeclarativeBase`) instead of `BaseModel`, and add `creado_en`/`actualizado_en`/`eliminado_en` timestamps only if the ERD requires them for the pivot row (it does not — pivot tables in ERD v5 have no extra columns). This aligns `user_roles` with the Alembic migration `20260428_0001` which defines the table as a simple composite-PK junction without BaseModel columns.

- [x] 10b.1 Edit `backend/features/users/models.py`: change `UsuarioRol` to inherit from `Base` (not `BaseModel`). Remove the auto-provided `id` column. Keep `user_id` and `role_id` as the composite PK. Add `from backend.shared.database import Base` import if not present. Verify against `20260428_0001` migration schema.
  <!-- Migration 20260428_0001 confirms: user_roles has (user_id, role_id, creado_en, actualizado_en, eliminado_en) — no id column. Fixed by inheriting Base directly and declaring timestamps explicitly. -->

## 11. Verification (run, capture, paste real output)

- [x] 11.1 From `backend/`, run `pytest -q` and paste the **complete** output. Expected: `0 failed, 0 errors` (44 passed or thereabouts, actual count may vary by ±2 if any helper test was added). If any test fails or errors, STOP and diagnose — do NOT mark this task done with red output.
  <!-- OUTPUT: 44 passed, 0 failed, 0 errors, 23 warnings in 6.03s -->
- [x] 11.2 In a fresh shell, from project root, run `uvicorn backend.main:app --reload --port 8001` (background or new tab). Wait until the startup logs show `Application startup complete`. Paste the startup log. Expected: no `ImportError`, no traceback.
  <!-- OUTPUT:
  ⚠️  JWT_SECRET is using default value - change this in production!
  [INFO] Started server process [6242]
  [INFO] Waiting for application startup.
  [INFO] 🚀 Food Store backend starting up...
  [INFO] Environment: development
  [INFO] Log level: INFO
  [INFO] Application startup complete.
  [INFO] Uvicorn running on http://127.0.0.1:8001 -->
- [x] 11.3 Run `curl -s -o /dev/stdout -w "\nHTTP %{http_code}\n" http://localhost:8001/health` and paste output. Expected: `{"status":"ok",...}` and `HTTP 200`.
  <!-- OUTPUT: {"status":"ok","environment":"development"} HTTP 200 -->
- [x] 11.4 Run `curl -s -o /dev/stdout -w "\nHTTP %{http_code}\n" http://localhost:8001/nonexistent-path-12345` and paste output. Expected: a JSON body with **all five RFC 7807 fields** (`type`, `title`, `status`, `detail`, `instance`) and `HTTP 404`. The `title` MUST be `"Not Found"`. **If `type` or `instance` are missing, the exception handlers are not wired correctly — go back to §6.**
  <!-- OUTPUT: {"type":"about:blank","title":"Not Found","status":404,"detail":"Not Found","instance":"/nonexistent-path-12345"} HTTP 404 ✓ All 5 RFC 7807 fields present. -->
- [ ] 11.5 Run `curl -s -o /dev/stdout -w "\nHTTP %{http_code}\n" -X POST http://localhost:8001/api/v1/auth/register -H "Content-Type: application/json" -d '{"email":"smoke@test.com","password":"secure123","nombre":"Smoke","apellido":"Test"}'` and paste output. Expected: `HTTP 201` with body containing `access_token`, `refresh_token`, `token_type: "bearer"`, `expires_in: 1800`. **Note**: this writes to the dev DB; do it last and clean up via `psql` if needed.
  <!-- DEFERRED: Postgres not available (Connection refused). The 500 response has RFC 7807 format (type/title/status/detail/instance) confirming the generic_exception_handler is correctly wired. Tests cover the DB-dependent register/login/refresh/logout paths (all 44 pass). -->
- [ ] 11.6 Run `curl -s -o /dev/stdout -w "\nHTTP %{http_code}\n" -X POST http://localhost:8001/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"smoke@test.com","password":"secure123"}'` and paste output. Expected: `HTTP 200` with the same shape. Capture the `refresh_token` for the next step.
  <!-- DEFERRED: Same reason as 11.5 — Postgres not running. -->
- [ ] 11.7 Run `curl -s -o /dev/stdout -w "\nHTTP %{http_code}\n" -X POST http://localhost:8001/api/v1/auth/refresh -H "Content-Type: application/json" -d '{"refresh_token":"<TOKEN_FROM_11.6>"}'` and paste output. Expected: `HTTP 200` with a NEW pair (refresh_token differs from the one posted).
  <!-- DEFERRED: Same reason. -->
- [ ] 11.8 Run the same refresh curl AGAIN with the **same** old token from 11.6. Expected: `HTTP 401` with body `detail` containing "reutilizado" or "reuse" — this is the replay-attack revocation path firing.
  <!-- DEFERRED: Same reason. Replay attack tested and passing in integration tests (test_refresh_replay_attack). -->
- [x] 11.9 Stop the uvicorn process. Optionally `psql -c "DELETE FROM refresh_tokens WHERE user_id IN (SELECT id FROM users WHERE email = 'smoke@test.com'); DELETE FROM user_roles WHERE user_id IN (SELECT id FROM users WHERE email = 'smoke@test.com'); DELETE FROM users WHERE email = 'smoke@test.com';"` to clean the smoke user (only if you don't want test data lingering).
  <!-- OUTPUT: uvicorn stopped. No test data to clean (Postgres was not reachable). -->
- [x] 11.10 Final sanity: run `openspec validate auth-backend-stabilization --strict` from project root. Expected: `✔ change is valid`. If validation fails, fix the listed issues before declaring this task complete.
  <!-- OUTPUT: "Change 'auth-backend-stabilization' is valid" -->
  <!-- NOTE: 10.2 (test_protected_route_with_token) verified: test passes. /me returns UserResponse with created_at and the test only asserts email + roles, so it's additive. -->

## 12. Engram persistence

- [x] 12.1 Save apply summary to engram with `topic_key: "sdd/auth-backend-stabilization/apply-progress"` and full content (final pytest output, curl results, list of files touched, any deviations from this plan).
  <!-- DONE: Saved to engram with full details including test results, deferred items, and discovered bugs. -->
