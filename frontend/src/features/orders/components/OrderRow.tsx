import { Eye } from 'lucide-react';
import type { PedidoListItem } from '../types/orders.types';
import { OrderStatusBadge } from './OrderStatusBadge';

function formatCurrency(value: string): string {
  return `$${parseFloat(value).toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
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
    <tr className="border-b border-glass-border hover:bg-glass-hover transition-colors">
      <td className="px-4 py-3 text-sm font-medium text-foreground">#{order.id}</td>
      <td className="px-4 py-3">
        <OrderStatusBadge estado={order.estado_codigo} />
      </td>
      <td className="px-4 py-3 text-sm text-foreground">{formatCurrency(order.total)}</td>
      <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
        {formatDate(order.creado_en)}
      </td>
      <td className="px-4 py-3 text-sm text-muted-foreground text-right">
        {order.items_count} {order.items_count === 1 ? 'ítem' : 'ítems'}
      </td>
      <td className="px-4 py-3 text-right">
        <button
          type="button"
          onClick={() => onViewDetail(order.id)}
          className="inline-flex items-center gap-1.5 rounded-md border border-glass-border bg-glass backdrop-blur-sm px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-glass-hover transition-colors"
        >
          <Eye className="h-3.5 w-3.5" />
          Ver detalle
        </button>
      </td>
    </tr>
  );
}
