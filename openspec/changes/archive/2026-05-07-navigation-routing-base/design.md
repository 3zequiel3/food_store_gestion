## Context

El scaffold (`setup-frontend-core`) dejó: `AppLayout` con `Navbar` + `Outlet`, guards `PrivateRoute`/`PublicRoute`/`RoleRoute` funcionales, y un router con 9 rutas de las cuales la mayoría son placeholders de texto. La `Navbar` reconoce si el usuario es ADMIN pero muestra el mismo menú para todos los demás roles. El logout solo limpia el estado local. No hay toast UI visible.

## Goals / Non-Goals

**Goals:**
- Navbar con secciones de menú diferenciadas por rol (US-075).
- Logout con call a `authService.logout` para invalidar el refresh token en el backend.
- `LoginForm` respeta `location.state?.from` para redirect post-login.
- `ToastContainer` visible en todas las páginas (montado en `AppLayout`).
- Router con todas las rutas de la app registradas con guards correctos.

**Non-Goals:**
- Implementar las páginas reales de las rutas placeholder (vienen en changes posteriores).
- Animaciones o transiciones de navegación.
- Menú hamburger / mobile drawer (se puede mejorar en un change de UX posterior).
- Lazy loading de rutas (optimización postergable).

## Decisions

### D1: Navbar con secciones de menú condicionales (vs. un menú único con items ocultos)

**Decisión**: La `Navbar` computa un array `navItems` basado en los roles del usuario y renderiza solo los items válidos para ese rol. No hay items ocultos con `display: none` — si no estás en el array, no se renderiza.

**Por qué**: Más limpio semánticamente. Un `display: none` sería accesible via DOM y confuso para lectores de pantalla. Además, los ítems varían estructuralmente entre roles (no es solo mostrar/ocultar sino rutas completamente distintas).

### D2: Logout async en Navbar (vs. logout síncrono)

**Decisión**: El handler de logout en `Navbar` llama `authService.logout(refreshToken)` (best-effort, no bloquea) y en el `.finally()` llama `useAuthStore.getState().logout()`. La UI responde inmediatamente; el call al backend es fuego-y-olvido.

**Por qué**: Consistente con el patrón ya establecido en `authService.logout` (best-effort). El usuario no debe esperar a que el backend responda para que la sesión se cierre localmente.

### D3: ToastContainer en AppLayout (vs. en el root de la app)

**Decisión**: `<ToastContainer />` se monta dentro de `AppLayout`, encima del `<main>`. Usa `position: fixed` para mostrarse sobre el contenido.

**Por qué**: `AppLayout` ya es el wrapper de todas las rutas. Montarlo ahí garantiza que esté disponible en cualquier página sin modificar `main.tsx`.

### D4: Toast auto-dismiss con `useEffect` + `setTimeout` (vs. librería externa)

**Decisión**: `ToastContainer` implementa auto-dismiss con `useEffect` que llama `dismissToast(id)` después de `durationMs` (default 4000ms). No se instala ninguna librería de toasts externa.

**Por qué**: `useUIStore` ya tiene la infraestructura (pushToast/dismissToast). Una librería externa duplicaría el estado y añadiría dependencia sin beneficio real para el scope actual.

### D5: Rutas placeholder como divs inline (vs. componentes de página vacíos)

**Decisión**: Las rutas que aún no tienen página real usan `<div className="p-8 text-center">Próximamente</div>` directamente en el router. No se crean archivos de componente vacíos.

**Por qué**: Es temporal y honesto. No tiene sentido crear `CartPage.tsx` con un div — ese archivo se sobreescribirá entero en el change correspondiente. Menos archivos muertos.

### D6: Tabla de permisos de rutas

| Ruta | Guard | Roles permitidos |
|---|---|---|
| `/` | pública | todos |
| `/products` | pública | todos |
| `/login`, `/register` | PublicRoute | no autenticados |
| `/cart` | PrivateRoute | todos autenticados |
| `/checkout` | PrivateRoute | todos autenticados |
| `/orders` | PrivateRoute | CLIENT |
| `/profile` | PrivateRoute | todos autenticados |
| `/addresses` | PrivateRoute | CLIENT |
| `/admin/products` | PrivateRoute + RoleRoute | ADMIN, STOCK |
| `/admin/categories` | PrivateRoute + RoleRoute | ADMIN, STOCK |
| `/admin/ingredients` | PrivateRoute + RoleRoute | ADMIN, STOCK |
| `/admin/orders` | PrivateRoute + RoleRoute | ADMIN, PEDIDOS |
| `/admin/users` | PrivateRoute + RoleRoute | ADMIN |
| `/admin/metrics` | PrivateRoute + RoleRoute | ADMIN |
| `/forbidden` | pública | todos |
| `*` | pública | todos (404) |

## Risks / Trade-offs

- **[Risk] Rutas placeholder sin página** → Si alguien navega a `/cart` antes de que exista la página, ve "Próximamente". Aceptable — las guards están correctas, el contenido llega en el change siguiente.
- **[Trade-off] Toast sin animación** → Los toasts aparecen y desaparecen sin fade. Funcional pero básico. Una mejora de UX puede venir después con CSS transitions o Framer Motion.
- **[Risk] Logout async sin feedback** → Si el usuario hace logout y el backend está caído, la sesión local se cierra igual (diseño intencional). El refresh token queda activo en BD hasta que expire (7 días). Aceptable por la naturaleza best-effort del logout.

## Migration Plan

1. Crear `src/shared/ui/ToastContainer.tsx` con auto-dismiss.
2. Agregar `<ToastContainer />` en `AppLayout.tsx`.
3. Refactorizar `Navbar.tsx` con menús por rol + logout async.
4. Actualizar `LoginForm.tsx` para respetar `location.state?.from`.
5. Extender `Router.tsx` con todas las rutas de la tabla D6.
6. Exportar `ToastContainer` desde `shared/ui/index.ts`.

Sin rollback complejo — todos los cambios son aditivos o modifican archivos que ya existían sin romper funcionalidad existente.

## Open Questions

- **¿Sidebar vs Navbar para roles de gestión?**: US-075 no especifica si el menú de STOCK/PEDIDOS/ADMIN debe ser un sidebar lateral o links en el top navbar. Por ahora se implementa todo en el top navbar para mantener consistencia con el diseño existente. Un sidebar puede añadirse en un change de UX dedicado.
