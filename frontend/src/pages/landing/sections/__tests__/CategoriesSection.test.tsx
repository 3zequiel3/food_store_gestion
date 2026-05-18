import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { CategoriesSection } from '../CategoriesSection';
import * as useCategoriasMod from '../../../../features/categorias/hooks/useCategorias';
import type { CategoriaRead } from '../../../../features/categorias/types/categorias.types';

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

vi.mock('../../../../features/categorias/hooks/useCategorias');

const defaultCategorias: CategoriaRead[] = [
  { id: 1, nombre: 'Pizza', padre_id: null },
  { id: 2, nombre: 'Hamburguesa', padre_id: null },
  { id: 3, nombre: 'Sandwich', padre_id: null },
  { id: 4, nombre: 'Cafe', padre_id: null },
  { id: 5, nombre: 'Postre', padre_id: null },
  { id: 6, nombre: 'Sopa', padre_id: null },
];

function renderCategories() {
  return render(
    <MemoryRouter>
      <CategoriesSection />
    </MemoryRouter>,
  );
}

describe('CategoriesSection', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
    vi.spyOn(useCategoriasMod, 'useCategorias').mockReturnValue({
      data: defaultCategorias,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as ReturnType<typeof useCategoriasMod.useCategorias>);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders up to 6 category cards', () => {
    renderCategories();
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThanOrEqual(1);
    expect(buttons.length).toBeLessThanOrEqual(6);
  });

  it('each category card has role="button" and tabIndex=0', () => {
    renderCategories();
    const buttons = screen.getAllByRole('button');
    buttons.forEach((btn) => {
      expect(btn).toHaveAttribute('tabindex', '0');
    });
  });

  it('cards apply min-h or h height class for larger sizing', () => {
    renderCategories();
    const buttons = screen.getAllByRole('button');
    const hasHeightClass = buttons.some(
      (btn) =>
        btn.className.includes('min-h-[8rem]') ||
        btn.className.includes('min-h-32') ||
        btn.className.includes('h-32') ||
        btn.className.includes('h-[8rem]'),
    );
    expect(hasHeightClass).toBe(true);
  });

  it('the scroll container has overflow-x-auto and snap-x classes', () => {
    renderCategories();
    const section = screen.getByRole('heading', { name: /categor/i }).closest('section');
    const scrollContainer = section?.querySelector('.overflow-x-auto');
    expect(scrollContainer).not.toBeNull();
    expect(scrollContainer?.className).toContain('snap-x');
  });

  it('shows loading skeletons when isLoading is true (no buttons)', () => {
    vi.spyOn(useCategoriasMod, 'useCategorias').mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as ReturnType<typeof useCategoriasMod.useCategorias>);

    renderCategories();
    const buttons = screen.queryAllByRole('button');
    expect(buttons.length).toBe(0);
  });

  it('shows error state with retry button when isError is true', () => {
    vi.spyOn(useCategoriasMod, 'useCategorias').mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: vi.fn(),
    } as ReturnType<typeof useCategoriasMod.useCategorias>);

    renderCategories();
    expect(screen.getByText(/reintentar/i)).toBeInTheDocument();
  });
});
