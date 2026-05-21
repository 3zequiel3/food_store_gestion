import { useState } from 'react';
import { FileText, Play, CheckCircle } from 'lucide-react';
import type { CocinaPedidoResponse, CocinaEstado } from '../types/cocina.types';
import { useUrgencyTimer } from '../hooks/useUrgencyTimer';
import { UrgencyBadge } from './UrgencyBadge';
import { KitchenOrderDetail } from './KitchenOrderDetail';

interface KitchenOrderCardProps {
  order: CocinaPedidoResponse;
  onTransition: (orderId: number, targetState: string) => void;
  isTransitioning: boolean;
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
}: KitchenOrderCardProps) {
  const [showDetail, setShowDetail] = useState(false);
  const { elapsedMinutes, level } = useUrgencyTimer(order.cocina_entry_at);

  const isConfirmado = order.estado === 'CONFIRMADO';

  return (
    <>
      <div className="bg-card border border-border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
        {/* Header: order number + urgency */}
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-bold text-foreground">
            Pedido #{order.id}
          </h3>
          <UrgencyBadge elapsedMinutes={elapsedMinutes} level={level} />
        </div>

        {/* Items list */}
        <ul className="space-y-1.5 mb-3">
          {order.items.map((item, idx) => (
            <li key={`${item.producto_id}-${idx}`} className="text-sm text-foreground">
              <span className="font-medium">{item.nombre_snapshot}</span>
              <span className="text-muted-foreground"> × {item.cantidad}</span>
              {item.personalizacion && item.personalizacion.length > 0 && (
                <span className="ml-1 text-xs text-destructive">
                  (sin ingredientes {item.personalizacion.join(', ')})
                </span>
              )}
            </li>
          ))}
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
              disabled={isTransitioning}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5" />
              Iniciar preparación
            </button>
          ) : (
            <button
              onClick={() => onTransition(order.id, 'TERMINADO')}
              disabled={isTransitioning}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm bg-success text-success-foreground rounded-lg hover:bg-success/90 transition-colors disabled:opacity-50"
            >
              <CheckCircle className="h-3.5 w-3.5" />
              Terminado
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
        />
      )}
    </>
  );
}
