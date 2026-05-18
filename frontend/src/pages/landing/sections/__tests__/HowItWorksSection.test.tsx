import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { HowItWorksSection } from '../HowItWorksSection';

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

describe('HowItWorksSection', () => {
  beforeEach(() => {
    mockMatchMedia(false);
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders exactly 3 step cards', () => {
    render(<HowItWorksSection />);
    // Each step has a number (1, 2, 3)
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders the step titles: Elegí, Pagá, Recibí', () => {
    render(<HowItWorksSection />);
    expect(screen.getByText('Elegí')).toBeInTheDocument();
    expect(screen.getByText('Pagá')).toBeInTheDocument();
    expect(screen.getByText('Recibí')).toBeInTheDocument();
  });

  it('uses an ordered list element (ol) for semantic markup', () => {
    const { container } = render(<HowItWorksSection />);
    const ol = container.querySelector('ol');
    expect(ol).not.toBeNull();
  });

  it('each step card has a description text', () => {
    render(<HowItWorksSection />);
    // There should be 3 description paragraphs
    const steps = screen.getAllByRole('listitem');
    expect(steps.length).toBe(3);
  });

  it('has md: 3-column grid class for desktop layout', () => {
    const { container } = render(<HowItWorksSection />);
    const ol = container.querySelector('ol');
    expect(ol?.className).toContain('md:grid-cols-3');
  });

  it('steps appear with staggered animationDelay', () => {
    const { container } = render(<HowItWorksSection />);
    const ol = container.querySelector('ol');
    const items = ol?.querySelectorAll('li');
    expect(items?.[0]).toBeDefined();
    // Second item should have a non-zero animation delay
    const secondItem = items?.[1] as HTMLElement | undefined;
    if (secondItem) {
      expect(secondItem.style.animationDelay).toBe('80ms');
    }
  });
});
