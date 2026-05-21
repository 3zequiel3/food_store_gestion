import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { KitchenKanban } from '../components/KitchenKanban';
import { useKitchenOrders } from '../hooks/useKitchenOrders';
import { useCocinaWebSocket } from '../hooks/useCocinaWebSocket';
import { transitionKitchenOrder } from '../api/cocinaApi';

/**
 * Página principal del Kitchen Display System (KDS).
 *
 * Compone:
 * - WebSocket hook para eventos en tiempo real
 * - TanStack Query hook para carga inicial + polling de fallback
 * - Kanban board con 2 columnas
 *
 * Cuando el WS se desconecta, activa polling cada 30s como fallback.
 */
export function CocinaPage() {
  const { isConnected } = useCocinaWebSocket();
  const queryClient = useQueryClient();
  const [transitioningId, setTransitioningId] = useState<number | null>(null);

  // Polling de fallback cuando WS está caído
  const { data: orders = [] } = useKitchenOrders({
    refetchInterval: isConnected ? false : 30_000,
  });

  async function handleTransition(orderId: number, targetState: string) {
    setTransitioningId(orderId);
    try {
      await transitionKitchenOrder(orderId, targetState);
      // Invalidar para refrescar desde el backend
      queryClient.invalidateQueries({ queryKey: ['cocina', 'pedidos'] });
    } catch {
      // El error ya fue manejado por el interceptor (toast)
    } finally {
      setTransitioningId(null);
    }
  }

  return (
    <KitchenKanban
      orders={orders}
      isConnected={isConnected}
      onTransition={handleTransition}
      transitioningId={transitioningId}
    />
  );
}
