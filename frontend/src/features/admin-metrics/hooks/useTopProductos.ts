import { useQuery } from '@tanstack/react-query';
import { getTopProductos } from '../services/admin-metrics.service';
import type { MetricsDateFilter } from '../types/admin-metrics.types';

export function useTopProductos(filter: MetricsDateFilter, top = 10) {
  return useQuery({
    queryKey: ['admin-metrics', 'top-productos', filter, top],
    queryFn: () => getTopProductos(filter, top),
    staleTime: 60_000,
  });
}
