import type { IngredienteAsignado } from '../types/ingredientes.types';

export type IngredientChange =
  | { type: 'add'; ingrediente: IngredienteAsignado }
  | { type: 'remove'; ingrediente: IngredienteAsignado }
  | { type: 'update'; before: IngredienteAsignado; after: IngredienteAsignado };

/**
 * Diff two ingredient lists and return the sequence of changes needed.
 * - Added: in current but not in original
 * - Removed: in original but not in current
 * - Updated: same id, different es_removible (requires DELETE then POST)
 */
export function diffIngredientes(
  original: IngredienteAsignado[],
  current: IngredienteAsignado[],
): IngredientChange[] {
  const originalMap = new Map(original.map((ing) => [ing.id, ing]));
  const currentMap = new Map(current.map((ing) => [ing.id, ing]));

  const changes: IngredientChange[] = [];

  // Removed: in original but not in current
  for (const ing of original) {
    if (!currentMap.has(ing.id)) {
      changes.push({ type: 'remove', ingrediente: ing });
    }
  }

  // Added: in current but not in original
  for (const ing of current) {
    if (!originalMap.has(ing.id)) {
      changes.push({ type: 'add', ingrediente: ing });
    }
  }

  // Updated: same id, different es_removible
  for (const ing of current) {
    const orig = originalMap.get(ing.id);
    if (orig && orig.es_removible !== ing.es_removible) {
      changes.push({ type: 'update', before: orig, after: ing });
    }
  }

  return changes;
}
