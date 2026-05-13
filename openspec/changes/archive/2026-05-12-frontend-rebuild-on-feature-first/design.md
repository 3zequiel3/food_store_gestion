## Context

Between sessions el frontend fue **reestructurado completamente**. Pasó de FSD nominal (canónico en `docs/Descripcion.txt:99`) a **Feature-First plano** (decisión F1, documentada en `docs/frontend-architecture.md`). Ese refactor invalidó cuatro changes ya archivados que asumían FSD y 4 stores fijos:

- #2 `setup-frontend-core` — estructura FSD (`shared/entities/features/widgets/pages/app/`) hoy inexistente.
- #5 `zustand-stores-base` — los 4 stores (`auth`, `cart`, `payment`, `ui`) están borrados.
- #7 `auth-frontend-interceptor` — login/register forms + Axios interceptor borrados.
- #8 `navigation-routing-base` — layout, navbar role-aware, guards borrados.

**Estado actual real del frontend** (validado con `eza`/`bat` sobre `frontend/src/`):
- `api/client.ts` existe (instancia con `baseURL: '/api/v1'`, sin interceptors).
- `lib/constants/endpoints.ts` existe (single source of truth de paths backend).
- `features/{addresses,auth,cart,catalog,checkout,orders,payments,profile}/{components,hooks,schemas,services,stores,types}/` — todas las subcarpetas vacías.
- `pages/admin/AdminLayout.tsx` + `pages/client/ClienteLayout.tsx` — esqueletos de 8 líneas, sin sidebar, sin role-awareness.
- `router/AppRoute.tsx` — 2 rutas (`/admin`, `/cliente`) sin guards ni layout.
- `package.json` — contiene `react-hook-form` + `@hookform/resolvers` como dependencias "fantasma" (decidido descartar en F9).

**Restricciones**:
- El backend está congelado para esta capa — esta change **NO** modifica nada de `backend/`. Solo consume endpoints ya existentes y mapeados.
- El usuario eligió **Opción A** (single change consolidado) sobre reabrir los 4 archivos o partir en 4 sub-changes.
- Roadmap (`docs/CHANGES.md`): los archivados #2/#5/#7/#8 se marcan como `⚠️ Refactored 2026-05-12` y este change pasa a ser **bloqueante de Fase B** (catálogo, carrito, checkout, pedidos).
- `pnpm`, no npm. `lucide-react` para iconos. TanStack Form (NO react-hook-form).

**Stakeholders**: el usuario (developer único). Sin equipo externo, sin proceso de review formal — pero hay cátedra que evalúa con rúbrica.

## Goals / Non-Goals

**Goals:**

- Reponer la fundación del frontend adaptada a Feature-First plano de manera que la Fase B pueda arrancar sin bloqueos.
- HTTP client con interceptors funcionales: auth header + refresh single-flight + parser RFC 7807.
- Auth funcional end-to-end: schemas Zod + service + hooks + formularios `LoginForm` y `RegisterForm` con TanStack Form, integrados a `authStore`.
- Stores Zustand **justificados** (no especulativos): solo `authStore` y `cartStore` ahora; el resto se difiere hasta que aparezca una necesidad real.
- Layout sidebar-based responsive mobile-first, role-aware vía `authStore.user.roles`.
- Sistema de design tokens (CSS custom properties + Tailwind `theme.extend`) que evite hex hardcodeados.
- Defaults globales de TanStack Query (`retry: 1`, `staleTime: 30s`, `refetchOnWindowFocus: false`).
- Iconografía: `lucide-react` con named imports, prohibición de namespace imports vía ESLint.

**Non-Goals:**

- UI polish profundo para login/register más allá de funcional + accesible (queda para un change `frontend-design` posterior).
- Formularios de pago (#27, Sprint 10), visualización de pedidos (#28, Sprint 11), dashboards admin (#30, Sprint 12).
- Cart UI completa más allá del store + add/remove básicos (Sprint 9).
- E2E tests con Playwright.
- Storybook.
- Codegen `openapi-typescript` (R4 abierto en `frontend-architecture.md` — out of scope acá).
- Internacionalización (i18n) — la app es solo español por mandato del proyecto.

## Decisions

### D1 — Refresh rotation con single-flight queue

**Decisión**: Implementar el manejador de 401 con un patrón **single-flight**: una variable de módulo `let refreshPromise: Promise<string> | null` que, mientras esté activa, **encola** los retries de todos los 401 concurrentes y los resuelve cuando termina el refresh. Si el refresh falla, se rechaza la cola entera y se hace logout + redirect.

**Alternativas consideradas**:
- *Blocking sequential*: cada 401 espera al anterior. Inviable bajo concurrencia real (3 queries simultáneas en una página = 3 refresh calls innecesarios).
- *Cada request retries solo*: cada interceptor hace su propio refresh. Stampede garantizado al rotar el token (porque un refresh exitoso invalida el viejo refresh token).
- *Single-flight con `Promise.all` queue*: el ganador. Una promesa compartida, el resto la `await`ea.

**Por qué**: el backend rota `refresh_token` en cada llamada (validado en `auth-backend` archivado). Stampede de refreshes mata la sesión.

### D2 — Solo 2 Zustand stores (auth + cart) upfront, defer payment/ui

**Decisión**: Crear únicamente `authStore` y `cartStore` ahora. NO crear `paymentStore` ni `uiStore` hasta que aparezca una necesidad concreta:
- `paymentStore` — el flujo de pago es mayoritariamente efímero. Si llega a hacer falta state cross-component en Sprint 10, se crea ahí.
- `uiStore` — solo justificado si sidebar collapse o theme necesitan persistencia. Hoy no.

**Alternativas consideradas**:
- *Mantener los 4 stores del archivado #5*: violaba YAGNI. Tres de los cuatro estaban vacíos en uso real (verificado en el código pre-refactor).
- *Cero stores upfront, crear ad-hoc*: el interceptor necesita `authStore.getState()` desde código no-React; el cart necesita persistir entre sesiones. Imposible sin stores.

**Por qué**: Zustand store es deuda hasta que se usa. `cartStore` es legítimo (frontend-only, persistente), `authStore` es obligatorio (interceptor + guards). Resto a demanda.

### D3 — Layout dual: sidebar hover-expand en desktop + bottom navigation en mobile

**Decisión** (refinada por el usuario): la navegación primaria tiene **dos paradigmas según viewport**, no un solo componente responsive. Se implementa **con Tailwind directo, sin `react-pro-sidebar` ni librerías externas**.

**Desktop (md+)** — sidebar lateral izquierdo con tres estados:

1. **Collapsed (default)**: 64px de ancho, solo íconos lucide-react centrados, sin labels.
2. **Hover-expanded**: al pasar el mouse sobre el sidebar, se expande a 240px revelando labels y submenús. Al sacar el mouse, vuelve a collapsed (con transición de 150-200ms para no flickerear).
3. **Locked-open**: un botón de toggle en el header del sidebar permite "fijar" el estado expandido. Click 1 = locked open (ignora hover). Click 2 = locked collapsed (también ignora hover). Click 3 = vuelve a hover-mode.

Submenús: solo se renderizan en estado expanded (hover o locked). El submenú activo (el de la ruta actual) se autoexpande; los otros quedan colapsados aunque tengan items.

Estado del lock vive en `useState` local de `AppLayout` por ahora (no en `uiStore`, ver R4). Si en el futuro se quiere persistir, scopear por layout (`adminSidebarLocked`, `clientSidebarLocked`).

**Mobile (<md)** — **NO hay sidebar**. Se reemplaza por:

- **Bottom Navigation Bar**: fixed bottom, 4-5 items principales role-aware, íconos lucide + label corto debajo. Touch targets 56×56px mínimo (iOS HIG). El activo se highlightea con `bg-primary/10` + ícono filled.
  - Admin: Productos, Pedidos, Usuarios, Métricas, Más (drawer con items secundarios — Categorías, Ingredientes)
  - Cliente: Catálogo, Mis Pedidos, Direcciones, Perfil
- **Top Navbar (cliente)**: fixed top, contiene logo + **carrito (icono con badge de items count, click → drawer/sheet con el carrito)** + menú de usuario. El carrito SOLO aparece en navegación de cliente, no en admin.
- **Top Navbar (admin)**: fixed top, contiene logo + menú de usuario. Sin carrito.

Cuando el bottom-nav requiere más de 5 items, el 5to es "Más" y abre un sheet/drawer con los items secundarios.

**Library decision**: **Tailwind direct, sin react-pro-sidebar/react-sidebar/etc.**
- React-pro-sidebar trae su propio styling y pelea con el sistema de tokens (D5).
- El hover-to-expand + locked-state es UX custom — más limpio construirlo que sobreescribir defaults de una lib.
- Bottom nav es `fixed bottom-0 left-0 right-0 flex` — trivial en Tailwind.
- Una dependencia menos.

**Alternativas consideradas**:
- *react-pro-sidebar*: descartado — trae CSS propio, choca con design tokens.
- *Sidebar persistente en mobile*: ocupa 60-70% de la pantalla, mata el espacio para contenido.
- *Solo bottom nav en desktop también*: pierde affordance de navegación persistente que el desktop SÍ banca.
- *Solo hamburguesa sin bottom nav*: requiere 2 taps para cualquier navegación. Bottom nav es 1 tap.

**Componentes a crear**:
- `components/layout/Sidebar.tsx` (desktop, hover-expand + lock)
- `components/layout/SidebarItem.tsx` (item individual con submenú opcional)
- `components/layout/BottomNav.tsx` (mobile, fixed bottom, 4-5 items + "Más")
- `components/layout/MobileMoreDrawer.tsx` (sheet con items secundarios)
- `components/layout/TopNavbar.tsx` (mobile + desktop top — logo + cart cliente + user menu)
- `components/layout/CartDrawer.tsx` (sheet que se abre al tocar el cart del navbar — reusable mobile/desktop)
- `components/layout/AppLayout.tsx` (orchestra Sidebar/BottomNav/TopNavbar según viewport con `useMediaQuery`)

**Por qué**: dos paradigmas adecuados a cada viewport > un solo componente comprometido. Bottom nav es el patrón mobile estándar (Instagram, Uber, MercadoLibre). Hover-expand sidebar es Vercel-style — denso en información cuando se necesita, limpio cuando no.

### D4 — TanStack Table con card-reflow en mobile (no horizontal scroll)

**Decisión**: Las tablas (`TanStack Table`) se renderizan como **tabla en md+** y como **lista de cards en <md**. Cada fila pasa a ser una card con label-value pairs. Se implementa con dos templates en el componente Table (`<Table />` desktop / `<CardList />` mobile) y un breakpoint `useMediaQuery('(min-width: 768px)')`.

**Alternativas consideradas**:
- *Horizontal scroll en mobile*: requiere swipe, esconde columnas, mata accesibilidad.
- *Solo desktop (esconder tabla en mobile)*: deja a usuarios mobile sin acceso a data tabular.
- *Stacked rows*: cada celda en una fila — termina pareciéndose a un card pero peor formateado.

**Por qué**: card-reflow conserva accesibilidad, es el patrón que usan Stripe Dashboard, GitHub Issues, Linear. Las primeras tablas reales aparecen en Sprint 12 (#29 admin-users-frontend) y #28 (order-visualization-frontend); este change deja el patrón listo pero no obliga a usarlo aún.

### D5 — Design tokens dark-mode first via Tailwind v4 `@theme` directive en `src/index.css`

**Decisión** (refinada por el usuario): el sistema de design tokens vive **completamente en `frontend/src/index.css`** (NO en `tailwind.config.ts` — estamos en Tailwind v4 con `@theme` directiva). El proyecto es **dark-mode first** — los tokens del `@theme` son los valores dark, y un override `:root.light` redefine para tema claro.

**Stack confirmado**: Tailwind v4 (`tailwindcss ^4.2.2` + `@tailwindcss/vite`). `tailwind.config.ts` queda casi vacío — auto-content-scanning hace todo. La definición de tokens vive en CSS, no en JS.

**Estructura de tokens** (a implementar comprehensivamente, no solo colors):

1. **Color tokens** — usando OKLCH (no hex) para mejor mezclado y previsibilidad cross-display:
   - `background`, `foreground` (par principal)
   - `card`, `card-foreground` (superficies elevadas)
   - `popover`, `popover-foreground` (overlays/menús)
   - `primary`, `primary-foreground` (CTAs, brand)
   - `secondary`, `secondary-foreground` (acciones secundarias)
   - `muted`, `muted-foreground` (texto/UI desaturada)
   - `accent`, `accent-foreground` (highlights, hover states)
   - `destructive`, `destructive-foreground` (errors, delete)
   - `success`, `success-foreground` (confirmaciones)
   - `warning`, `warning-foreground` (alerts amarillos)
   - `border`, `input`, `ring` (utility colors)

2. **Typography tokens**:
   - `--font-sans` (Inter o system stack)
   - `--font-mono` (JetBrains Mono o ui-monospace)

3. **Radius tokens**: `--radius-sm`, `--radius`, `--radius-lg`, `--radius-xl`.

4. **Shadow tokens** específicos para dark mode (más sutiles, menos contraste que en light).

5. **`color-scheme`**: `html { color-scheme: dark }` por default + `html.light { color-scheme: light }` — controla los scrollbars y form controls nativos del browser.

**Light mode**: override completo en `:root.light` con tokens equivalentes pero en valores claros. El toggle (cuando se implemente) es agregar/quitar `class="light"` al `<html>`.

**Paleta inicial**: orientada a food store — primary warm (orange/amber, evoca apetito), background warm-tinted dark (no negro frío). NO es la paleta final — es starter, ajustable en un futuro change `frontend-design` pass.

**Alternativas consideradas**:
- *Tailwind v3 con `tailwind.config.ts`*: ya no aplica — estamos en v4.
- *Light-mode first con `.dark` override*: el usuario prefiere dark; invertimos la convención de shadcn.
- *Hex en vez de OKLCH*: hex no permite mezclas perceptualmente uniformes. OKLCH es lo que usa Tailwind v4 internamente.
- *JS-side tokens (token objects exportados)*: pierde el switching CSS reactivo.

**Por qué**: Tailwind v4 + `@theme` es el patrón moderno (shadcn/ui v2, Radix Themes nuevo, Vercel design system). Permite dark/light switching sin rebuild ni re-render React. El cambio de paleta full afecta automáticamente todos los componentes que usen `bg-primary`, `text-foreground`, etc. — cero refactor.

**Implementación inmediata**: el archivo `src/index.css` actual tiene un esqueleto de tokens (light-mode con hex blue/purple/pink). Se reescribe completo en este change.

### D6 — `ApiError` como **clase** (instanceof checkable), no discriminated union

**Decisión**: `ApiError extends Error` con constructor que recibe el shape RFC 7807. Permite `if (e instanceof ApiError)` en catch blocks y exposición tipada de `e.status`, `e.detail`, `e.errors`.

```ts
class ApiError extends Error {
  constructor(
    public readonly type: string,
    public readonly title: string,
    public readonly status: number,
    public readonly detail: string,
    public readonly instance?: string,
    public readonly errors?: Array<{ field: string; message: string }>,
  ) { super(detail || title); this.name = 'ApiError'; }
}
```

**Alternativas consideradas**:
- *Discriminated union* (`type ApiError = AuthError | ValidationError | ...`): obliga a un switch en cada catch, duplica shapes. Más type-safe pero más fricción.
- *Plain object retornado*: pierde el throwing nativo, fuerza a chequear retorno en cada llamada.

**Por qué**: `instanceof` se integra natural con TanStack Query (`mutation.error instanceof ApiError`) y permite extender (e.g., `class ValidationError extends ApiError` futuro) sin breaking changes.

### D7 — Interceptor wiring **eager** en `client.ts` (no lazy)

**Decisión**: Los interceptors se atachan en `client.ts` **antes** de exportar `apiClient`. Esto significa que `client.ts` importa de `interceptors/` y los registra como side effect del módulo. NO se hace lazy wiring en `main.tsx` después de la hidratación del store.

```ts
// client.ts
import { applyAuthInterceptor } from './interceptors/auth';
import { applyErrorInterceptor } from './interceptors/error';

export const apiClient = axios.create({ baseURL: '/api/v1', timeout: 30_000 });
applyAuthInterceptor(apiClient);
applyErrorInterceptor(apiClient);
```

**Alternativas consideradas**:
- *Lazy wiring en `main.tsx` después de `authStore.persist.onFinishHydration`*: complejo, race-prone, y obliga a renderizar un loader hasta que termine la hidratación.
- *Wiring en cada feature*: viola DRY, garantiza inconsistencias.

**Por qué**: el interceptor lee `useAuthStore.getState()` en cada request. El primer request real **no ocurre hasta que un componente lo dispara**, momento en que el store ya está hidratado por Zustand's `persist` (sincrónico en localStorage). El timing es seguro. Riesgo R1 abajo trata el edge case del Suspense de hidratación.

### D8 — Lucide named imports, enforced via ESLint

**Decisión**: Solo se permite `import { Home, ShoppingCart } from 'lucide-react'`. Prohibido `import * as Icons from 'lucide-react'`. Se agrega una regla ESLint `no-restricted-syntax` o `no-restricted-imports` con `patterns: [{ group: ['lucide-react'], importNamePattern: '^\\*$' }]` (o equivalente).

**Alternativas consideradas**:
- *Documentar la regla y rezar*: garantiza que alguien la rompa.
- *Codemod automático*: overkill para lucide.

**Por qué**: namespace import de lucide bloatea el bundle (cientos de íconos). El tree-shaking de Vite/Rollup funciona perfecto con named imports. ESLint es la red de seguridad gratuita.

### D9 — Router tree **nested con `<Outlet />`** (vs flat con guards en cada ruta)

**Decisión**: Usar nested routes de react-router-dom v7 donde el guard (`PrivateRoute`, `RoleGuard`) está en el route padre vía `element={<PrivateRoute><AppLayout /></PrivateRoute>}` y todas las rutas hijas se renderizan dentro del `<Outlet />`. Estructura:

```tsx
<Routes>
  <Route element={<PublicRoute />}>           {/* redirige a / si está auth */}
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
  </Route>

  <Route element={<PrivateRoute />}>          {/* requiere auth */}
    <Route element={<AppLayout />}>           {/* sidebar + header + outlet */}
      <Route element={<RoleGuard roles={['ADMIN','STOCK','PEDIDOS']} />}>
        <Route path="/admin/*" element={<AdminLayout />} />
      </Route>
      <Route element={<RoleGuard roles={['CLIENTE']} />}>
        <Route path="/cliente/*" element={<ClienteLayout />} />
      </Route>
    </Route>
  </Route>

  <Route path="/403" element={<Forbidden />} />
  <Route path="/401" element={<Unauthorized />} />
  <Route path="*" element={<NotFound />} />
</Routes>
```

**Alternativas consideradas**:
- *Flat con guard en cada ruta*: `<Route path="/admin" element={<RoleGuard roles={['ADMIN']}><AdminPage /></RoleGuard>} />`. Repite el guard en cada ruta protegida, ruido visual, fácil olvidarlo.
- *Data routers (`createBrowserRouter`)*: más poder (loaders/actions) pero out of scope acá. Migración futura posible sin breaking.

**Por qué**: nested con Outlet centraliza el guard, hace explícita la jerarquía de protección, y permite que `AppLayout` envuelva todas las rutas autenticadas sin repetición.

## Risks / Trade-offs

### R1 — Hydration race: interceptor necesita token antes de que `authStore` rehidrate

**Riesgo**: El interceptor lee `useAuthStore.getState().accessToken` síncrónicamente. Si el primer request sale **antes** de que Zustand termine de leer `localStorage`, viaja sin `Authorization` header y dispara un 401 inmediato.

**Mitigación**: Zustand's `persist` middleware con `storage: createJSONStorage(() => localStorage)` es **sincrónico** en el getter de localStorage. El store se hidrata en el primer `useAuthStore` o `useAuthStore.getState()`, antes del primer render de cualquier componente. **Adicional**: ningún request se dispara desde `main.tsx` o `App.tsx` top-level; todos vienen de hooks dentro de componentes que ya viven post-mount. Si en el futuro se agrega un request "boot-time", se gating con `useAuthStore.persist.hasHydrated()` antes de disparar.

### R2 — Refresh stampede: múltiples 401s paralelos

**Riesgo**: Catálogo y "mis pedidos" se cargan en paralelo; ambos disparan 401 al mismo tiempo. Sin coordinación, ambos llaman a `/auth/refresh`, el segundo recibe un refresh token ya rotado e invalido, y el usuario es deslogueado a pesar de tener una sesión válida.

**Mitigación**: D1 single-flight resuelve esto por diseño. Una sola promesa compartida — todos los retries esperan al mismo refresh.

### R3 — Validación Zod laggy en formularios con muchos campos

**Riesgo**: TanStack Form con Zod en `onChange` valida cada keystroke. En forms con 10+ campos o regex pesados (email validation profunda) puede generar lag perceptible.

**Mitigación**: configurar `validators: { onBlur: schema }` por default. Solo escalar a `onChange` en campos cortos con feedback inmediato (toggles, dropdowns). El submit re-valida con `onSubmit` siempre — Zod garantiza el contrato sin importar el timing.

### R4 — State leak entre layouts admin y cliente si `uiStore` se comparte

**Riesgo**: Cuando llegue a crearse `uiStore` (no en esta change), si se usa el mismo store para sidebar state en admin y en cliente, un toggle del usuario en `/admin` persiste al volver a `/cliente`. Confuso.

**Mitigación**: el sidebar state queda **en local `useState`** dentro de `AppLayout` (no en store). Si en el futuro hay necesidad real de persistencia por layout, scope-arlo por key (`sidebarOpen_admin`, `sidebarOpen_cliente`) o por route prefix. Esta change deja el state local — no introduce el problema.

### R5 — Bundle bloat si alguien hace namespace import de `lucide-react`

**Riesgo**: Tree-shaking se rompe si alguien hace `import * as Icons from 'lucide-react'`. El bundle final mete los ~1500 íconos.

**Mitigación**: D8 — ESLint rule contra namespace imports de lucide. Documentado en `frontend-architecture.md` antipatrones.

### R6 — Testing responsive no automatizado

**Riesgo**: No hay Playwright ni Cypress configurado para tests E2E responsive. Las decisiones D3 (sidebar overlay) y D4 (card-reflow) se verifican solo a ojo en DevTools.

**Mitigación**: incluir en `tasks.md` un **checklist manual de viewports** (375px / 768px / 1280px) para cada componente touched. Si en el futuro se agrega Playwright (#post-Sprint-12), estos checks pasan a tests automatizados. Por ahora — manual, documentado, suficiente para el alcance del proyecto.

## Migration Plan

Esta change **NO toca backend** ni rompe contratos con la API. Es una reconstrucción interna del frontend.

**Pasos de deploy** (todos en una sola PR / commit chain):

1. **Cleanup deps**: agregar `lucide-react`, remover `react-hook-form` + `@hookform/resolvers`, `pnpm install`. Verificar que el lockfile queda limpio.
2. **Tokens**: agregar CSS custom properties + Tailwind theme.extend (cambio inerte, no rompe nada).
3. **HTTP interceptors**: implementar y wire en `client.ts`. **Sin uso real todavía** — los componentes que disparan requests aún no existen.
4. **Stores**: `authStore` + `cartStore` con `persist`. Sin consumidores aún.
5. **Auth feature**: schemas + service + hooks + forms.
6. **Router rewrite**: guards + nested tree + error pages. `AppRoute.tsx` se reescribe atómicamente.
7. **Layout**: `Sidebar` + `Header` + `AppLayout`, integrados a admin/client layouts.
8. **QueryClient defaults** en `main.tsx`.
9. **Docs**: actualizar `docs/CHANGES.md` (#2/#5/#7/#8 → refactored) y `docs/frontend-architecture.md` (sección 12 Design Tokens).

**Rollback**: si algo explota antes de archive, revert del commit/PR completo. Como no hay migraciones de DB ni cambios de schema, el rollback es trivial.

**Validación pre-archive**:
- `pnpm dev` arranca sin errores.
- `pnpm build` produce bundle sin warnings.
- Manual: login con usuario existente → ver sidebar role-aware → logout → redirect a /login.
- Manual: viewports 375/768/1280 verificados en DevTools.
- Manual: 401 simulado (token expirado a mano) → refresh single-flight verificado en Network tab.

## Open Questions

- **¿Theme dark/light en este change o defer?** — Decisión tomada: **defer**. Los tokens dejan el sistema listo (`:root` y `.dark { ... }` placeholders), pero el toggle UI y el `uiStore.theme` quedan para cuando se justifique. La decisión D5 lo deja desbloqueado sin trabajo adicional.
- **¿Toaster global en este change o defer?** — **Defer**. No hay `uiStore.toasts` (D2). Cuando se necesite, se agrega una librería liviana (sonner/react-hot-toast) y se enlaza al `ApiError` parser de manera no-invasiva.
- **¿Codegen `openapi-typescript` ahora?** — Out of scope (riesgo R4 del `frontend-architecture.md`). Se evalúa después de que la Fase B esté funcionando y haya volumen real de drift entre Zod y Pydantic.
- **¿i18n preparado?** — No. La app es monolingüe español por mandato del proyecto.
