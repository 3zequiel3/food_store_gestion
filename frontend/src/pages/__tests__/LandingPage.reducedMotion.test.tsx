/**
 * Tests for prefers-reduced-motion behavior on LandingPage.
 * Verifies that all sections are immediately visible when reduced motion is active,
 * and that content does not depend on IntersectionObserver to become visible.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, afterEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { LandingPage } from '../LandingPage';

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

vi.mock('../../features/auth/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { isAuthenticated: () => boolean }) => unknown) =>
    selector({ isAuthenticated: () => false }),
  ),
}));

vi.mock('../../features/products/hooks/useProducts', () => ({
  useProducts: vi.fn(() => ({
    data: {
      items: [
        {
          id: 1,
          nombre: 'Pizza Margherita',
          descripcion: null,
          precio: 2500,
          imagen_url: null,
          disponible: true,
          stock_cantidad: 5,
          categoria_id: null,
          imagenes: [],
        },
      ],
      total: 1,
      page: 1,
      limit: 8,
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
}));

vi.mock('../../features/categorias/hooks/useCategorias', () => ({
  useCategorias: vi.fn(() => ({
    data: [{ id: 1, nombre: 'Pizza', padre_id: null }],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
}));

function renderLanding() {
  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );
}

describe('LandingPage — prefers-reduced-motion', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('sections are visible immediately when prefers-reduced-motion: reduce is active', () => {
    // Simulate prefers-reduced-motion: reduce
    mockMatchMedia(true);
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

    renderLanding();

    // Hero copy should be visible (not opacity-0)
    const heroCopy = screen.getByTestId('hero-copy');
    expect(heroCopy).toBeInTheDocument();
    expect(heroCopy.className).not.toContain('opacity-0');
    expect(heroCopy.className).toContain('opacity-100');
  });

  it('renders hero section content without waiting for IntersectionObserver', () => {
    mockMatchMedia(false);
    // Remove IntersectionObserver completely
    vi.stubGlobal('IntersectionObserver', undefined);

    renderLanding();

    // Hero copy must still be visible (fallback: isInView = true immediately)
    const heroCopy = screen.getByTestId('hero-copy');
    expect(heroCopy).toBeInTheDocument();
    expect(heroCopy.className).toContain('opacity-100');
  });

  it('stats are visible without scroll trigger under reduced motion', () => {
    mockMatchMedia(true);
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

    renderLanding();
    expect(screen.getByText(/1000 pedidos/i)).toBeVisible();
  });

  it('HowItWorks steps visible immediately under reduced motion', () => {
    mockMatchMedia(true);
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

    renderLanding();
    expect(screen.getByText('Elegí')).toBeVisible();
    expect(screen.getByText('Pagá')).toBeVisible();
    expect(screen.getByText('Recibí')).toBeVisible();
  });
});
