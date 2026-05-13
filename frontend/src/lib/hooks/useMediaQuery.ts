import { useState, useEffect } from 'react';

/**
 * Hook que detecta si el viewport coincide con un media query.
 * Útil para condicionar renders entre mobile y desktop (D3).
 *
 * Ejemplo:
 *   const isDesktop = useMediaQuery('(min-width: 768px)');
 *
 * SSR-safe: el valor inicial es `false` (mobile-first por defecto)
 * hasta que el efecto corre en el browser.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    // Inicializamos ya con el valor correcto del browser
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQueryList = window.matchMedia(query);

    // El handler es el único lugar donde llamamos setState — dentro de callback
    const handler = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    mediaQueryList.addEventListener('change', handler);
    return () => mediaQueryList.removeEventListener('change', handler);
  }, [query]);

  return matches;
}
