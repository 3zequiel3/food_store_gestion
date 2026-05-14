import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, ShoppingCart, Check, Tag, ChevronLeft, ChevronRight } from 'lucide-react';
import { useProduct } from '../../features/products/hooks/useProduct';
import { ProductImage } from '../../features/products/components/ProductImage';
import { useCartStore } from '../../features/cart/stores/cartStore';
import { NotFound } from '../errors/NotFound';
import { isAxiosError } from 'axios';
import type { ImagenRead } from '../../features/products/types/products.types';

/**
 * ProductDetailPage — página de detalle de un producto.
 *
 * 6.1: useParams obtiene el :id del router y llama useProduct(Number(id)).
 * 6.2: Renderiza imagen grande, nombre, descripción, precio, badge disponibilidad,
 *      chips de categorías, lista de ingredientes con alerta de alérgenos no-removibles.
 * 6.3: Selector de cantidad + botón "Agregar al carrito".
 * 6.4: Link "← Volver al catálogo" con useNavigate(-1) o fallback.
 * 6.5: Error 404 → NotFound.
 * 8.1: Image carousel with thumbnails for products with multiple images.
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

  // 8.1 — Carousel state
  const [activeImageIndex, setActiveImageIndex] = useState(0);

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

  // 8.1 — Get sorted images and determine active image
  const sortedImages = [...(producto.imagenes ?? [])].sort((a, b) => a.orden - b.orden);
  const hasMultipleImages = sortedImages.length > 1;
  const hasImages = sortedImages.length > 0;

  // Determine which image to show: primary first, then by orden
  function getInitialImageIndex(images: ImagenRead[]): number {
    if (images.length === 0) return -1;
    const primaryIdx = images.findIndex((img) => img.es_primaria);
    return primaryIdx >= 0 ? primaryIdx : 0;
  }

  // Reset active index when product changes
  const initialImageIdx = getInitialImageIndex(sortedImages);

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
        personalizacionIds: excluidos.size > 0 ? Array.from(excluidos) : undefined,
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

  // 8.1 — Carousel navigation
  function goToImage(index: number) {
    setActiveImageIndex(index);
  }

  function goNext() {
    setActiveImageIndex((prev) => (prev + 1) % sortedImages.length);
  }

  function goPrev() {
    setActiveImageIndex((prev) => (prev - 1 + sortedImages.length) % sortedImages.length);
  }

  // Current display image
  const displayImage = hasImages ? sortedImages[activeImageIndex >= 0 ? activeImageIndex : initialImageIdx] : null;

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
        {/* 8.1 — Image area (carousel or single image) */}
        <div className="flex flex-col gap-3">
          <div className="relative aspect-square w-full rounded-xl bg-muted overflow-hidden flex items-center justify-center">
            {hasImages && displayImage ? (
              <>
                <div data-testid="main-image" className="w-full h-full">
                  <ProductImage
                    src={displayImage.url}
                    alt={producto.nombre}
                    className="w-full h-full object-cover"
                    loading="eager"
                    placeholder={<span className="text-muted-foreground/30 text-6xl">🍽</span>}
                  />
                </div>
                {/* Carousel navigation arrows (only when multiple images) */}
                {hasMultipleImages && (
                  <>
                    <button
                      type="button"
                      onClick={goPrev}
                      className="absolute left-2 top-1/2 -translate-y-1/2 p-1.5 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors"
                      aria-label="Imagen anterior"
                    >
                      <ChevronLeft className="h-5 w-5" />
                    </button>
                    <button
                      type="button"
                      onClick={goNext}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors"
                      aria-label="Imagen siguiente"
                    >
                      <ChevronRight className="h-5 w-5" />
                    </button>
                  </>
                )}
              </>
            ) : (
              <span data-testid="image-placeholder" className="text-muted-foreground/30 text-6xl">🍽</span>
            )}
          </div>

          {/* 8.1 — Thumbnail strip (only when multiple images) */}
          {hasMultipleImages && (
            <div data-testid="thumbnail-strip" className="flex gap-2 overflow-x-auto">
              {sortedImages.map((img, idx) => (
                <button
                  key={img.id}
                  data-testid="thumbnail-item"
                  type="button"
                  onClick={() => goToImage(idx)}
                  className={`flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border-2 transition-all ${
                    idx === activeImageIndex
                      ? 'border-primary ring-2 ring-primary/20'
                      : 'border-border hover:border-primary/40'
                  }`}
                >
                  <img
                    src={img.url}
                    alt={`Thumbnail ${idx + 1}`}
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
            </div>
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
              <span className="inline-flex items-center rounded-full bg-success/10 px-2.5 py-1 text-xs font-semibold text-success">
                Disponible
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full bg-destructive/10 px-2.5 py-1 text-xs font-semibold text-destructive">
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
                      <span className="inline-flex items-center gap-1 rounded-full bg-warning/15 px-2 py-0.5 text-xs font-medium text-warning">
                        Alérgeno
                      </span>
                    )}
                    {esAlergenoNoRemovible && (
                      <span title="Alérgeno no removible" className="text-warning">
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

function ProductDetailSkeleton() {
  const shimmer = 'animate-shimmer bg-[length:200%_100%] bg-gradient-to-r from-muted/50 via-muted to-muted/50';
  return (
    <div className="max-w-4xl mx-auto w-full p-4 sm:p-6">
      <div className={`h-5 w-32 rounded-md ${shimmer} mb-6`} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className={`aspect-square w-full rounded-xl ${shimmer}`} />
        <div className="flex flex-col gap-4">
          <div className={`h-8 w-3/4 rounded-md ${shimmer}`} />
          <div className={`h-10 w-1/3 rounded-md ${shimmer}`} />
          <div className={`h-5 w-1/4 rounded-full ${shimmer}`} />
          <div className={`h-20 w-full rounded-md ${shimmer}`} />
          <div className={`h-12 w-full rounded-md ${shimmer} mt-4`} />
        </div>
      </div>
    </div>
  );
}
