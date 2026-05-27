import { useState } from 'react';
import { FileText, Play, CheckCircle, Lock } from 'lucide-react';
import type { CocinaPedidoResponse } from '../types/cocina.types';
import { useUrgencyTimer } from '../hooks/useUrgencyTimer';
import { UrgencyBadge } from './UrgencyBadge';
import { KitchenOrderDetail } from './KitchenOrderDetail';

/**
 * Collect the names of non-excluded ingredients that the kitchen marked as
 * unavailable. Excluded ingredients (via personalizacion) don't block the
 * pedido because they're skipped in preparation anyway.
 */
function collectBlockedIngredients(order: CocinaPedidoResponse): string[] {
  const blocked = new Set<string>();
  for (const item of order.items) {
    const excluded = new Set(item.exclusiones_nombres);
    for (const ing of item.ingredientes) {
      if (!ing.activo && !excluded.has(ing.nombre)) {
        blocked.add(ing.nombre);
      }
    }
  }
  return [...blocked];
}

interface KitchenOrderCardProps {
  order: CocinaPedidoResponse;
  onTransition: (orderId: number, targetState: string) => void;
  isTransitioning: boolean;
  /** Called when the cook marks an ingredient as unavailable (P0.1 cook trigger). */
  onIngredientUnavailable?: (ingredientId: number) => void;
}

/**
 * Tarjeta de pedido para el tablero Kanban de cocina.
 *
 * Muestra:
 * - Nº de pedido (prominente)
 * - Lista de ítems: nombre_snapshot × cantidad
 * - Exclusiones de personalización (en rojo/naranja)
 * - Notas del pedido (en itálica)
 * - Timer de urgencia (recalculado cada 15s)
 * - Botón de acción según la columna:
 *   - CONFIRMADO → "Iniciar preparación" (→ EN_PREPARACION)
 *   - EN_PREPARACION → "Terminado" (→ TERMINADO)
 * - "Ver detalle" que abre KitchenOrderDetail
 */
export function KitchenOrderCard({
  order,
  onTransition,
  isTransitioning,
  onIngredientUnavailable,
}: KitchenOrderCardProps) {
  const [showDetail, setShowDetail] = useState(false);
  const { elapsedMinutes, level } = useUrgencyTimer(order.cocina_entry_at);

  const isConfirmado = order.estado === 'CONFIRMADO';

  // Pedido is blocked from advancing when at least one required ingredient
  // is reported unavailable (Ingrediente.activo = false on the backend).
  // The FSM guard on the server rejects the transition with a 422; we mirror
  // that here so the cook can't even attempt the click and sees the reason.
  const blockedIngredients = collectBlockedIngredients(order);
  const isBlocked = blockedIngredients.length > 0;

  return (
    <>
      <div
        className={`bg-card border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow ${
          isBlocked
            ? 'border-destructive/40 ring-1 ring-destructive/30 bg-destructive/[0.03]'
            : 'border-border'
        }`}
      >
        {/* Header: order number + urgency */}
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-bold text-foreground">
            Pedido #{order.id}
          </h3>
          <UrgencyBadge elapsedMinutes={elapsedMinutes} level={level} />
        </div>

        {/* Blocked banner: shown when one or more ingredients are unavailable */}
        {isBlocked && (
          <div className="mb-3 flex items-start gap-2 px-3 py-2 rounded-lg bg-destructive/10 border border-destructive/30 text-xs">
            <Lock className="h-3.5 w-3.5 text-destructive shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-destructive">
                Bloqueado — faltante de ingredientes
              </p>
              <p className="text-destructive/80 mt-0.5">
                {blockedIngredients.join(', ')}
              </p>
              <p className="text-destructive/60 mt-1">
                El admin tiene que resolver el faltante antes de avanzar el pedido.
              </p>
            </div>
          </div>
        )}

        {/* Items list */}
        <ul className="space-y-1.5 mb-3">
          {order.items.map((item, idx) => {
            // D10: prefer resolved names; fall back gracefully when absent.
            const exclusionLabel =
              item.exclusiones_nombres && item.exclusiones_nombres.length > 0
                ? item.exclusiones_nombres.join(', ')
                : item.personalizacion && item.personalizacion.length > 0
                  ? item.personalizacion.join(', ')
                  : null;

            return (
              <li key={`${item.producto_id}-${idx}`} className="text-sm text-foreground">
                <span className="font-medium">{item.nombre_snapshot}</span>
                <span className="text-muted-foreground"> × {item.cantidad}</span>
                {exclusionLabel && (
                  <span className="ml-1 text-xs text-destructive">
                    (sin: {exclusionLabel})
                  </span>
                )}
              </li>
            );
          })}
        </ul>

        {/* Order-level notes */}
        {order.notas && (
          <p className="text-xs text-muted-foreground italic mb-3 border-l-2 border-warning/50 pl-2">
            {order.notas}
          </p>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2 border-t border-border">
          {isConfirmado ? (
            <button
              onClick={() => onTransition(order.id, 'EN_PREPARACION')}
              disabled={isTransitioning || isBlocked}
              title={isBlocked ? 'Esperando que el admin resuelva el faltante' : undefined}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isBlocked ? <Lock className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
              {isBlocked ? 'Bloqueado' : 'Iniciar preparación'}
            </button>
          ) : (
            <button
              onClick={() => onTransition(order.id, 'TERMINADO')}
              disabled={isTransitioning || isBlocked}
              title={isBlocked ? 'Esperando que el admin resuelva el faltante' : undefined}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm bg-success text-success-foreground rounded-lg hover:bg-success/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isBlocked ? <Lock className="h-3.5 w-3.5" /> : <CheckCircle className="h-3.5 w-3.5" />}
              {isBlocked ? 'Bloqueado' : 'Terminado'}
            </button>
          )}

          <button
            onClick={() => setShowDetail(true)}
            className="p-2 rounded-lg border border-border hover:bg-accent transition-colors text-muted-foreground"
            title="Ver detalle"
          >
            <FileText className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Detail modal */}
      {showDetail && (
        <KitchenOrderDetail
          orderId={order.id}
          items={order.items}
          notas={order.notas}
          onClose={() => setShowDetail(false)}
          orderEstado={order.estado}
          onIngredientUnavailable={onIngredientUnavailable}
        />
      )}
    </>
  );
}
