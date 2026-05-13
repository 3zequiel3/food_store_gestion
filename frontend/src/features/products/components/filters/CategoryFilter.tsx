import { useSearchParams } from 'react-router-dom';
import { useLeafCategories } from '../../hooks/useLeafCategories';

/**
 * CategoryFilter — dropdown de categorías hoja.
 *
 * Poblado via `useLeafCategories()` (staleTime 5 min).
 * Al cambiar, actualiza `categoria_id` en la URL y resetea `page=1`.
 * Primera opción = "Todas las categorías" (sin filtro).
 */
export function CategoryFilter() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: categories, isLoading } = useLeafCategories();

  const selectedId = searchParams.get('categoria_id') ?? '';

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value;
    setSearchParams((prev) => {
      const updated = new URLSearchParams(prev);
      if (val) {
        updated.set('categoria_id', val);
      } else {
        updated.delete('categoria_id');
      }
      updated.set('page', '1');
      return updated;
    });
  }

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="categoria-filter" className="text-sm font-medium text-foreground">
        Categoría
      </label>
      <select
        id="categoria-filter"
        value={selectedId}
        onChange={handleChange}
        disabled={isLoading}
        className="rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
      >
        <option value="">Todas las categorías</option>
        {categories?.map((cat) => (
          <option key={cat.id} value={String(cat.id)}>
            {cat.nombre}
          </option>
        ))}
      </select>
    </div>
  );
}
