import { Badge } from '../../../components/ui/Badge';
import type { EstadoCodigo } from '../types/orders.types';

const ESTADO_CONFIG: Record<EstadoCodigo, { label: string; variant: 'success' | 'warning' | 'info' | 'destructive' | 'neutral' | 'primary' }> = {
  PENDIENTE: { label: 'Pendiente', variant: 'warning' },
  CONFIRMADO: { label: 'Confirmado', variant: 'info' },
  EN_PREPARACION: { label: 'En preparación', variant: 'primary' },
  TERMINADO: { label: 'Listo para retirar/entregar', variant: 'info' },
  ENTREGADO: { label: 'Entregado', variant: 'success' },
  CANCELADO: { label: 'Cancelado', variant: 'neutral' },
};

interface OrderStatusBadgeProps {
  estado: EstadoCodigo;
}

export function OrderStatusBadge({ estado }: OrderStatusBadgeProps) {
  const config = ESTADO_CONFIG[estado] ?? { label: estado, variant: 'neutral' as const };

  return (
    <Badge variant={config.variant}>
      {config.label}
    </Badge>
  );
}
