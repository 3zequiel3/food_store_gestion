import { useQuery } from '@tanstack/react-query';
import { getIngredientes } from '../services/ingredientes.service';

export function useIngredientes(page = 1, limit = 20) {
  return useQuery({
    queryKey: ['ingredientes', page, limit],
    queryFn: () => getIngredientes(page, limit),
    staleTime: 30_000,
  });
}
