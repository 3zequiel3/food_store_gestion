import { useEffect } from 'react';
import { Trash2, X, Loader2 } from 'lucide-react';
import { useDeleteProduct } from '../../hooks/useDeleteProduct';
import type { ProductoRead } from '../../types/products.types';

interface DeleteProductModalProps {
  product: ProductoRead;
  onClose: () => void;
}

export function DeleteProductModal({ product, onClose }: DeleteProductModalProps) {
  const { mutate, isPending } = useDeleteProduct(onClose);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-card border border-border rounded-lg w-full max-w-sm p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            <h2 className="text-lg font-semibold">Eliminar producto</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-accent text-muted-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="text-sm text-muted-foreground mb-1">
          ¿Estás seguro de que querés eliminar?
        </p>
        <p className="text-sm font-semibold text-foreground mb-5">"{product.nombre}"</p>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2 text-sm border border-border rounded-lg hover:bg-accent transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => mutate(product.id)}
            disabled={isPending}
            className="flex-1 px-4 py-2 text-sm bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Eliminando...
              </>
            ) : 'Eliminar'}
          </button>
        </div>
      </div>
    </div>
  );
}
