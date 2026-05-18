import { Button } from '../../../components/ui/Button';
import { useProducts } from '../../../features/products/hooks/useProducts';
import { LandingProductCard } from '../../../features/products/components/LandingProductCard';
import { ProductCardSkeleton } from '../../../features/products/components/ProductCardSkeleton';
import { useInViewAnimation } from '../hooks/useInViewAnimation';

export function FeaturedProductsSection() {
  const { data, isLoading, isError, refetch } = useProducts({
    disponible: true,
    limit: 8,
  });
  const { ref, isInView } = useInViewAnimation();

  const productos = data?.items ?? [];

  if (isLoading) {
    return (
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-10 text-center">
            Productos destacados
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <ProductCardSkeleton key={i} />
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (isError) {
    return (
      <section className="py-24 px-4 sm:px-6 lg:px-8 text-center">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Productos destacados
          </h2>
          <p className="text-muted-foreground mb-4">
            No se pudieron cargar los productos.
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            Reintentar
          </Button>
        </div>
      </section>
    );
  }

  if (productos.length === 0) {
    return (
      <section className="py-24 px-4 sm:px-6 lg:px-8 text-center">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Productos destacados
          </h2>
          <p className="text-muted-foreground">
            A&uacute;n no hay productos disponibles.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section
      ref={ref as React.RefCallback<HTMLElement>}
      className={`py-24 px-4 sm:px-6 lg:px-8 transition-all duration-700 ${
        isInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
    >
      <div className="max-w-7xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-10 text-center">
          Productos destacados
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {productos.map((producto, index) => (
            <div
              key={producto.id}
              style={{ animationDelay: `${index * 80}ms` }}
            >
              <LandingProductCard producto={producto} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
