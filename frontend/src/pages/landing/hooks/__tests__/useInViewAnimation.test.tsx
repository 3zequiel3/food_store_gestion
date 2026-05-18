import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useInViewAnimation } from '../useInViewAnimation';

// ---- IntersectionObserver mock -----------------------------------------------
type IntersectionCallback = (entries: IntersectionObserverEntry[]) => void;

let observerCallback: IntersectionCallback | null = null;
let observeTarget: Element | null = null;

const mockObserve = vi.fn((el: Element) => {
  observeTarget = el;
});
const mockUnobserve = vi.fn();
const mockDisconnect = vi.fn();

class MockIntersectionObserver {
  constructor(callback: IntersectionCallback) {
    observerCallback = callback;
  }
  observe = mockObserve;
  unobserve = mockUnobserve;
  disconnect = mockDisconnect;
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

// ---- helper to fire intersection events -------------------------------------
function fireIntersection(isIntersecting: boolean) {
  if (!observerCallback || !observeTarget) return;
  act(() => {
    observerCallback!([
      {
        isIntersecting,
        target: observeTarget!,
      } as IntersectionObserverEntry,
    ]);
  });
}

// ==============================================================================
describe('useInViewAnimation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    observerCallback = null;
    observeTarget = null;

    // Default: normal motion preferences, IntersectionObserver available
    mockMatchMedia(false);
    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns { ref, isInView } with isInView initially false', () => {
    const { result } = renderHook(() => useInViewAnimation());
    expect(result.current.ref).toBeDefined();
    expect(result.current.isInView).toBe(false);
  });

  it('sets isInView to true when IntersectionObserver fires with isIntersecting: true', () => {
    const { result } = renderHook(() => useInViewAnimation());

    const div = document.createElement('div');
    act(() => {
      result.current.ref(div);
    });

    fireIntersection(true);
    expect(result.current.isInView).toBe(true);
  });

  it('does NOT revert isInView to false after becoming true (once-only)', () => {
    const { result } = renderHook(() => useInViewAnimation());

    const div = document.createElement('div');
    act(() => {
      result.current.ref(div);
    });

    fireIntersection(true);
    expect(result.current.isInView).toBe(true);

    fireIntersection(false);
    expect(result.current.isInView).toBe(true); // must NOT flip back
  });

  it('returns isInView: true immediately when prefers-reduced-motion: reduce is active', () => {
    mockMatchMedia(true);
    const { result } = renderHook(() => useInViewAnimation());
    expect(result.current.isInView).toBe(true);
  });

  it('returns isInView: true immediately when IntersectionObserver is undefined', () => {
    vi.stubGlobal('IntersectionObserver', undefined);
    const { result } = renderHook(() => useInViewAnimation());
    expect(result.current.isInView).toBe(true);
  });

  it('calls disconnect on cleanup (unmount)', () => {
    const { result, unmount } = renderHook(() => useInViewAnimation());

    const div = document.createElement('div');
    act(() => {
      result.current.ref(div);
    });

    unmount();
    expect(mockDisconnect).toHaveBeenCalled();
  });
});
