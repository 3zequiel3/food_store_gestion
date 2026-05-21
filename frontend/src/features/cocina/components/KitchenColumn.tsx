import type { CocinaPedidoResponse, CocinaEstado } from '../types/cocina.types';
import { KitchenOrderCard } from './KitchenOrderCard';

interface KitchenColumnProps {
  title: string;
  estado: CocinaEstado;
  orders: CocinaPedidoResponse[];
  onTransition: (orderId: number, targetState: string) => void;
  transitioningId: number | null;
}

/**
 * Columna del Kanban de cocina.
 *
 * Header con nombre + cantidad de pedidos.
 * Lista de KitchenOrderCard filtrados por estado.
 */
export function KitchenColumn({
  title,
  estado,
  orders,
  onTransition,
  transitioningId,
}: KitchenColumnProps) {
  const filtered = orders.filter((o) => o.estado === estado);

  return (
    <div className="flex flex-col bg-muted/30 rounded-xl border border-border overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-muted/50">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground uppercase tracking-wide">
            {title}
          </h2>
          <span className="text-xs font-mono bg-secondary text-secondary-foreground px-2 py-0.5 rounded-full">
            {filtered.length}
          </span>
        </div>
      </div>

      {/* Cards */}
      <div className="flex-1 p-3 space-y-3 overflow-y-auto min-h-[200px]">
        {filtered.length === 0 ? (
          <p className="text-center text-sm text-muted-foreground py-8">
            No hay pedidos
          </p>
        ) : (
          filtered.map((order) => (
            <KitchenOrderCard
              key={order.id}
              order={order}
              onTransition={onTransition}
              isTransitioning={transitioningId === order.id}
            />
          ))
        )}
      </div>
    </div>
  );
}
