import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { FeaturedProductsSection } from '../FeaturedProductsSection';
import * as useProductsMod from '../../../../features/products/hooks/useProducts';
import type { ProductoRead } from '../../../../features/products/types/products.types';

// ---- Mocks -------------------------------------------------------------------
class MockIntersectionObserver {
  constructor() {}
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

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

vi.mock('../../../../features/auth/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { isAuthenticated: () => boolean }) => unknown) =>
    selector({ isAuthenticated: () => false }),
  ),
}));

vi.mock('../../../../features/products/hooks/useProducts');

function makeProduct(id: number): ProductoRead {
  return {
    id,
    nombre: `Producto ${id}`,
    descripcion: 'Descripción del producto',
    precio: 1500,
    imagen_url: null,
    disponible: true,
    stock_cantidad: 10,
    categoria_id: null,
    imagenes: [],
  };
}

const defaultProducts: ProductoRead[] = Array.from({ length: 4 }, (_, i) => makeProduct(i + 1));

function renderFeatured() {
  return render(
    <MemoryRouter>
      <FeaturedProductsSection />
    </MemoryRouter>,
  );
}

describe('FeaturedProductsSection', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
    vi.spyOn(useProductsMod, 'useProducts').mockReturnValue({
      data: { items: defaultProducts, total: 4, page: 1, limit: 8 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as ReturnType<typeof useProductsMod.useProducts>);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders up to 8 products via LandingProductCard', () => {
    renderFeatured();
    // Each LandingProductCard renders a "Ver más" button — use heading or product name
    expect(screen.getByText('Producto 1')).toBeInTheDocument();
    expect(screen.getByText('Producto 4')).toBeInTheDocument();
  });

  it('each product item wrapper has an animationDelay style (stagger)', () => {
    renderFeatured();
    // The wrapping div for each product card has style.animationDelay
    const heading = screen.getByRole('heading', { name: /productos destacados/i });
    const grid = heading.nextElementSibling;
    // First wrapper item should have animationDelay: '0ms'
    const firstItem = grid?.children[0] as HTMLElement;
    expect(firstItem?.style.animationDelay).toBe('0ms');
    // Second item
    const secondItem = grid?.children[1] as HTMLElement;
    expect(secondItem?.style.animationDelay).toBe('80ms');
  });

  it('shows loading skeletons when isLoading is true', () => {
    vi.spyOn(useProductsMod, 'useProducts').mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as ReturnType<typeof useProductsMod.useProducts>);

    renderFeatured();
    // Loading renders ProductCardSkeleton — no product names
    expect(screen.queryByText('Producto 1')).not.toBeInTheDocument();
  });

  it('shows error state with retry button', () => {
    vi.spyOn(useProductsMod, 'useProducts').mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    } as ReturnType<typeof useProductsMod.useProducts>);

    renderFeatured();
    expect(screen.getByText(/reintentar/i)).toBeInTheDocument();
  });

  it('shows empty state when products list is empty', () => {
    vi.spyOn(useProductsMod, 'useProducts').mockReturnValue({
      data: { items: [], total: 0, page: 1, limit: 8 },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as ReturnType<typeof useProductsMod.useProducts>);

    renderFeatured();
    expect(screen.getByText(/no hay productos/i)).toBeInTheDocument();
  });
});
