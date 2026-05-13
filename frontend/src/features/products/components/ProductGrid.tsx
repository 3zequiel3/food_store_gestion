import { PackageSearch } from 'lucide-react';
import { ProductCard } from './ProductCard';
import { ProductCardSkeleton } from './ProductCardSkeleton';
import type { ProductoRead } from '../types/products.types';

interface ProductGridProps {
  products: ProductoRead[];
  isLoading: boolean;
  isEmpty: boolean;
}

export function ProductGrid({ products, isLoading, isEmpty }: ProductGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
        {Array.from({ length: 12 }).map((_, i) => (
          <ProductCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-glass backdrop-blur-xl border border-glass-border">
          <PackageSearch className="h-8 w-8 text-muted-foreground/60" />
        </div>
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
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
      {products.map((producto) => (
        <ProductCard key={producto.id} producto={producto} />
      ))}
    </div>
  );
}
