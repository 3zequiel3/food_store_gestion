import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShoppingCart, Check } from 'lucide-react';
import { useCartStore } from '../../cart/stores/cartStore';
import type { ProductoRead } from '../types/products.types';

interface ProductCardProps {
  producto: ProductoRead;
}

export function ProductCard({ producto }: ProductCardProps) {
  const navigate = useNavigate();
  const [added, setAdded] = useState(false);

  const sinStock = !producto.disponible || producto.stock_cantidad === 0;

  function handleNavigate() {
    navigate(`/cliente/catalogo/${producto.id}`);
  }

  function handleAgregar(e: React.MouseEvent) {
    e.stopPropagation();
    if (sinStock) return;

    useCartStore.getState().addItem(
      {
        producto_id: producto.id,
        nombre: producto.nombre,
        precio: Number(producto.precio),
        imagen_url: producto.imagen_url ?? undefined,
      },
      1,
    );

    setAdded(true);
    setTimeout(() => setAdded(false), 1000);
  }

  const precio = new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
  }).format(producto.precio);

  return (
    <div
      className="group flex flex-col rounded-xl bg-glass backdrop-blur-xl border border-glass-border overflow-hidden cursor-pointer hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
      onClick={handleNavigate}
      role="link"
      aria-label={`Ver detalle de ${producto.nombre}`}
    >
      <div className="aspect-square w-full bg-muted flex items-center justify-center overflow-hidden relative">
        {producto.imagen_url ? (
          <img
            src={producto.imagen_url}
            alt={producto.nombre}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <FoodPlaceholder />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-glass to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
      </div>

      <div className="flex flex-col gap-2 p-4 flex-1">
        <h3 className="text-sm font-semibold text-foreground line-clamp-2 leading-snug">
          {producto.nombre}
        </h3>
        <p className="text-lg font-bold text-primary tracking-tight">{precio}</p>

        <div className="mt-auto pt-2">
          <button
            type="button"
            onClick={handleAgregar}
            disabled={sinStock}
            title={sinStock ? 'Sin stock' : 'Agregar al carrito'}
            aria-label={sinStock ? 'Sin stock' : `Agregar ${producto.nombre} al carrito`}
            className="w-full flex items-center justify-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150
              bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm shadow-primary/20
              disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary"
          >
            {added ? (
              <>
                <Check className="h-4 w-4" />
                Agregado
              </>
            ) : (
              <>
                <ShoppingCart className="h-4 w-4" />
                {sinStock ? 'Sin stock' : 'Agregar'}
              </>
            )}
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
      className="h-16 w-16 text-muted-foreground/40"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M32 8a24 24 0 1 0 0 48A24 24 0 0 0 32 8zm0 4a20 20 0 1 1 0 40A20 20 0 0 1 32 12zM20 28h4v8h-4zm10 0h4v8h-4zm10 0h4v8h-4z" />
    </svg>
  );
}
