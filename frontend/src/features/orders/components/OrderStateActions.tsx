import { useState } from 'react';
import type { PedidoDetalle, EstadoCodigo } from '../types/orders.types';
import { useTransitionOrderState } from '../hooks/useTransitionOrderState';

interface Transition {
  estado_codigo_destino: string;
  label: string;
  variant: 'primary' | 'danger';
  requiresMotivo: boolean;
}

/**
 * Admin-facing transitions only.
 * PENDIENTE → CONFIRMADO is webhook-only (MercadoPago payment confirmation).
 * CANCELADO_ADMIN is the admin cancellation target (not legacy CANCELADO).
 */
function getTransitions(estado: EstadoCodigo): Transition[] {
  switch (estado) {
    case 'PENDIENTE':
      return [
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
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-muted/30 p-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Acciones
      </p>

      {pendingTransition ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm text-foreground">
            Motivo para{' '}
            <span className="font-medium">cancelar</span>{' '}
            (obligatorio):
          </p>
          <input
            type="text"
            value={motivoInput}
            onChange={(e) => setMotivoInput(e.target.value)}
            placeholder="Escribí el motivo…"
            className="rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleConfirmWithMotivo}
              disabled={mutation.isPending}
              className="flex-1 rounded-lg bg-destructive px-3 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {mutation.isPending ? 'Procesando…' : 'Confirmar'}
            </button>
            <button
              type="button"
              onClick={handleCancelMotivo}
              disabled={mutation.isPending}
              className="flex-1 rounded-lg border border-border px-3 py-2 text-sm font-medium text-foreground hover:bg-accent disabled:opacity-50 transition-colors"
            >
              Cancelar
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
                  ? 'rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity'
                  : 'rounded-lg border border-destructive/50 px-3 py-2 text-sm font-semibold text-destructive hover:bg-destructive/10 disabled:opacity-50 transition-colors'
              }
            >
              {mutation.isPending ? 'Procesando…' : t.label}
            </button>
          ))}
        </div>
      )}

      {mutation.isError && (
        <p className="text-xs text-destructive">
          Error al actualizar el estado. Intentá de nuevo.
        </p>
      )}
    </div>
  );
}
