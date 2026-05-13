import { useQuery } from '@tanstack/react-query';
import { getAllergenIngredients } from '../services/ingredients.service';

/**
 * Hook para el listado de ingredientes alérgenos.
 *
 * staleTime de 5 minutos — el catálogo de alérgenos es estable.
 * Se usa en AllergenFilter para el multi-select de exclusión.
 */
export function useAllergenIngredients() {
  return useQuery({
    queryKey: ['ingredients', 'allergens'],
    queryFn: getAllergenIngredients,
    staleTime: 5 * 60_000,
  });
}
