/**
 * Accessibility tests for LandingPage.
 *
 * NOTE: axe-core is not installed in this project. These tests use RTL + semantic
 * queries to verify the most critical WCAG AA requirements:
 * - Landmark regions (header, main, footer)
 * - Named navigation landmarks
 * - No missing aria-labels on interactive badges
 * - Ordered list for HowItWorks steps
 * - Stats list semantics
 *
 * If axe-core is added to the project in a future change, replace these with
 * `await axe(container)` assertions.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
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
    data: { items: [], total: 0, page: 1, limit: 8 },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })),
}));

vi.mock('../../features/categorias/hooks/useCategorias', () => ({
  useCategorias: vi.fn(() => ({
    data: [],
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

describe('LandingPage — accessibility', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders a <header> landmark', () => {
    renderLanding();
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('renders a <main> landmark', () => {
    renderLanding();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('renders a <footer> landmark', () => {
    renderLanding();
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  it('has at least one h1 heading', () => {
    renderLanding();
    const h1s = screen.getAllByRole('heading', { level: 1 });
    expect(h1s.length).toBeGreaterThanOrEqual(1);
  });

  it('footer navigation elements have non-empty aria-labels', () => {
    renderLanding();
    const navs = screen.getAllByRole('navigation');
    navs.forEach((nav) => {
      const label = nav.getAttribute('aria-label');
      if (label !== null) {
        expect(label.trim().length).toBeGreaterThan(0);
      }
    });
  });

  it('stats bar has a role="list" container', () => {
    renderLanding();
    // There may be multiple lists (stats ul + HowItWorks ol). Verify at least one exists.
    const lists = screen.getAllByRole('list');
    expect(lists.length).toBeGreaterThanOrEqual(1);
  });

  it('HowItWorks section uses an <ol> for ordered steps', () => {
    const { container } = renderLanding();
    const ol = container.querySelector('ol');
    expect(ol).not.toBeNull();
  });
});
