import { Routes, Route, Navigate } from 'react-router-dom';
import { PublicRoute } from './guards/PublicRoute';
import { PrivateRoute } from './guards/PrivateRoute';
import { RoleGuard } from './guards/RoleGuard';
import { AppLayout } from '../components/layout/AppLayout';
import { LandingPage } from '../pages/LandingPage';
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { NotFound } from '../pages/errors/NotFound';
import { Forbidden } from '../pages/errors/Forbidden';
import { Unauthorized } from '../pages/errors/Unauthorized';
import { AdminLayout } from '../pages/admin/AdminLayout';
import { ClienteLayout } from '../pages/client/ClienteLayout';
import { useAuthStore } from '../features/auth/stores/authStore';
import { CatalogPage } from '../pages/client/CatalogPage';
import { ProductDetailPage } from '../pages/client/ProductDetailPage';
import { ProfilePage } from '../pages/client/ProfilePage';
import { AddressesPage } from '../pages/client/AddressesPage';
import { CheckoutPage } from '../features/checkout/components/CheckoutPage';
import { OrderConfirmationPage } from '../features/orders/components/OrderConfirmationPage';
import { PedidosAdminPage } from '../pages/admin/PedidosAdminPage';
import { AdminUsersPage } from '../pages/admin/AdminUsersPage';
import { AdminMetricasPage } from '../pages/admin/AdminMetricasPage';
import { AdminProductosPage } from '../pages/admin/AdminProductosPage';
import { AdminCategoriasPage } from '../pages/admin/AdminCategoriasPage';
import { AdminIngredientesPage } from '../pages/admin/AdminIngredientesPage';
import { AdminProfilePage } from '../pages/admin/AdminProfilePage';
import { AdminFaltantesPage } from '../pages/admin/AdminFaltantesPage';
import { MisPedidosPage } from '../pages/client/MisPedidosPage';
import { CocinaPage } from '../features/cocina/pages/CocinaPage';

/**
 * Redirige `/dashboard` según el rol del usuario:
 *  - Si tiene rol COCINA → `/cocina`
 *  - Si tiene rol staff (ADMIN/STOCK/PEDIDOS) → `/admin`
 *  - Si tiene rol CLIENT → `/cliente`
 *  - Si no tiene rol (caso raro) → `/403`
 *
 * PrivateRoute garantiza que `user` no sea null cuando se llega acá.
 */
function RootRedirect() {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;

  if (user.roles.includes('COCINA')) {
    return <Navigate to="/cocina" replace />;
  }

  const isStaff = user.roles.some((codigo) =>
    ['ADMIN', 'STOCK', 'PEDIDOS'].includes(codigo),
  );
  return <Navigate to={isStaff ? '/admin' : '/cliente'} replace />;
}

/**
 * Árbol de rutas nested con guards (D9).
 *
 * Estructura:
 *   / → LandingPage (pública, sin guard)
 *   PublicRoute → /login, /register (redirige a / si ya auth)
 *   AppLayout (auth-aware) → /cliente/catalogo, /cliente/catalogo/:id (públicas)
 *   PrivateRoute → AppLayout → {
 *     /dashboard → redirect inteligente según rol
 *     RoleGuard(ADMIN/STOCK/PEDIDOS) → /admin/*
 *     RoleGuard(CLIENTE) → /cliente/* (excepto catalogo, que es pública)
 *   }
 *   /401, /403, /* → páginas de error (sin AppLayout)
 *
 * D4 — Solo /cliente/catalogo y /cliente/catalogo/:id son públicas.
 * El resto de /cliente/* sigue privado.
 */
export default function AppRoute() {
  return (
    <Routes>
      {/* ── Ruta pública — landing page (accesible para todos) ──────────── */}
      <Route path="/" element={<LandingPage />} />

      {/* ── Rutas públicas (solo para no-autenticados) ──────────────────── */}
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      {/* ── Catálogo público (D4): accesible sin autenticación ──────────── */}
      {/* AppLayout es auth-aware: Sidebar retorna null cuando user === null  */}
      <Route element={<AppLayout />}>
        <Route
          path="/cliente/catalogo"
          element={<div className="p-4 md:p-6"><CatalogPage /></div>}
        />
        <Route
          path="/cliente/catalogo/:id"
          element={<div className="p-4 md:p-6"><ProductDetailPage /></div>}
        />
      </Route>

      {/* ── Rutas privadas (requieren autenticación) ─────────────────────── */}
      <Route element={<PrivateRoute />}>
        {/* AppLayout envuelve TODAS las rutas autenticadas */}
        <Route element={<AppLayout />}>
          {/* Dashboard → redirect role-aware (staff → /admin, cliente → /cliente) */}
          <Route path="/dashboard" element={<RootRedirect />} />

          {/* Cocina (rol COCINA o ADMIN). Vive adentro del AppLayout para
              tener sidebar + logout iguales al resto del panel staff. */}
          <Route element={<RoleGuard roles={['COCINA', 'ADMIN']} />}>
            <Route path="/cocina" element={<CocinaPage />} />
          </Route>

          {/* /admin/faltantes: accesible para COCINA (read-only) y staff
              operativo. La página detecta el rol del user y oculta los
              botones de resolución cuando es COCINA puro. */}
          <Route element={<RoleGuard roles={['COCINA', 'ADMIN', 'PEDIDOS', 'STOCK']} />}>
            <Route path="/admin/faltantes" element={<AdminLayout />}>
              <Route index element={<AdminFaltantesPage />} />
            </Route>
          </Route>

          {/* Admin (roles operativos) — rutas hijas declaradas explícitamente. */}
          <Route element={<RoleGuard roles={['ADMIN', 'STOCK', 'PEDIDOS']} />}>
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<Navigate to="pedidos" replace />} />
              <Route path="productos" element={<AdminProductosPage />} />
              <Route path="productos/nuevo" element={<AdminProductosPage />} />
              <Route
                path="pedidos"
                element={<PedidosAdminPage />}
              />
              <Route path="usuarios" element={<AdminUsersPage />} />
              <Route path="metricas" element={<AdminMetricasPage />} />
              <Route path="categorias" element={<AdminCategoriasPage />} />
              <Route path="ingredientes" element={<AdminIngredientesPage />} />
              <Route path="perfil" element={<AdminProfilePage />} />
            </Route>
          </Route>

          {/* Cliente (código de rol del backend es CLIENT, no CLIENTE) */}
          {/* /cliente/catalogo y /cliente/catalogo/:id quedan FUERA de este nest (ver arriba) */}
          <Route element={<RoleGuard roles={['CLIENT']} />}>
            <Route path="/cliente" element={<ClienteLayout />}>
              <Route index element={<Navigate to="catalogo" replace />} />
              <Route
                path="pedidos"
                element={<MisPedidosPage />}
              />
              <Route path="pedidos/:id/confirmacion" element={<OrderConfirmationPage />} />
              <Route path="direcciones" element={<AddressesPage />} />
              <Route path="perfil" element={<ProfilePage />} />
              <Route path="checkout" element={<CheckoutPage />} />
            </Route>
          </Route>
        </Route>
      </Route>

      {/* ── Páginas de error (fuera de AppLayout) ────────────────────────── */}
      <Route path="/401" element={<Unauthorized />} />
      <Route path="/403" element={<Forbidden />} />

      {/* Catch-all → 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
