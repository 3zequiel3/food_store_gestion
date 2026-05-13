import type { HistorialEstado } from '../types/orders.types';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const ESTADO_LABELS: Record<string, string> = {
  PENDIENTE: 'Pendiente',
  CONFIRMADO: 'Confirmado',
  EN_PREPARACION: 'En preparación',
  EN_CAMINO: 'En camino',
  ENTREGADO: 'Entregado',
  CANCELADO: 'Cancelado',
};

interface OrderTimelineProps {
  historial: HistorialEstado[];
}

export function OrderTimeline({ historial }: OrderTimelineProps) {
  if (historial.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin historial de estados.</p>;
  }

  return (
    <ol className="relative flex flex-col gap-0">
      {historial.map((event, idx) => {
        const isLast = idx === historial.length - 1;
        return (
          <li key={event.id} className="relative flex gap-3 pb-4 last:pb-0">
            <div className="flex flex-col items-center">
              <div className="mt-0.5 h-2.5 w-2.5 rounded-full bg-primary ring-2 ring-primary/30 shrink-0" />
              {!isLast && <div className="mt-1 flex-1 w-px bg-border" />}
            </div>
            <div className="flex flex-col gap-0.5 min-w-0">
              <span className="text-sm font-medium text-foreground">
                {ESTADO_LABELS[event.estado_nuevo_codigo] ?? event.estado_nuevo_codigo}
              </span>
              <span className="text-xs text-muted-foreground">{formatDate(event.creado_en)}</span>
              {event.motivo && (
                <span className="text-xs text-muted-foreground italic">{event.motivo}</span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
