/**
 * ProductCardSkeleton — placeholder animado durante la carga inicial.
 *
 * D9: imita la forma exacta de ProductCard (imagen, 2 líneas de texto, botón).
 * Se renderizan 12 instancias de este componente mientras isLoading === true.
 */
export function ProductCardSkeleton() {
  return (
    <div className="flex flex-col rounded-xl border border-border bg-card overflow-hidden animate-pulse">
      {/* Imagen placeholder */}
      <div className="aspect-square w-full bg-muted" />

      <div className="flex flex-col gap-3 p-4">
        {/* Nombre */}
        <div className="h-4 w-3/4 rounded-md bg-muted" />
        {/* Precio */}
        <div className="h-4 w-1/3 rounded-md bg-muted" />
        {/* Botón */}
        <div className="h-9 w-full rounded-md bg-muted mt-1" />
      </div>
    </div>
  );
}
