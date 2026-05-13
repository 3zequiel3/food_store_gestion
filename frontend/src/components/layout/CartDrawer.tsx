import { useEffect, useRef } from 'react';
import { X, ShoppingCart, Trash2, Minus, Plus } from 'lucide-react';
import { useCartStore } from '../../features/cart/stores/cartStore';

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Drawer lateral del carrito (right side sheet).
 * Reusable mobile + desktop (7.B.9).
 * El checkout es placeholder por ahora — llega en Sprint 9 (#26).
 */
export function CartDrawer({ isOpen, onClose }: CartDrawerProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const items = useCartStore((s) => s.items);
  const removeItem = useCartStore((s) => s.removeItem);
  const updateQuantity = useCartStore((s) => s.updateQuantity);
  const getTotalPrice = useCartStore((s) => s.getTotalPrice);
  const clearCart = useCartStore((s) => s.clearCart);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [isOpen]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) {
      onClose();
    }
  };

  const total = getTotalPrice();

  return (
    <dialog
      ref={dialogRef}
      onClick={handleBackdropClick}
      onClose={onClose}
      className="
        fixed right-0 inset-y-0 m-0 h-full w-full sm:max-w-md
        bg-card border-l border-border p-0
        backdrop:bg-black/50 backdrop:backdrop-blur-sm
        open:animate-in open:slide-in-from-right-4
      "
      aria-label="Carrito de compras"
    >
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-4">
          <div className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-primary" />
            <h2 className="font-semibold text-foreground">Carrito</h2>
            {items.length > 0 && (
              <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-bold text-primary-foreground">
                {items.reduce((sum, i) => sum + i.cantidad, 0)}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
            aria-label="Cerrar carrito"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Items list */}
        <div className="flex-1 overflow-y-auto">
          {items.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
              <ShoppingCart className="h-12 w-12 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                Tu carrito está vacío.
                <br />
                ¡Agregá productos del catálogo!
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {items.map((item) => (
                <li
                  key={item.producto_id}
                  className="flex items-center gap-3 px-4 py-3"
                >
                  {/* Imagen o placeholder */}
                  <div className="h-12 w-12 flex-shrink-0 rounded-lg bg-muted overflow-hidden">
                    {item.imagen_url ? (
                      <img
                        src={item.imagen_url}
                        alt={item.nombre}
                        className="h-full w-full object-cover"
                      />
                    ) : null}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">
                      {item.nombre}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      ${Number(item.precio).toFixed(2)} c/u
                    </p>
                    {item.personalizacion && (
                      <p className="truncate text-xs text-muted-foreground italic">
                        {item.personalizacion}
                      </p>
                    )}
                  </div>

                  {/* Controles cantidad + subtotal + remove */}
                  <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                    <span className="text-sm font-semibold text-foreground">
                      ${(Number(item.precio) * item.cantidad).toFixed(2)}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => updateQuantity(item.producto_id, item.cantidad - 1)}
                        className="flex h-6 w-6 items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-accent transition-colors"
                        aria-label={`Reducir cantidad de ${item.nombre}`}
                      >
                        <Minus className="h-3 w-3" />
                      </button>
                      <span className="w-6 text-center text-sm font-medium text-foreground">
                        {item.cantidad}
                      </span>
                      <button
                        type="button"
                        onClick={() => updateQuantity(item.producto_id, item.cantidad + 1)}
                        className="flex h-6 w-6 items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-accent transition-colors"
                        aria-label={`Aumentar cantidad de ${item.nombre}`}
                      >
                        <Plus className="h-3 w-3" />
                      </button>
                      <button
                        type="button"
                        onClick={() => removeItem(item.producto_id)}
                        className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors ml-1"
                        aria-label={`Eliminar ${item.nombre}`}
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer — solo cuando hay items */}
        {items.length > 0 && (
          <div className="border-t border-border p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Total</span>
              <span className="text-lg font-bold text-foreground">
                ${total.toFixed(2)}
              </span>
            </div>
            <button
              type="button"
              onClick={clearCart}
              className="text-xs text-muted-foreground hover:text-destructive transition-colors text-center"
            >
              Vaciar carrito
            </button>
            <button
              type="button"
              disabled
              title="Checkout disponible en Sprint 9"
              className="h-11 w-full rounded-lg bg-primary text-primary-foreground text-sm font-semibold opacity-60 cursor-not-allowed"
            >
              Ir al checkout
            </button>
          </div>
        )}
      </div>
    </dialog>
  );
}
