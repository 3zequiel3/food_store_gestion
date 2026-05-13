import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, ShoppingCart, Check, Tag } from 'lucide-react';
import { useProduct } from '../../features/products/hooks/useProduct';
import { useCartStore } from '../../features/cart/stores/cartStore';
import { NotFound } from '../errors/NotFound';
import { isAxiosError } from 'axios';

/**
 * ProductDetailPage — página de detalle de un producto.
 *
 * 6.1: useParams obtiene el :id del router y llama useProduct(Number(id)).
 * 6.2: Renderiza imagen grande, nombre, descripción, precio, badge disponibilidad,
 *      chips de categorías, lista de ingredientes con alerta de alérgenos no-removibles.
 * 6.3: Selector de cantidad + botón "Agregar al carrito".
 * 6.4: Link "← Volver al catálogo" con useNavigate(-1) o fallback.
 * 6.5: Error 404 → NotFound.
 */
export function ProductDetailPage() {
  // 6.1 — Obtener id del router
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const productoId = Number(id);

  const { data: producto, isLoading, error } = useProduct(productoId);
  const [cantidad, setCantidad] = useState(1);
  const [added, setAdded] = useState(false);
  const [excluidos, setExcluidos] = useState<Set<number>>(new Set());

  function toggleExcluido(id: number) {
    setExcluidos((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // 6.4 — Volver al catálogo
  function handleBack() {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate('/cliente/catalogo');
    }
  }

  // 6.5 — Manejo de error 404
  if (error) {
    const is404 =
      isAxiosError(error) && error.response?.status === 404;
    if (is404) return <NotFound />;
    // Otro error: mensaje genérico
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-muted-foreground">Error al cargar el producto.</p>
      </div>
    );
  }

  // Loading state
  if (isLoading || !producto) {
    return <ProductDetailSkeleton />;
  }

  const sinStock = !producto.disponible || producto.stock_cantidad === 0;

  // 6.3 — Agregar al carrito
  function handleAgregar() {
    if (!producto || sinStock) return;

    const ingredientesRemovibles = producto.ingredientes?.filter((i) => i.es_removible) ?? [];
    const excluye = ingredientesRemovibles.filter((i) => excluidos.has(i.id));
    const personalizacion = excluye.length > 0
      ? excluye.map((i) => `sin ${i.nombre}`).join(', ')
      : undefined;

    useCartStore.getState().addItem(
      {
        producto_id: producto.id,
        nombre: producto.nombre,
        precio: Number(producto.precio),
        imagen_url: producto.imagen_url ?? undefined,
        personalizacion,
      },
      cantidad,
    );

    setAdded(true);
    setTimeout(() => setAdded(false), 1500);
  }

  const precio = new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
  }).format(producto.precio);

  return (
    <div className="max-w-4xl mx-auto w-full p-4 sm:p-6">
      {/* 6.4 — Volver */}
      <button
        type="button"
        onClick={handleBack}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Volver al catálogo
      </button>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Imagen grande */}
        <div className="aspect-square w-full rounded-xl bg-muted overflow-hidden flex items-center justify-center">
          {producto.imagen_url ? (
            <img
              src={producto.imagen_url}
              alt={producto.nombre}
              className="w-full h-full object-cover"
            />
          ) : (
            <span className="text-muted-foreground/30 text-6xl">🍽</span>
          )}
        </div>

        {/* Info + acciones */}
        <div className="flex flex-col gap-4">
          {/* Nombre */}
          <h1 className="text-2xl font-bold text-foreground">{producto.nombre}</h1>

          {/* Precio */}
          <p className="text-3xl font-bold text-primary">{precio}</p>

          {/* Badge disponibilidad */}
          <div>
            {producto.disponible && producto.stock_cantidad > 0 ? (
              <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-800 dark:bg-green-900/30 dark:text-green-400">
                Disponible
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-800 dark:bg-red-900/30 dark:text-red-400">
                Sin stock
              </span>
            )}
          </div>

          {/* Descripción */}
          <p className="text-sm text-muted-foreground leading-relaxed">
            {producto.descripcion ?? 'Sin descripción.'}
          </p>

          {/* Categorías */}
          {producto.categorias && producto.categorias.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {producto.categorias.map((cat) => (
                <span
                  key={cat.id}
                  className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-xs text-foreground"
                >
                  <Tag className="h-3 w-3 text-muted-foreground" />
                  {cat.nombre}
                </span>
              ))}
            </div>
          )}

          {/* 6.3 — Selector de cantidad + botón */}
          <div className="flex flex-col gap-3 pt-2">
            <div className="flex items-center gap-3">
              <label htmlFor="cantidad" className="text-sm font-medium text-foreground">
                Cantidad
              </label>
              <input
                id="cantidad"
                type="number"
                min={1}
                max={producto.stock_cantidad || 1}
                value={cantidad}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  if (!isNaN(val) && val >= 1) {
                    setCantidad(Math.min(val, producto.stock_cantidad || 1));
                  }
                }}
                disabled={sinStock}
                className="w-20 rounded-md border border-input bg-background px-3 py-2 text-sm text-center text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              />
            </div>

            <button
              type="button"
              onClick={handleAgregar}
              disabled={sinStock}
              className="flex items-center justify-center gap-2 rounded-md px-6 py-3 text-base font-medium
                bg-primary text-primary-foreground hover:bg-primary/90 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {added ? (
                <>
                  <Check className="h-5 w-5" />
                  Agregado al carrito
                </>
              ) : (
                <>
                  <ShoppingCart className="h-5 w-5" />
                  {sinStock ? 'Sin stock' : 'Agregar al carrito'}
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 6.2 — Ingredientes */}
      {producto.ingredientes && producto.ingredientes.length > 0 && (
        <div className="mt-10">
          <div className="flex items-baseline gap-2 mb-4">
            <h2 className="text-lg font-semibold text-foreground">Ingredientes</h2>
            {producto.ingredientes.some((i) => i.es_removible) && (
              <span className="text-xs text-muted-foreground">Desmarcá los que no querés</span>
            )}
          </div>
          <ul className="divide-y divide-border rounded-xl border border-border overflow-hidden">
            {producto.ingredientes.map((ing) => {
              const esAlergenoNoRemovible = ing.es_alergeno && !ing.es_removible;
              return (
                <li
                  key={ing.id}
                  className="flex items-center justify-between px-4 py-3 bg-card"
                >
                  <div className="flex items-center gap-3">
                    {ing.es_removible ? (
                      <input
                        type="checkbox"
                        id={`ing-${ing.id}`}
                        checked={!excluidos.has(ing.id)}
                        onChange={() => toggleExcluido(ing.id)}
                        disabled={sinStock}
                        className="h-4 w-4 rounded border-input accent-primary cursor-pointer"
                        aria-label={`Incluir ${ing.nombre}`}
                      />
                    ) : (
                      <div className="h-4 w-4 flex-shrink-0" />
                    )}
                    <label
                      htmlFor={ing.es_removible ? `ing-${ing.id}` : undefined}
                      className={`text-sm ${ing.es_removible ? 'cursor-pointer select-none' : ''} ${excluidos.has(ing.id) ? 'line-through text-muted-foreground' : 'text-foreground'}`}
                    >
                      {ing.nombre}
                    </label>
                  </div>
                  <div className="flex items-center gap-2">
                    {ing.es_alergeno && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-400">
                        Alérgeno
                      </span>
                    )}
                    {esAlergenoNoRemovible && (
                      <span title="Alérgeno no removible" className="text-amber-600 dark:text-amber-400">
                        <AlertTriangle className="h-4 w-4" aria-label="Alérgeno no removible" />
                      </span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Skeleton para el detalle mientras carga */
function ProductDetailSkeleton() {
  return (
    <div className="max-w-4xl mx-auto w-full p-4 sm:p-6 animate-pulse">
      <div className="h-5 w-32 rounded-md bg-muted mb-6" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="aspect-square w-full rounded-xl bg-muted" />
        <div className="flex flex-col gap-4">
          <div className="h-8 w-3/4 rounded-md bg-muted" />
          <div className="h-10 w-1/3 rounded-md bg-muted" />
          <div className="h-5 w-1/4 rounded-full bg-muted" />
          <div className="h-20 w-full rounded-md bg-muted" />
          <div className="h-12 w-full rounded-md bg-muted mt-4" />
        </div>
      </div>
    </div>
  );
}
