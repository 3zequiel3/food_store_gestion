import type { EstadoCodigo } from '../types/orders.types';

const ESTADO_CONFIG: Record<EstadoCodigo, { label: string; className: string }> = {
  PENDIENTE: {
    label: 'Pendiente',
    className: 'bg-yellow-500/15 text-yellow-400 ring-1 ring-yellow-400/30',
  },
  CONFIRMADO: {
    label: 'Confirmado',
    className: 'bg-blue-500/15 text-blue-400 ring-1 ring-blue-400/30',
  },
  EN_PREPARACION: {
    label: 'En preparación',
    className: 'bg-orange-500/15 text-orange-400 ring-1 ring-orange-400/30',
  },
  EN_CAMINO: {
    label: 'En camino',
    className: 'bg-indigo-500/15 text-indigo-400 ring-1 ring-indigo-400/30',
  },
  ENTREGADO: {
    label: 'Entregado',
    className: 'bg-green-500/15 text-green-400 ring-1 ring-green-400/30',
  },
  CANCELADO: {
    label: 'Cancelado',
    className: 'bg-muted text-muted-foreground ring-1 ring-border',
  },
};

interface OrderStatusBadgeProps {
  estado: EstadoCodigo;
}

export function OrderStatusBadge({ estado }: OrderStatusBadgeProps) {
  const config = ESTADO_CONFIG[estado] ?? {
    label: estado,
    className: 'bg-muted text-muted-foreground',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${config.className}`}
    >
      {config.label}
    </span>
  );
}
