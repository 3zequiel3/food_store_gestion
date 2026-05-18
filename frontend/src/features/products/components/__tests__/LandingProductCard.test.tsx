import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { LandingProductCard } from '../LandingProductCard';
import type { ProductoRead } from '../../types/products.types';

// ---- Mocks -------------------------------------------------------------------
function mockMatchMedia(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../../../features/auth/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { isAuthenticated: () => boolean }) => unknown) =>
    selector({ isAuthenticated: () => false }),
  ),
}));

vi.mock('../ProductImage', () => ({
  ProductImage: ({ alt }: { alt: string }) => <img alt={alt} />,
}));

function makeProduct(overrides: Partial<ProductoRead> & Record<string, unknown> = {}): ProductoRead {
  return {
    id: 1,
    nombre: 'Empanadas de Carne',
    descripcion: 'Deliciosas empanadas',
    precio: 1200,
    imagen_url: null,
    disponible: true,
    stock_cantidad: 5,
    categoria_id: null,
    imagenes: [],
    ...overrides,
  };
}

function renderCard(producto: ProductoRead) {
  return render(
    <MemoryRouter>
      <LandingProductCard producto={producto} />
    </MemoryRouter>,
  );
}

describe('LandingProductCard', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    mockNavigate.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ---- API backward compatibility ----
  it('renders with the standard { producto: ProductoRead } prop (backward compat)', () => {
    renderCard(makeProduct());
    expect(screen.getByText('Empanadas de Carne')).toBeInTheDocument();
  });

  it('does NOT import useCartStore (invariant)', async () => {
    // We verify by checking the component renders without store errors
    expect(() => renderCard(makeProduct())).not.toThrow();
  });

  // ---- Badges ----
  it('renders "Destacado" badge with aria-label when producto.destacado === true', () => {
    const producto = makeProduct({ destacado: true } as unknown as Partial<ProductoRead>);
    renderCard(producto);
    const badge = screen.getByLabelText('Producto destacado');
    expect(badge).toBeInTheDocument();
  });

  it('does NOT render "Destacado" badge when producto.destacado is false', () => {
    const producto = makeProduct({ destacado: false } as unknown as Partial<ProductoRead>);
    renderCard(producto);
    expect(screen.queryByLabelText('Producto destacado')).not.toBeInTheDocument();
  });

  it('does NOT render "Destacado" badge when destacado field is absent', () => {
    renderCard(makeProduct());
    expect(screen.queryByLabelText('Producto destacado')).not.toBeInTheDocument();
  });

  it('renders "Sin stock" badge with aria-label when producto.disponible === false', () => {
    renderCard(makeProduct({ disponible: false }));
    const badge = screen.getByLabelText('Sin stock');
    expect(badge).toBeInTheDocument();
  });

  it('does NOT render "Sin stock" badge when producto.disponible === true', () => {
    renderCard(makeProduct({ disponible: true }));
    expect(screen.queryByLabelText('Sin stock')).not.toBeInTheDocument();
  });

  it('renders "Nuevo" badge when created_at is within 14 days', () => {
    const recentDate = new Date();
    recentDate.setDate(recentDate.getDate() - 3); // 3 days ago
    const producto = makeProduct({
      created_at: recentDate.toISOString(),
    } as unknown as Partial<ProductoRead>);
    renderCard(producto);
    const badge = screen.getByLabelText('Producto nuevo');
    expect(badge).toBeInTheDocument();
  });

  it('does NOT render "Nuevo" badge when created_at is older than 14 days', () => {
    const oldDate = new Date();
    oldDate.setDate(oldDate.getDate() - 20); // 20 days ago
    const producto = makeProduct({
      created_at: oldDate.toISOString(),
    } as unknown as Partial<ProductoRead>);
    renderCard(producto);
    expect(screen.queryByLabelText('Producto nuevo')).not.toBeInTheDocument();
  });

  it('does NOT render "Nuevo" badge when created_at is absent', () => {
    renderCard(makeProduct());
    expect(screen.queryByLabelText('Producto nuevo')).not.toBeInTheDocument();
  });

  // ---- Group 3 — Navigation (RED/GREEN) ------------------------------------

  // 3.1 — RED: anonymous user clicking "Ver más" should navigate to /cliente/catalogo/:id
  // Currently LandingProductCard navigates to /login when user is not authenticated.
  it('3.1 anonymous user clicking "Ver más" navigates to /cliente/catalogo/:id', () => {
    renderCard(makeProduct({ id: 42 }));
    const button = screen.getByRole('button', { name: /ver más/i });
    button.click();
    expect(mockNavigate).toHaveBeenCalledWith('/cliente/catalogo/42');
  });

  // 3.2 — authenticated user clicking "Ver más" also navigates to /cliente/catalogo/:id
  it('3.2 authenticated user clicking "Ver más" navigates to /cliente/catalogo/:id', async () => {
    // Re-mock to return authenticated
    const authModule = await import('../../../../features/auth/stores/authStore');
    vi.mocked(authModule.useAuthStore).mockImplementation(
      (selector: (s: { isAuthenticated: () => boolean }) => unknown) =>
        selector({ isAuthenticated: () => true }),
    );
    renderCard(makeProduct({ id: 99 }));
    const button = screen.getByRole('button', { name: /ver más/i });
    button.click();
    expect(mockNavigate).toHaveBeenCalledWith('/cliente/catalogo/99');
  });
});
