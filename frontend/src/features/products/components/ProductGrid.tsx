import { PackageSearch } from 'lucide-react';
import { ProductCard } from './ProductCard';
import { ProductCardSkeleton } from './ProductCardSkeleton';
import type { ProductoRead } from '../types/products.types';

interface ProductGridProps {
  products: ProductoRead[];
  isLoading: boolean;
  isEmpty: boolean;
}

/**
 * ProductGrid — grid responsivo de productos.
 *
 * - Cargando: 12 ProductCardSkeleton (D9).
 * - Sin resultados: mensaje vacío.
 * - Con datos: grid de ProductCard (1 col → 2 en sm: → 3 en lg:).
 */
export function ProductGrid({ products, isLoading, isEmpty }: ProductGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <ProductCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
        <PackageSearch className="h-12 w-12 text-muted-foreground/50" />
        <div>
          <p className="text-base font-medium text-foreground">Sin resultados</p>
          <p className="text-sm text-muted-foreground mt-1">
            No se encontraron productos con estos filtros.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {products.map((producto) => (
        <ProductCard key={producto.id} producto={producto} />
      ))}
    </div>
  );
}
