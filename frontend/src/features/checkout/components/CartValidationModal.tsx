import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, TrendingUp } from 'lucide-react';
import { useCartStore } from '../../cart/stores/cartStore';
import type { ValidationResult } from '../types/validation.types';

interface CartValidationModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: ValidationResult;
}

export function CartValidationModal({ isOpen, onClose, result }: CartValidationModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const navigate = useNavigate();
  const updateItemPrice = useCartStore((s) => s.updateItemPrice);

  const hasStockIssues = result.stockIssues.length > 0;
  const hasPriceChanges = result.priceChanges.length > 0;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen) dialog.showModal();
    else dialog.close();
  }, [isOpen]);

  function handleBackdropClick(e: React.MouseEvent<HTMLDialogElement>) {
    if (e.target === dialogRef.current) onClose();
  }

  function handleUpdateAndContinue() {
    for (const change of result.priceChanges) {
      updateItemPrice(change.producto_id, change.precioNuevo);
    }
    onClose();
    navigate('/cliente/checkout');
  }

  return (
    <dialog
      ref={dialogRef}
      onClick={handleBackdropClick}
      onClose={onClose}
      className="rounded-xl border border-border bg-card p-0 shadow-xl backdrop:bg-black/50 backdrop:backdrop-blur-sm w-full max-w-md mx-auto"
    >
      <div className="flex flex-col gap-0">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-border px-6 py-4">
          {hasStockIssues ? (
            <AlertTriangle className="h-5 w-5 text-destructive flex-shrink-0" />
          ) : (
            <TrendingUp className="h-5 w-5 text-amber-500 flex-shrink-0" />
          )}
          <h2 className="font-semibold text-foreground">
            {hasStockIssues ? 'Productos sin stock suficiente' : 'Cambios de precio'}
          </h2>
        </div>

        {/* Body */}
        <div className="px-6 py-4 flex flex-col gap-4">
          {hasStockIssues && (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-muted-foreground">
                Los siguientes productos no tienen el stock que necesitás. Ajustá el carrito antes de continuar.
              </p>
              <ul className="divide-y divide-border rounded-lg border border-border overflow-hidden">
                {result.stockIssues.map((issue) => (
                  <li key={issue.producto_id} className="flex items-center justify-between px-4 py-3 bg-background">
                    <span className="text-sm font-medium text-foreground truncate">{issue.nombre}</span>
                    <span className="text-xs text-destructive font-medium ml-4 flex-shrink-0">
                      {issue.disponible ? `Stock disponible: ${issue.stockDisponible}` : 'Sin stock'}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!hasStockIssues && hasPriceChanges && (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-muted-foreground">
                Los precios de estos productos cambiaron. Podés actualizar y continuar o volver al carrito.
              </p>
              <ul className="divide-y divide-border rounded-lg border border-border overflow-hidden">
                {result.priceChanges.map((change) => (
                  <li key={change.producto_id} className="flex items-center justify-between px-4 py-3 bg-background">
                    <span className="text-sm font-medium text-foreground truncate">{change.nombre}</span>
                    <span className="text-xs text-muted-foreground ml-4 flex-shrink-0">
                      <span className="line-through">${change.precioAnterior.toFixed(2)}</span>
                      {' → '}
                      <span className="text-foreground font-semibold">${change.precioNuevo.toFixed(2)}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-2 border-t border-border px-6 py-4 justify-end">
          {hasStockIssues ? (
            <button
              type="button"
              onClick={onClose}
              className="h-10 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Entendido
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={onClose}
                className="h-10 rounded-lg border border-border px-4 text-sm font-medium text-foreground hover:bg-accent transition-colors"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleUpdateAndContinue}
                className="h-10 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Actualizar precios y continuar
              </button>
            </>
          )}
        </div>
      </div>
    </dialog>
  );
}
