import { useSearchParams } from 'react-router-dom';
import { useAllergenIngredients } from '../../../ingredients/hooks/useAllergenIngredients';

/**
 * AllergenFilter — D6:
 *   1. Checkbox `excluir_alergenos` (bool) — excluye todos los alérgenos no-removibles.
 *   2. Multi-select de ingredientes alérgenos — popula `excluir_alergeno_ids[]`.
 * Semántica AND (definida por el backend).
 */
export function AllergenFilter() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: allergens } = useAllergenIngredients();

  const excluirAlergenos = searchParams.get('excluir_alergenos') === 'true';
  const excluirIds = searchParams.getAll('excluir_alergeno_ids').map(Number);

  function handleExcluirAlergenosChange(e: React.ChangeEvent<HTMLInputElement>) {
    setSearchParams((prev) => {
      const updated = new URLSearchParams(prev);
      if (e.target.checked) {
        updated.set('excluir_alergenos', 'true');
      } else {
        updated.delete('excluir_alergenos');
      }
      updated.set('page', '1');
      return updated;
    });
  }

  function handleIngredienteToggle(id: number) {
    setSearchParams((prev) => {
      const updated = new URLSearchParams(prev);
      const current = updated.getAll('excluir_alergeno_ids').map(Number);
      // Eliminar todos los valores del param y reescribir
      updated.delete('excluir_alergeno_ids');
      const next = current.includes(id)
        ? current.filter((x) => x !== id)
        : [...current, id];
      for (const i of next) {
        updated.append('excluir_alergeno_ids', String(i));
      }
      updated.set('page', '1');
      return updated;
    });
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm font-medium text-foreground">Alérgenos</p>

      {/* Checkbox principal */}
      <label className="flex items-center gap-2 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={excluirAlergenos}
          onChange={handleExcluirAlergenosChange}
          className="h-4 w-4 rounded border-input accent-primary"
        />
        <span className="text-sm text-foreground">Excluir todos los alérgenos</span>
      </label>

      {/* Multi-select de ingredientes alérgenos */}
      {allergens && allergens.length > 0 && (
        <div className="flex flex-col gap-1.5 pl-2">
          <p className="text-xs text-muted-foreground">Excluir ingredientes específicos:</p>
          {allergens.map((ing) => (
            <label key={ing.id} className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={excluirIds.includes(ing.id)}
                onChange={() => handleIngredienteToggle(ing.id)}
                className="h-4 w-4 rounded border-input accent-primary"
              />
              <span className="text-sm text-foreground">{ing.nombre}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
