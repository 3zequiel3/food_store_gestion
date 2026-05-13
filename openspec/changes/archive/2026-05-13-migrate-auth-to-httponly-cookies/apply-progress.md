# Apply Progress: Migrate Auth to HttpOnly Cookies

## Mode
Standard apply. Workload decision resolved by user approval; chain strategy recorded as `feature-branch-chain`.

## Completed Tasks
- 1.1 Delta specs for auth, auth-service, http-client, routing-guards, zustand-stores.
- 1.2 Backend auth cookie settings in `backend/config.py`.
- 1.3 Cookie helpers in `backend/features/auth/cookies.py`.
- 1.4 Public `AuthSessionResponse` excluding raw tokens.
- 2.1 Login/register set cookies and return session metadata.
- 2.2 Refresh/logout read refresh cookie, rotate/revoke, set/clear cookies.
- 2.3 `get_current_user` and optional auth read access cookie.
- 2.4 Existing AuthService token generation/rotation preserved.
- 3.1 Axios `withCredentials: true`.
- 3.2 Auth interceptor no longer injects Bearer; refresh is cookie-based.
- 3.3 Auth service uses cookie contracts.
- 3.4 Auth store no longer has token fields.
- 3.5 Login/register/logout/me hooks updated for cookie sessions.
- 4.1 Backend auth integration tests updated and passing.
- 4.2 Backend integration helpers updated to stop parsing `access_token` JSON; invalid Bearer tests preserved.
- 4.3 Frontend auth store/client tests added for no token localStorage and no Authorization header.
- 4.4 Targeted backend auth/user/order/payment tests and frontend Vitest/TypeScript checks pass.
- 5.1 Stale backend docs/comments updated from Bearer/JWT wording to cookie-backed sessions.
- 5.2 `food-store-auth` persist version migration strips old `accessToken`/`refreshToken` payloads and keeps only `user`.

## Verification
- PASS: `.venv/bin/python -m pytest backend/tests/integration/test_auth.py -q` → 15 passed.
- PASS: `.venv/bin/python -m pytest backend/tests/integration/test_auth.py backend/tests/integration/test_user_profile.py backend/tests/integration/test_orders.py backend/tests/integration/test_payments.py -q` → 84 passed, 6 skipped.
- PASS: `pnpm -C frontend exec vitest run` → 2 files / 4 tests passed.
- PASS: `pnpm -C frontend exec tsc -b`.
- PASS: `openspec validate migrate-auth-to-httponly-cookies --strict`.

## Remaining
- None. Ready for verify.
