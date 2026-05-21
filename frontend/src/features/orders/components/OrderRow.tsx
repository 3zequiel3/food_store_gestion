import { Eye } from 'lucide-react';
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
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface OrderRowProps {
  order: PedidoListItem;
  onViewDetail: (id: number) => void;
}

export function OrderRow({ order, onViewDetail }: OrderRowProps) {
  return (
    <tr className="border-b border-glass-border hover:bg-glass/50 transition-colors group">
      <td className="px-4 py-3">
        <span className="text-sm font-mono font-semibold text-foreground">#{order.id}</span>
      </td>
      <td className="px-4 py-3">
        <OrderStatusBadge estado={order.estado_codigo} />
      </td>
      <td className="px-4 py-3">
        <span className="text-sm font-semibold text-foreground tabular-nums">
          {formatCurrency(order.total)}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {formatDate(order.creado_en)}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className="text-sm text-muted-foreground">
          {order.items_count} {order.items_count === 1 ? 'ítem' : 'ítems'}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <button
          type="button"
          onClick={() => onViewDetail(order.id)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-glass-border bg-glass backdrop-blur-sm px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all duration-150 opacity-60 group-hover:opacity-100"
        >
          <Eye className="h-3.5 w-3.5" />
          Ver detalle
        </button>
      </td>
    </tr>
  );
}
