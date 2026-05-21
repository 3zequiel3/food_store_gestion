import { useState } from 'react';
import { ChevronRight, AlertTriangle, Zap } from 'lucide-react';
import type { PedidoDetalle, EstadoCodigo } from '../types/orders.types';
import { useTransitionOrderState } from '../hooks/useTransitionOrderState';

interface Transition {
  estado_codigo_destino: string;
  label: string;
  variant: 'primary' | 'danger';
  requiresMotivo: boolean;
}

function getTransitions(estado: EstadoCodigo): Transition[] {
  switch (estado) {
    case 'PENDIENTE':
      return [
        { estado_codigo_destino: 'CONFIRMADO', label: 'Confirmar pedido', variant: 'primary', requiresMotivo: false },
        { estado_codigo_destino: 'CANCELADO_ADMIN', label: 'Rechazar', variant: 'danger', requiresMotivo: true },
      ];
    case 'CONFIRMADO':
      return [
        { estado_codigo_destino: 'EN_PREPARACION', label: 'Iniciar preparación', variant: 'primary', requiresMotivo: false },
        { estado_codigo_destino: 'CANCELADO_ADMIN', label: 'Cancelar', variant: 'danger', requiresMotivo: true },
      ];
    case 'EN_PREPARACION':
      return [
        { estado_codigo_destino: 'TERMINADO', label: 'Marcar listo', variant: 'primary', requiresMotivo: false },
        { estado_codigo_destino: 'CANCELADO_ADMIN', label: 'Cancelar', variant: 'danger', requiresMotivo: true },
      ];
    case 'TERMINADO':
      return [
        { estado_codigo_destino: 'ENTREGADO', label: 'Marcar entregado', variant: 'primary', requiresMotivo: false },
      ];
    default:
      return [];
  }
}

interface OrderStateActionsProps {
  order: PedidoDetalle;
}

export function OrderStateActions({ order }: OrderStateActionsProps) {
  const transitions = getTransitions(order.estado_codigo);
  const mutation = useTransitionOrderState();
  const [motivoInput, setMotivoInput] = useState('');
  const [pendingTransition, setPendingTransition] = useState<Transition | null>(null);

  if (transitions.length === 0) return null;

  function handleClick(transition: Transition) {
    if (transition.requiresMotivo) {
      setPendingTransition(transition);
      setMotivoInput('');
    } else {
      mutation.mutate({ id: order.id, estado_codigo_destino: transition.estado_codigo_destino });
    }
  }

  function handleConfirmWithMotivo() {
    if (!pendingTransition) return;
    mutation.mutate({
      id: order.id,
      estado_codigo_destino: pendingTransition.estado_codigo_destino,
      motivo: motivoInput.trim() || undefined,
    });
    setPendingTransition(null);
    setMotivoInput('');
  }

  function handleCancelMotivo() {
    setPendingTransition(null);
    setMotivoInput('');
  }

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 overflow-hidden">
      {/* Panel header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-primary/10">
        <Zap className="h-3.5 w-3.5 text-primary" />
        <p className="text-xs font-semibold uppercase tracking-wider text-primary/80">
          Acciones del pedido
        </p>
        <div className="ml-auto h-2 w-2 rounded-full bg-primary animate-pulse" />
      </div>

      <div className="p-4">
        {pendingTransition ? (
          <div className="flex flex-col gap-3">
            <div className="flex items-start gap-2.5 rounded-xl bg-destructive/10 border border-destructive/20 px-3.5 py-3">
              <AlertTriangle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
              <p className="text-sm text-destructive">
                Ingresá el motivo para{' '}
                <span className="font-semibold">{pendingTransition.label.toLowerCase()}</span>:
              </p>
            </div>
            <input
              type="text"
              value={motivoInput}
              onChange={(e) => setMotivoInput(e.target.value)}
              placeholder="Motivo de cancelación…"
              className="rounded-xl border border-glass-border bg-background/50 px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-destructive/40 transition-all w-full"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleConfirmWithMotivo}
                disabled={mutation.isPending}
                className="flex-1 rounded-xl bg-destructive px-4 py-2.5 text-sm font-semibold text-white hover:bg-destructive/90 disabled:opacity-50 transition-all"
              >
                {mutation.isPending ? 'Procesando…' : 'Confirmar'}
              </button>
              <button
                type="button"
                onClick={handleCancelMotivo}
                disabled={mutation.isPending}
                className="rounded-xl border border-glass-border bg-background/30 px-4 py-2.5 text-sm font-medium text-foreground hover:bg-glass-hover disabled:opacity-50 transition-colors"
              >
                Volver
              </button>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {transitions.map((t) => (
              <button
                key={t.estado_codigo_destino}
                type="button"
                onClick={() => handleClick(t)}
                disabled={mutation.isPending}
                className={
                  t.variant === 'primary'
                    ? 'flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-all shadow-sm shadow-primary/20'
                    : 'flex items-center gap-1.5 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-2.5 text-sm font-semibold text-destructive hover:bg-destructive/10 disabled:opacity-50 transition-colors'
                }
              >
                {mutation.isPending ? 'Procesando…' : t.label}
                {t.variant === 'primary' && !mutation.isPending && (
                  <ChevronRight className="h-3.5 w-3.5" />
                )}
              </button>
            ))}
          </div>
        )}

        {mutation.isError && (
          <p className="mt-3 text-xs text-destructive">
            Error al actualizar el estado. Intentá de nuevo.
          </p>
        )}
      </div>
    </div>
  );
}
