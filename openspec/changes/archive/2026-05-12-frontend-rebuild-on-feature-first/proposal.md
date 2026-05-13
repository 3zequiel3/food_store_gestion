## Why

El frontend fue reestructurado entre sesiones — pasó de FSD nominal (Descripcion.txt:99) a **Feature-First plano** (decisión F1, ver `docs/frontend-architecture.md`). Ese refactor borró todo lo que cuatro changes ya archivados habían producido: `setup-frontend-core` (#2), `zustand-stores-base` (#5), `auth-frontend-interceptor` (#7) y `navigation-routing-base` (#8). Hoy el frontend tiene únicamente `api/client.ts`, `lib/constants/endpoints.ts`, layouts esqueléticos de 8 líneas y subcarpetas vacías por feature — no hay interceptors, ni stores, ni auth UI, ni guards, ni sidebar, ni tema. Sin esta base reconstruida, la Fase B del roadmap (catálogo, carrito, checkout, pedidos) no puede arrancar. Este change es **el consolidado** que repone esa fundación adaptada a la nueva arquitectura, sin reabrir los archivos ni fragmentar en 4 sub-changes (Opción A elegida por el usuario).

## What Changes

- **NEW** `api/interceptors/auth.ts` — request interceptor que inyecta `Authorization: Bearer` desde `authStore.getState()`, response interceptor que maneja 401 con refresh rotation **single-flight** (cola compartida de requests pendientes durante el refresh).
- **NEW** `api/interceptors/error.ts` — parser de RFC 7807 → clase `ApiError` tipada con `{ type, title, status, detail, instance, errors?: [{ field, message }] }`. Surface de errores field-level para que TanStack Form los mapee de vuelta.
- **NEW** `features/auth/stores/authStore.ts` — Zustand con `persist` (localStorage). Métodos: `setSession`, `clearSession`, `getAccessToken`, `getRefreshToken`, `isAuthenticated`, `hasRole`.
- **NEW** `features/cart/stores/cartStore.ts` — Zustand con `persist`. Items, add/remove/update, total computado. Funciona sin auth.
- **DEFERRED** `paymentStore` y `uiStore` — solo se crean cuando se prueben necesarios (decisión D2). Sin pre-creación especulativa.
- **NEW** Auth feature funcional: schemas Zod (login, register, password change), `auth.service.ts` (login/register/refresh/logout/me), hooks (`useLogin`, `useRegister`, `useLogout`, `useMe`), formularios `LoginForm`, `RegisterForm` con **TanStack Form + Zod** (NO react-hook-form).
- **NEW** Router con guards: `PublicRoute`, `PrivateRoute`, `RoleGuard`. Árbol de rutas nested con `<Outlet />`.
- **NEW** Layout basado en **sidebar** (NO topbar): `Sidebar.tsx` (overlay mobile / persistente desktop), `Header.tsx` (hamburguesa solo mobile), `AppLayout.tsx` (composición). Sidebar role-aware via `authStore.hasRole`.
- **NEW** Páginas de error: `404 NotFound`, `403 Forbidden`, `401 Unauthorized`.
- **NEW** Sistema de design tokens: CSS custom properties en `index.css` + `tailwind.config.ts` con `theme.extend` consumiendo esos tokens. Cero hex hardcodeados en componentes.
- **NEW** TanStack Query defaults globales en `main.tsx`: `retry: 1`, `staleTime: 30_000`, `refetchOnWindowFocus: false`.
- **NEW** Mobile-first responsive: breakpoints `sm/md/lg`, touch targets ≥44px, sidebar overlay <md, tablas con reflow a cards <md.
- **NEW** Iconografía: `lucide-react` (named imports solamente, ESLint rule contra namespace imports).
- **REMOVED** `react-hook-form` y `@hookform/resolvers` del `package.json`. `pnpm install` para limpiar lockfile.
- **BREAKING (interno)** Los specs `frontend-setup`, `http-client`, `zustand-stores`, `auth-forms`, `routing-guards` y `theme-styling` fueron escritos contra FSD nominal y 4 stores fijos. Acá se redefinen contra Feature-First plano + stores justificados.
- **DOCS** `docs/CHANGES.md` marca #2/#5/#7/#8 como `⚠️ Refactored 2026-05-12 — sustituidos por frontend-rebuild-on-feature-first`. Este change pasa a ser bloqueante de Fase B.
- **DOCS** `docs/frontend-architecture.md` recibe sección 12 "Design tokens" y posibles F13-F1N si emergen decisiones nuevas en el apply.

## Capabilities

### New Capabilities
- `frontend-foundation`: capability consolidada que cubre el HTTP client con interceptors (auth + RFC 7807), los stores Zustand justificados (auth + cart), la auth feature funcional (schemas + services + hooks + forms), el router con guards de rol, el layout sidebar-based responsive mobile-first, las páginas de error, los design tokens y los defaults globales de TanStack Query. Esta capability es la **fundación reconstruida** post-refactor Feature-First plano y reemplaza a `frontend-setup` + `http-client` + `zustand-stores` + `auth-forms` + `routing-guards` + `theme-styling` como contrato vivo.

### Modified Capabilities
- `frontend-setup`: la estructura de carpetas pasa de FSD nominal a Feature-First plano (espejo del backend). Se elimina la mención a `entities/` y `widgets/`. La spec vigente queda **superseded** por `frontend-foundation`.
- `http-client`: los interceptors dejan de ser "futuros" — se especifican concretamente (refresh single-flight, `ApiError` class, RFC 7807). La spec vigente queda **superseded** por `frontend-foundation`.
- `zustand-stores`: deja de mandatar 4 stores fijos (auth/cart/payment/ui). Solo `auth` y `cart` se crean; el resto se difiere. La spec vigente queda **superseded** por `frontend-foundation`.
- `auth-forms`: el formulario login/register se reescribe con **TanStack Form** (no react-hook-form). La spec vigente queda **superseded** por `frontend-foundation`.
- `routing-guards`: se redefine sobre el nuevo router (`AppRoute.tsx` actual con 2 rutas → árbol nested completo con guards). La spec vigente queda **superseded** por `frontend-foundation`.
- `theme-styling`: se introduce sistema de design tokens (CSS custom properties + Tailwind `theme.extend`). Sidebar responsive mobile-first. La spec vigente queda **superseded** por `frontend-foundation`.

## Impact

- **Código afectado**:
  - `frontend/package.json` — agregar `lucide-react`, remover `react-hook-form` + `@hookform/resolvers`.
  - `frontend/src/api/interceptors/` — crear `auth.ts`, `error.ts`, `index.ts`.
  - `frontend/src/api/client.ts` — wire interceptors (sin perder la baseURL `/api/v1`).
  - `frontend/src/features/auth/` — completar `stores/authStore.ts`, `schemas/`, `services/auth.service.ts`, `hooks/`, `components/LoginForm.tsx` + `RegisterForm.tsx`.
  - `frontend/src/features/cart/stores/cartStore.ts` — crear.
  - `frontend/src/router/` — agregar `guards/PublicRoute.tsx`, `guards/PrivateRoute.tsx`, `guards/RoleGuard.tsx`. Reescribir `AppRoute.tsx`.
  - `frontend/src/components/layout/` — crear `Sidebar.tsx`, `Header.tsx`, `AppLayout.tsx`.
  - `frontend/src/pages/admin/AdminLayout.tsx` + `frontend/src/pages/client/ClienteLayout.tsx` — adaptar para usar `AppLayout`.
  - `frontend/src/pages/errors/` — crear `NotFound.tsx`, `Forbidden.tsx`, `Unauthorized.tsx`.
  - `frontend/src/index.css` — definir CSS custom properties (tokens).
  - `frontend/tailwind.config.ts` — extender theme leyendo tokens.
  - `frontend/src/main.tsx` — configurar `QueryClient` con defaults globales.
- **APIs**: ninguna mutación del backend. Solo se consumen endpoints ya mapeados en `lib/constants/endpoints.ts` (auth.login, auth.register, auth.refresh, auth.logout, auth.me).
- **Dependencias**: `+lucide-react`, `-react-hook-form`, `-@hookform/resolvers`.
- **Sistemas**: ninguno externo. Solo frontend.
- **Roadmap**: este change pasa a ser **bloqueante de Fase B** (`docs/CHANGES.md`). Los archivados #2/#5/#7/#8 se marcan como refactored, no se reabren.
- **Riesgos**: hidratación tardía de `authStore` antes del primer render (R1), stampede de refresh paralelos (R2), validación Zod laggy en forms grandes (R3), state leak entre layouts admin/cliente si `uiStore` es compartido (R4), bundle bloat si alguien hace namespace import de lucide (R5), testing responsive no automatizado (R6). Mitigaciones detalladas en `design.md`.
