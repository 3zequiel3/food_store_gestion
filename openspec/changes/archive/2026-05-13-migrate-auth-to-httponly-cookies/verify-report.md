# Verify Report: Migrate Auth to HttpOnly Cookies

**Change**: `migrate-auth-to-httponly-cookies`  
**Date**: 2026-05-13  
**Mode**: Standard verify  
**Verdict**: FAIL

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 19 |
| Tasks complete | 19 |
| Tasks incomplete | 0 |

All tasks are marked complete in `tasks.md`, but full backend verification found test-suite regressions in broader integration helpers.

## Build & Tests Execution

### Backend auth-focused tests

✅ Passed

```text
.venv/bin/python -m pytest backend/tests/integration/test_auth.py -q
15 passed, 9 warnings in 4.23s
```

### Backend full integration suite

❌ Failed

```text
.venv/bin/python -m pytest backend/tests/integration -q
13 failed, 462 passed, 11 skipped, 805 warnings in 222.30s
```

Failing tests:

```text
FAILED backend/tests/integration/test_categories.py::TestDelete::test_delete_unauthenticated_returns_401
FAILED backend/tests/integration/test_delivery_addresses.py::test_update_other_user_address_returns_404
FAILED backend/tests/integration/test_delivery_addresses.py::test_delete_other_user_address_returns_404
FAILED backend/tests/integration/test_delivery_addresses.py::test_set_principal_other_user_address_returns_404
FAILED backend/tests/integration/test_ingredients.py::TestIncluidoEliminados::test_sin_auth_incluir_eliminados_no_ve_soft_deleted
FAILED backend/tests/integration/test_products.py::TestRBAC::test_put_unauthenticated_returns_401
FAILED backend/tests/integration/test_products.py::TestRBAC::test_patch_disponibilidad_unauthenticated_returns_401
FAILED backend/tests/integration/test_products.py::TestRBAC::test_patch_stock_unauthenticated_returns_401
FAILED backend/tests/integration/test_products.py::TestRBAC::test_delete_unauthenticated_returns_401
FAILED backend/tests/integration/test_products.py::TestRBAC::test_put_categorias_unauthenticated_returns_401
FAILED backend/tests/integration/test_products.py::TestRBAC::test_post_ingredientes_unauthenticated_returns_401
FAILED backend/tests/integration/test_products.py::TestRBAC::test_delete_ingrediente_unauthenticated_returns_401
FAILED backend/tests/integration/test_products.py::TestIncluidoEliminados::test_sin_auth_incluir_eliminados_no_ve_soft_deleted
```

Observed pattern: tests create authenticated cookies on the shared `TestClient`, then later make requests that are intended to be unauthenticated or from another user. Since auth is now cookie-backed, `headers={}` no longer removes authentication; the TestClient cookie jar still sends the last login cookie. Multi-user address tests also pass empty headers for both users, so the last login cookie wins.

### Frontend tests and TypeScript

✅ Passed

```text
pnpm -C frontend exec vitest run
Test Files  2 passed (2)
Tests       4 passed (4)

pnpm -C frontend exec tsc -b
exit 0
```

### OpenSpec validation

✅ Passed

```text
openspec validate migrate-auth-to-httponly-cookies --strict
Change 'migrate-auth-to-httponly-cookies' is valid
```

## Spec Compliance Matrix

| Requirement | Scenario | Evidence | Result |
|-------------|----------|----------|--------|
| Auth endpoints transport tokens via HttpOnly cookies | Login sets `access_token` and `refresh_token`, no raw token JSON | `backend/tests/integration/test_auth.py::TestLogin::test_login_success` passed | ✅ COMPLIANT |
| Auth endpoints transport tokens via HttpOnly cookies | Refresh rotates cookies and revokes old token | `backend/tests/integration/test_auth.py::TestTokenRefresh::test_refresh_success` passed | ✅ COMPLIANT |
| Auth endpoints transport tokens via HttpOnly cookies | Protected request authenticates from `access_token` cookie | `backend/tests/integration/test_auth.py::TestProtectedRoutes::test_protected_route_with_cookie` passed | ✅ COMPLIANT |
| Frontend auth service uses cookie session responses | Login returns `{ user, expires_in, token_type: "cookie" }` | Static inspection of `auth.service.ts`; covered indirectly by TS and auth types | ⚠️ PARTIAL |
| Axios sends cookies and does not inject Bearer | `withCredentials: true`, no Authorization injection | `frontend/src/api/__tests__/client.test.ts` passed | ✅ COMPLIANT |
| Guards use cookie-backed session state | Private/public routes derive from `user !== null` | Static inspection; TypeScript passed | ⚠️ PARTIAL |
| Auth store does not persist tokens | Persisted auth state excludes old/new token fields | `frontend/src/features/auth/stores/__tests__/authStore.test.ts` passed | ✅ COMPLIANT |
| Business endpoint contracts remain unchanged | Broad backend integration suite passes | Full integration suite failed | ❌ FAILING |

**Compliance summary**: 5 compliant, 2 partial, 1 failing.

## Correctness / Static Evidence

| Area | Status | Notes |
|------|--------|-------|
| Backend cookie settings | ✅ Implemented | `backend/config.py` has cookie names, paths, `SameSite=lax`, `Secure=false`. |
| Cookie helpers | ✅ Implemented | `set_auth_cookies`/`clear_auth_cookies` set/delete HttpOnly cookies with matching paths. |
| Auth router | ✅ Implemented | Login/register/refresh set cookies and return `AuthSessionResponse`; logout clears cookies. |
| Auth dependency | ✅ Implemented | Reads access token from cookie first; Bearer fallback remains for tooling/tests. |
| Frontend client | ✅ Implemented | Axios has `withCredentials: true`. |
| Frontend interceptor | ✅ Implemented | No request Authorization injection; refresh is single-flight POST with credentials. |
| Auth store migration | ✅ Implemented | Persists only `user`; version migration strips old token fields. |
| Backend broad tests | ❌ Incomplete | Several tests/helpers still assume header-based auth isolation and fail with TestClient cookies. |

## Coherence with Design

| Decision | Followed? | Notes |
|----------|-----------|-------|
| `access_token` + `refresh_token` HttpOnly cookies | ✅ Yes | Backend sets both cookies; frontend does not read raw tokens. |
| Dev flags `HttpOnly=true`, `SameSite=Lax`, `Secure=false` | ✅ Yes | Confirmed in config/helper and auth tests. |
| Cookie paths access `/api/v1`, refresh `/api/v1/auth` | ✅ Yes | Config and helper match design. |
| Public auth response excludes raw tokens | ✅ Yes | `AuthSessionResponse` returns `user`, `expires_in`, `token_type`. |
| No CSRF token in this change | ✅ Yes | Matches design/out-of-scope decision. |
| Business endpoints unchanged | ⚠️ Needs more cleanup | Code paths mostly preserved, but test suite now exposes cookie-state assumptions in broad integration tests. |

## Issues Found

### CRITICAL

1. Full backend integration suite fails: `13 failed, 462 passed, 11 skipped`.
2. Several tests intended to be unauthenticated still run authenticated because the shared `TestClient` keeps cookies after helper login.
3. Multi-user address tests pass empty headers for both users under cookie auth, so the last login cookie determines the user and anti-leak assertions become invalid.

### WARNING

1. Some frontend scenarios are verified by TypeScript/static inspection rather than component-level route tests.
2. Bearer fallback remains in backend dependency intentionally for tooling/tests; this is coherent with current implementation but should be documented if kept long-term.

### SUGGESTION

1. Update broad backend tests/helpers to use explicit client cookie isolation: `client.cookies.clear()`, separate `TestClient` instances, or helper functions that return authenticated clients/sessions instead of `{}` headers.
2. Re-run full `backend/tests/integration -q` after that cleanup before archive.

## Verdict

**FAIL** — the auth-focused backend tests, frontend tests, TypeScript, and OpenSpec validation pass, but full backend integration verification fails due remaining cookie-auth test isolation issues. Do not archive yet.
