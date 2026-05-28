import { useQuery } from '@tanstack/react-query';
import { listOrders } from '../services/orders.service';
import type { OrderFilters } from '../types/orders.types';

export function useOrders(filters: OrderFilters = {}, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: ['orders', filters],
    queryFn: () => listOrders(filters),
    // Always refetch on mount + focus so re-navigating to "Mis pedidos"
    // or coming back to the tab brings the latest list. WS realtime
    // updates the cache while open; these settings cover cold loads.
    staleTime: 0,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
    refetchInterval,
  });
}
