import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { getProducts } from '../services/products.service';
import type { ProductFilters } from '../types/products.types';

/**
 * Hook para el listado paginado de productos con filtros.
 *
 * D2: usa `keepPreviousData` para evitar flicker al cambiar de página.
 * El queryKey incluye el objeto completo de filtros — TanStack Query lo
 * serializa y lo usa como clave de cache, así el cache es por combinación
 * de filtros (D1: filtros en URL → queryKey derivado de searchParams).
 */
export function useProducts(filters: ProductFilters = {}) {
  return useQuery({
    queryKey: ['products', filters],
    queryFn: () => getProducts(filters),
    placeholderData: keepPreviousData,
  });
}
