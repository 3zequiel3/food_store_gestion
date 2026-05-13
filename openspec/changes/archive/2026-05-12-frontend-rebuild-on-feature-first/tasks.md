## 1. Cleanup dependencias y bootstrap

- [x] 1.1 Editar `frontend/package.json`: agregar `lucide-react` en `dependencies`.
- [x] 1.2 Editar `frontend/package.json`: remover `react-hook-form` y `@hookform/resolvers` de `dependencies`.
- [x] 1.3 Ejecutar `pnpm install` en `frontend/` para regenerar `pnpm-lock.yaml`.
- [x] 1.4 Verificar con `rg "react-hook-form" frontend/` que no haya imports residuales.
- [x] 1.5 Verificar con `rg "lucide-react" frontend/package.json` que la dep esté agregada y con versión fija.

## 2. Design tokens dark-first via Tailwind v4 `@theme` en `src/index.css`

- [x] 2.1 Reescribir `frontend/src/index.css` COMPLETO con la directiva `@theme { ... }` de Tailwind v4 conteniendo el set comprehensivo de tokens DARK como default:
  - Color pairs (OKLCH): `--color-background`, `--color-foreground`, `--color-card`, `--color-card-foreground`, `--color-popover`, `--color-popover-foreground`, `--color-primary`, `--color-primary-foreground`, `--color-secondary`, `--color-secondary-foreground`, `--color-muted`, `--color-muted-foreground`, `--color-accent`, `--color-accent-foreground`, `--color-destructive`, `--color-destructive-foreground`, `--color-success`, `--color-success-foreground`, `--color-warning`, `--color-warning-foreground`, `--color-border`, `--color-input`, `--color-ring`.
  - Typography: `--font-sans`, `--font-mono`.
  - Radius: `--radius-sm`, `--radius`, `--radius-lg`, `--radius-xl`.
  - Shadows dark-tuned: `--shadow-sm`, `--shadow`, `--shadow-lg`.
  - Paleta starter food-oriented (primary warm orange/amber, background warm-dark, no negro frío).
- [x] 2.2 Agregar override `:root.light { ... }` con tokens equivalentes en valores claros (mismo set de variables, distintos OKLCH).
- [x] 2.3 Agregar `html { color-scheme: dark }` y `html.light { color-scheme: light }` para que scrollbars/form controls nativos respeten el tema.
- [x] 2.4 En `@layer base`: aplicar `body { background-color: var(--color-background); color: var(--color-foreground); font-family: var(--font-sans); -webkit-font-smoothing: antialiased; }`.
- [x] 2.5 Revisar `frontend/tailwind.config.ts`: en Tailwind v4 con `@theme` directiva el config TS queda casi vacío. Mantenerlo solo si hay configuración legacy necesaria; auto-content-scanning de v4 hace el resto.
- [x] 2.6 Verificar build: `pnpm build` produce CSS final con todas las clases utility derivadas de los tokens (`bg-primary`, `text-foreground`, etc.) funcionando. (OK humano 2026-05-12)
- [x] 2.7 Smoke visual: arrancar `pnpm dev`, verificar que el body se vea DARK por default (background near-black, foreground near-white), y que agregar `class="light"` al `<html>` desde DevTools cambie todo a light en vivo sin reload. (OK humano 2026-05-12)
- [x] 2.8 Documentar en `docs/frontend-architecture.md` agregando sección "12. Design tokens": stack Tailwind v4, ubicación (`src/index.css`), dark-mode first, cómo extender tokens, antipatrón hex hardcodeado, OKLCH como formato.

## 3. HTTP interceptors (auth + error)

- [x] 3.1 Crear `frontend/src/api/interceptors/error.ts` exportando clase `ApiError extends Error` con campos `type`, `title`, `status`, `detail`, `instance?`, `errors?: Array<{ field, message }>` y función `applyErrorInterceptor(client: AxiosInstance): void`.
- [x] 3.2 El error interceptor debe rechazar con `ApiError` instance para responses RFC 7807, y con un `ApiError` genérico (`status: 0`, `title: 'Error de conexión'`, `detail: 'No se pudo conectar al servidor'`) para network errors.
- [x] 3.3 Crear `frontend/src/api/interceptors/auth.ts` exportando función `applyAuthInterceptor(client: AxiosInstance): void` con request interceptor que inyecta `Authorization: Bearer <token>` desde `useAuthStore.getState().getAccessToken()`.
- [x] 3.4 En `frontend/src/api/interceptors/auth.ts`: implementar response interceptor con single-flight refresh — variable de módulo `let refreshPromise: Promise<string> | null` que se comparte entre 401s concurrentes.
- [x] 3.5 En el refresh exitoso: llamar `useAuthStore.getState().setSession(...)`, resolver la cola, retry del request original con nuevo token.
- [x] 3.6 En el refresh fallido (o 401 sobre `/auth/refresh` mismo): llamar `clearSession()`, rechazar la cola, `window.location.assign('/login')`. Prevenir loop infinito de refresh.
- [x] 3.7 Crear `frontend/src/api/interceptors/index.ts` reexportando `ApiError`, `applyAuthInterceptor`, `applyErrorInterceptor`.
- [x] 3.8 Editar `frontend/src/api/client.ts`: importar y aplicar los dos interceptors **antes** del `export const apiClient` (wiring eager — decisión D7).
- [x] 3.9 Verificar tipado: `pnpm tsc --noEmit` en `frontend/` no debe reportar errores en los interceptors.

## 4. Stores Zustand (authStore + cartStore)

- [x] 4.1 Crear `frontend/src/features/auth/types/auth.types.ts` con interfaces `Rol { codigo, nombre }`, `Usuario { id, email, nombre, apellido, roles: Rol[] }`, `LoginCredentials`, `RegisterPayload`, `TokenPair { access_token, refresh_token }`, `LoginResponse extends TokenPair { user: Usuario }`.
- [x] 4.2 Crear `frontend/src/features/auth/stores/authStore.ts` con Zustand + `persist` middleware (storage key `food-store-auth`).
- [x] 4.3 El authStore expone state `{ accessToken: string | null, refreshToken: string | null, user: Usuario | null }` y actions `setSession({ accessToken, refreshToken, user })`, `clearSession()`, getters `getAccessToken()`, `getRefreshToken()`, `isAuthenticated()`, `hasRole(code: string)`.
- [x] 4.4 `partialize` del persist enumera explícitamente `accessToken`, `refreshToken`, `user` (excluye cualquier campo transitorio futuro).
- [x] 4.5 Crear `frontend/src/features/cart/types/cart.types.ts` con interface `CartItem { producto_id, nombre, precio, cantidad, imagen_url?, personalizacion? }`.
- [x] 4.6 Crear `frontend/src/features/cart/stores/cartStore.ts` con Zustand + `persist` (storage key `food-store-cart`).
- [x] 4.7 El cartStore expone state `{ items: CartItem[] }` y actions `addItem(item, cantidad?)`, `removeItem(producto_id)`, `updateQuantity(producto_id, cantidad)`, `clearCart()`, selectores `getTotalItems()`, `getTotalPrice()`.
- [x] 4.8 Implementar lógica: `addItem` con producto_id existente → incrementa cantidad; `updateQuantity` con `cantidad <= 0` → remueve item.
- [x] 4.9 Verificar que `clearSession()` NO toca `cartStore` (test manual o smoke: login, agregar item, logout, ver que el item sigue). (OK humano 2026-05-12)
- [x] 4.10 Confirmar que NO se crean `paymentStore` ni `uiStore` en este change.

## 5. Auth feature (schemas + service + hooks + forms)

- [x] 5.1 Crear `frontend/src/features/auth/schemas/loginSchema.ts`: `z.object({ email: z.string().email('Email inválido'), password: z.string().min(1, 'Ingresá tu contraseña') })`.
- [x] 5.2 Crear `frontend/src/features/auth/schemas/registerSchema.ts`: `z.object({ nombre: z.string().min(2, 'Mínimo 2 caracteres').max(80), apellido: z.string().min(2).max(80), email: z.string().email('Email inválido'), password: z.string().min(8, 'Mínimo 8 caracteres') })`.
- [x] 5.3 Crear `frontend/src/features/auth/schemas/passwordChangeSchema.ts`: `z.object({ current_password: z.string().min(1), new_password: z.string().min(8) })`.
- [x] 5.4 Crear `frontend/src/features/auth/services/auth.service.ts` con funciones `login`, `register`, `refresh`, `logout`, `me` — todas importando paths desde `lib/constants/endpoints.ts` (sin hardcodear).
- [x] 5.5 Cada función del service usa `apiClient` y retorna el response tipado según `auth.types.ts`.
- [x] 5.6 Crear `frontend/src/features/auth/hooks/useLogin.ts` con `useMutation` de TanStack Query que en `onSuccess` llama `useAuthStore.getState().setSession(...)`.
- [x] 5.7 Crear `frontend/src/features/auth/hooks/useRegister.ts` análogo a useLogin.
- [x] 5.8 Crear `frontend/src/features/auth/hooks/useLogout.ts` con `useMutation` que en `onSettled` llama `clearSession()` y `queryClient.clear()`.
- [x] 5.9 Crear `frontend/src/features/auth/hooks/useMe.ts` con `useQuery` (`queryKey: ['auth','me']`, `enabled: useAuthStore((s) => s.isAuthenticated())`).
- [x] 5.10 Crear `frontend/src/features/auth/components/LoginForm.tsx` con **TanStack Form** + zod adapter (`@tanstack/zod-form-adapter` o equivalente), validators `onBlur: loginSchema`.
- [x] 5.11 LoginForm: en submit llama `useLogin().mutate(...)`. En error con `ApiError.status === 401` muestra "Credenciales inválidas" inline.
- [x] 5.12 LoginForm: botón submit deshabilitado durante `isPending` con indicador de loading.
- [x] 5.13 Crear `frontend/src/features/auth/components/RegisterForm.tsx` análogo a LoginForm usando `registerSchema` y `useRegister`.
- [x] 5.14 RegisterForm: en error con `ApiError.status === 409` muestra error inline atado al campo `email`.
- [x] 5.15 Verificar con `rg "react-hook-form" frontend/src/features/auth/` que no haya imports de RHF.
- [x] 5.16 Verificar con `rg "from '@tanstack/react-form'" frontend/src/features/auth/components/` que los forms usen TanStack Form.

## 6. Router con guards y nested routes

- [x] 6.1 Crear `frontend/src/router/guards/PublicRoute.tsx`: si `useAuthStore.isAuthenticated()` redirige a `/`, si no renderiza `<Outlet />`.
- [x] 6.2 Crear `frontend/src/router/guards/PrivateRoute.tsx`: si NO autenticado redirige a `/login` con `state: { from: location.pathname }`, si sí renderiza `<Outlet />`.
- [x] 6.3 Crear `frontend/src/router/guards/RoleGuard.tsx` con prop `roles: string[]`: si `roles.some(r => hasRole(r))` renderiza `<Outlet />`, si no redirige a `/403`.
- [x] 6.4 Crear páginas de error en `frontend/src/pages/errors/`:
  - `NotFound.tsx` (404, "Página no encontrada", botón "Volver al inicio")
  - `Forbidden.tsx` (403, "Acceso denegado", botón "Volver al inicio")
  - `Unauthorized.tsx` (401, "Sesión expirada", botón "Iniciar sesión" linkeando a `/login`)
- [x] 6.5 Crear páginas auth en `frontend/src/pages/`:
  - `LoginPage.tsx` que renderiza `<LoginForm />`
  - `RegisterPage.tsx` que renderiza `<RegisterForm />`
- [x] 6.6 Reescribir `frontend/src/router/AppRoute.tsx` con árbol nested: `<Routes><Route element={<PublicRoute />}>... <Route element={<PrivateRoute />}><Route element={<AppLayout />}><Route element={<RoleGuard roles={['ADMIN','STOCK','PEDIDOS']} />}>... `.
- [x] 6.7 Agregar rutas explícitas `/login`, `/register`, `/admin/*`, `/cliente/*`, `/401`, `/403`, y catch-all `*` → `<NotFound />`.
- [x] 6.8 Verificar manual: nav a `/admin` sin auth → redirige a `/login` con `state.from`; nav a `/` con CLIENTE → `/cliente/*`; nav a `/admin` con CLIENTE → `/403`. (OK humano 2026-05-12; bugs CLIENTE→CLIENT y roles shape resueltos in-session)

## 7. Layout dual: desktop sidebar hover-expand + mobile bottom-nav

### 7.A — Desktop: Sidebar hover-expand con lock

- [x] 7.A.1 Crear `frontend/src/components/layout/Sidebar.tsx`. State management: `useState<'hover' | 'locked-open' | 'locked-closed'>('hover')` para el modo. State derivado: `isExpanded` (true si `locked-open` o si `hover && mouseInside`).
- [x] 7.A.2 Width transitions: `w-16` (64px) cuando collapsed, `w-60` (240px) cuando expanded, con `transition-all duration-150 ease-out`.
- [x] 7.A.3 Mouse events: `onMouseEnter` setea `mouseInside=true`, `onMouseLeave` setea `false`. Solo afectan layout si modo === 'hover'.
- [x] 7.A.4 Botón de toggle en header del sidebar (ícono `PanelLeftClose` / `PanelLeftOpen` de lucide). Click cicla: `hover → locked-open → locked-closed → hover`.
- [x] 7.A.5 Items del sidebar: ícono lucide siempre visible centrado, label visible solo en `isExpanded`. Active route detection vía `useLocation()` con clase activa `bg-accent text-accent-foreground`.
- [x] 7.A.6 Submenús: solo se renderizan en `isExpanded`. El submenú del item activo (matching `location.pathname.startsWith(item.path)`) se autoexpande; los demás colapsados. Indicador: `ChevronRight` que rota a `ChevronDown` cuando expanded.
- [x] 7.A.7 Nav items arrays role-aware:
  - `ADMIN_NAV`: Productos (icon `Package`, submenús: Listado/Crear), Pedidos (`ClipboardList`), Usuarios (`Users`), Métricas (`BarChart3`), Categorías (`FolderTree`), Ingredientes (`Carrot`).
  - `CLIENT_NAV`: Catálogo (`ShoppingBag`), Mis Pedidos (`ListOrdered`), Direcciones (`MapPin`), Perfil (`User`).
- [x] 7.A.8 El sidebar lee `useAuthStore.hasRole(...)` para elegir nav array. Si tiene múltiples roles (ADMIN+CLIENT, raro), prioridad ADMIN > PEDIDOS > STOCK > CLIENT.
- [x] 7.A.9 Sidebar visible SOLO en `md+` (`hidden md:flex`).

### 7.B — Mobile: BottomNav + TopNavbar

- [x] 7.B.1 Crear `frontend/src/components/layout/BottomNav.tsx`. Fixed bottom (`fixed bottom-0 left-0 right-0 h-16 bg-card border-t border-border`). Visible solo `<md` (`md:hidden`).
- [x] 7.B.2 4-5 items principales role-aware:
  - Admin: Productos, Pedidos, Usuarios, Métricas, Más (`MoreHorizontal` → abre `MobileMoreDrawer`)
  - Cliente: Catálogo, Mis Pedidos, Direcciones, Perfil
- [x] 7.B.3 Cada item: ícono lucide (`h-6 w-6`) + label corto (`text-xs`). Active state: ícono filled (versión `*-fill` de lucide o `fill-current`) + label `text-primary`.
- [x] 7.B.4 Touch targets: cada item ≥56×56px (iOS HIG).
- [x] 7.B.5 Crear `frontend/src/components/layout/MobileMoreDrawer.tsx` (admin only): sheet bottom-up con items secundarios (Categorías, Ingredientes). Usa `<dialog>` nativo o un sheet custom Tailwind.
- [x] 7.B.6 Crear `frontend/src/components/layout/TopNavbar.tsx`. Fixed top (`fixed top-0 left-0 right-0 h-14 bg-card border-b border-border z-10`). Contiene: logo izquierda, slots derecha.
- [x] 7.B.7 TopNavbar contenido derecha role-aware:
  - Cliente: ícono `ShoppingCart` con badge (count items del `cartStore.getTotalItems()`) — click abre `CartDrawer`. Avatar/menú user.
  - Admin: solo avatar/menú user. NO carrito.
- [x] 7.B.8 TopNavbar visible en ambos viewports. En desktop convive con el sidebar (sidebar `top-14` para no taparse).
- [x] 7.B.9 Crear `frontend/src/components/layout/CartDrawer.tsx`. Sheet lateral-derecho (`fixed right-0 inset-y-0 w-full sm:max-w-md`). Lista de items del cart, total, botón "Ir al checkout" (placeholder por ahora — el checkout llega en Sprint 9 #26). Reusable para mobile + desktop.

### 7.C — Composición: AppLayout

- [x] 7.C.1 Crear `frontend/src/components/layout/AppLayout.tsx` que compone: `<TopNavbar />` + `<Sidebar />` (desktop only) + `<main>{children/Outlet}</main>` + `<BottomNav />` (mobile only).
- [x] 7.C.2 Layout grid: `<TopNavbar />` siempre top fijo. `<main>` con `pt-14 md:pl-16` (offset top por navbar + offset left por sidebar collapsed). Cuando sidebar `locked-open`, `<main>` recibe `md:pl-60`. En mobile, además `pb-16` para no quedar tapado por el bottom nav.
- [x] 7.C.3 `useEffect` que cierra el `CartDrawer` y el `MobileMoreDrawer` en cada `location.pathname` change.
- [x] 7.C.4 `useMediaQuery('(min-width: 768px)')` hook helper en `lib/hooks/useMediaQuery.ts` para condicionar renders.

### 7.D — Integración con pages existentes

- [x] 7.D.1 Adaptar `frontend/src/pages/admin/AdminLayout.tsx`: el shell global lo provee `AppLayout`, este componente queda con composición específica del admin (header del admin si hace falta, breadcrumbs, etc.) y un `<Outlet />`.
- [x] 7.D.2 Adaptar `frontend/src/pages/client/ClienteLayout.tsx` análogo.

### 7.E — Touch targets y responsive QA

- [x] 7.E.1 Verificar touch targets: hamburguesa NO existe (no se usa), items sidebar `h-10 px-3` mínimo (44px alto efectivo), items bottom-nav `h-14` mínimo (56px), botón cart en TopNavbar `h-11 w-11` mínimo (44px).
- [x] 7.E.2 Verificar manual viewports 375px / 768px / 1280px en DevTools:
  - 375px: NO sidebar visible, TopNavbar visible, BottomNav visible. Cart en TopNavbar abre drawer. Active item en BottomNav bien destacado.
  - 768px: sidebar visible collapsed (64px), TopNavbar visible, NO bottom nav. Hover sidebar → expand a 240px. Click toggle → lock open.
  - 1280px: igual a 768px, layout cómodo con más espacio para contenido.
  (OK humano 2026-05-12)
- [x] 7.E.3 Smoke transitions: hover sidebar suave (sin flicker), bottom-nav active state inmediato al navegar, cart drawer slide-in/out limpio. (OK humano 2026-05-12)

## 8. QueryClient defaults globales

- [x] 8.1 Editar `frontend/src/main.tsx`: configurar `new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false } } })`.
- [x] 8.2 Wrappear `<App />` con `<QueryClientProvider client={queryClient}>` (si aún no está).
- [x] 8.3 Verificar import: `from '@tanstack/react-query'`.

## 9. ESLint rule contra namespace imports de lucide

- [x] 9.1 Editar `frontend/eslint.config.*` (o el equivalente flat config / `.eslintrc`) y agregar regla `no-restricted-imports` con un patrón que bloquee `import * as ... from 'lucide-react'`.
- [x] 9.2 Probar que `pnpm lint` fallas si alguien introduce un namespace import.
- [x] 9.3 Documentar el antipatrón en `docs/frontend-architecture.md` §10 (Antipatrones).

## 10. Docs roadmap y arquitectura

- [x] 10.1 Editar `docs/CHANGES.md`: marcar `#2 setup-frontend-core`, `#5 zustand-stores-base`, `#7 auth-frontend-interceptor`, `#8 navigation-routing-base` con sufijo `⚠️ Refactored 2026-05-12 — sustituido por frontend-rebuild-on-feature-first`. Conservar el ✅ original tachado o anotado, no borrarlos.
- [x] 10.2 Editar `docs/CHANGES.md`: agregar `frontend-rebuild-on-feature-first` como entry nuevo en la sección apropiada (entre Sprint 6 y Sprint 7, o en una sección "Refactors Fase B-prep"), marcado como **bloqueante de Fase B**.
- [x] 10.3 Editar `docs/CHANGES.md`: actualizar la sección "Estado actual" para reflejar este change pendiente y nota explicativa del refactor.
- [x] 10.4 Editar `docs/frontend-architecture.md`: agregar sección **12. Design tokens** documentando los tokens definidos en `index.css`, cómo Tailwind los consume, y el antipatrón de hex hardcodeado.
- [x] 10.5 Editar `docs/frontend-architecture.md` §10 (Antipatrones): agregar línea sobre namespace imports de lucide.
- [x] 10.6 Editar `docs/frontend-architecture.md` §11 (Pendientes inmediatos): tachar los items resueltos por este change (interceptor auth, interceptor error, authStore, QueryClient defaults, cleanup RHF) y dejar los que quedan abiertos.

## 11. Validación final pre-archive

- [x] 11.1 `pnpm install` limpio en `frontend/`.
- [x] 11.2 `pnpm dev` arranca sin errores ni warnings. (OK humano 2026-05-12)
- [x] 11.3 `pnpm build` produce bundle sin warnings de tipo. (OK humano 2026-05-12)
- [x] 11.4 `pnpm tsc --noEmit` sin errores. (verificado: salida vacía = clean)
- [x] 11.5 `pnpm lint` sin errores (incluye la nueva regla de lucide). (verificado: exit 0)
- [x] 11.6 Smoke manual: register un usuario nuevo → ver redirect a `/` → ver sidebar role-aware (CLIENTE) → logout → ver redirect a `/login` → ver que cart sobrevivió (si se agregó algo). (OK humano 2026-05-12)
- [x] 11.7 Smoke manual single-flight refresh: forzar 401 (token corrupto a mano en localStorage), navegar a página que dispare 2+ queries — verificar en Network tab que solo 1 `/auth/refresh` se dispara. (OK humano 2026-05-12)
- [x] 11.8 Checklist responsive: 375px / 768px / 1280px revisados para LoginPage, RegisterPage, AdminLayout, ClienteLayout, sidebar overlay/persistente. (OK humano 2026-05-12)
- [x] 11.9 `rg "from 'react-hook-form'" frontend/src/` retorna 0 matches. (solo comentarios en JSDoc, no imports reales)
- [x] 11.10 `rg "#[0-9a-fA-F]{3,8}" frontend/src/components/ frontend/src/features/` retorna 0 matches.
- [x] 11.11 Pedir review humana al usuario ANTES de `/opsx:archive`. NO archivar sin OK explícito. (OK humano explícito 2026-05-12: "marca todo okey y archivalo")
