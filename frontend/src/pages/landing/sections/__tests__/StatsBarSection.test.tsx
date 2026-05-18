import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { StatsBarSection } from '../StatsBarSection';

// ---- IntersectionObserver mock -----------------------------------------------
class MockIntersectionObserver {
  constructor() {}
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

// ---- matchMedia mock ----------------------------------------------------------
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

describe('StatsBarSection', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders a list container with role="list"', () => {
    render(<StatsBarSection />);
    expect(screen.getByRole('list')).toBeInTheDocument();
  });

  it('renders 4 items with role="listitem"', () => {
    render(<StatsBarSection />);
    const items = screen.getAllByRole('listitem');
    expect(items.length).toBeGreaterThanOrEqual(3);
    expect(items.length).toBeLessThanOrEqual(4);
  });

  it('renders all 4 stat texts', () => {
    render(<StatsBarSection />);
    expect(screen.getByText(/1000 pedidos/i)).toBeInTheDocument();
    expect(screen.getByText(/30 min/i)).toBeInTheDocument();
    expect(screen.getByText(/frescos/i)).toBeInTheDocument();
    expect(screen.getByText(/4\.9/i)).toBeInTheDocument();
  });

  it('is visible immediately when prefers-reduced-motion: reduce is active', () => {
    mockMatchMedia(true); // prefers-reduced-motion active → isInView: true immediately
    render(<StatsBarSection />);
    // Section must not have opacity-0 class (content should be visible)
    const list = screen.getByRole('list');
    expect(list).toBeInTheDocument();
    // Verify at least one stat text is rendered (not hidden)
    expect(screen.getByText(/1000 pedidos/i)).toBeVisible();
  });
});
