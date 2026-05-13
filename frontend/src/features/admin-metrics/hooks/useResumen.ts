import { useQuery } from '@tanstack/react-query';
import { getResumen } from '../services/admin-metrics.service';
import type { MetricsDateFilter } from '../types/admin-metrics.types';

export function useResumen(filter: MetricsDateFilter) {
  return useQuery({
    queryKey: ['admin-metrics', 'resumen', filter],
    queryFn: () => getResumen(filter),
    staleTime: 60_000,
  });
}
