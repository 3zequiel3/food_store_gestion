import { useQuery } from '@tanstack/react-query';
import { getKitchenOrders } from '../api/cocinaApi';

/**
 * TanStack Query hook para GET /cocina/pedidos.
 *
 * Se usa como:
 * - Carga inicial del tablero
 * - Polling de fallback cuando el WebSocket se desconecta
 */
export function useKitchenOrders(opts?: {
  enabled?: boolean;
  refetchInterval?: number | false;
}) {
  return useQuery({
    queryKey: ['cocina', 'pedidos'],
    queryFn: getKitchenOrders,
    staleTime: 10_000,
    enabled: opts?.enabled,
    refetchInterval: opts?.refetchInterval ?? false,
  });
}
