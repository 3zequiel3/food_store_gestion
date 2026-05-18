/**
 * Tests — Group 4: TopNavbar dual-mode (anonymous vs authenticated)
 *
 * 4.1 (RED): anonymous user sees Login/Register CTAs, no avatar.
 * 4.2 (PASS): anonymous user with cart items sees badge with totalItems.
 * 4.3 (PASS): anonymous user with empty cart sees cart button without badge.
 * 4.4 (PASS): authenticated CLIENT sees avatar + cart, no public CTAs.
 * 4.5 (PASS): authenticated ADMIN sees avatar, no cart button.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Usuario } from '../../../features/auth/types/auth.types';

// ---- Mutable mock state (mutated in beforeEach per test) -------------------
const authState = {
  user: null as Usuario | null,
};

const cartItems: Array<{ producto_id: number; cantidad: number }> = [];

vi.mock('../../../features/auth/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: {
    user: Usuario | null;
    hasRole: (r: string) => boolean;
  }) => unknown) =>
    selector({
      user: authState.user,
      hasRole: (role: string) => authState.user?.roles.includes(role) ?? false,
    }),
  ),
}));

vi.mock('../../../features/cart/stores/cartStore', () => ({
  useCartStore: vi.fn((selector: (s: {
    items: Array<{ producto_id: number; cantidad: number }>;
  }) => unknown) =>
    selector({ items: cartItems }),
  ),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    Link: ({ to, children }: { to: string; children: React.ReactNode }) => (
      <a href={to}>{children}</a>
    ),
  };
});

import { TopNavbar } from '../TopNavbar';

const clientUser: Usuario = {
  id: 1,
  email: 'cliente@test.com',
  nombre: 'Juan',
  apellido: 'Perez',
  roles: ['CLIENT'],
};

const adminUser: Usuario = {
  id: 2,
  email: 'admin@test.com',
  nombre: 'Admin',
  apellido: 'User',
  roles: ['ADMIN'],
};

// Helper to reset cart
function clearCartItems() {
  cartItems.splice(0, cartItems.length);
}

function setCartItems(items: typeof cartItems) {
  clearCartItems();
  cartItems.push(...items);
}

function renderNavbar() {
  // vi.mock factories above close over authState / cartItems (mutable objects).
  // The selector is called at render time with the latest values.
  return render(<TopNavbar onCartOpen={vi.fn()} />);
}

describe('TopNavbar dual-mode (Group 4)', () => {
  beforeEach(() => {
    authState.user = null;
    clearCartItems();
  });

  // 4.1 — RED: anonymous sees "Iniciar sesión" and "Registrarse", no avatar
  it('4.1 anonymous user sees Login and Register CTAs, no avatar', () => {
    renderNavbar();
    expect(screen.getByText('Iniciar sesión')).toBeInTheDocument();
    expect(screen.getByText('Registrarse')).toBeInTheDocument();
    // No user name visible (avatar with name is shown only when authenticated)
    expect(screen.queryByText('Juan')).not.toBeInTheDocument();
  });

  // 4.2 — anonymous user with items in cart sees badge showing totalItems
  it('4.2 anonymous user with cart items sees cart badge with totalItems', () => {
    setCartItems([
      { producto_id: 1, cantidad: 2 },
      { producto_id: 2, cantidad: 3 },
    ]);
    renderNavbar();
    // Cart button visible
    expect(screen.getByRole('button', { name: /carrito/i })).toBeInTheDocument();
    // Badge with total count (5)
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  // 4.3 — anonymous user with empty cart sees cart button without badge
  it('4.3 anonymous user with empty cart sees cart button without badge', () => {
    clearCartItems();
    renderNavbar();
    expect(screen.getByRole('button', { name: /carrito/i })).toBeInTheDocument();
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  // 4.4 — authenticated CLIENT sees avatar + cart, no public CTAs
  it('4.4 authenticated CLIENT sees avatar and cart, no Login/Register CTAs', () => {
    authState.user = clientUser;
    renderNavbar();
    const initials = `${clientUser.nombre.charAt(0)}${clientUser.apellido.charAt(0)}`.toUpperCase();
    expect(screen.getByText(initials)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /carrito/i })).toBeInTheDocument();
    expect(screen.queryByText('Iniciar sesión')).not.toBeInTheDocument();
    expect(screen.queryByText('Registrarse')).not.toBeInTheDocument();
  });

  // 4.5 — authenticated ADMIN sees avatar, no cart button
  it('4.5 authenticated ADMIN sees avatar, no cart button', () => {
    authState.user = adminUser;
    renderNavbar();
    const initials = `${adminUser.nombre.charAt(0)}${adminUser.apellido.charAt(0)}`.toUpperCase();
    expect(screen.getByText(initials)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /carrito/i })).not.toBeInTheDocument();
    expect(screen.queryByText('Iniciar sesión')).not.toBeInTheDocument();
    expect(screen.queryByText('Registrarse')).not.toBeInTheDocument();
  });
});
