import { Check, X } from 'lucide-react';
import type { HistorialEstado } from '../types/orders.types';

const STATE_ORDER = ['PENDIENTE', 'CONFIRMADO', 'EN_PREPARACION', 'TERMINADO', 'ENTREGADO'] as const;
const CANCEL_STATES = ['CANCELADO_ADMIN', 'CANCELADO_CLIENTE', 'CANCELADO'] as const;

export const ESTADO_LABELS: Record<string, string> = {
  PENDIENTE: 'Pendiente',
  CONFIRMADO: 'Confirmado',
  EN_PREPARACION: 'Preparando',
  TERMINADO: 'Listo',
  ENTREGADO: 'Entregado',
  CANCELADO: 'Cancelado',
  CANCELADO_ADMIN: 'Cancelado',
  CANCELADO_CLIENTE: 'Cancelado',
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
  /** Pass true to hide the horizontal progress stepper (when rendered separately) */
  hideProgressBar?: boolean;
}

export function OrderTimeline({ historial, currentEstado, hideProgressBar = false }: OrderTimelineProps) {
  if (historial.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin historial de estados.</p>;
  }

  const currentState = currentEstado ?? historial[historial.length - 1]?.estado_nuevo_codigo ?? '';
  const isCancelled = isCancelState(currentState);
  const currentIdx = isCancelled
    ? -1
    : STATE_ORDER.indexOf(currentState as (typeof STATE_ORDER)[number]);

  return (
    <div className="flex flex-col gap-4">
      {/* Horizontal progress bar (optional) */}
      {!hideProgressBar && (
        <OrderProgressBar currentEstado={currentState} />
      )}

      {/* Cancelled state badge */}
      {isCancelled && (
        <div className="flex items-center gap-2 rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2">
          <X className="h-3.5 w-3.5 text-destructive shrink-0" />
          <span className="text-sm font-medium text-destructive">
            {ESTADO_LABELS[currentState] ?? currentState}
          </span>
        </div>
      )}

      {/* History entries */}
      <ol className="flex flex-col gap-0">
        {historial.map((event, idx) => {
          const isLast = idx === historial.length - 1;
          const isCancelEvent = isCancelState(event.estado_nuevo_codigo);

          return (
            <li key={event.id} className="relative flex gap-3 pb-4 last:pb-0">
              <div className="flex flex-col items-center">
                <div
                  className={[
                    'mt-0.5 h-2.5 w-2.5 rounded-full ring-[3px] shrink-0',
                    isCancelEvent
                      ? 'bg-destructive ring-destructive/20'
                      : 'bg-primary ring-primary/20',
                  ].join(' ')}
                />
                {!isLast && (
                  <div
                    className={[
                      'mt-1.5 flex-1 w-px min-h-[20px]',
                      isCancelEvent
                        ? 'bg-gradient-to-b from-destructive/30 to-transparent'
                        : 'bg-gradient-to-b from-primary/30 to-transparent',
                    ].join(' ')}
                  />
                )}
              </div>
              <div className="flex flex-col gap-0.5 min-w-0 pb-0.5">
                <span
                  className={[
                    'text-sm font-medium leading-tight',
                    isCancelEvent ? 'text-destructive' : 'text-foreground',
                  ].join(' ')}
                >
                  {ESTADO_LABELS[event.estado_nuevo_codigo] ?? event.estado_nuevo_codigo}
                </span>
                <span className="text-xs text-muted-foreground">{formatDate(event.creado_en)}</span>
                {event.motivo && (
                  <span className="text-xs text-muted-foreground italic mt-0.5">
                    "{event.motivo}"
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

interface OrderProgressBarProps {
  currentEstado: string;
}

export function OrderProgressBar({ currentEstado }: OrderProgressBarProps) {
  const isCancelled = isCancelState(currentEstado);
  const currentIdx = isCancelled
    ? -1
    : STATE_ORDER.indexOf(currentEstado as (typeof STATE_ORDER)[number]);

  return (
    <div className="flex items-start gap-0">
      {STATE_ORDER.map((state, idx) => {
        const isCompleted = !isCancelled && idx < currentIdx;
        const isCurrent = !isCancelled && idx === currentIdx;

        return (
          <div key={state} className="flex items-start flex-1">
            <div className="flex flex-col items-center flex-1">
              <div
                className={[
                  'h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-all',
                  isCompleted ? 'bg-green-500 text-white' : '',
                  isCurrent ? 'bg-primary text-primary-foreground ring-4 ring-primary/20' : '',
                  !isCompleted && !isCurrent ? 'bg-muted/50 border border-glass-border text-muted-foreground' : '',
                ].join(' ')}
              >
                {isCompleted ? <Check className="h-3.5 w-3.5" /> : idx + 1}
              </div>
              <span className="text-[9px] mt-1.5 text-center leading-tight text-muted-foreground w-full px-0.5">
                {ESTADO_LABELS[state]}
              </span>
            </div>
            {idx < STATE_ORDER.length - 1 && (
              <div
                className={[
                  'flex-1 h-0.5 mt-3.5 mx-0.5',
                  isCompleted ? 'bg-green-500' : 'bg-glass-border',
                ].join(' ')}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
