import { useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { KitchenKanban } from '../components/KitchenKanban';
import { useKitchenOrders } from '../hooks/useKitchenOrders';
import { useCocinaWebSocket } from '../hooks/useCocinaWebSocket';
import { transitionKitchenOrder } from '../api/cocinaApi';
import type { AvailabilityRestoredPayload } from '../hooks/useCocinaWebSocket';

/**
 * Página principal del Kitchen Display System (KDS).
 *
 * Compone:
 * - WebSocket hook para eventos en tiempo real
 * - TanStack Query hook para carga inicial + polling de fallback
 * - Kanban board con 2 columnas
 *
 * Cuando el WS se desconecta, activa polling cada 30s como fallback.
 *
 * P0.1 (cook): expone reportIngredientUnavailable al kanban via WS send.
 * ingredient_availability_restored → toast de notificación al cocinero.
 */
export function CocinaPage() {
  const queryClient = useQueryClient();
  const [transitioningId, setTransitioningId] = useState<number | null>(null);

  const handleAvailabilityRestored = useCallback(
    (payload: AvailabilityRestoredPayload) => {
      const name = payload.ingrediente_nombre ?? `Ingrediente #${payload.ingrediente_id}`;
      toast.success(`"${name}" vuelve a estar disponible`, {
        description: 'El ingrediente fue repuesto por el admin.',
        duration: 6_000,
      });
    },
    [],
  );

  const { isConnected, reportIngredientUnavailable } = useCocinaWebSocket({
    onAvailabilityRestored: handleAvailabilityRestored,
  });

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
      onIngredientUnavailable={reportIngredientUnavailable}
    />
  );
}
