import { KitchenColumn } from './KitchenColumn';
import { ConnectionStatus } from './ConnectionStatus';
import type { CocinaPedidoResponse } from '../types/cocina.types';

interface KitchenKanbanProps {
  orders: CocinaPedidoResponse[];
  isConnected: boolean;
  onTransition: (orderId: number, targetState: string) => void;
  transitioningId: number | null;
}

/**
 * Tablero Kanban de cocina con 2 columnas:
 * - CONFIRMADO = "Por preparar"
 * - EN_PREPARACION = "En preparación"
 *
 * Incluye indicador de conexión WebSocket.
 */
export function KitchenKanban({
  orders,
  isConnected,
  onTransition,
  transitioningId,
}: KitchenKanbanProps) {
  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">Cocina</h1>
        <ConnectionStatus isConnected={isConnected} />
      </div>

      {/* Kanban columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <KitchenColumn
          title="Por preparar"
          estado="CONFIRMADO"
          orders={orders}
          onTransition={onTransition}
          transitioningId={transitioningId}
        />
        <KitchenColumn
          title="En preparación"
          estado="EN_PREPARACION"
          orders={orders}
          onTransition={onTransition}
          transitioningId={transitioningId}
        />
      </div>
    </div>
  );
}
