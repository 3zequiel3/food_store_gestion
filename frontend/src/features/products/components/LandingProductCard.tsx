import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { ProductImage } from './ProductImage';
import type { ProductoRead } from '../types/products.types';

interface LandingProductCardProps {
  producto: ProductoRead;
}

/** Days threshold to consider a product "new" */
const NUEVO_THRESHOLD_DAYS = 14;

function isNuevo(producto: ProductoRead): boolean {
  if (!producto.creado_en) return false;
  const createdAt = new Date(producto.creado_en);
  const diffMs = Date.now() - createdAt.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays < NUEVO_THRESHOLD_DAYS;
}

/** Badge pill displayed over the product image */
function ProductBadge({
  label,
  ariaLabel,
  className,
}: {
  label: string;
  ariaLabel: string;
  className: string;
}) {
  return (
    <span
      aria-label={ariaLabel}
      className={`absolute top-2 left-2 z-10 px-2 py-0.5 rounded-full text-xs font-semibold ${className}`}
    >
      {label}
    </span>
  );
}

export function LandingProductCard({ producto }: LandingProductCardProps) {
  const navigate = useNavigate();

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

  // D4 — Navigate always to product detail; catalog is public (no auth check needed).
  function handleVerMas() {
    navigate(`/cliente/catalogo/${producto.id}`);
  }

  const showNuevo = isNuevo(producto);
  const showSinStock = producto.disponible === false;

  return (
    <div className="group flex flex-col rounded-xl bg-glass backdrop-blur-xl border border-glass-border overflow-hidden
      hover:-translate-y-1 hover:shadow-xl transition-all duration-300">
      {/* Image with overlay and zoom */}
      <div className="relative aspect-square w-full bg-muted overflow-hidden">
        {/* Badges */}
        {showNuevo && (
          <ProductBadge
            label="Nuevo"
            ariaLabel="Producto nuevo"
            className="bg-success text-success-foreground"
          />
        )}
        {showSinStock && (
          <ProductBadge
            label="Sin stock"
            ariaLabel="Sin stock"
            className="bg-destructive text-destructive-foreground"
          />
        )}

        {/* Image with zoom on hover */}
        <div className="w-full h-full transition-transform duration-500 group-hover:scale-105">
          <ProductImage
            src={producto.imagenes?.[0]?.url ?? producto.imagen_url}
            alt={producto.nombre}
            className="w-full h-full object-cover"
            placeholder={<FoodPlaceholder />}
          />
        </div>

        {/* Hover overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent
          opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
          aria-hidden="true"
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
