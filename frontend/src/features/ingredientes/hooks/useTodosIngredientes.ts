import { useQuery } from '@tanstack/react-query';
import { getTodosIngredientes } from '../services/ingredientes.service';

export function useTodosIngredientes() {
  return useQuery({
    queryKey: ['ingredientes', 'todos'],
    queryFn: getTodosIngredientes,
    staleTime: 60_000,
  });
}
