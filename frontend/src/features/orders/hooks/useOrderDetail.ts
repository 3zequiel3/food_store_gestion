import { useQuery } from '@tanstack/react-query';
import { getOrderDetail } from '../services/orders.service';

interface UseOrderDetailOptions {
  /**
   * Polling interval in ms. Pass `false` to disable (default).
   * Set to 30_000 when the WS transport is degraded (P1.5 fallback).
   */
  refetchInterval?: number | false;
}

export function useOrderDetail(id: number | null, options: UseOrderDetailOptions = {}) {
  return useQuery({
    queryKey: ['orders', id],
    queryFn: () => getOrderDetail(id!),
    enabled: id !== null,
    refetchInterval: options.refetchInterval ?? false,
  });
}
