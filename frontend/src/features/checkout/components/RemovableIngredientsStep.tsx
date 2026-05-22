/**
 * RemovableIngredientsStep — P1.6
 *
 * Pre-checkout review step that lets the client toggle removable ingredients
 * per cart item before confirming. Non-removable ingredients are shown as fixed.
 *
 * Props:
 *   cartItems           — items currently in the cart
 *   exclusions          — map of { [producto_id]: Set<ingrediente_id> } (excluded IDs)
 *   onExclusionsChange  — called with (producto_id, newSet) when a toggle changes
 */

import { useQueries } from '@tanstack/react-query';
import type { CartItem } from '../../cart/types/cart.types';
import { getProduct } from '../../products/services/products.service';
import type { IngredienteAsociadoRead } from '../../products/types/products.types';

interface Props {
  cartItems: Array<Pick<CartItem, 'producto_id' | 'nombre' | 'precio' | 'cantidad'>>;
  exclusions: Record<number, Set<number>>;
  onExclusionsChange: (productoId: number, newExclusions: Set<number>) => void;
}

export function RemovableIngredientsStep({ cartItems, exclusions, onExclusionsChange }: Props) {
  // Fetch all product details in parallel.
  const productQueries = useQueries({
    queries: cartItems.map((item) => ({
      queryKey: ['product-detail', item.producto_id],
      queryFn: () => getProduct(item.producto_id),
      staleTime: 60_000,
    })),
  });

  return (
    <div className="space-y-4">
      {cartItems.map((item, idx) => {
        const query = productQueries[idx];
        const ingredientes: IngredienteAsociadoRead[] = query.data?.ingredientes ?? [];
        const removable = ingredientes.filter((i) => i.es_removible);
        const fixed = ingredientes.filter((i) => !i.es_removible);
        const excluded = exclusions[item.producto_id] ?? new Set<number>();

        function toggle(ingredienteId: number) {
          const next = new Set(excluded);
          if (next.has(ingredienteId)) {
            next.delete(ingredienteId);
          } else {
            next.add(ingredienteId);
          }
          onExclusionsChange(item.producto_id, next);
        }

        return (
          <div
            key={item.producto_id}
            className="rounded-xl bg-glass border border-glass-border overflow-hidden"
          >
            {/* Item header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-glass-border bg-glass/30">
              <span className="text-sm font-semibold text-foreground">{item.nombre}</span>
              <span className="text-xs text-muted-foreground">×{item.cantidad}</span>
            </div>

            <div className="px-4 py-3 space-y-2">
              {query.isLoading && (
                <p className="text-xs text-muted-foreground animate-pulse">
                  Cargando ingredientes…
                </p>
              )}

              {query.isError && (
                <p className="text-xs text-destructive">
                  Error al cargar ingredientes.
                </p>
              )}

              {query.isSuccess && removable.length === 0 && (
                <p className="text-xs text-muted-foreground italic">
                  No hay ingredientes removibles para este producto.
                </p>
              )}

              {/* Removable — shown as toggles */}
              {removable.length > 0 && (
                <ul className="space-y-1.5">
                  {removable.map((ing) => {
                    const isExcluded = excluded.has(ing.id);
                    return (
                      <li key={ing.id} className="flex items-center gap-3">
                        <input
                          id={`ck-${item.producto_id}-${ing.id}`}
                          type="checkbox"
                          checked={!isExcluded}
                          onChange={() => toggle(ing.id)}
                          className="h-4 w-4 rounded border-input accent-primary cursor-pointer"
                          aria-label={ing.nombre}
                        />
                        <label
                          htmlFor={`ck-${item.producto_id}-${ing.id}`}
                          className={`text-sm cursor-pointer select-none ${
                            isExcluded ? 'line-through text-muted-foreground' : 'text-foreground'
                          }`}
                        >
                          {ing.nombre}
                          {ing.es_alergeno && (
                            <span className="ml-1.5 text-xs text-warning font-medium">
                              (alérgeno)
                            </span>
                          )}
                        </label>
                      </li>
                    );
                  })}
                </ul>
              )}

              {/* Non-removable — shown as fixed text */}
              {fixed.length > 0 && (
                <ul className="space-y-1 mt-2 pt-2 border-t border-glass-border/50">
                  {fixed.map((ing) => (
                    <li
                      key={ing.id}
                      className="flex items-center gap-3 text-muted-foreground"
                    >
                      {/* Spacer to align with checkboxes */}
                      <span className="h-4 w-4 flex-shrink-0" aria-hidden />
                      <span className="text-sm">
                        {ing.nombre}
                        {ing.es_alergeno && (
                          <span className="ml-1.5 text-xs text-warning font-medium">
                            (alérgeno)
                          </span>
                        )}
                        <span className="ml-1.5 text-xs opacity-50">(fijo)</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
