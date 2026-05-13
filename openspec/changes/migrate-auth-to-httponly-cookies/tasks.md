# Tasks: Migrate Auth to HttpOnly Cookies

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 650-900 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 backend cookies/specs → PR2 frontend auth → PR3 tests cleanup |
| Delivery strategy | ask-on-risk, resolved by user approval |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend cookie auth contract | PR 1 | Auth router/deps/schemas/config + backend tests. |
| 2 | Frontend cookie session flow | PR 2 | Depends on PR 1; apiClient/interceptor/store/hooks. |
| 3 | Spec/test cleanup | PR 3 | Delta specs, stale token cleanup, regression tests. |

## Phase 1: Specs and Backend Foundation

- [x] 1.1 Add delta specs under `openspec/changes/migrate-auth-to-httponly-cookies/specs/` for `auth`, `auth-service`, `http-client`, `routing-guards`, and `zustand-stores`.
- [x] 1.2 Add auth cookie settings to `backend/config.py`: names, paths, `SameSite=Lax`, `Secure=false`, max-age values.
- [x] 1.3 Create `backend/features/auth/cookies.py` with helpers to set access/refresh cookies and clear both cookies.
- [x] 1.4 Update `backend/features/auth/schemas.py` with public cookie-session response type that excludes raw tokens.

## Phase 2: Backend Cookie Auth

- [x] 2.1 Update `backend/features/auth/router.py` login/register to call `AuthService`, set cookies from generated tokens, and return user/session metadata only.
- [x] 2.2 Update `backend/features/auth/router.py` refresh/logout to read `refresh_token` from cookies, rotate/revoke through `AuthService`, and set/clear cookies.
- [x] 2.3 Update `backend/features/auth/dependencies.py` so `get_current_user` and `get_optional_user` read `access_token` from `Request.cookies`.
- [x] 2.4 Preserve existing `AuthService` token generation, hashing, rotation, replay detection, and UoW boundaries.

## Phase 3: Frontend Cookie Session Flow

- [x] 3.1 Update `frontend/src/api/client.ts` with `withCredentials: true`.
- [x] 3.2 Rewrite `frontend/src/api/interceptors/auth.ts` to remove Bearer injection and perform single-flight cookie refresh with `POST /auth/refresh` no body.
- [x] 3.3 Update `frontend/src/features/auth/services/auth.service.ts` so login/register/refresh/logout use cookie contracts and never pass raw tokens.
- [x] 3.4 Update `frontend/src/features/auth/stores/authStore.ts` to remove token fields and localStorage token persistence; store user/session status only.
- [x] 3.5 Update `frontend/src/features/auth/hooks/useLogin.ts`, `useRegister.ts`, `useLogout.ts`, and `useMe.ts` for cookie-backed session rehydration.

## Phase 4: Tests and Verification

- [x] 4.1 Update backend auth tests to assert `Set-Cookie` flags, no raw token JSON, cookie-backed `/auth/me`, refresh rotation, and logout clearing.
- [x] 4.2 Update backend test helpers that build `Authorization: Bearer` headers to use TestClient cookies where browser auth is expected.
- [x] 4.3 Update frontend tests for auth store/interceptor/services to assert no token localStorage and no Authorization header.
- [x] 4.4 Run targeted backend auth/user/order/payment tests and frontend Vitest auth tests.

## Phase 5: Cleanup

- [x] 5.1 Remove stale comments/types mentioning frontend token persistence or Bearer injection.
- [x] 5.2 Add startup cleanup for old `food-store-auth` token payload if needed to avoid stale sessions.
