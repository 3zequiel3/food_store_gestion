import { Routes, Route, Navigate } from 'react-router-dom';
import { PublicRoute } from './guards/PublicRoute';
import { PrivateRoute } from './guards/PrivateRoute';
import { RoleGuard } from './guards/RoleGuard';
import { AppLayout } from '../components/layout/AppLayout';
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
import { MisPedidosPage } from '../pages/client/MisPedidosPage';
import { PaymentPage } from '../pages/client/PaymentPage';
import { PaymentResultPage } from '../pages/client/PaymentResultPage';

/**
 * Redirige la raíz `/` según el rol del usuario:
 *  - Si tiene rol staff (ADMIN/STOCK/PEDIDOS) → `/admin`
 *  - Si tiene rol CLIENT → `/cliente`
 *  - Si no tiene rol (caso raro) → `/403`
 *
 * PrivateRoute garantiza que `user` no sea null cuando se llega acá.
 */
function RootRedirect() {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;

  const isStaff = user.roles.some((codigo) =>
    ['ADMIN', 'STOCK', 'PEDIDOS'].includes(codigo),
  );
  return <Navigate to={isStaff ? '/admin' : '/cliente'} replace />;
}

/**
 * Árbol de rutas nested con guards (D9).
 *
 * Estructura:
 *   PublicRoute → /login, /register (redirige a / si ya auth)
 *   PrivateRoute → AppLayout → {
 *     / → redirect inteligente según rol
 *     RoleGuard(ADMIN/STOCK/PEDIDOS) → /admin/*
 *     RoleGuard(CLIENTE) → /cliente/*
 *   }
 *   /401, /403, /* → páginas de error (sin AppLayout)
 */
export default function AppRoute() {
  return (
    <Routes>
      {/* ── Rutas públicas (solo para no-autenticados) ──────────────────── */}
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      {/* ── Rutas privadas (requieren autenticación) ─────────────────────── */}
      <Route element={<PrivateRoute />}>
        {/* AppLayout envuelve TODAS las rutas autenticadas */}
        <Route element={<AppLayout />}>
          {/* Raíz → redirect role-aware (staff → /admin, cliente → /cliente) */}
          <Route path="/" element={<RootRedirect />} />

          {/* Admin (roles operativos) — rutas hijas declaradas explícitamente.
              Cada `element` se reemplaza por el componente real cuando llegue
              el sprint correspondiente; el PlaceholderPage no se modifica. */}
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
            </Route>
          </Route>

          {/* Cliente (código de rol del backend es CLIENT, no CLIENTE) */}
          <Route element={<RoleGuard roles={['CLIENT']} />}>
            <Route path="/cliente" element={<ClienteLayout />}>
              <Route index element={<Navigate to="catalogo" replace />} />
              <Route path="catalogo" element={<CatalogPage />} />
              <Route path="catalogo/:id" element={<ProductDetailPage />} />
              <Route
                path="pedidos"
                element={<MisPedidosPage />}
              />
              <Route path="pedidos/:id/confirmacion" element={<OrderConfirmationPage />} />
              <Route path="pedidos/:id/pago" element={<PaymentPage />} />
              <Route path="pago/resultado" element={<PaymentResultPage />} />
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
