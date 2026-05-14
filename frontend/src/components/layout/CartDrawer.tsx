import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ShoppingCart, Trash2, Minus, Plus } from 'lucide-react';
import { useCartStore } from '../../features/cart/stores/cartStore';
import { useValidateCart } from '../../features/checkout/hooks/useValidateCart';
import { CartValidationModal } from '../../features/checkout/components/CartValidationModal';
import { Button } from '../ui/Button';
import type { ValidationResult } from '../../features/checkout/types/validation.types';
import { ProductImage } from '../../features/products/components/ProductImage';

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CartDrawer({ isOpen, onClose }: CartDrawerProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const navigate = useNavigate();
  const items = useCartStore((s) => s.items);
  const removeItem = useCartStore((s) => s.removeItem);
  const updateQuantity = useCartStore((s) => s.updateQuantity);
  const getTotalPrice = useCartStore((s) => s.getTotalPrice);
  const clearCart = useCartStore((s) => s.clearCart);

  const { mutate: validate, isPending } = useValidateCart();
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen) dialog.showModal();
    else dialog.close();
  }, [isOpen]);

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) onClose();
  };

  function handleCheckout() {
    validate(undefined, {
      onSuccess(result) {
        const hasIssues = result.stockIssues.length > 0 || result.priceChanges.length > 0;
        if (!hasIssues) {
          onClose();
          navigate('/cliente/checkout', { state: { validated: true } });
        } else {
          setValidationResult(result);
        }
      },
    });
  }

  const total = getTotalPrice();
  const itemCount = items.reduce((sum, i) => sum + i.cantidad, 0);

  return (
    <>
      <dialog
        ref={dialogRef}
        onClick={handleBackdropClick}
        onClose={onClose}
        className="
          fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 p-0
          w-full max-w-2xl min-h-[60vh]
          rounded-2xl bg-white shadow-2xl shadow-black/15
          backdrop:bg-black/30 backdrop:backdrop-blur-md
          open:animate-in open:fade-in open:zoom-in-95
        "
        aria-label="Carrito de compras"
      >
        <div className="flex flex-col min-h-[60vh]">
          <div className="relative flex items-center justify-between px-6 h-16 border-b border-gray-100">
            <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-primary/80 to-primary/30" />
            <div className="flex items-center gap-3">
              <div className="relative">
                <ShoppingCart className="h-6 w-6 text-primary" strokeWidth={1.5} />
                {itemCount > 0 && (
                  <span className="absolute -top-2 -right-2.5 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary px-1 text-[11px] font-bold text-white shadow-sm shadow-primary/30">
                    {itemCount}
                  </span>
                )}
              </div>
              <span className="text-base font-semibold text-gray-900">Carrito</span>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex h-9 w-9 items-center justify-center rounded-xl text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
              aria-label="Cerrar carrito"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto bg-gray-50/50 grid">
            {items.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-5 px-8 text-center min-h-full">
                <div className="flex h-28 w-28 items-center justify-center rounded-full bg-primary/[0.04]">
                  <ShoppingCart className="h-12 w-12 text-primary/20" strokeWidth={1} />
                </div>
                <div className="space-y-2">
                  <p className="text-base font-semibold text-gray-900">Tu carrito está vacío</p>
                  <p className="text-sm text-gray-400 leading-relaxed max-w-[200px]">
                    Agregá productos del catálogo y volvé acá para finalizar tu pedido
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-4 space-y-3">
                {items.map((item) => (
                  <div
                    key={item.producto_id}
                    className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm transition-all duration-150 hover:shadow-md"
                  >
                    <div className="flex gap-4">
                      <div className="h-24 w-24 flex-shrink-0 rounded-xl bg-gray-50 overflow-hidden">
                        <ProductImage
                          src={item.imagen_url}
                          alt={item.nombre}
                          className="h-full w-full object-cover"
                          placeholder={
                            <div className="flex h-full w-full items-center justify-center">
                              <ShoppingCart className="h-8 w-8 text-gray-200" strokeWidth={1} />
                            </div>
                          }
                        />
                      </div>

                      <div className="flex-1 min-w-0 flex flex-col">
                        <p className="text-sm font-medium text-gray-900 leading-snug line-clamp-2">
                          {item.nombre}
                        </p>
                        <p className="mt-1 text-xs text-gray-400">
                          ${Number(item.precio).toFixed(2)} c/u
                        </p>
                        {item.personalizacion && (
                          <p className="mt-0.5 text-[11px] text-gray-400 italic truncate">
                            {item.personalizacion}
                          </p>
                        )}

                        <div className="mt-auto flex items-center justify-between pt-3">
                          <div className="flex items-center rounded-xl border border-gray-200 bg-gray-50 overflow-hidden">
                            <button
                              type="button"
                              onClick={() => updateQuantity(item.producto_id, item.cantidad - 1)}
                              className="flex h-9 w-10 items-center justify-center text-gray-500 hover:bg-white hover:text-gray-700 transition-colors"
                              aria-label={`Reducir cantidad de ${item.nombre}`}
                            >
                              <Minus className="h-4 w-4" strokeWidth={1.5} />
                            </button>
                            <span className="flex h-9 w-10 items-center justify-center text-sm font-semibold text-gray-900 bg-white border-x border-gray-200">
                              {item.cantidad}
                            </span>
                            <button
                              type="button"
                              onClick={() => updateQuantity(item.producto_id, item.cantidad + 1)}
                              className="flex h-9 w-10 items-center justify-center text-gray-500 hover:bg-white hover:text-gray-700 transition-colors"
                              aria-label={`Aumentar cantidad de ${item.nombre}`}
                            >
                              <Plus className="h-4 w-4" strokeWidth={1.5} />
                            </button>
                          </div>

                          <span className="text-sm font-bold text-gray-900">
                            ${(Number(item.precio) * item.cantidad).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 pt-3 border-t border-dashed border-gray-100 flex justify-end">
                      <button
                        type="button"
                        onClick={() => removeItem(item.producto_id)}
                        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" strokeWidth={1.5} />
                        Eliminar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {items.length > 0 && (
            <div className="bg-white border-t border-gray-100 px-6 py-4 space-y-3 shadow-[0_-8px_30px_-12px_rgba(0,0,0,0.15)]">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Total del pedido</span>
                <span className="text-2xl font-bold text-gray-900 tracking-tight">
                  ${total.toFixed(2)}
                </span>
              </div>
              <Button
                size="lg"
                onClick={handleCheckout}
                isLoading={isPending}
                className="w-full shadow-sm"
                rightIcon={!isPending ? <ShoppingCart className="h-4 w-4" /> : undefined}
              >
                {isPending ? 'Verificando...' : 'Ir al checkout'}
              </Button>
              <div className="flex justify-center">
                <button
                  type="button"
                  onClick={clearCart}
                  className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="h-3.5 w-3.5" strokeWidth={1.5} />
                  Vaciar carrito
                </button>
              </div>
            </div>
          )}
        </div>
      </dialog>

      {validationResult && (
        <CartValidationModal
          isOpen={validationResult !== null}
          onClose={() => setValidationResult(null)}
          result={validationResult}
        />
      )}
    </>
  );
}
