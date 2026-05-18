import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { HeroSection } from '../HeroSection';

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

// Mock authStore
vi.mock('../../../../features/auth/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { isAuthenticated: () => boolean }) => unknown) =>
    selector({ isAuthenticated: () => false }),
  ),
}));

function renderHero() {
  return render(
    <MemoryRouter>
      <HeroSection />
    </MemoryRouter>,
  );
}

describe('HeroSection', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders two distinguishable areas: copy (data-testid=hero-copy) and visual (data-testid=hero-visual)', () => {
    renderHero();
    expect(screen.getByTestId('hero-copy')).toBeInTheDocument();
    expect(screen.getByTestId('hero-visual')).toBeInTheDocument();
  });

  it('has a two-column grid class at lg breakpoint', () => {
    renderHero();
    // The grid container uses lg:grid-cols-[3fr_2fr]
    const grid = screen.getByTestId('hero-copy').parentElement;
    expect(grid?.className).toContain('lg:grid-cols-');
  });

  it('does NOT render the old centered Card variant="glass" inline-block pattern', () => {
    renderHero();
    // The old hero had a single centered glass card. Verify it's gone.
    // We check that there's no element with class "inline-block" inside the hero section
    const section = screen.getByTestId('hero-copy').closest('section');
    const inlineBlock = section?.querySelector('.inline-block');
    expect(inlineBlock).toBeNull();
  });

  it('renders a "Ver menú" CTA button', () => {
    renderHero();
    expect(screen.getByRole('button', { name: /ver men/i })).toBeInTheDocument();
  });

  it('renders an "Ingresar" CTA button', () => {
    renderHero();
    expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument();
  });

  it('the "Ver menú" button is clickable (has onClick)', () => {
    renderHero();
    const btn = screen.getByRole('button', { name: /ver men/i });
    expect(btn).not.toBeDisabled();
  });
});
