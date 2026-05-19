import { ShoppingBag, CreditCard, Banknote } from 'lucide-react';
import type { PedidoListItem } from '../types/orders.types';
import { OrderStatusBadge } from './OrderStatusBadge';

function formatCurrency(value: string): string {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
  }).format(parseFloat(value));
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
  const isTarjeta = order.forma_pago_codigo === 'TARJETA';

  return (
    <button
      type="button"
      onClick={() => onClick(order.id)}
      className="w-full rounded-xl bg-glass backdrop-blur-xl border border-glass-border p-4 text-left transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 hover:border-primary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/10">
            <ShoppingBag className="h-4 w-4 text-primary" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-semibold text-foreground">Pedido #{order.id}</span>
            <span className="text-xs text-muted-foreground">{formatDate(order.creado_en)}</span>
          </div>
        </div>
        <OrderStatusBadge estado={order.estado_codigo} />
      </div>

      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {isTarjeta ? (
            <CreditCard className="h-3 w-3" />
          ) : (
            <Banknote className="h-3 w-3" />
          )}
          <span>{isTarjeta ? 'Tarjeta' : 'Efectivo'}</span>
          <span className="text-glass-border">·</span>
          <span>
            {order.items_count} {order.items_count === 1 ? 'ítem' : 'ítems'}
          </span>
        </div>
        <span className="text-sm font-bold text-foreground tabular-nums">
          {formatCurrency(order.total)}
        </span>
      </div>
    </button>
  );
}
