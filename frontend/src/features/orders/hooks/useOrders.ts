import { useQuery } from '@tanstack/react-query';
import { listOrders } from '../services/orders.service';
import type { OrderFilters } from '../types/orders.types';

export function useOrders(filters: OrderFilters = {}) {
  return useQuery({
    queryKey: ['orders', filters],
    queryFn: () => listOrders(filters),
    staleTime: 30_000,
  });
}
