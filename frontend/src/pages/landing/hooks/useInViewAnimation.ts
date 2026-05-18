import { useCallback, useEffect, useRef, useState } from 'react';

interface UseInViewAnimationReturn {
  ref: React.RefCallback<HTMLElement>;
  isInView: boolean;
}

/**
 * Returns a callback ref and `isInView` boolean.
 *
 * - Fires once: once `isInView` becomes `true` it never reverts.
 * - Respects `prefers-reduced-motion: reduce` — returns `true` immediately.
 * - Falls back to `true` when `IntersectionObserver` is unavailable.
 */
export function useInViewAnimation(
  options: { threshold?: number; rootMargin?: string } = {},
): UseInViewAnimationReturn {
  const { threshold = 0.15, rootMargin = '0px' } = options;

  // Determine initial value: skip animation if user prefers reduced motion
  // or if IntersectionObserver is not supported.
  function shouldSkipAnimation(): boolean {
    if (typeof IntersectionObserver === 'undefined') return true;
    if (
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return true;
    }
    return false;
  }

  const [isInView, setIsInView] = useState<boolean>(() => shouldSkipAnimation());

  // Keep a ref to the observer so we can clean up when the element changes
  const observerRef = useRef<IntersectionObserver | null>(null);

  const ref = useCallback(
    (el: HTMLElement | null) => {
      // Cleanup previous observer if element changes
      if (observerRef.current) {
        observerRef.current.disconnect();
        observerRef.current = null;
      }

      if (!el) return;

      // Already visible — no need for an observer
      if (shouldSkipAnimation()) {
        setIsInView(true);
        return;
      }

      const observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              setIsInView(true);
              observer.unobserve(entry.target);
            }
          }
        },
        { threshold, rootMargin },
      );

      observer.observe(el);
      observerRef.current = observer;
    },
    [threshold, rootMargin],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
        observerRef.current = null;
      }
    };
  }, []);

  return { ref, isInView };
}
