import { useSearchParams } from 'react-router-dom';
import { X } from 'lucide-react';
import { useLeafCategories } from '../../hooks/useLeafCategories';
import { useAllergenIngredients } from '../../../ingredients/hooks/useAllergenIngredients';

export function ActiveFilterChips() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: categories } = useLeafCategories();
  const { data: allergens } = useAllergenIngredients();

  const search = searchParams.get('search');
  const categoriaId = searchParams.get('categoria_id');
  const excluirAlergenos = searchParams.get('excluir_alergenos') === 'true';
  const excluirIds = searchParams.getAll('excluir_alergeno_ids').map(Number);

  const hasFilters =
    !!search || !!categoriaId || excluirAlergenos || excluirIds.length > 0;

  if (!hasFilters) return null;

  function removeFilter(key: string, value?: string) {
    setSearchParams((prev) => {
      const updated = new URLSearchParams(prev);
      if (key === 'excluir_alergeno_ids' && value != null) {
        const current = updated.getAll('excluir_alergeno_ids');
        updated.delete('excluir_alergeno_ids');
        for (const id of current) {
          if (id !== value) updated.append('excluir_alergeno_ids', id);
        }
      } else {
        updated.delete(key);
      }
      updated.set('page', '1');
      return updated;
    });
  }

  function clearAll() {
    setSearchParams({ page: '1' });
  }

  const categoriaLabel =
    categoriaId && categories
      ? (categories.find((c) => String(c.id) === categoriaId)?.nombre ?? `Categoría ${categoriaId}`)
      : null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {search && (
        <Chip label={`Búsqueda: ${search}`} onRemove={() => removeFilter('search')} />
      )}

      {categoriaId && categoriaLabel && (
        <Chip label={`Categoría: ${categoriaLabel}`} onRemove={() => removeFilter('categoria_id')} />
      )}

      {excluirAlergenos && (
        <Chip label="Sin alérgenos" onRemove={() => removeFilter('excluir_alergenos')} />
      )}

      {excluirIds.map((id) => {
        const nombre = allergens?.find((a) => a.id === id)?.nombre ?? `Alérgeno ${id}`;
        return (
          <Chip
            key={id}
            label={`Sin: ${nombre}`}
            onRemove={() => removeFilter('excluir_alergeno_ids', String(id))}
          />
        );
      })}

      <button
        type="button"
        onClick={clearAll}
        className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2 ml-1 transition-colors"
      >
        Limpiar todo
      </button>
    </div>
  );
}

interface ChipProps {
  label: string;
  onRemove: () => void;
}

function Chip({ label, onRemove }: ChipProps) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 backdrop-blur-sm px-3 py-1 text-xs font-medium text-primary border border-primary/20">
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Quitar filtro: ${label}`}
        className="ml-0.5 flex items-center justify-center rounded-full hover:bg-primary/20 p-0.5 transition-colors"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}
