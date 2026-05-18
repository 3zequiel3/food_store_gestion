import { Check, X } from 'lucide-react';
import type { HistorialEstado } from '../types/orders.types';

const STATE_ORDER = ['PENDIENTE', 'CONFIRMADO', 'EN_PREPARACION', 'TERMINADO', 'ENTREGADO'] as const;
const CANCEL_STATES = ['CANCELADO_ADMIN', 'CANCELADO_CLIENTE', 'CANCELADO'] as const;

const ESTADO_LABELS: Record<string, string> = {
  PENDIENTE: 'Pendiente',
  CONFIRMADO: 'Confirmado',
  EN_PREPARACION: 'En preparación',
  TERMINADO: 'Listo',
  ENTREGADO: 'Entregado',
  CANCELADO: 'Cancelado',
  CANCELADO_ADMIN: 'Cancelado (Admin)',
  CANCELADO_CLIENTE: 'Cancelado (Cliente)',
};

function isCancelState(estado: string): boolean {
  return (CANCEL_STATES as readonly string[]).includes(estado);
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

interface OrderTimelineProps {
  historial: HistorialEstado[];
  currentEstado?: string;
}

export function OrderTimeline({ historial, currentEstado }: OrderTimelineProps) {
  if (historial.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin historial de estados.</p>;
  }

  // Determine the current state from the last history entry or the prop
  const currentState = currentEstado ?? historial[historial.length - 1]?.estado_nuevo_codigo ?? '';
  const isCancelled = isCancelState(currentState);

  // Build the state sequence — cancelled orders show only their terminal state

  // Find the index of the current state in the standard order
  const currentIdx = isCancelled
    ? -1
    : STATE_ORDER.indexOf(currentState as typeof STATE_ORDER[number]);

  return (
    <div className="flex flex-col gap-0">
      {/* State progression bar */}
      <div className="flex items-center gap-1 mb-4">
        {STATE_ORDER.map((state, idx) => {
          const isCompleted = !isCancelled && idx < currentIdx;
          const isCurrent = !isCancelled && idx === currentIdx;
          const isFuture = !isCancelled && idx > currentIdx;

          return (
            <div key={state} className="flex items-center flex-1">
              <div className="flex flex-col items-center flex-1">
                <div
                  className={`
                    h-8 w-8 rounded-full flex items-center justify-center text-xs font-semibold shrink-0
                    ${isCompleted ? 'bg-green-500 text-white' : ''}
                    ${isCurrent ? 'bg-primary text-primary-foreground ring-4 ring-primary/20' : ''}
                    ${isFuture ? 'bg-muted text-muted-foreground' : ''}
                    ${isCancelled && state === currentState ? 'bg-destructive text-white' : ''}
                  `}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" />
                  ) : isCancelled && state === currentState ? (
                    <X className="h-4 w-4" />
                  ) : (
                    idx + 1
                  )}
                </div>
                <span className="text-[10px] mt-1 text-center text-muted-foreground hidden sm:block">
                  {ESTADO_LABELS[state]}
                </span>
              </div>
              {idx < STATE_ORDER.length - 1 && (
                <div
                  className={`
                    flex-1 h-0.5 mx-1
                    ${isCompleted ? 'bg-green-500' : ''}
                    ${isCurrent ? 'bg-primary/50' : ''}
                    ${isFuture ? 'bg-muted' : ''}
                  `}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Cancel state display */}
      {isCancelled && (
        <div className="flex items-center gap-2 rounded-lg bg-destructive/10 border border-destructive/30 px-3 py-2 mb-4">
          <X className="h-4 w-4 text-destructive shrink-0" />
          <span className="text-sm font-medium text-destructive">
            {ESTADO_LABELS[currentState] ?? currentState}
          </span>
        </div>
      )}

      {/* History entries */}
      <ol className="relative flex flex-col gap-0">
        {historial.map((event, idx) => {
          const isLast = idx === historial.length - 1;
          const isCancelEvent = isCancelState(event.estado_nuevo_codigo);

          return (
            <li key={event.id} className="relative flex gap-3 pb-4 last:pb-0">
              <div className="flex flex-col items-center">
                <div
                  className={`
                    mt-0.5 h-3 w-3 rounded-full ring-4 shrink-0 shadow-sm
                    ${isCancelEvent
                      ? 'bg-destructive ring-destructive/20 shadow-destructive/30'
                      : 'bg-primary ring-primary/20 shadow-primary/30'
                    }
                  `}
                />
                {!isLast && (
                  <div
                    className={`
                      mt-1 flex-1 w-px
                      ${isCancelEvent
                        ? 'bg-gradient-to-b from-destructive/50 to-glass-border'
                        : 'bg-gradient-to-b from-primary/50 to-glass-border'
                      }
                    `}
                  />
                )}
              </div>
              <div className="flex flex-col gap-0.5 min-w-0">
                <span
                  className={`text-sm font-medium ${isCancelEvent ? 'text-destructive' : 'text-foreground'}`}
                >
                  {ESTADO_LABELS[event.estado_nuevo_codigo] ?? event.estado_nuevo_codigo}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatDate(event.creado_en)}
                </span>
                {event.motivo && (
                  <span className="text-xs text-muted-foreground italic">{event.motivo}</span>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
