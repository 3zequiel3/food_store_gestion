import { useEffect } from 'react';
import { X } from 'lucide-react';
import type { CocinaPedidoItem } from '../types/cocina.types';

interface KitchenOrderDetailProps {
  orderId: number;
  items: CocinaPedidoItem[];
  notas: string | null;
  onClose: () => void;
}

/**
 * Modal de detalle de pedido para la cocina.
 *
 * Muestra cada producto con sus ingredientes/exclusiones (personalización)
 * y las notas del pedido.
 */
export function KitchenOrderDetail({ items, notas, onClose }: KitchenOrderDetailProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-lg w-full max-w-lg p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">Detalle del pedido</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-accent text-muted-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {notas && (
          <div className="mb-4 px-3 py-2 rounded-lg bg-muted/50 border border-border">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
              Notas
            </p>
            <p className="text-sm text-foreground italic">{notas}</p>
          </div>
        )}

        <div className="space-y-3">
          {items.map((item, idx) => (
            <div
              key={`${item.producto_id}-${idx}`}
              className="px-3 py-2 rounded-lg border border-border"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-foreground">
                  {item.nombre_snapshot}
                </p>
                <span className="text-xs font-mono bg-secondary text-secondary-foreground px-2 py-0.5 rounded">
                  × {item.cantidad}
                </span>
              </div>

              {item.personalizacion && item.personalizacion.length > 0 && (
                <div className="mt-1">
                  <p className="text-xs text-destructive">
                    Sin: {item.personalizacion.map((id) => `Ingrediente #${id}`).join(', ')}
                  </p>
                </div>
              )}

              {item.notas && (
                <p className="mt-1 text-xs text-muted-foreground italic">
                  {item.notas}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
