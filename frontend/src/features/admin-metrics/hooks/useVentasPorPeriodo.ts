import { useQuery } from '@tanstack/react-query';
import { getVentasPorPeriodo } from '../services/admin-metrics.service';
import type { Granularidad, MetricsDateFilter } from '../types/admin-metrics.types';

export function useVentasPorPeriodo(filter: MetricsDateFilter, granularidad: Granularidad) {
  return useQuery({
    queryKey: ['admin-metrics', 'ventas-por-periodo', filter, granularidad],
    queryFn: () => getVentasPorPeriodo(filter, granularidad),
    staleTime: 60_000,
  });
}
