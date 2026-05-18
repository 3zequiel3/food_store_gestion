/**
 * Tests RED — Group 1: Public catalog routing
 *
 * Verify that /cliente/catalogo and /cliente/catalogo/:id are accessible
 * without authentication, while other /cliente/* routes redirect to /login.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

// ---- Mock heavy layout/page components so tests are fast and isolated --------
vi.mock('../../components/layout/AppLayout', async () => {
  const { Outlet } = await import('react-router-dom');
  return {
    AppLayout: () => (
      <div data-testid="app-layout">
        <Outlet />
      </div>
    ),
  };
});

vi.mock('../../pages/client/CatalogPage', () => ({
  CatalogPage: () => <div data-testid="catalog-page">CatalogPage</div>,
}));

vi.mock('../../pages/client/ProductDetailPage', () => ({
  ProductDetailPage: () => <div data-testid="product-detail-page">ProductDetailPage</div>,
}));

vi.mock('../../pages/LandingPage', () => ({
  LandingPage: () => <div data-testid="landing-page">LandingPage</div>,
}));

vi.mock('../../pages/LoginPage', () => ({
  LoginPage: () => <div data-testid="login-page">LoginPage</div>,
}));

vi.mock('../../pages/RegisterPage', () => ({
  RegisterPage: () => <div data-testid="register-page">RegisterPage</div>,
}));

vi.mock('../../pages/errors/NotFound', () => ({
  NotFound: () => <div data-testid="not-found">NotFound</div>,
}));

vi.mock('../../pages/errors/Forbidden', () => ({
  Forbidden: () => <div data-testid="forbidden">Forbidden</div>,
}));

vi.mock('../../pages/errors/Unauthorized', () => ({
  Unauthorized: () => <div data-testid="unauthorized">Unauthorized</div>,
}));

vi.mock('../../pages/client/ProfilePage', () => ({
  ProfilePage: () => <div data-testid="profile-page">ProfilePage</div>,
}));

vi.mock('../../pages/client/AddressesPage', () => ({
  AddressesPage: () => <div data-testid="addresses-page">AddressesPage</div>,
}));

vi.mock('../../features/checkout/components/CheckoutPage', () => ({
  CheckoutPage: () => <div data-testid="checkout-page">CheckoutPage</div>,
}));

vi.mock('../../features/orders/components/OrderConfirmationPage', () => ({
  OrderConfirmationPage: () => <div data-testid="order-confirmation-page">OrderConfirmationPage</div>,
}));

vi.mock('../../pages/client/MisPedidosPage', () => ({
  MisPedidosPage: () => <div data-testid="mis-pedidos-page">MisPedidosPage</div>,
}));

vi.mock('../../pages/admin/AdminLayout', () => ({
  AdminLayout: () => <div data-testid="admin-layout">AdminLayout</div>,
}));

vi.mock('../../pages/admin/PedidosAdminPage', () => ({
  PedidosAdminPage: () => <div>PedidosAdminPage</div>,
}));

vi.mock('../../pages/admin/AdminUsersPage', () => ({
  AdminUsersPage: () => <div>AdminUsersPage</div>,
}));

vi.mock('../../pages/admin/AdminMetricasPage', () => ({
  AdminMetricasPage: () => <div>AdminMetricasPage</div>,
}));

vi.mock('../../pages/admin/AdminProductosPage', () => ({
  AdminProductosPage: () => <div>AdminProductosPage</div>,
}));

vi.mock('../../pages/admin/AdminCategoriasPage', () => ({
  AdminCategoriasPage: () => <div>AdminCategoriasPage</div>,
}));

vi.mock('../../pages/admin/AdminIngredientesPage', () => ({
  AdminIngredientesPage: () => <div>AdminIngredientesPage</div>,
}));

vi.mock('../../pages/admin/AdminProfilePage', () => ({
  AdminProfilePage: () => <div>AdminProfilePage</div>,
}));

vi.mock('../../pages/client/ClienteLayout', async () => {
  const { Outlet } = await import('react-router-dom');
  return {
    ClienteLayout: () => (
      <div data-testid="cliente-layout">
        <Outlet />
      </div>
    ),
  };
});

// ---- Auth store mock — anonymous by default ----------------------------------
const mockAuthState = {
  user: null as null | { id: number; email: string; nombre: string; apellido: string; roles: string[] },
  isAuthenticated: () => mockAuthState.user !== null,
  hasRole: (role: string) => mockAuthState.user?.roles.includes(role) ?? false,
};

vi.mock('../../features/auth/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: typeof mockAuthState) => unknown) =>
    selector(mockAuthState),
  ),
}));

// ---- Import AppRoute AFTER mocks --------------------------------------------
import AppRoute from '../AppRoute';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoute />
    </MemoryRouter>,
  );
}

describe('AppRoute — public catalog access (Group 1 RED)', () => {
  beforeEach(() => {
    // Reset to anonymous
    mockAuthState.user = null;
  });

  // 1.1 — RED: anonymous visitor sees CatalogPage at /cliente/catalogo (currently fails)
  it('1.1 anonymous visitor renders CatalogPage at /cliente/catalogo without redirect', () => {
    renderAt('/cliente/catalogo');
    expect(screen.getByTestId('catalog-page')).toBeInTheDocument();
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument();
  });

  // 1.2 — RED: anonymous visitor sees ProductDetailPage at /cliente/catalogo/:id (currently fails)
  it('1.2 anonymous visitor renders ProductDetailPage at /cliente/catalogo/123 without redirect', () => {
    renderAt('/cliente/catalogo/123');
    expect(screen.getByTestId('product-detail-page')).toBeInTheDocument();
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument();
  });

  // 1.3 — SHOULD PASS: anonymous visitor is redirected from /cliente/checkout to /login
  it('1.3 anonymous visitor navigating to /cliente/checkout is redirected to /login', () => {
    renderAt('/cliente/checkout');
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('checkout-page')).not.toBeInTheDocument();
  });

  // 1.4 — SHOULD PASS: anonymous visitor is redirected from /cliente/perfil to /login
  it('1.4 anonymous visitor navigating to /cliente/perfil is redirected to /login', () => {
    renderAt('/cliente/perfil');
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('profile-page')).not.toBeInTheDocument();
  });
});
