import { useEffect } from 'react';
import { X, AlertCircle } from 'lucide-react';
import type { CocinaPedidoItem, IngredienteInfo } from '../types/cocina.types';

interface KitchenOrderDetailProps {
  orderId: number;
  items: CocinaPedidoItem[];
  notas: string | null;
  onClose: () => void;
  /** States in which the cook can mark an ingredient unavailable (optional). */
  orderEstado?: string;
  /** Called when the cook marks an ingredient as unavailable. */
  onIngredientUnavailable?: (ingredientId: number) => void;
}

/**
 * Modal de detalle de pedido para la cocina.
 *
 * P1.4 (D10): muestra la lista completa de ingredientes por nombre.
 * Las exclusiones se muestran por nombre (exclusiones_nombres del backend),
 * no como "Ingrediente #N".
 *
 * P0.1 (cook): si el pedido está en CONFIRMADO o EN_PREPARACION,
 * cada ingrediente muestra un botón "Marcar no disponible".
 */
export function KitchenOrderDetail({
  orderId,
  items,
  notas,
  onClose,
  orderEstado,
  onIngredientUnavailable,
}: KitchenOrderDetailProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const canReportUnavailable =
    onIngredientUnavailable !== undefined &&
    (orderEstado === 'CONFIRMADO' || orderEstado === 'EN_PREPARACION');

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-lg w-full max-w-lg p-6 shadow-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">
            Detalle del pedido #{orderId}
          </h2>
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
            <IngredientItemBlock
              key={`${item.producto_id}-${idx}`}
              item={item}
              orderId={orderId}
              canReportUnavailable={canReportUnavailable}
              onIngredientUnavailable={onIngredientUnavailable}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: one product block with its full ingredient list
// ---------------------------------------------------------------------------

interface IngredientItemBlockProps {
  item: CocinaPedidoItem;
  orderId: number;
  canReportUnavailable: boolean;
  onIngredientUnavailable?: (ingredientId: number) => void;
}

function IngredientItemBlock({
  item,
  orderId: _orderId,
  canReportUnavailable,
  onIngredientUnavailable,
}: IngredientItemBlockProps) {
  const exclusionSet = new Set(item.exclusiones_nombres);

  return (
    <div className="px-3 py-2 rounded-lg border border-border">
      {/* Product header */}
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-foreground">
          {item.nombre_snapshot}
        </p>
        <span className="text-xs font-mono bg-secondary text-secondary-foreground px-2 py-0.5 rounded">
          × {item.cantidad}
        </span>
      </div>

      {/* Exclusion summary by name (D10) */}
      {item.exclusiones_nombres.length > 0 && (
        <div className="mb-2">
          <p className="text-xs text-destructive font-medium">
            Sin: {item.exclusiones_nombres.join(', ')}
          </p>
        </div>
      )}

      {/* Full ingredient list (D10 — names, not raw IDs) */}
      {item.ingredientes.length > 0 && (
        <div className="mt-1 space-y-1">
          {item.ingredientes.map((ing) => (
            <IngredienteRow
              key={ing.id}
              ingrediente={ing}
              isExcluded={exclusionSet.has(ing.nombre)}
              canReportUnavailable={canReportUnavailable}
              onReport={onIngredientUnavailable}
            />
          ))}
        </div>
      )}

      {/* Item-level notes */}
      {item.notas && (
        <p className="mt-2 text-xs text-muted-foreground italic">{item.notas}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: single ingredient row with optional unavailable trigger
// ---------------------------------------------------------------------------

interface IngredienteRowProps {
  ingrediente: IngredienteInfo;
  isExcluded: boolean;
  canReportUnavailable: boolean;
  onReport?: (ingredientId: number) => void;
}

function IngredienteRow({
  ingrediente,
  isExcluded,
  canReportUnavailable,
  onReport,
}: IngredienteRowProps) {
  return (
    <div className="flex items-center justify-between gap-2 text-xs">
      <span
        className={
          isExcluded
            ? 'line-through text-muted-foreground/60'
            : 'text-foreground/80'
        }
      >
        {ingrediente.nombre}
        {ingrediente.es_removible && !isExcluded && (
          <span className="ml-1 text-muted-foreground">(removible)</span>
        )}
      </span>

      {canReportUnavailable && !isExcluded && onReport && (
        <button
          type="button"
          onClick={() => onReport(ingrediente.id)}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-destructive hover:bg-destructive/10 transition-colors whitespace-nowrap"
          title={`Marcar "${ingrediente.nombre}" como no disponible`}
          aria-label={`Marcar ${ingrediente.nombre} no disponible`}
        >
          <AlertCircle className="h-3 w-3" />
          <span>Marcar no disponible</span>
        </button>
      )}
    </div>
  );
}
