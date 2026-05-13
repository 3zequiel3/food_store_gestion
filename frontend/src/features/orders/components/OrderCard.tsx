import { ShoppingBag } from 'lucide-react';
import type { PedidoListItem } from '../types/orders.types';
import { OrderStatusBadge } from './OrderStatusBadge';

function formatCurrency(value: string): string {
  return `$${parseFloat(value).toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

interface OrderCardProps {
  order: PedidoListItem;
  onClick: (id: number) => void;
}

export function OrderCard({ order, onClick }: OrderCardProps) {
  return (
    <button
      type="button"
      onClick={() => onClick(order.id)}
      className="w-full rounded-xl border border-border bg-card p-4 text-left transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10">
            <ShoppingBag className="h-4 w-4 text-primary" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-foreground">Pedido #{order.id}</span>
            <span className="text-xs text-muted-foreground">{formatDate(order.creado_en)}</span>
          </div>
        </div>
        <OrderStatusBadge estado={order.estado_codigo} />
      </div>

      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          {order.items_count} {order.items_count === 1 ? 'ítem' : 'ítems'}
        </span>
        <span className="font-semibold text-foreground">{formatCurrency(order.total)}</span>
      </div>
    </button>
  );
}
