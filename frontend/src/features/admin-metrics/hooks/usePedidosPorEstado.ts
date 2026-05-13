import { useQuery } from '@tanstack/react-query';
import { getPedidosPorEstado } from '../services/admin-metrics.service';
import type { MetricsDateFilter } from '../types/admin-metrics.types';

export function usePedidosPorEstado(filter: MetricsDateFilter) {
  return useQuery({
    queryKey: ['admin-metrics', 'pedidos-por-estado', filter],
    queryFn: () => getPedidosPorEstado(filter),
    staleTime: 60_000,
  });
}
