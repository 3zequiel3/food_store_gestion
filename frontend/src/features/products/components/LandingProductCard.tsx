import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { ProductImage } from './ProductImage';
import { useAuthStore } from '../../../features/auth/stores/authStore';
import type { ProductoRead } from '../types/products.types';

interface LandingProductCardProps {
  producto: ProductoRead;
}

export function LandingProductCard({ producto }: LandingProductCardProps) {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());

  const precio = new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
  }).format(producto.precio);

  const descripcion = producto.descripcion
    ? producto.descripcion.length > 80
      ? `${producto.descripcion.slice(0, 80)}...`
      : producto.descripcion
    : '';

  function handleVerMas() {
    if (isAuthenticated) {
      navigate(`/cliente/catalogo/${producto.id}`);
    } else {
      navigate('/login');
    }
  }

  return (
    <div className="flex flex-col rounded-xl bg-glass backdrop-blur-xl border border-glass-border overflow-hidden hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
      <div className="aspect-square w-full bg-muted overflow-hidden">
        <ProductImage
          src={producto.imagenes?.[0]?.url ?? producto.imagen_url}
          alt={producto.nombre}
          className="w-full h-full object-cover"
          placeholder={<FoodPlaceholder />}
        />
      </div>

      <div className="flex flex-col gap-2 p-4 flex-1">
        <h3 className="text-sm font-semibold text-foreground line-clamp-2 leading-snug">
          {producto.nombre}
        </h3>

        {descripcion && (
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {descripcion}
          </p>
        )}

        <p className="text-lg font-bold text-primary tracking-tight">{precio}</p>

        <div className="mt-auto pt-2">
          <button
            type="button"
            onClick={handleVerMas}
            className="w-full flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150
              bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm shadow-primary/20"
          >
            Ver m&aacute;s
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function FoodPlaceholder() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      className="h-16 w-16 text-muted-foreground/40 mx-auto mt-8"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M32 8a24 24 0 1 0 0 48A24 24 0 0 0 32 8zm0 4a20 20 0 1 1 0 40A20 20 0 0 1 32 12zM20 28h4v8h-4zm10 0h4v8h-4zm10 0h4v8h-4z" />
    </svg>
  );
}
