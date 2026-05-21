import { Loader2 } from 'lucide-react';
import { useCartStore } from '../../cart/stores/cartStore';

interface OrderSummaryPanelProps {
  isLocalPickup: boolean;
  isProcessing: boolean;
  isDisabled: boolean;
  onConfirm: () => void;
}

const SHIPPING_COST = 50;

export function OrderSummaryPanel({
  isLocalPickup,
  isProcessing,
  isDisabled,
  onConfirm,
}: OrderSummaryPanelProps) {
  const items = useCartStore((s) => s.items);

  const subtotal = items.reduce((sum, item) => sum + Number(item.precio) * item.cantidad, 0);
  const shippingCost = isLocalPickup ? 0 : SHIPPING_COST;
  const total = subtotal + shippingCost;

  const fmt = (n: number) =>
    new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', minimumFractionDigits: 2 }).format(n);

  return (
    <div className="rounded-xl bg-glass backdrop-blur-xl border border-glass-border overflow-hidden">

      {/* Header */}
      <div className="px-5 py-4 border-b border-glass-border">
        <h2 className="text-sm font-semibold text-foreground">Resumen del pedido</h2>
      </div>

      {/* Items list */}
      <div className="divide-y divide-glass-border">
        {items.map((item) => (
          <div key={item.producto_id} className="flex items-start justify-between gap-3 px-5 py-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{item.nombre}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {fmt(Number(item.precio))} × {item.cantidad}
              </p>
            </div>
            <p className="text-sm font-semibold text-foreground shrink-0">
              {fmt(Number(item.precio) * item.cantidad)}
            </p>
          </div>
        ))}
      </div>

      {/* Totals */}
      <div className="px-5 py-4 space-y-2 border-t border-glass-border bg-background/20">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">
            Productos ({items.reduce((s, i) => s + i.cantidad, 0)})
          </span>
          <span className="text-foreground">{fmt(subtotal)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Envío</span>
          <span className={isLocalPickup ? 'text-primary font-medium' : 'text-foreground'}>
            {isLocalPickup ? 'Retiro en local' : fmt(shippingCost)}
          </span>
        </div>
        <div className="flex justify-between items-baseline pt-3 border-t border-glass-border">
          <span className="font-semibold text-foreground">Total</span>
          <span className="text-xl font-bold text-foreground">{fmt(total)}</span>
        </div>
      </div>

      {/* Confirm button */}
      <div className="px-5 pb-5 pt-3">
        <button
          type="button"
          onClick={onConfirm}
          disabled={isDisabled}
          className="w-full flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3.5 text-sm font-bold text-primary-foreground
            hover:bg-primary/90 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed
            transition-all duration-150 shadow-md shadow-primary/20"
        >
          {isProcessing ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Procesando…
            </>
          ) : (
            `Confirmar pedido · ${fmt(total)}`
          )}
        </button>
        <p className="mt-2.5 text-xs text-center text-muted-foreground">
          Al confirmar aceptás los términos del servicio
        </p>
      </div>
    </div>
  );
}
