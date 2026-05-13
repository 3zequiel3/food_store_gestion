import { useQuery } from '@tanstack/react-query';
import { getLeafCategories } from '../../categories/services/categories.service';

/**
 * Hook para el listado de categorías hoja.
 *
 * D3: staleTime de 5 minutos — las categorías cambian raramente.
 * Se usa en CategoryFilter para poblar el dropdown.
 */
export function useLeafCategories() {
  return useQuery({
    queryKey: ['categories', 'leaves'],
    queryFn: getLeafCategories,
    staleTime: 5 * 60_000,
  });
}
